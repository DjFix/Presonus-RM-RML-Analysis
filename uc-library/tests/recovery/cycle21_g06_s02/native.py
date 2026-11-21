"""Execute the FX initializer, effect query and original interpolation dispatch."""
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP

TASK = Path(__file__).parent.name
BASE = Path("temp/recovery-work/reconstruction10x10-20261121/packeting")
PACKET = BASE / "post32-next-batch02/packets" / TASK
INPUTS = BASE / "READ_INPUTS-post32-next-batch02-cycle21_g06-post32-next39-scoped01-dispatch02.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fbits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def floating(word):
    return struct.unpack("<f", struct.pack("<I", word))[0]


def load_target():
    request = json.loads((PACKET / "request.json").read_text())
    target, = request["targets"]
    release, = request["work_binding"]["binary_releases"]
    record = json.loads(INPUTS.read_text())[release["original_path"]]
    elf_path = Path(record["frozen_read_path"])
    assert digest(elf_path.read_bytes()) == record["sha256"] == target["original_elf_sha256"]
    with elf_path.open("rb") as stream:
        elf = ELFFile(stream)
        section = elf.get_section(target["section"])
        entry, size = target["address"], target["size"]
        offset = section["sh_offset"] + entry - section["sh_addr"]
        assert 0 <= entry-section["sh_addr"] <= section["sh_size"]-size
        stream.seek(offset)
        body = stream.read(size)
        assert digest(body) in (PACKET/"ELF_CONTEXT.md").read_text()
        segments = [(s["p_vaddr"], s["p_memsz"], s.data()) for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
        symbol_table = elf.get_section_by_name(".symtab")
        symbols = {s.name: (s["st_value"], s["st_size"]) for s in symbol_table.iter_symbols()
                   if s.name == "_ZNK8Presonus5Mixer11FXComponent10getTypeNumEv"}
    return ({"elf": str(elf_path), "target": target, "section": section.name,
             "file_offset": offset, "range_sha256": digest(body)}, segments, symbols)


def make_cpu(segments):
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    lo = min(a for a, _, _ in segments)&~0xfff
    hi = max(a+n for a, n, _ in segments)
    cpu.mem_map(lo, (hi-lo+0xfff)&~0xfff)
    for addr, _, data in segments:
        cpu.mem_write(addr, data)
    cpu.mem_map(0x3000000, 0x10000)
    return cpu


def generate():
    proof, segments, _ = load_target()
    entry = proof["target"]["address"]
    startup = 0x3ac0c
    stop = 0x3000100
    reference = make_cpu(segments)
    reference.reg_write(UC_ARM_REG_SP, 0x300ff00)
    reference.reg_write(UC_ARM_REG_LR, stop)
    def check_initializer(cpu, address, _size, _context):
        assert startup <= address < startup+2928, hex(address)
    reference.hook_add(UC_HOOK_CODE, check_initializer)
    reference.emu_start(startup, stop, count=2000)
    assert reference.reg_read(UC_ARM_REG_PC) == stop
    table_bytes = bytes(reference.mem_read(0x171370, 24))
    assert digest(table_bytes) == "4f6046e28d127faccfe005dc93f2418ad09b4557711581d37cd61ee75fcb1a9f"
    arrays = {address: bytes(reference.mem_read(address, 156))
              for address in struct.unpack("<6I", table_bytes)}
    proof["initializer"] = {"address": startup, "size": 2928,
                            "sha256": digest(bytes(reference.mem_read(startup, 2928))),
                            "arrays": {hex(a): digest(b) for a, b in arrays.items()}}
    cases = []
    # mode 0 absent, 1 non-numeric, 2 no factory, 3 successful factory.
    inputs = [(0, 0, 0, 0.25), (1, 1, 1, 0.25),
              (2, 0, 0, 0.25), (2, 0, 1, 0.25), (4, 0, 0, 0.25)] + [
                  (3, slot, effect, frac)
                  for slot in range(6) for effect in range(13)
                  for frac in (0.25,)]
    for mode, slot, effect, fraction in inputs:
        u = make_cpu(segments)
        for address, data in arrays.items():
            u.mem_write(address, data)
        base = 0x3000000
        obj, param, skew, storage, stop = (base+i*0x400 for i in range(5))
        def get(addr):
            return struct.unpack("<I", u.mem_read(addr, 4))[0]
        def put(addr, number):
            u.mem_write(addr, struct.pack("<I", number))
        put(obj, 0x16fc40)
        put(obj+0x100+4*slot, param if mode else 0)
        put(obj+0x134, storage)
        put(obj+0x13c, int(mode == 2 and effect == 1))
        put(param, 0x41b068 if mode != 1 else 0x41af68)
        put(skew, 0x35ec68)
        assert get(0x16fc40+0x4c) == 0x3c944
        for register, value in [(UC_ARM_REG_R0, obj), (UC_ARM_REG_R1, slot),
                                 (UC_ARM_REG_R2, effect),
                                 (UC_ARM_REG_SP, base+0xff00), (UC_ARM_REG_LR, stop)]:
            u.reg_write(register, value)
        trace = []
        def observe(cpu, addr, _size, _context):
            r0, r1, r2, r3 = (cpu.reg_read(reg) for reg in
                              (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3))
            if addr == 0xacf4:
                assert (r0, r1, r2, r3) == (param, 4305512, 4305472, 0)
                cpu.reg_write(UC_ARM_REG_R0, param if mode >= 2 else 0)
            elif addr == 0x112844:
                assert bytes(cpu.mem_read(r0,5)) == b"skew\0"
                cpu.reg_write(UC_ARM_REG_R0, skew if mode == 3 else 0)
            elif addr == 0x11def8:
                assert r0 == param
                trace.extend([1, fbits(fraction)])
                cpu.reg_write(UC_ARM_REG_R0, fbits(fraction))
            elif addr == 0x3c944:
                assert r0 == obj and r1 == effect
                trace.extend([2, r1])
                return
            elif addr == 0xd1a34:
                assert r0 == skew
                trace.extend([3, r1, r2, r3])
            elif addr in (0x11e2fc, 0x11e258, 0x11e1e4):
                assert r0 == param
                trace.extend([{0x11e2fc:4, 0x11e258:5, 0x11e1e4:6}[addr], r1])
            elif addr == 0x11c400:
                assert (r0,r1) == (param,skew)
            elif addr == 0x11d8c8:
                assert r0 == param
                trace.extend([7,r1,r2])
            elif addr == 0x12640:
                assert (r0,r1) == (obj+0x130,1)
                if mode != 4:
                    put(obj+0x13c,1)
                cpu.reg_write(UC_ARM_REG_R0,int(mode != 4))
            else:
                assert entry <= addr < entry+proof["target"]["size"] or 0x3c944 <= addr < 0x3c958, hex(addr)
                return
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE, observe)
        u.emu_start(entry, stop, count=1000)
        assert u.reg_read(UC_ARM_REG_PC) == stop
        count = get(obj+0x138)
        assert count in (0,1) and (not count or get(storage) == param)
        # Check that all argument words, including min/mid/max ordering, are
        # inherited from the executed original callsites.
        cases.append({"input":[mode,slot,effect,fraction],
                      "observed":[*(trace[:4] + trace[8:] + trace[5:8] if trace else []), count],
                      "native_call_order":trace})
    proof["cases"] = cases
    return proof


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
