"""Execute the exact offline mixer hook, directly and through its native vtable."""
import hashlib
import json
import struct
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

source = Path(sys.argv[1])
digest = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
mangled = "_ZN8Presonus16MeterManagerBase13processMetersEb"
with source.open("rb") as stream:
    assert hashlib.file_digest(stream, "sha256").hexdigest() == digest
    stream.seek(0)
    elf = ELFFile(stream)
    table = elf.get_section_by_name(".symtab")

    def exact_range(name, section_name, address, size, file_offset, expected):
        symbol, = table.get_symbol_by_name(name)
        section = elf.get_section(symbol["st_shndx"])
        assert (section.name, symbol["st_value"], symbol["st_size"]) == (
            section_name, address, size)
        offset = address - section["sh_addr"]
        assert section["sh_offset"] + offset == file_offset
        body = section.data()[offset:offset + size]
        assert hashlib.sha256(body).hexdigest() == expected
        return body

    start, size, offset = 0x8bb28, 16, 0x83b28
    original_hash = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
    body = exact_range(mangled, ".text", start, size, offset, original_hash)
    vtable_addr = 0x357de8
    vtable = exact_range("_ZTVN8Presonus16MeterManagerBaseE", ".rodata",
                         vtable_addr, 28, 0x34fde8,
                         "2258a5374c8f5ac83f20817e5ea9b79885c87d0247816681afe1ff32b5f633a1")
    assert struct.unpack_from("<I", vtable, 20) == (start,)

cases = []
receiver, stack, trampoline, stop = 0x40000000, 0x41000000, 0x42000000, 0x43000000
for route in ("direct", "vtable"):
    for seed in (0, 117):
        for phase in (0, 1):
            uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
            for address, data in (
                (start, body), (vtable_addr, vtable),
                (receiver, struct.pack("<I", vtable_addr + 8) + bytes([seed]) * 252),
                (stack, b""),
                (trampoline, struct.pack("<II", 0xe590c000, 0xe59cf00c)),
                (stop, b""),
            ):
                uc.mem_map(address & ~4095, 4096)
                if data:
                    uc.mem_write(address, data)
            before = bytes(uc.mem_read(receiver, 256))
            trace, effects = [], []

            def observe(_uc, pc, _size, _data):
                trace.append(pc)

            def write(_uc, _access, address, length, _value, _data):
                if not stack <= address <= stack + 4096 - length:
                    effects.append([address, length])

            uc.hook_add(UC_HOOK_CODE, observe)
            uc.hook_add(UC_HOOK_MEM_WRITE, write)
            uc.reg_write(UC_ARM_REG_R0, receiver)
            uc.reg_write(UC_ARM_REG_R1, phase)
            uc.reg_write(UC_ARM_REG_SP, stack + 2048)
            uc.reg_write(UC_ARM_REG_LR, stop)
            uc.emu_start(start if route == "direct" else trampoline, stop, count=20)
            assert uc.reg_read(UC_ARM_REG_PC) == stop
            assert trace[-4:] == list(range(start, start + size, 4))
            assert not effects
            cases.append(dict(route=route, seed=seed, phase=phase, trace=trace,
                              unchanged=before == bytes(uc.mem_read(receiver, 256)),
                              r0_unchanged=uc.reg_read(UC_ARM_REG_R0) == receiver,
                              effects=effects))

print(json.dumps(dict(elf={"path": str(source), "sha256": digest}, mangled=mangled,
                      address=start, size=size, section=".text", file_offset=offset,
                      original_sha256=original_hash, vtable_address=vtable_addr,
                      cases=cases), indent=2))
