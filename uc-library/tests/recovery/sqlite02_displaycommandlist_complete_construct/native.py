"""Execute the exact native constructor and bounded application code that consumes it."""
import ctypes
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP,
)

TASK = Path(__file__).resolve().parent.name
CONTEXT = Path("temp/recovery-work/sqlite-issued/packet") / TASK / "CONTEXT.json"
BITMAP, RECT, COLOR = 0x123000, 0x124000, 0x124020
OBJECT_SIZE = 0x1188
STACK, STOP = 0x13F000, 0x140000
ARGS = [-2, 17, 3, -5, 23, 19]
BOUNDS = [-11, 19, 103, 200]
RGBA = [21, 43, 65, 87]
GEOMETRY = "_ZN8Presonus18DisplayCommandList8fillRectERKN4Core5TRectIiEERKNS1_5ColorE"
DRAW = "_ZN8Presonus18DisplayCommandList10drawBitmapEiiRKN4Core8Portable6BitmapEiiii"

COMPARATOR = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
BSEARCH = ctypes.CDLL("libc.so.6").bsearch
BSEARCH.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t, COMPARATOR,
]
BSEARCH.restype = ctypes.c_void_p


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verified_body(image, name):
    matches = image.get_section_by_name(".symtab").get_symbol_by_name(name)
    assert len(matches) == 1
    symbol = matches[0]
    section_idx = symbol["st_shndx"]
    section = image.get_section(section_idx)
    address, length = symbol["st_value"], symbol["st_size"]
    relative = address - section["sh_addr"]
    assert section.name == ".text" and 0 <= relative <= section["sh_size"] - length
    body = section.data()[relative:relative + length]
    return body, dict(mangled=name, address=address, size=length, section=section_idx,
                      section_name=section.name, file_offset=section["sh_offset"] + relative,
                      range_sha256=digest(body))


def observe_state(machine, receiver):
    data = machine.mem_read(receiver, OBJECT_SIZE)
    u32 = lambda offset: struct.unpack_from("<I", data, offset)[0]
    bitmap_count = u32(0x1080)
    return dict(count=u32(8), auxiliary_cursor=u32(0x3F8),
                next_bitmap_id=struct.unpack_from("<H", data, 0x1184)[0],
                bitmap_count=bitmap_count,
                entries=[list(struct.unpack_from("<IH", data, 0x1084 + 8 * i))
                         for i in range(bitmap_count)])


def run_case(bodies, receiver, poison):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    machine.mem_map(0xA000, 0x1000)
    machine.mem_map(0x62000, 0x3000)
    machine.mem_map(0x120000, 0x21000)
    for body, identity in bodies:
        machine.mem_write(identity["address"], body)
    machine.mem_write(receiver - 8, bytes([poison]) * (OBJECT_SIZE + 16))
    machine.mem_write(RECT, struct.pack("<4i", *BOUNDS))
    machine.mem_write(COLOR, bytes(RGBA))
    writes = []
    calls = []

    def write_hook(uc, access, address, size, value, user_data):
        if receiver - 8 <= address < receiver + OBJECT_SIZE + 8:
            assert receiver <= address and address + size <= receiver + OBJECT_SIZE
            writes.append([address - receiver, size, value])

    def bsearch_hook(uc, address, size, user_data):
        pointer, table, count, stride = [
            uc.reg_read(register) for register in (
                UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
            )
        ]
        callback = struct.unpack("<I", uc.mem_read(uc.reg_read(UC_ARM_REG_SP), 4))[0]
        assert (table, count, stride, callback) == (receiver + 0x1084, 0, 8, 0x6445C)
        key_data = bytes(uc.mem_read(pointer, stride))
        assert struct.unpack_from("<I", key_data)[0] == BITMAP

        @COMPARATOR
        def unused_comparator(left, right):
            calls.append(["unexpected-comparison"])
            return 0

        assert BSEARCH(key_data, b"", count, stride, unused_comparator) is None
        calls.append(dict(count=count, stride=stride, callback=callback,
                          key=BITMAP, result=None))
        uc.reg_write(UC_ARM_REG_R0, 0)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    machine.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    machine.hook_add(UC_HOOK_CODE, bsearch_hook, begin=0xAC84, end=0xAC84)

    def execute(identity, registers, stack_args=()):
        machine.mem_write(STACK, struct.pack("<4i", *stack_args) if stack_args else bytes(16))
        for register, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3),
                                   registers):
            machine.reg_write(register, value & 0xFFFFFFFF)
        machine.reg_write(UC_ARM_REG_SP, STACK)
        machine.reg_write(UC_ARM_REG_LR, STOP)
        machine.emu_start(identity["address"], STOP, count=3000)
        assert machine.reg_read(UC_ARM_REG_PC) == STOP

    execute(bodies[0][1], (receiver,))
    assert machine.reg_read(UC_ARM_REG_R0) == receiver
    constructor_writes = writes.copy()
    initial_bytes = bytes(machine.mem_read(receiver, OBJECT_SIZE))
    expected = bytearray([poison]) * OBJECT_SIZE
    for offset, size, value in constructor_writes:
        expected[offset:offset + size] = value.to_bytes(size, "little")
    assert initial_bytes == expected
    assert initial_bytes[0xC:0x3F4] == bytes([poison]) * 1000
    assert struct.unpack_from("<I", initial_bytes, 4)[0] == receiver + 12
    assert struct.unpack_from("<I", initial_bytes, 0x3F4)[0] == receiver + 0x3FC
    assert struct.unpack_from("<I", initial_bytes, 0x107C)[0] == receiver + 0x1084
    assert initial_bytes[0x3FC:0x107C:64] == bytes(50)
    assert all(bytes(initial_bytes[0x1084 + 8*i:0x108A + 8*i]) == bytes(6)
               for i in range(32))
    initial = observe_state(machine, receiver)
    writes.clear()
    execute(bodies[1][1], (receiver, RECT, COLOR))
    execute(bodies[2][1], (receiver, *ARGS[:2], BITMAP), ARGS[2:])
    result = observe_state(machine, receiver)
    commands = bytes(machine.mem_read(receiver + 12, result["count"] * 20))
    command_offsets = sorted({i - 12 for offset, width, _ in writes
                              for i in range(offset, offset + width)
                              if 12 <= i < 12 + len(commands)})
    assert len(calls) == 1 and isinstance(calls[0], dict)
    return dict(receiver=receiver, poison=poison, constructor_writes=constructor_writes,
                initial=initial, result=result, native_commands=commands.hex(),
                command_offsets=command_offsets, operation_writes=writes, bsearch=calls[0])


def main():
    original = json.loads(CONTEXT.read_text())["originals"][0]["original"]
    elf = Path(original["elf_path"])
    assert digest(elf.read_bytes()) == original["elf"]
    with elf.open("rb") as stream:
        image = ELFFile(stream)
        assert image.elfclass == 32 and image["e_machine"] == "EM_ARM" and image.little_endian
        bodies = [verified_body(image, name) for name in (original["mangled"], GEOMETRY, DRAW)]
    body, identity = bodies[0]
    assert all(value == original[key] for key, value in identity.items())
    assert body.hex() == original["range_hex"]
    return dict(original=identity, elf_sha256=original["elf"], elf_path=original["elf_path"],
                operations=[row for _, row in bodies[1:]], bitmap_key=BITMAP,
                bitmap_args=ARGS, rect=BOUNDS, rgba=RGBA,
                cases=[run_case(bodies, 0x128000, 0xA5), run_case(bodies, 0x12A000, 0x3C)])


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
