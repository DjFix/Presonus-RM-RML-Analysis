"""Execute the exact RM OMAP default property getter directly and through its native vtable."""
import hashlib
import json
import struct
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP

source = Path(sys.argv[1])
elf_hash = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
mangled = "_ZN8Presonus3Dsp17OMAPTargetHandler11getPropertyERN4Core8PropertyE"
with source.open("rb") as stream:
    assert hashlib.file_digest(stream, "sha256").hexdigest() == elf_hash
    stream.seek(0)
    elf = ELFFile(stream)
    symbols = elf.get_section_by_name(".symtab")

    def exact_range(name, section_name, address, size, file_offset, digest):
        symbol, = symbols.get_symbol_by_name(name)
        section = elf.get_section(symbol["st_shndx"])
        assert (section.name, symbol["st_value"], symbol["st_size"]) == (
            section_name, address, size)
        relative = address - section["sh_addr"]
        assert section["sh_offset"] + relative == file_offset
        body = section.data()[relative:relative + size]
        assert hashlib.sha256(body).hexdigest() == digest
        return body

    start, size, offset = 0x86a60, 16, 0x7ea60
    original_hash = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
    body = exact_range(mangled, ".text", start, size, offset, original_hash)
    table_name = "_ZTVN8Presonus3Dsp17OMAPTargetHandlerE"
    table_addr, table_size, table_offset, slot = 0x3579d8, 20, 0x34f9d8, 4
    table_hash = "5454e64a9ebb21ea9bee9271c2108647a013e62f46c30f5853057d52e2a66582"
    table = exact_range(table_name, ".rodata", table_addr, table_size, table_offset, table_hash)
    assert struct.unpack_from("<II", table) == (0, 0x357a4c)
    assert struct.unpack_from("<I", table, 8 + slot) == (start,)

receiver, stack, trampoline, stop = 0x38000100, 0x60000000, 0x71000000, 0x70000000
cases = []
for route in ("ordinary", "vtable"):
    for seed in (0, 41, 255):
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        for address, data in (
            (start, body), (table_addr, table),
            (receiver, struct.pack("<I", table_addr + 8) + bytes([seed]) * 252),
            (stack, b""),
            (trampoline, struct.pack("<II", 0xe590c000, 0xe59cf000 | slot)),
            (stop, b""),
        ):
            uc.mem_map(address & ~4095, 4096)
            if data:
                uc.mem_write(address, data)
        before = bytes(uc.mem_read(receiver, 256))
        prop = receiver + 256
        property_input = struct.pack("<5I", seed, 20, seed, seed ^ 0x5aa55aa5,
                                     0xffffffff ^ seed)
        uc.mem_write(prop, property_input)
        trace, accesses = [], []

        def observe(_uc, address, _length, _data):
            trace.append(address)

        def access(_uc, mode, address, length, _value, _data):
            accesses.append([mode, address, length])

        uc.hook_add(UC_HOOK_CODE, observe)
        uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, access)
        for reg, value in [(UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, prop),
                           (UC_ARM_REG_R2, 0x12345678 ^ seed), (UC_ARM_REG_R3, 0x76543210 ^ seed),
                           (UC_ARM_REG_SP, stack + 4080), (UC_ARM_REG_LR, stop)]:
            uc.reg_write(reg, value)
        uc.emu_start(start if route == "ordinary" else trampoline, stop, count=20)
        assert uc.reg_read(UC_ARM_REG_PC) == stop
        assert trace[-4:] == list(range(start, start + size, 4))
        nonstack = [row for row in accesses if not stack <= row[1] < stack + 4096]
        expected = [[16, receiver, 4], [16, table_addr + 8 + slot, 4]] if route == "vtable" else []
        assert nonstack == expected
        cases.append(dict(dispatch=route, seed=seed, trace=trace, access=accesses,
                          whole_state_unchanged=before == bytes(uc.mem_read(receiver, 256)),
                          property_unchanged=property_input == bytes(uc.mem_read(prop, 20)),
                          r0_preserved=uc.reg_read(UC_ARM_REG_R0) == receiver))
        assert all(cases[-1][key] for key in ("whole_state_unchanged", "property_unchanged", "r0_preserved"))

print(json.dumps(dict(elf={"path": str(source), "sha256": elf_hash}, mangled=mangled,
                      address=start, size=size, section=".text", file_offset=offset,
                      original_sha256=original_hash, vtable=dict(mangled=table_name, address=table_addr,
                      slot_vptr_relative=slot, size=table_size, file_offset=table_offset,
                      section=".rodata", sha256=table_hash), cases=cases), indent=2))
