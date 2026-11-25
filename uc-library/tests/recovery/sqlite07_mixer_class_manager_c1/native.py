"""Execute each independently verified original ARM lifecycle entry."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP,
)

TASK = Path(__file__).parent.name
CONTEXT = Path("temp/recovery-work/sqlite-issued/packet") / TASK / "CONTEXT.json"
WORK, ARRAY, RECORDS, STACK, STOP = range(0x700000, 0x705000, 0x1000)


def load_range(original, direct, elf_root):
    path = elf_root / original["elf_path"]
    assert sha256(path.read_bytes()).hexdigest() == original["elf"]
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        symbols = elf.get_section_by_name(".symtab")
        symbol, = symbols.get_symbol_by_name(original["mangled"])
        addr, length, section = (symbol[k] for k in ("st_value", "st_size", "st_shndx"))
        assert (addr, length, section) == tuple(original[k] for k in ("address", "size", "section"))
        sec = elf.get_section(section)
        assert sec.name == original["section_name"] == ".text"
        offset = addr - sec["sh_addr"]
        assert offset + sec["sh_offset"] == original["file_offset"]
        code = sec.data()[offset:offset + length]
        assert len(code) == length
        assert sha256(code).hexdigest() == original["range_sha256"]
        assert code.hex() == original["range_hex"]
        vtable, = symbols.get_symbol_by_name(
            "_ZTVN4Core6VectorIPN8Presonus17MixerClassManager10MixerClassEEE"
        )

    target, = [row for row in direct if
               (row["original"]["elf"], row["original"]["mangled"]) ==
               (original["elf"], original["mangled"])]
    assert target["range_sha256"] == original["range_sha256"]
    call_names = {
        "6resizeEi": "vector_resize",
        "_ZdlPv": "record_delete",
        "EED1Ev": "vector_destroy",
    }
    calls = {}
    for call in target["calls"]:
        label, = [name for token, name in call_names.items()
                  if any(token in mangled for mangled in call["mangled"])]
        calls[call["address"]] = label
    return code, calls, vtable["st_value"] + 8


def execute(original, code, calls, vptr, count):
    entry = original["address"]
    constructor = "C" in original["mangled"][-4:]
    emu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for page in {addr & ~4095 for addr in (entry, entry + len(code) - 1, *calls,
                                           WORK, ARRAY, RECORDS, STACK, STOP)}:
        emu.mem_map(page, 4096)
    emu.mem_write(entry, code)

    def get(addr):
        return struct.unpack("<I", emu.mem_read(addr, 4))[0]

    def put(addr, *values):
        emu.mem_write(addr, struct.pack(f"<{len(values)}I", *values))

    expected_header = (vptr, ARRAY if count else 0, count,
                       ((count + 4) // 5) * 5, 5)
    records = [RECORDS + i * 8 for i in range(count)]
    borrowed = [(0x121000 + i * 4, 0x133000 + i * 8) for i in range(count)]
    if constructor:
        put(WORK, *([0xA5A5A5A5] * 5))
    else:
        put(WORK, *expected_header)
        for i, (record, fields) in enumerate(zip(records, borrowed)):
            put(ARRAY + i * 4, record)
            put(record, *fields)

    events = []

    def hook(machine, addr, _size, _opaque):
        if addr not in calls:
            assert entry <= addr < entry + len(code), hex(addr)
            return
        label = calls[addr]
        arg = machine.reg_read(UC_ARM_REG_R0)
        if label == "record_delete":
            index = records.index(arg)
            assert (get(arg), get(arg + 4)) == borrowed[index]
            events.append([label, index])
            put(arg, 0xDEADDEAD, 0xDEADDEAD)
        else:
            assert arg == WORK
            assert tuple(get(WORK + 4 * i) for i in range(5)) == expected_header
            if label == "vector_resize":
                assert machine.reg_read(UC_ARM_REG_R1) == 0
                events.append([label, 0])
                machine.reg_write(UC_ARM_REG_R0, 1)
            else:
                assert label == "vector_destroy"
                events.append([label])
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    emu.hook_add(UC_HOOK_CODE, hook)
    emu.reg_write(UC_ARM_REG_R0, WORK)
    emu.reg_write(UC_ARM_REG_LR, STOP)
    emu.reg_write(UC_ARM_REG_SP, STACK + 2048)
    emu.emu_start(entry, STOP, count=1000)
    assert emu.reg_read(UC_ARM_REG_PC) == STOP
    assert emu.reg_read(UC_ARM_REG_R0) == WORK
    assert tuple(get(WORK + 4 * i) for i in range(5)) == expected_header
    if constructor:
        assert events == [["vector_resize", 0]]
    else:
        assert events == [["record_delete", i] for i in range(count)] + [["vector_destroy"]]
    return {"count": count, "events": events, "observed_native_fields": expected_header}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit", action="store_true")
    parser.add_argument("--elf-root", type=Path, default=Path("."))
    args = parser.parse_args()
    packet = json.loads(CONTEXT.read_text())
    direct_path = next(Path(path) for path in packet["read_files"] if path.endswith("_DIRECT.json"))
    direct = json.loads(direct_path.read_text())["originals"]
    cases = []
    for item in packet["originals"]:
        original = item["original"]
        code, calls, vptr = load_range(original, direct, args.elf_root)
        counts = (0,) if "C" in original["mangled"][-4:] else (0, 2, 6)
        for count in counts:
            cases.append({"original": original, **execute(original, code, calls, vptr, count)})
    fixture = Path(__file__).with_name("fixtures.json")
    payload = json.dumps({"cases": cases}, indent=2) + "\n"
    if args.emit:
        fixture.write_text(payload)
    else:
        assert fixture.read_text() == payload
    print(f"{TASK}: {len(cases)} verified native scenarios")


if __name__ == "__main__":
    main()
