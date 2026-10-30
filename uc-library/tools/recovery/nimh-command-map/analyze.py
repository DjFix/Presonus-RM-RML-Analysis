"""Offline NIMH startup/memory and protocol discovery. No device I/O."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import struct
from datetime import datetime, timezone

import capstone as cs
from capstone.arm import ARM_OP_MEM, ARM_OP_REG, ARM_OP_IMM, ARM_REG_PC
import unicorn as uc
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_LR


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root', type=Path)
    args = ap.parse_args()
    root = args.root.resolve()
    out = root/'evidence/recovery/2026-10-27/nimh-command-map'
    out.mkdir(parents=True, exist_ok=True)
    source = root/'evidence/recovery/2026-10-27/xmen-stm32'
    b = (source/'images/mixer-analysis/_ZL13nimh_arm_code.bin').read_bytes()
    assert len(b) == 216908 and sha(b) == 'b0979352e18a1093051fc6118a47694773cb9240e88087eca03aaa2ffe0f5e17'
    base = 0x08000000

    def save(name, data):
        (out/name).write_text(json.dumps(data, indent=2)+'\n')

    def readword(a):
        if base <= a <= base+len(b)-4:
            return struct.unpack_from('<I', b, a-base)[0]

    strings = [{'offset': m.start(), 'address': base+m.start(), 'text': m.group().decode()}
               for m in re.finditer(rb'[\x20-\x7e]{4,}', b)]
    save('strings.json', strings)
    (out/'strings.txt').write_text(''.join(f'{s["address"]:08x} {s["text"]}\n' for s in strings))
    decoder = cs.Cs(cs.CS_ARCH_ARM, cs.CS_MODE_THUMB | cs.CS_MODE_LITTLE_ENDIAN)
    decoder.detail = True
    decoder.skipdata = True
    instructions = [i for i in decoder.disasm(b[0x10:0x24260], base+0x10) if i.id]
    literal_refs = []
    for i in instructions:
        for op in i.operands:
            if op.type == ARM_OP_MEM and op.mem.base == ARM_REG_PC:
                a = ((i.address+4)&~3)+op.mem.disp
                value = readword(a)
                if value is not None:
                    literal_refs.append({'instruction': i.address, 'literal': a, 'value': value,
                                         'instruction_text': i.mnemonic+' '+i.op_str})
    save('literal-references-candidates.json', literal_refs)
    # Exact references to diagnostic string starts, allowing leading printable
    # instruction bytes that happened to coalesce with a string in the inventory.
    keywords = (b'SPI_CMD_UI_SET', b'bad route rcvd', b'AVB Start', b'AVB Stop',
                b'SPI Rx Dump', b'SPI Tx Dump', b'Storm SPI', b'Idle Thread',
                b'STM32 Internal Flash', b'DiceDriver', b'linkHandler.c')
    anchors = []
    for keyword in keywords:
        at = b.find(keyword)
        if at < 0:
            continue
        addr = base+at
        anchors.append({'text': keyword.decode(), 'offset': at, 'address': addr,
                        'literal_references': [r for r in literal_refs if r['value'] == addr]})
    save('anchors.json', anchors)
    with (out/'anchor-windows.thumb.txt').open('w') as f:
        for a in anchors:
            for r in a['literal_references']:
                f.write(f'\n# {a["text"]}: xref {r["instruction"]:#x}, candidate window only\n')
                lo, hi = max(0x10, r['instruction']-base-96), r['instruction']-base+128
                for i in decoder.disasm(b[lo:hi], base+lo):
                    f.write(f'{i.address:08x} {i.mnemonic} {i.op_str}\n')
    # Map copied initialized-data addresses back to their image offsets.
    def cstring(a):
        offset = a-base
        if 0x20000400 <= a < 0x20001264:
            offset = 0x340e8+a-0x20000400
        if not 0 <= offset < len(b):
            return None
        end = b.find(b'\0', offset, min(offset+2048, len(b)))
        if end < 0 or not all(x in (9,10,13) or 32 <= x <= 126 for x in b[offset:end]):
            return None
        return b[offset:end].decode()
    cli = []
    for hit in re.finditer(b'loot', b):
        off = hit.start()-12
        if off < 0:
            continue
        pairs = []
        for cur in range(off, min(off+256, len(b)-7), 8):
            pair = struct.unpack_from('<II', b, cur)
            pairs.append(pair)
            if pair[0] == 0xffffffff:
                break
        fields = dict(pairs)
        if fields.get(2) != 0x746f6f6c or not {1,3,8,11,0xffffffff} <= fields.keys():
            continue
        cli.append(dict(descriptor_offset=off, name=cstring(fields[1]),
                        context=cstring(fields.get(12,0)), callback=fields[3],
                        usage=cstring(fields[8]), description=cstring(fields[11]),
                        raw_tag_value_pairs=pairs,
                        original_function_symbol=None, extent_verified=False))
    save('cli-registrations.json', cli)
    sdk = [s for s in strings if '/packages/' in s['text']]
    save('sdk-source-paths.json', sdk)
    # Replay exactly the reset data-copy/BSS/vector segment. The hardware init
    # callee and SVC privilege trampoline are hooked, not executed or simulated.
    machine = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_THUMB | uc.UC_MODE_MCLASS)
    machine.mem_map(base, 0x80000)
    machine.mem_write(base, b)
    machine.mem_map(0x20000000, 0x10000)
    machine.mem_write(0x20000000, b'\xa5'*0x10000)
    machine.mem_map(0xe000e000, 0x2000)
    machine.reg_write(UC_ARM_REG_SP, 0x20010000)
    machine.reg_write(UC_ARM_REG_LR, 0x080045d5)
    trace, hooks = [], []
    def hook_code(m, address, size, _):
        trace.append(address)
        if address == 0x08004a44:
            hooks.append({'address':hex(address), 'model':'skip hardware init; preserve registers'})
            m.reg_write(UC_ARM_REG_PC, m.reg_read(UC_ARM_REG_LR))
        elif address == 0x0800454e:
            hooks.append({'address':hex(address), 'model':'skip SVC instruction; no privilege transition proof'})
            m.reg_write(UC_ARM_REG_PC, (address+size)|1)
        elif address == 0x08004576:
            m.emu_stop()
    machine.hook_add(uc.UC_HOOK_CODE, hook_code)
    machine.emu_start(0x08004511, 0, count=200000)
    assert trace[-1] == 0x08004576, hex(trace[-1])
    data = bytes(machine.mem_read(0x20000400, 0xe64))
    assert data == b[0x340e8:0x34f4c]
    assert bytes(machine.mem_read(0x20001268, 0xd1ac)) == b'\0'*0xd1ac
    assert bytes(machine.mem_read(0xe000ed08, 4)) == struct.pack('<I', 0x20000000)
    assert bytes(machine.mem_read(0x20001264, 4)) == b'\xa5'*4
    vectors = list(struct.unpack('<75I', machine.mem_read(0x20000000, 300)))
    startup = dict(initial_sp='0x20010000', reset='0x08004510',
                   boot_trampoline='0x08000010', vector_base='0x20000000',
                   vector_words_written={'first':2, 'last':74},
                   vectors_0_1='not written by this reset segment; not assumed initialized',
                   flash_data_start='0x080340e8', data_start='0x20000400', data_end='0x20001264',
                   data_bytes=len(data), gap='0x20001264..0x20001268 remains untouched',
                   bss_start='0x20001268', bss_end='0x2000e414', bss_bytes=0xd1ac,
                   bytes_above_bss_end=0x10000-0xe414,
                   stack_heap_boundary='not established by these symbols alone',
                   runtime_vectors=[hex(x) for x in vectors], hooks=hooks,
                   trace_instructions=len(trace), stopped_before='0x08004576',
                   scope='executed reset segment only; not successful boot or hardware equivalence')
    save('startup-replay.json', startup)
    save('startup-trace.json', [hex(a) for a in trace])
    with (out/'startup.thumb.txt').open('w') as f:
        for lo, hi in ((0x10,0x1c),(0x4510,0x45d8),(0x44f4,0x4510),(0x4a44,0x4b78),(0x586a,0x5940)):
            f.write(f'\n# region {base+lo:#x}..{base+hi:#x}; boundaries are analysis bounds\n')
            for i in decoder.disasm(b[lo:hi], base+lo):
                f.write(f'{i.address:08x} {i.mnemonic} {i.op_str}\n')
    proof = dict(started_at=datetime.now(timezone.utc).isoformat(), image_sha256=sha(b),
                 input_symbol='_ZL13nimh_arm_code', host_elf_sha256='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
                 image_bytes=len(b), capstone=cs.__version__, unicorn=uc.__version__,
                 tool_sha256=sha(Path(__file__).read_bytes()), cli_records=len(cli),
                 sdk_source_paths=len(sdk), startup_replay_passed=True,
                 original_embedded_symbols_available=False, reconstructed_cpp_functions=0,
                 hardware_actions=0)
    save('analysis.json', proof)
    print(json.dumps(proof))
    for a in anchors:
        print(a['text'], [hex(r['instruction']) for r in a['literal_references']])
    print('CLI groups', sorted({x['context'] or '' for x in cli}))


if __name__ == '__main__':
    main()
