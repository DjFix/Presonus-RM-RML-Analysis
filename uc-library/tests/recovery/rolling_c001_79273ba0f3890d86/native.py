"""Replay the exact identified ARM body against bounded independent list layouts."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from struct import pack

from elftools.elf.elffile import ELFFile
import unicorn as uc
from unicorn.arm_const import UC_ARM_REG_CPSR, UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

STACK = 0x101000
DATA = 0x200000
STOP = 0x300000
RECEIVER = DATA + 0x100
ROSTER_COUNTS = [(0, 0), (1, 7), (3, 1), (4, 4), (5, 17), (8, 3),
                 (15, 16), (16, 15), (17, 5), (32, 32), (2, 0), (0, 2)]


def execute(code, address, listeners, talkers):
    machine = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_ARM)
    machine.mem_map(address & ~4095, 8192)
    machine.mem_write(address, code)
    machine.mem_map(STACK - 4096, 4096, uc.UC_PROT_READ | uc.UC_PROT_WRITE)
    machine.mem_map(DATA, 4096, uc.UC_PROT_READ | uc.UC_PROT_WRITE)
    machine.mem_map(STOP, 4096)
    for head_offset, roster_base, length in ((0x80, DATA + 0x300, listeners),
                                              (0x74, DATA + 0x700, talkers)):
        machine.mem_write(RECEIVER + head_offset, pack("<I", roster_base if length else 0))
        for index in range(length):
            node = roster_base + 16 * index
            next_node = node + 16 if index + 1 < length else 0
            machine.mem_write(node, pack("<II", 0xF0000000 + index, next_node))

    accesses = []
    machine.hook_add(uc.UC_HOOK_MEM_READ | uc.UC_HOOK_MEM_WRITE,
                     lambda engine, kind, address, size, value, _: accesses.append((kind, address, size)))
    machine.reg_write(UC_ARM_REG_CPSR, 0x10)
    machine.reg_write(UC_ARM_REG_R0, RECEIVER)
    machine.reg_write(UC_ARM_REG_SP, STACK)
    machine.reg_write(UC_ARM_REG_FP, 0x12345678)
    machine.reg_write(UC_ARM_REG_LR, STOP)
    machine.emu_start(address, STOP, count=512)
    assert machine.reg_read(UC_ARM_REG_PC) == STOP
    assert machine.reg_read(UC_ARM_REG_SP) == STACK
    assert machine.reg_read(UC_ARM_REG_FP) == 0x12345678
    assert all(size == 4 for _, _, size in accesses)
    assert sorted(addr for kind, addr, _ in accesses if kind == uc.UC_MEM_WRITE) == [
        STACK - 16, STACK - 12, STACK - 8, STACK - 4
    ]
    result = machine.reg_read(UC_ARM_REG_R0)
    return {"listeners": listeners, "talkers": talkers, "result": result,
            "data_reads": [addr - DATA for kind, addr, _ in accesses
                           if kind == uc.UC_MEM_READ and DATA <= addr < DATA + 4096]}


def observe(original):
    path = Path(original["frozen_elf"])
    assert sha256(path.read_bytes()).hexdigest() == original["elf_sha256"]
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        assert elf["e_machine"] == "EM_ARM" and elf.little_endian
        records = [sym for sym in elf.get_section_by_name(".symtab").get_symbol_by_name(original["mangled"])
                   if sym["st_value"] == original["address"] and sym["st_size"] == original["size"]]
        assert len(records) == 1
        assert records[0]["st_shndx"] == original["section_index"]
        sec = elf.get_section(original["section_index"])
        offset = sec["sh_offset"] + original["address"] - sec["sh_addr"]
        assert sec.name == original["section"] and offset == original["file_offset"]
        assert sec["sh_addr"] <= original["address"] <= sec["sh_addr"] + sec["sh_size"] - original["size"]
        stream.seek(offset)
        code = stream.read(original["size"])
    assert sha256(code).hexdigest() == original["range_sha256"]
    cases = [execute(code, original["address"], lhs, rhs) for lhs, rhs in ROSTER_COUNTS]
    # Distinct receiver offsets and independent rosters detect a wrong list.
    head = 0x74 if "Talkers" in original["mangled"] else 0x80
    base = 0x700 if head == 0x74 else 0x300
    key = "talkers" if head == 0x74 else "listeners"
    for case in cases:
        assert case["data_reads"] == [0x100 + head] + [
            base + 16 * index + 4 for index in range(case[key])
        ]
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    fixtures = json.loads(args.fixtures.read_text())
    observations = [observe(original) for original in fixtures["originals"]]
    if args.record:
        assert "observations" not in fixtures
        fixtures.update(unicorn_version=uc.__version__, observations=observations)
        args.fixtures.write_text(json.dumps(fixtures, indent=2) + "\n")
    else:
        assert observations == fixtures["observations"]
    print(json.dumps({"native_verified": True, "cases_per_original": [len(cases) for cases in observations]}))


if __name__ == "__main__":
    main()
