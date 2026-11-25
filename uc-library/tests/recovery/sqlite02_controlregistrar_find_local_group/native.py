"""Execute the sealed ARM lookup against independent synthetic local rosters."""
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import struct
import sys

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

ROOT = 0x70000000
STOP = ROOT + 0x9000
TAGS = (12, 3, 12, -2, 0)
CASES = ((0, 99), (1, 12), (1, 3), (1, -2), (1, 0), (1, 99),
         (1, 4), (0, 12), (0, 0), (1, -(2**31)), (1, 2**31 - 1))
GROUP = "_ZNK8Presonus5Panel12ControlGroup"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def function(elf, image, name):
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    section_index = symbol["st_shndx"]
    section = elf.get_section(section_index)
    address, size = symbol["st_value"], symbol["st_size"]
    assert symbol["st_info"]["type"] == "STT_FUNC"
    assert section.name == ".text" and section["sh_type"] == "SHT_PROGBITS"
    relative = address - section["sh_addr"]
    assert size > 0 and 0 <= relative <= section["sh_size"] - size
    file_offset = section["sh_offset"] + relative
    code = image[file_offset:file_offset + size]
    assert code == section.data()[relative:relative + size]
    return dict(address=address, size=size, section=section_index,
                section_name=section.name, file_offset=file_offset,
                range_sha256=sha(code), range_hex=code.hex()), code


def execute(original, firmware_root, selected):
    image = (firmware_root / original["elf_path"]).read_bytes()
    assert sha(image) == original["elf"]
    elf = ELFFile(io.BytesIO(image))
    assert elf["e_machine"] == "EM_ARM" and elf.little_endian
    identity, code = function(elf, image, original["mangled"])
    for name, value in identity.items():
        assert original[name] == value, (name, original[name], value)

    accessors = {}
    for operation in ("5countEv", "2atEi", "5byTagEi"):
        name = GROUP + operation
        accessors[operation] = function(elf, image, name)[0]
    destructor = function(elf, image, "_ZN8Presonus5Panel12ControlGroupD1Ev")[0]

    instructions = Cs(CS_ARCH_ARM, CS_MODE_ARM).disasm(code, identity["address"])
    imports = [int(insn.op_str.removeprefix("#"), 16)
               for insn in instructions if insn.mnemonic == "bl"]
    assert imports == selected["cxx_abi_import_addresses"]
    guard, sentinel, sentinel_vtable = struct.unpack_from("<III", code, len(code) - 20)
    assert sentinel == selected["sentinel"]["address"]

    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(0x8000, 0x600000)
    uc.mem_map(ROOT, 0x10000)
    for segment in elf.iter_segments():
        if segment["p_type"] == "PT_LOAD":
            uc.mem_write(segment["p_vaddr"], segment.data())

    def put(address, *values):
        uc.mem_write(address, struct.pack("<" + "I" * len(values),
                                          *(value & 0xffffffff for value in values)))

    def word(address):
        return struct.unpack("<I", uc.mem_read(address, 4))[0]

    def signed_word(address):
        return struct.unpack("<i", uc.mem_read(address, 4))[0]

    calls = []

    def boundary(emulator, pc, size, _):
        if pc not in imports:
            return
        first, second, third = (emulator.reg_read(reg) for reg in
                                (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        action = imports.index(pc)
        calls.append([action, first, second, third])
        if action == 0:
            assert first == guard and word(guard) == 0
            emulator.reg_write(UC_ARM_REG_R0, 1)
        elif action == 1:
            assert first == guard
            assert [word(sentinel + offset) for offset in (0, 4, 8, 12)] == [
                sentinel_vtable, 0, sentinel + 16, 0]
            put(guard, 1)
        else:
            assert first == sentinel and second == destructor["address"]
            emulator.reg_write(UC_ARM_REG_R0, 0)
        emulator.reg_write(UC_ARM_REG_PC, emulator.reg_read(UC_ARM_REG_LR))

    def invoke(address, this, arg=0):
        for reg, value in ((UC_ARM_REG_SP, ROOT + 0xf000), (UC_ARM_REG_R0, this),
                           (UC_ARM_REG_R1, arg & 0xffffffff), (UC_ARM_REG_LR, STOP)):
            uc.reg_write(reg, value)
        uc.emu_start(address, STOP, count=500)
        assert uc.reg_read(UC_ARM_REG_PC) == STOP
        return uc.reg_read(UC_ARM_REG_R0)

    uc.hook_add(UC_HOOK_CODE, boundary)
    registrars = (ROOT, ROOT + 0x100)
    roster = ROOT + 0x1000
    groups = [ROOT + 0x2000 + index * 0x500 for index in range(len(TAGS))]
    for address, tag in zip(groups, TAGS):
        put(address, sentinel_vtable, tag, address + 16, 0)
    put(roster, *groups)
    put(registrars[0] + 0x18, roster, 0)
    put(registrars[1] + 0x18, roster, len(groups))
    before = bytes(uc.mem_read(ROOT, 0x4000))
    initial_guard = word(guard)
    assert initial_guard == 0

    cases = []
    for registrar_index, tag in CASES:
        registrar = registrars[registrar_index]
        result = invoke(identity["address"], registrar, tag)
        if result == sentinel:
            index = -1
        else:
            index = groups.index(result)
            assert registrar_index == 1 and signed_word(result + 4) == tag
        size = word(registrar + 0x1c)
        assert word(registrar + 0x18) == roster
        observed_tags = [signed_word(word(roster + i * 4) + 4) for i in range(size)]
        outputs = [index, signed_word(result + 4),
                   invoke(accessors["5countEv"]["address"], result),
                   int(invoke(accessors["2atEi"]["address"], result, 0) == 0),
                   int(invoke(accessors["5byTagEi"]["address"], result, 12) == 0),
                   size, *observed_tags]
        cases.append(dict(registrar=registrar_index, tag=tag, outputs=outputs,
                          returned_address=result))
        assert bytes(uc.mem_read(ROOT, 0x4000)) == before

    assert calls == selected["first_miss_calls"], calls
    assert word(guard) == 1
    return dict(original=original, accessors=accessors, destructor=destructor,
                abi_imports=imports, first_miss_calls=calls, guard_address=guard,
                sentinel_address=sentinel, final_guard=word(guard),
                sentinel_words=[word(sentinel + offset) for offset in (0, 4, 8, 12)],
                roster_unchanged=True, cases=cases)


def main():
    context_path, firmware_root, selected_path = map(Path, sys.argv[1:])
    context = json.loads(context_path.read_bytes())
    selected_bytes = selected_path.read_bytes()
    assert sha(selected_bytes) == context["task"]["review"]["equivalence"]["sha256"]
    selected = {item["role"]: item for item in json.loads(selected_bytes)["items"]}
    entries = [execute(row["original"], firmware_root, selected[row["original"]["role"]])
               for row in context["originals"]]
    versions = {package: importlib.metadata.version(package)
                for package in ("capstone", "pyelftools", "unicorn")}
    print(json.dumps(dict(versions=versions, entries=entries), indent=2))


if __name__ == "__main__":
    main()
