"""Replay the exact RM metadata getter against seeded ParamInfo words."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

TASK = "sqlite02_slreverbcontroller_get_parameter_info"
PACKET = Path(f"temp/recovery-work/sqlite-issued/packet/{TASK}/CONTEXT.json")


def native_image(packet):
    original, = json.loads(packet.read_text())["originals"]
    original = original["original"]
    path = Path(original["elf_path"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original["elf"]
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(original["mangled"])
        start, size, number = original["address"], original["size"], original["section"]
        assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (start, size, number)
        section = elf.get_section(number)
        relative = start - section["sh_addr"]
        assert section.name == original["section_name"]
        assert 0 <= relative <= section["sh_size"] - size
        assert relative + section["sh_offset"] == original["file_offset"]
        body = section.data()[relative:relative + size]
        assert body.hex() == original["range_hex"]
        assert hashlib.sha256(body).hexdigest() == original["range_sha256"]
        segments = [
            (segment["p_vaddr"], segment["p_memsz"], segment.data())
            for segment in elf.iter_segments() if segment["p_type"] == "PT_LOAD"
        ]
    return original, segments


def machine(segments):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    begin = min(address for address, _, _ in segments) & ~4095
    end = (max(address + size for address, size, _ in segments) + 4095) & ~4095
    uc.mem_map(begin, end - begin)
    for address, _, data in segments:
        uc.mem_write(address, data)
    uc.mem_map(0x10000000, 4096)
    uc.mem_map(0x20000000, 4096)
    return uc


def observe(original, segments, index, byte_size):
    uc = machine(segments)
    receiver, info, stack, stop = 0x10000000, 0x10000400, 0x20000800, 0x30000000
    source = (0x3417, 0, 0, 0xf1f2, 0x7851, 0x137f, byte_size, 0)
    uc.mem_write(info, struct.pack("<8I", *source))
    uc.mem_write(receiver, bytes([0xA7]) * 1024)
    for reg, value in [(UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, info),
                       (UC_ARM_REG_R2, index & 0xffffffff), (UC_ARM_REG_SP, stack),
                       (UC_ARM_REG_LR, stop)]:
        uc.reg_write(reg, value)
    offsets = []

    def trace(_uc, address, size, _data):
        assert size == 4 and original["address"] <= address < original["address"] + original["size"]
        offsets.append(address - original["address"])

    uc.hook_add(UC_HOOK_CODE, trace)
    uc.emu_start(original["address"], stop, count=64)
    assert uc.reg_read(UC_ARM_REG_PC) == stop
    assert uc.reg_read(UC_ARM_REG_SP) == stack
    assert uc.mem_read(receiver, 1024) == bytes([0xA7]) * 1024
    after = list(struct.unpack("<8I", uc.mem_read(info, 32)))
    pointers = {key: after[key] for key in (1, 2, 7)}
    for key, address in pointers.items():
        after[key] = bytes(uc.mem_read(address, 24)).split(b"\0", 1)[0].decode() if address else "-"
    return {"index": index, "byte_size": byte_size, "r0": uc.reg_read(UC_ARM_REG_R0),
            "offsets": offsets, "output": after, "literal_addresses": list(pointers.values())}


def result():
    original, segments = native_image(PACKET)
    cases = [observe(original, segments, index, size)
             for index in (-2147483648, -1, 0, 1, 2, 3, 4, 57, 2147483647)
             for size in (4, 32)]
    return {"original": original, "cases": cases}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    data = result()
    if args.record:
        with args.fixture.open("x") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
    else:
        assert json.loads(args.fixture.read_text()) == data
    print(f"PASS {len(data['cases'])} ARM cases")


if __name__ == "__main__":
    main()
