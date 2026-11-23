"""Run exact native notify and fallback instructions with bounded provider hooks."""
import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

import unicorn
from elftools.elf.elffile import ELFFile
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

ELF_HASH = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
TARGET = "_ZN8Presonus5Mixer18FilterGroupManager6notifyERKNS_2UC17MessageAttributesE"
FALLBACK = "_ZN8Presonus2UC15ServerComponent6notifyERKNS0_17MessageAttributesE"
TARGET_HASH = "8dd34983433e30769e9234158c7deff26639e11e387c42215d603d2da258431c"
FALLBACK_HASH = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
RECEIVER, MESSAGE, ID, VECTOR, STACK, EXIT = (
    0x600000, 0x601000, 0x601100, 0x602000, 0x610000, 0x620000
)
CHILDREN = [0x603000, 0x604000, 0x605000, 0x606000]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def symbol_range(elf, name, expected_address, expected_size, expected_hash, expected_type):
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    assert symbol["st_info"]["type"] == expected_type
    address = symbol["st_value"]
    size = symbol["st_size"]
    section = elf.get_section(symbol["st_shndx"])
    rel = address - section["sh_addr"]
    assert (address, size) == (expected_address, expected_size)
    assert 0 <= rel <= section["sh_size"] - size
    row = dict(mangled=name, address=address, size=size, section=section.name,
               section_index=symbol["st_shndx"])
    if section["sh_type"] == "SHT_NOBITS":
        assert expected_hash is None
        row["storage"] = "ELF zero-initialized SHT_NOBITS"
    else:
        actual = sha(section.data()[rel:rel + size])
        assert actual == expected_hash
        row.update(file_offset=section["sh_offset"] + rel, range_sha256=actual)
    return row


def case(elf, message_id, old, new):
    arm = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    arm.mem_map(0x8000, 0x4A0000 - 0x8000)
    for segment in elf.iter_segments():
        if segment["p_type"] == "PT_LOAD":
            arm.mem_write(segment["p_vaddr"], segment.data())
    arm.mem_map(RECEIVER, 0x21000)

    def write_words(address, values):
        arm.mem_write(address, struct.pack(f"<{len(values)}I", *values))

    def c_string(address):
        return bytes(arm.mem_read(address, 32)).split(b"\0", 1)[0].decode("ascii")

    def read(reg):
        return arm.reg_read(reg)

    def result(value):
        arm.reg_write(UC_ARM_REG_R0, value & 0xFFFFFFFF)
        arm.reg_write(UC_ARM_REG_PC, read(UC_ARM_REG_LR))

    children = CHILDREN.copy()
    write_words(RECEIVER + 0x58, [VECTOR, len(children)])
    write_words(VECTOR, children)
    if message_id is not None:
        arm.mem_write(ID, message_id.encode("ascii") + b"\0")
    trace = []
    fallback_instructions = []
    fallback_accesses = []
    invalid_old = False

    def code(_, address, size, __):
        nonlocal invalid_old
        r0, r1, r2 = map(read, (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        if address == 0xFFF08:
            assert r0 == MESSAGE
            trace.append(["getID", message_id])
            result(ID if message_id is not None else 0)
        elif address == 0xAF70:
            left, right = c_string(r0), c_string(r1)
            trace.append(["strcmp", left, right])
            result((left > right) - (left < right))
        elif address == 0x1223B4:
            assert r0 == MESSAGE
            key = c_string(r1)
            value = {"ReorderOldIndex": old, "ReorderNewIndex": new}[key]
            trace.append(["getInt", key, value])
            result(value)
        elif address == 0x11954C:
            assert r0 == RECEIVER
            child = CHILDREN.index(r1) if r1 else None
            trace.append(["removeChild", child])
            if child is None:
                # Stop on the pinned provider precondition boundary. Its original
                # firmware implementation, assertions and continuation are excluded.
                invalid_old = True
                arm.emu_stop()
                return
            children.remove(r1)
            result(0)
        elif address == 0x119C78:
            assert r0 == RECEIVER
            assert 0 <= r1 <= len(children) and r2 not in children
            trace.append(["insertChildAt", r1, CHILDREN.index(r2)])
            children.insert(r1, r2)
            result(1)
        elif address == 0x5B2E0:
            assert r0 == RECEIVER
            trace.append(["resetChannelNames", [CHILDREN.index(c) for c in children]])
            result(0)
        elif 0xF5BB4 <= address < 0xF5BC4:
            if address == 0xF5BB4:
                assert (r0, r1) == (RECEIVER, MESSAGE)
                trace.append(["fallback"])
            fallback_instructions.append(address)
        else:
            assert 0x5B4A8 <= address < 0x5B560, hex(address)

    def memory(_, access, address, size, value, __):
        if 0xF5BB4 <= read(UC_ARM_REG_PC) < 0xF5BC4:
            assert STACK - 0x100 <= address < STACK
            fallback_accesses.append([access, address - STACK, size])

    arm.hook_add(unicorn.UC_HOOK_CODE, code)
    arm.hook_add(unicorn.UC_HOOK_MEM_READ | unicorn.UC_HOOK_MEM_WRITE, memory)
    for register, value in ((UC_ARM_REG_R0, RECEIVER), (UC_ARM_REG_R1, MESSAGE),
                            (UC_ARM_REG_SP, STACK), (UC_ARM_REG_LR, EXIT)):
        arm.reg_write(register, value)
    arm.emu_start(0x5B4A8, EXIT, count=100)
    assert read(UC_ARM_REG_PC) == (0x11954C if invalid_old else EXIT)
    if not invalid_old:
        assert fallback_instructions == list(range(0xF5BB4, 0xF5BC4, 4))
    return dict(input=[message_id, old, new], trace=trace,
                original_completed=not invalid_old,
                fallback_instructions=fallback_instructions,
                fallback_stack_accesses=fallback_accesses,
                order=[CHILDREN.index(c) for c in children])


def observe(path):
    data = path.read_bytes()
    assert sha(data) == ELF_HASH
    elf = ELFFile(io.BytesIO(data))
    assert elf["e_machine"] == "EM_ARM" and elf.little_endian
    ranges = [
        symbol_range(elf, TARGET, 0x5B4A8, 200, TARGET_HASH, "STT_FUNC"),
        symbol_range(elf, FALLBACK, 0xF5BB4, 16, FALLBACK_HASH, "STT_FUNC"),
        symbol_range(elf, "_ZN4Core11ConstVectorIPNS_8Portable9ComponentEE5errorE",
                     0x4930C4, 4, None, "STT_OBJECT"),
    ]
    reorder = "ReorderChannels"
    inputs = [
        (None, 0, 3), ("reorderChannels", 0, 3), ("", 2, 1),
        (reorder, 0, 3), (reorder, 3, 0), (reorder, 2, 2),
        (reorder, 2, 1), (reorder, -1, 1), (reorder, 4, 0),
    ]
    return dict(elf_sha256=ELF_HASH, unicorn_version=unicorn.__version__,
                ranges=ranges, cases=[case(elf, *item) for item in inputs])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--out", type=Path)
    action.add_argument("--verify", type=Path)
    args = parser.parse_args()
    observed = observe(args.elf)
    if args.out:
        with args.out.open("x") as stream:
            json.dump(observed, stream, indent=2)
            stream.write("\n")
    else:
        assert observed == json.loads(args.verify.read_text())
        print(f"{len(observed['cases'])} exact ARM observations reproduced")
