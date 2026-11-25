"""Verify and execute both original offline discovery assignment ranges."""
import argparse
import hashlib
import io
import json
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, __version__
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

CALLER = "_ZN8Presonus2UC19UDPDiscoveryHandler16onMulticastEventEPKcttiPNS0_9EventItemE"
WORD_BYTES = 20
STRING_BYTES = 64
LENGTH = WORD_BYTES + 4 * STRING_BYTES


def sha(data):
    return hashlib.sha256(data).hexdigest()


def function(elf, image, name):
    row, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    sid, address, size = row["st_shndx"], row["st_value"], row["st_size"]
    section = elf.get_section(sid)
    relative = address - section["sh_addr"]
    assert row["st_info"]["type"] == "STT_FUNC" and section.name == ".text"
    assert section["sh_type"] == "SHT_PROGBITS" and 0 <= relative <= section["sh_size"] - size
    offset = section["sh_offset"] + relative
    code = image[offset:offset + size]
    return dict(mangled=name, section=sid, address=address, size=size, file_offset=offset,
                range_sha256=sha(code), range_hex=code.hex()), code


def initial(seed):
    data = bytearray((seed + i * 31) % 256 for i in range(LENGTH))
    for index, term in enumerate((0, 7, 63, 31)):
        offset = WORD_BYTES + STRING_BYTES * index
        for i in range(term):
            data[offset + i] = (data[offset + i] % 26) + 65
        data[offset + term] = 0
        if term < 63:
            assert any(data[offset + term + 1:offset + STRING_BYTES])
    return bytes(data)


def execute(original, body, src_data, dst_data, self_assign):
    src, dst, stack, stop = 0x810100, 0x820100, 0x830800, 0x840000
    source = dst if self_assign else src
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    address = original["address"]
    pages = {src & ~4095, dst & ~4095, stack & ~4095, stop}
    pages.update(range(address & ~4095, ((address+len(body)-1) & ~4095)+4096, 4096))
    for page in pages:
        machine.mem_map(page, 4096)
    machine.mem_write(address, body)
    before, after = bytes(range(16)), bytes(range(16, 32))
    for pointer, contents in ((src, src_data), (dst, dst_data)):
        machine.mem_write(pointer-16, before + contents + after)
    for reg, value in ((UC_ARM_REG_R0, dst), (UC_ARM_REG_R1, source),
                       (UC_ARM_REG_SP, stack), (UC_ARM_REG_LR, stop)):
        machine.reg_write(reg, value)
    writes = []
    stack_writes = []
    pcs = []
    push, = Cs(CS_ARCH_ARM, CS_MODE_ARM).disasm(body[4:8], address+4)
    assert push.mnemonic == "push"
    assert push.op_str == "{r4, r5, r6, r7, r8, fp, ip, lr, pc}"
    saved_registers = len(push.op_str.split(","))
    saved_addresses = list(range(stack - 4 * saved_registers, stack, 4))

    def track(_machine, _kind, destination, size, value, _data):
        assert size == 4
        if pcs[-1] == push.address:
            assert destination in saved_addresses
            stack_writes.append(destination)
        else:
            assert dst <= destination <= dst + LENGTH - size
            writes.append((destination - dst, value))

    machine.hook_add(UC_HOOK_CODE, lambda _m, pc, _size, _d: pcs.append(pc))
    machine.hook_add(UC_HOOK_MEM_WRITE, track)
    machine.emu_start(address, stop, count=64)
    assert machine.reg_read(UC_ARM_REG_PC) == stop and machine.reg_read(UC_ARM_REG_SP) == stack
    assert machine.reg_read(UC_ARM_REG_R0) == dst
    assert pcs == list(range(address, address+len(body), 4))
    assert stack_writes == saved_addresses
    assert [offset for offset, _ in writes] == list(range(0, LENGTH, 4))
    output = bytes(machine.mem_read(dst, LENGTH))
    assert output == (dst_data if self_assign else src_data)
    assert bytes(machine.mem_read(src, LENGTH)) == src_data
    for pointer in (src, dst):
        assert bytes(machine.mem_read(pointer-16, 16)) == before
        assert bytes(machine.mem_read(pointer+LENGTH, 16)) == after
    return dict(source=src_data.hex(), destination=dst_data.hex(), self_assign=self_assign,
                result=output.hex(), source_preserved=True, destination_return=True, writes=writes,
                stack_push_offsets=[loc - stack for loc in stack_writes])


def observe(packet, rootfs):
    entries = []
    for item in json.loads(packet.read_text())["originals"]:
        original = item["original"]
        image = (rootfs / Path(original["elf_path"]).relative_to("rootfs")).read_bytes()
        assert sha(image) == original["elf"]
        elf = ELFFile(io.BytesIO(image))
        assert elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM"
        identity, body = function(elf, image, original["mangled"])
        assert all(original[key] == value for key, value in identity.items())
        caller, caller_body = function(elf, image, CALLER)
        visible = list(Cs(CS_ARCH_ARM, CS_MODE_ARM).disasm(caller_body[0x144:0x164], caller["address"]+0x144))
        assert [(i.mnemonic, i.op_str) for i in visible[:2]] == [
            ("add", "r1, r7, #0x9c"), ("sub", "r0, fp, #0x164")]
        assert {i.op_str for i in visible if i.mnemonic == "strb"} == {
            "r6, [fp, #-0x150]", "r6, [fp, #-0x110]", "r6, [fp, #-0xd0]", "r6, [fp, #-0x90]"}
        assert visible[-1].mnemonic == "bl" and int(visible[-1].op_str[1:], 16) == identity["address"]
        # Store only the relevant caller window alongside the full range hash.
        del caller["range_hex"]
        boundary = dict(application_caller=caller, caller_window=[(i.mnemonic, i.op_str) for i in visible],
                        word_bytes=WORD_BYTES, string_starts=[20, 84, 148, 212], string_length=STRING_BYTES)
        cases = [(13, 231, False), (0, 0, False), (101, 53, True), (255, 192, False)]
        entries.append(dict(original=original, boundaries=boundary,
                            cases=[execute(identity, body, initial(src), initial(dst), same)
                                   for src, dst, same in cases]))
    return dict(engine=f"Unicorn {__version__}", entries=entries)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("rootfs", type=Path)
    parser.add_argument("_direct", type=Path)
    args = parser.parse_args()
    print(json.dumps(observe(args.packet, args.rootfs), indent=2))
