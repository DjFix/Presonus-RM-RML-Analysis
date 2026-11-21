"""Run the exact ARM method with a bounded libc bsearch callback boundary."""
import ctypes
import hashlib
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP,
)

RUN = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261121")
READ_MAP = RUN / "packeting/READ_INPUTS-post15-wave-compatible35-batch04-cycle21_g10.json"
ELF_ENTRY = "rootfs/CS18_v13840/home/root/surface"
ADDRESS, SIZE, SECTION = 0x63FDC, 564, 12
ELF_HASH = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
RANGE_HASH = "8504cd8364af1edbf5e4a9c97e73cb99a522382cbe9b5ec8db0cbd45342c7f5b"
COMMAND, TABLE, RECEIVER, STACK, STOP = (0x120000, 0x125000, 0x128000, 0x13F000, 0x140000)
ARGS = [-65537, 65536, 32768, -32769, 65535, 65537]
COMPARATOR = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
LIBC = ctypes.CDLL("libc.so.6")
LIBC.bsearch.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t, COMPARATOR,
]
LIBC.bsearch.restype = ctypes.c_void_p


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run_case(body, key, count, entries, next_id):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    machine.mem_map(0xA000, 0x1000)
    machine.mem_map(0x63000, 0x2000)
    machine.mem_map(COMMAND, 0x21000)
    machine.mem_write(ADDRESS, body)
    machine.mem_write(COMMAND, b"\xa5" * 1000)
    machine.mem_write(TABLE, b"\xa5" * 256)
    machine.mem_write(RECEIVER + 4, struct.pack("<II", COMMAND, count))
    machine.mem_write(RECEIVER + 0x107C, struct.pack("<II", TABLE, len(entries)))
    machine.mem_write(RECEIVER + 0x1184, struct.pack("<H", next_id))
    for index, (entry, ident) in enumerate(entries):
        machine.mem_write(TABLE + index * 8, struct.pack("<IH", entry, ident))
    machine.mem_write(STACK, struct.pack("<iiii", *ARGS[2:]))
    for register, value in (
        (UC_ARM_REG_R0, RECEIVER), (UC_ARM_REG_R1, ARGS[0] & 0xFFFFFFFF),
        (UC_ARM_REG_R2, ARGS[1]), (UC_ARM_REG_R3, key),
        (UC_ARM_REG_SP, STACK), (UC_ARM_REG_LR, STOP),
    ):
        machine.reg_write(register, value)
    calls = []

    def hook(uc, address, size, _):
        if address != 0xAC84:
            return
        key_ptr, base, nmemb, stride = (
            uc.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)
        )
        callback = struct.unpack("<I", uc.mem_read(uc.reg_read(UC_ARM_REG_SP), 4))[0]
        assert (base, nmemb, stride, callback) == (TABLE, len(entries), 8, 0x6445C)
        key_data = bytes(uc.mem_read(key_ptr, stride))
        table_data = bytes(uc.mem_read(base, stride * nmemb))
        assert struct.unpack_from("<I", key_data)[0] == key
        comparisons = []

        @COMPARATOR
        def compare(left, right):
            a = ctypes.c_uint32.from_address(left).value
            b = ctypes.c_uint32.from_address(right).value
            result = (a > b) - (a < b)
            comparisons.append([a, b, result])
            return result

        table_buffer = ctypes.create_string_buffer(table_data)
        result = LIBC.bsearch(key_data, table_buffer, nmemb, stride, compare)
        offset = None if result is None else result - ctypes.addressof(table_buffer)
        calls.append(dict(key=key_data[:6].hex(), table=table_data.hex(),
                          callback=callback, comparisons=comparisons, offset=offset))
        uc.reg_write(UC_ARM_REG_R0, 0 if offset is None else base + offset)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    machine.hook_add(UC_HOOK_CODE, hook)
    machine.emu_start(ADDRESS, STOP, count=3000)
    assert machine.reg_read(UC_ARM_REG_PC) == STOP and len(calls) == 1
    out_count = struct.unpack("<I", machine.mem_read(RECEIVER + 8, 4))[0]
    table_count = struct.unpack("<I", machine.mem_read(RECEIVER + 0x1080, 4))[0]
    out_id = struct.unpack("<H", machine.mem_read(RECEIVER + 0x1184, 2))[0]
    table = [list(struct.unpack("<IH", machine.mem_read(TABLE + i * 8, 6)))
             for i in range(table_count)]
    return dict(key=key, initial_count=count, initial_entries=entries, initial_id=next_id,
                args=ARGS, count=out_count, bitmap_count=table_count, next_id=out_id,
                table=table, commands=bytes(machine.mem_read(COMMAND, 1000)).hex(),
                bsearch=calls[0])


def generate():
    binding = json.loads(READ_MAP.read_text())[ELF_ENTRY]
    elf = Path(binding["frozen_read_path"])
    assert sha(elf.read_bytes()) == binding["sha256"] == ELF_HASH
    with elf.open("rb") as file:
        image = ELFFile(file)
        section = image.get_section(SECTION)
        assert section.name == ".text" and image.elfclass == 32
        assert section["sh_addr"] <= ADDRESS
        assert ADDRESS + SIZE <= section["sh_addr"] + section["sh_size"]
        offset = section["sh_offset"] + ADDRESS - section["sh_addr"]
        file.seek(offset)
        body = file.read(SIZE)
    assert offset == 0x5BFDC and sha(body) == RANGE_HASH
    key = 0x80000100
    entries = [(key + 16 * i, i + 20) for i in range(-16, 16) if i != 0]
    cases = [
        (0, [], 0), (0, [(key, 25)], 55),
        (0, [(key + 16, 7)], 65535), (0, [(key - 16, 7)], 11),
        (0, [(key - 16, 19), (key + 16, 20)], 21), (0, entries, 31),
        (0, entries + [(key + 256, 77)], 32), (0, sorted(entries + [(key, 77)]), 32),
        (48, [], 0), (49, [], 0), (50, [], 0),
        (49, [(key, 12)], 13), (50, [(key, 12)], 13),
    ]
    return dict(elf_sha256=ELF_HASH, range_sha256=RANGE_HASH, address=ADDRESS,
                file_offset=offset, size=SIZE, section=SECTION,
                oracle="Original ARM application instructions. Real Linux libc bsearch on original table bytes with an explicit unsigned-key callback boundary inferred from ARM insertion and pinned CCL API. The original Core comparator and ARM libc are outside this execution.",
                cases=[run_case(body, key, *case) for case in cases])


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
