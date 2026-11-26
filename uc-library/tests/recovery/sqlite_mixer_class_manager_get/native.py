"""Recheck and execute exact ARM lookup ranges, with only libc strcmp hooked."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

WORK, ARRAY, RECORDS, STRINGS, STACK, STOP = range(0x700000, 0x706000, 0x1000)
GET = "_ZNK8Presonus17MixerClassManager13getMixerClassEPKc"
IS = "_ZNK8Presonus17MixerClassManager12isMixerClassEPKc"
ROSTER = ["dup", None, "", "Dup", "dup", "sixth", "last"]
SCENARIOS = [
    ([], None), ([], ""), ([], "missing"),
    *[(ROSTER, name) for name in (None, "", "dup", "Dup", "DUP", "sixth", "last", "missing")],
    (["", None], None), (["abc"], None), (["abc"], ""),
]


def verify_range(elf, original):
    sym, = elf.get_section_by_name(".symtab").get_symbol_by_name(original["mangled"])
    addr, length, index = (sym[key] for key in ("st_value", "st_size", "st_shndx"))
    assert (addr, length, index) == tuple(original[key] for key in ("address", "size", "section"))
    section = elf.get_section(index)
    assert section.name == original["section_name"] == ".text"
    offset = addr - section["sh_addr"]
    assert offset + section["sh_offset"] == original["file_offset"]
    raw = section.data()[offset:offset + length]
    assert len(raw) == length and raw.hex() == original["range_hex"]
    assert sha256(raw).hexdigest() == original["range_sha256"]
    return raw


def load(root, original, get):
    source = root / original["elf_path"]
    assert sha256(source.read_bytes()).hexdigest() == original["elf"] == get["elf"]
    entry, lookup = original["address"], get["address"]
    with source.open("rb") as file:
        elf = ELFFile(file)
        assert elf["e_machine"] == "EM_ARM"
        code = {entry: verify_range(elf, original), lookup: verify_range(elf, get)}
        # The PC-relative literal in getMixerClass points to an ELF-backed empty string.
        literal, = struct.unpack_from("<I", code[lookup], 116)
        segment = next(s for s in elf.iter_sections()
                       if s["sh_addr"] <= literal < s["sh_addr"] + s["sh_size"]
                       and s["sh_type"] != "SHT_NOBITS")
        empty = segment.data()[literal - segment["sh_addr"]:literal - segment["sh_addr"] + 1]
        assert empty == b"\0"
    return code, literal, empty


def execute(entry, lookup, strcmp, code, literal, empty, roster, query):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    pages = {addr & ~4095 for addr in (*code, strcmp, literal, WORK, ARRAY, RECORDS,
                                       STRINGS, STACK, STOP)}
    for addr, raw in code.items():
        pages.add((addr + len(raw) - 1) & ~4095)
    for page in pages:
        machine.mem_map(page, 4096)
    for addr, raw in code.items():
        machine.mem_write(addr, raw)
    machine.mem_write(literal, empty)

    def words(address, *values):
        machine.mem_write(address, struct.pack(f"<{len(values)}I", *values))

    def string(address, value):
        if value is None:
            return 0
        machine.mem_write(address, value.encode("ascii") + b"\0")
        return address

    query_address = string(STRINGS, query)
    record_addresses = [RECORDS + 8 * i for i in range(len(roster))]
    name_addresses = []
    for i, (name, address) in enumerate(zip(roster, record_addresses)):
        name_addresses.append(string(STRINGS + 64 * (i + 1), name))
        words(address, name_addresses[-1], 0x550000 + i * 4)
    words(ARRAY, *record_addresses)
    words(WORK, 0, ARRAY if roster else 0, len(roster), 0, 5)
    compared, lookup_calls = [], []

    def hook(uc, addr, _size, _opaque):
        left, right = (uc.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1))
        if addr == lookup and lookup != entry:
            assert (left, right) == (WORK, query_address)
            lookup_calls.append(addr)
        if addr != strcmp:
            assert any(start <= addr < start + len(body) for start, body in code.items())
            return
        index = len(compared)
        assert left == (query_address or literal)
        assert right == (name_addresses[index] or literal)
        lhs, rhs = (bytes(uc.mem_read(pointer, 32)).split(b"\0", 1)[0].decode("ascii")
                    for pointer in (left, right))
        assert (lhs, rhs) == (query or "", roster[index] or "")
        compared.append([lhs, rhs])
        uc.reg_write(UC_ARM_REG_R0, ((lhs > rhs) - (lhs < rhs)) & 0xffffffff)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    def write_hook(_machine, _access, address, size, _value, _opaque):
        assert STACK <= address and address + size <= STACK + 4096, hex(address)

    machine.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    machine.hook_add(UC_HOOK_CODE, hook)
    for reg, val in ((UC_ARM_REG_R0, WORK), (UC_ARM_REG_R1, query_address),
                     (UC_ARM_REG_LR, STOP), (UC_ARM_REG_SP, STACK + 2048)):
        machine.reg_write(reg, val)
    machine.emu_start(entry, STOP, count=3000)
    assert machine.reg_read(UC_ARM_REG_PC) == STOP
    raw = machine.reg_read(UC_ARM_REG_R0)
    assert lookup_calls == ([lookup] if entry != lookup else [])
    if entry == lookup:
        result = record_addresses.index(raw) if raw else None
    else:
        assert raw in (0, 1)
        result = raw
    return dict(roster=roster, query=query, expected=result, compared=compared,
                lookup_calls=lookup_calls, native_r0=raw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("variant", choices=("get", "is"))
    parser.add_argument("--elf-root", type=Path, required=True)
    parser.add_argument("--emit", action="store_true")
    args = parser.parse_args()
    task = f"sqlite_mixer_class_manager_{args.variant}"
    packet = Path("temp/recovery-work/sqlite-issued/packet") / task / "CONTEXT.json"
    context = json.loads(packet.read_text())
    evidence = next(row for row in context["task"]["review"]["evidence"]
                    if row["path"].endswith("_DIRECT.json"))
    direct_bytes = Path(evidence["path"]).read_bytes()
    assert sha256(direct_bytes).hexdigest() == evidence["sha256"]
    direct = json.loads(direct_bytes)["originals"]
    cases = []
    for item in context["originals"]:
        original = item["original"]
        assert original["mangled"] == (GET if args.variant == "get" else IS)
        rows = {r["original"]["mangled"]: r for r in direct if r["original"]["elf"] == original["elf"]}
        record = rows[GET]
        get = original
        if args.variant == "is":
            get_packet = packet.parent.parent / "sqlite_mixer_class_manager_get/CONTEXT.json"
            get, = [x["original"] for x in json.loads(get_packet.read_text())["originals"]
                    if x["original"]["elf"] == original["elf"]]
        assert record["range_sha256"] == get["range_sha256"]
        assert get["mangled"] == GET
        code, literal, empty = load(args.elf_root, original, get)
        call, = record["calls"]
        assert call["mangled"][0].startswith("strcmp@@")
        for roster, query in SCENARIOS:
            cases.append(dict(original=original, **execute(
                original["address"], get["address"], call["address"], code, literal, empty, roster, query)))
    path = Path(__file__).parent.parent / task / "fixtures.json"
    content = json.dumps({"variant": args.variant, "cases": cases}, indent=2) + "\n"
    if args.emit:
        path.write_text(content)
    else:
        assert path.read_text() == content
    print(f"{task}: verified {len(cases)} original cases")


if __name__ == "__main__":
    main()
