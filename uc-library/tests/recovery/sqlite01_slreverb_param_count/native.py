"""Execute the exact firmware getter on bytes from the native constructor."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R11, UC_ARM_REG_SP,
)

ELF_PATH = Path("rootfs/RML16AI_Rack_13731/home/root/mixer")
ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
MANGLED = "_ZNK8Presonus3Dsp18SLReverbController16getNumParametersEv"
VTABLE = "_ZTVN8Presonus3Dsp18SLReverbControllerE"
RANGE_SHA = "4c8a1b0970af641c2078e1d2d379bcade6ba048e5128f7b1e6bc8c3743fc7c2b"
CTOR_FIXTURE = Path(__file__).parent.parent / "frontier-scale02/frontier02_w03/fixtures.json"
ADDRESS, SIZE, SECTION, OFFSET = 0xBD5A8, 20, 12, 742824


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verified_range(path):
    assert digest(path.read_bytes()) == ELF_SHA
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        symbols = elf.get_section_by_name(".symtab")
        sym, = (s for s in symbols.iter_symbols() if s.name == MANGLED)
        assert (sym["st_value"], sym["st_size"], sym["st_shndx"]) == (
            ADDRESS, SIZE, SECTION,
        )
        assert sym["st_info"]["type"] == "STT_FUNC"
        section = elf.get_section(SECTION)
        assert section.name == ".text"
        table, = (s for s in symbols.iter_symbols() if s.name == VTABLE)
        table_section = elf.get_section(table["st_shndx"])
        table_address = table["st_value"]
        table_displacement = table_address - table_section["sh_addr"]
        table_file_offset = table_section["sh_offset"] + table_displacement
        assert table["st_size"] >= 24
        stream.seek(table_file_offset + 20)
        slot_target, = struct.unpack("<I", stream.read(4))
        assert slot_target == ADDRESS
        displacement = ADDRESS - section["sh_addr"]
        assert 0 <= displacement <= section["sh_size"] - SIZE
        assert section["sh_offset"] + displacement == OFFSET
        stream.seek(OFFSET)
        body = stream.read(SIZE)
    assert digest(body) == RANGE_SHA
    return body, {"mangled": VTABLE, "address": table_address, "file_offset": table_file_offset,
                  "slot_offset": 20, "slot_target": slot_target}


def observe(body, case):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    code_page = ADDRESS & ~0xFFF
    receiver_page, stack_page, stop = 0x10000000, 0x20000000, 0x30000000
    receiver, sp = receiver_page + 0x400, stack_page + 0x800
    fp = 0xDEADBEEF
    for page in (code_page, receiver_page, stack_page):
        uc.mem_map(page, 4096)
    uc.mem_write(ADDRESS, body)
    uc.mem_write(receiver_page, bytes([0xA7]) * 4096)
    uc.mem_write(receiver, bytes.fromhex(case["memory"]))
    uc.mem_write(stack_page, bytes([0x5D]) * 4096)
    receiver_before = bytes(uc.mem_read(receiver_page, 4096))
    stack_before = bytes(uc.mem_read(stack_page, 4096))
    uc.reg_write(UC_ARM_REG_R0, receiver)
    uc.reg_write(UC_ARM_REG_R11, fp)
    uc.reg_write(UC_ARM_REG_SP, sp)
    uc.reg_write(UC_ARM_REG_LR, stop)
    executed, writes = [], []

    def trace(machine, address, size, _):
        assert ADDRESS <= address < ADDRESS + SIZE and size == 4
        executed.append(address - ADDRESS)

    def write(machine, access, address, size, value, _):
        assert sp - 16 <= address and address + size <= sp
        writes.append([address - sp, size, value])

    uc.hook_add(UC_HOOK_CODE, trace)
    uc.hook_add(UC_HOOK_MEM_WRITE, write)
    uc.emu_start(ADDRESS, stop, count=32)
    assert uc.reg_read(UC_ARM_REG_PC) == stop
    assert uc.reg_read(UC_ARM_REG_SP) == sp
    assert uc.reg_read(UC_ARM_REG_R11) == fp
    assert bytes(uc.mem_read(receiver_page, 4096)) == receiver_before
    stack_after = bytes(uc.mem_read(stack_page, 4096))
    assert stack_after[:0x7F0] == stack_before[:0x7F0]
    assert stack_after[0x800:] == stack_before[0x800:]
    return {
        "id": case["id"],
        "receiver_sha256": digest(bytes.fromhex(case["memory"])),
        "r0": uc.reg_read(UC_ARM_REG_R0),
        "executed_offsets": executed,
        "stack_writes": writes,
        "receiver_and_canaries_unchanged": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    root = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / ELF_PATH).is_file())
    body, vtable = verified_range(root / ELF_PATH)
    seed = CTOR_FIXTURE.read_bytes()
    ctor = json.loads(seed)
    assert ctor["elf_sha256"] == ELF_SHA
    for case in ctor["cases"]:
        assert struct.unpack_from("<I", bytes.fromhex(case["memory"])) == (vtable["address"] + 8,)
    result = {
        "elf_sha256": ELF_SHA,
        "mangled": MANGLED,
        "address": ADDRESS,
        "size": SIZE,
        "section": SECTION,
        "section_name": ".text",
        "file_offset": OFFSET,
        "range_sha256": RANGE_SHA,
        "range_hex": body.hex(),
        "vtable": vtable,
        "constructor_fixture_sha256": digest(seed),
        "cases": [observe(body, case) for case in ctor["cases"]],
    }
    if args.record:
        with args.fixture.open("x") as stream:
            stream.write(json.dumps(result, indent=2) + "\n")
    else:
        assert json.loads(args.fixture.read_text()) == result
    print(f"PASS {len(result['cases'])} original executions with exact range and canaries")


if __name__ == "__main__":
    main()
