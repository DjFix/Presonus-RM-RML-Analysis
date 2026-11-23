"""Execute both exact ARM constructors and their actual soft-float helpers."""
import ctypes
import hashlib
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_LR

MANGLED = "_ZN8Presonus15MeterBallistics15MeterDecayTableC1EPKf"
ROLES = {
    "server": ("9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07",
               0x8c46c, 0x8446c, "6650cc8a51515a686b91fade908e6cbc8476d914037a5145d2abd4b94a228e28",
               0xae5c, (0x1572ac, 0x1576e8, 0x157550, 0x1578f8)),
    "client": ("304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0",
               0x13688, 0xb688, "82fa7d7dfaa420fe638e85975a0a2a3cc5c7d812d507eb9c19bef2972cddcb43",
               0xaff0, (0x18714c, 0x187588, 0x1873f0, 0x187798)),
}
ARITHMETIC = ("__aeabi_fsub", "__aeabi_fdiv", "__aeabi_fmul", "__aeabi_fcmplt")
POW = ctypes.CDLL("libm.so.6").powf
POW.argtypes = [ctypes.c_float, ctypes.c_float]
POW.restype = ctypes.c_float


def u32(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def f32(word):
    return struct.unpack("<f", struct.pack("<I", word))[0]


def observe(role, path):
    digest, start, offset, body_hash, pow_entry, helper_addresses = ROLES[role]
    with path.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == digest
        stream.seek(0)
        elf = ELFFile(stream)
        symbols = elf.get_section_by_name(".symtab")

        def capture(name):
            sym, = symbols.get_symbol_by_name(name)
            section = elf.get_section(sym["st_shndx"])
            addr, count = sym["st_value"], sym["st_size"]
            displacement = addr - section["sh_addr"]
            data = section.data()[displacement:displacement + count]
            assert len(data) == count and section.name == ".text"
            return data, dict(mangled=name, address=addr, size=count, section=section.name,
                              section_index=sym["st_shndx"], file_offset=section["sh_offset"] + displacement,
                              sha256=hashlib.sha256(data).hexdigest())

        body, target = capture(MANGLED)
        assert (target["address"], target["size"], target["section_index"],
                target["file_offset"], target["sha256"]) == (start, 172, 12, offset, body_hash)
        assert not symbols.get_symbol_by_name(MANGLED.replace("C1E", "C2E"))
        helpers = [capture(name) for name in ARITHMETIC]
        assert tuple(row["address"] for _, row in helpers) == helper_addresses
        helpers.extend(capture(name) for name in ("__aeabi_cfcmple", "__cmpsf2"))

        relplt = elf.get_section_by_name(".rel.plt")
        dynamic = elf.get_section(relplt["sh_link"])
        plt = elf.get_section_by_name(".plt")
        (idx, pow_relocation), = [(n, row) for n, row in enumerate(relplt.iter_relocations())
                                  if dynamic.get_symbol(row["r_info_sym"]).name == "powf"]
        assert plt["sh_addr"] + 20 + 12 * idx == pow_entry
        assert pow_relocation["r_info_type"] == 22  # R_ARM_JUMP_SLOT
        start_of_stub = pow_entry - plt["sh_addr"]
        stub = plt.data()[start_of_stub:start_of_stub + 12]
    cases = []
    points = [tuple(float(i + j) for j in range(6)) for i in (-4, 0, 1, 7)]
    points.append((-160.0, -145.0, -144.0, -141.0, -97.0, -31.0))
    obj, inputs, stack, stop = 0x22000000, 0x23000000, 0x24000000, 0x25000000
    blocks = [(start, body), (pow_entry, stub), *[(row["address"], data) for data, row in helpers]]
    helper_names = dict(zip(helper_addresses, ARITHMETIC))
    for point in points:
        cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        pages = {obj, inputs, stack, stop}
        for address, data in blocks:
            pages.update(range(address & ~4095, ((address + len(data) - 1) & ~4095) + 1, 4096))
        for page in pages:
            cpu.mem_map(page, 4096)
        for address, data in blocks:
            cpu.mem_write(address, data)
        cpu.mem_write(obj, b"\xa5" * 64)
        input_bytes = struct.pack("<6f", *point)
        cpu.mem_write(inputs, input_bytes)
        for reg, value in [(UC_ARM_REG_R0, obj), (UC_ARM_REG_R1, inputs),
                           (UC_ARM_REG_SP, stack + 2048), (UC_ARM_REG_LR, stop)]:
            cpu.reg_write(reg, value)
        events, writes = [], []

        def trace(uc, address, _size, _data):
            if address in helper_names or address == pow_entry:
                x, y = uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_R1)
                events.append([helper_names.get(address, "powf"), address, x, y])
                if address == pow_entry:
                    result = u32(POW(f32(x), f32(y)))
                    events[-1].append(result)
                    uc.reg_write(UC_ARM_REG_R0, result)
                    uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
            assert address == stop or any(a <= address < a + len(data) for a, data in blocks), hex(address)

        def write(_uc, _access, address, size, value, _data):
            if not stack <= address < stack + 4096:
                writes.append([address - obj, size, value & 0xffffffff])

        cpu.hook_add(UC_HOOK_CODE, trace)
        cpu.hook_add(UC_HOOK_MEM_WRITE, write)
        cpu.emu_start(start, stop, count=5000)
        assert cpu.reg_read(UC_ARM_REG_PC) == stop
        assert cpu.reg_read(UC_ARM_REG_SP) == stack + 2048
        assert cpu.reg_read(UC_ARM_REG_R0) == obj
        assert bytes(cpu.mem_read(inputs, 24)) == input_bytes
        assert bytes(cpu.mem_read(obj + 40, 24)) == b"\xa5" * 24
        output = list(struct.unpack("<10I", cpu.mem_read(obj, 40)))
        assert writes == [[i * 4, 4, word] for i, word in enumerate(output)]
        cases.append(dict(inputs=list(point), input_bits=list(struct.unpack("<6I", input_bytes)),
                          outputs=output, writes=writes, events=events))
    return dict(role=role, elf=dict(path=str(path), sha256=digest), target=target,
                soft_float=[row for _, row in helpers], powf=dict(address=pow_entry,
                relocation=pow_relocation["r_offset"], plt_sha256=hashlib.sha256(stub).hexdigest()),
                cases=cases)


print(json.dumps({"originals": [observe(role, Path(operand))
                                 for role, operand in zip(ROLES, sys.argv[1:], strict=True)]},
                 indent=2))
