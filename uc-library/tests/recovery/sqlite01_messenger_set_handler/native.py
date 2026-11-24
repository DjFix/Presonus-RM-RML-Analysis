from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
import unicorn as u
from unicorn import arm_const as arm

SYMBOL = "_ZN8Presonus4Link9Messenger13setMsgHandlerEPN4Core16IPropertyHandlerE"
ELF_PATH = Path("rootfs/RML16AI_Rack_13731/home/root/mixer")
ELF_HASH = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
RANGE_HASH = "4763d2cdf7c709d7e5e74f0ad0e9b17c28533de1a8f8f992797818bdabb7b537"
ADDRESS, OFFSET, SIZE, SECTION = 551568, 518800, 20, 12


def observe():
    elf_path = next(base / ELF_PATH for base in (Path.cwd(), *Path.cwd().parents)
                    if (base / ELF_PATH).is_file())
    raw = elf_path.read_bytes()
    assert sha256(raw).hexdigest() == ELF_HASH
    elf = ELFFile(BytesIO(raw))
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(SYMBOL)
    assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (
        ADDRESS, SIZE, SECTION)
    section = elf.get_section(SECTION)
    assert section.name == ".text" and elf["e_machine"] == "EM_ARM"
    assert section["sh_offset"] + ADDRESS - section["sh_addr"] == OFFSET
    code = raw[OFFSET:OFFSET + SIZE]
    assert sha256(code).hexdigest() == RANGE_HASH

    receiver, stack, ret = 0x200040, 0x301000, 0x400000
    handles = [0, 0x201240, 0x201380]
    machine = u.Uc(u.UC_ARCH_ARM, u.UC_MODE_ARM)
    machine.mem_map(ADDRESS & ~4095, 4096)
    machine.mem_write(ADDRESS, code)
    machine.mem_map(0x200000, 8192)
    machine.mem_map(stack - 4096, 4096)
    machine.mem_map(ret, 4096)
    seed = bytes((index * 17 + 3) % 256 for index in range(144))
    machine.mem_write(receiver - 8, seed)
    machine.mem_write(receiver + 8, bytes(4))

    writes = []
    machine.hook_add(u.UC_HOOK_MEM_WRITE,
                     lambda _, access, addr, size, value, data:
                     writes.append((addr, size, value)))
    program = [1, 2, 2, 0, 1]
    cases = []
    for index in program:
        writes.clear()
        before = bytes(machine.mem_read(receiver - 8, len(seed)))
        for reg, val in [(arm.UC_ARM_REG_SP, stack), (arm.UC_ARM_REG_LR, ret),
                         (arm.UC_ARM_REG_R0, receiver), (arm.UC_ARM_REG_R1, handles[index])]:
            machine.reg_write(reg, val)
        machine.emu_start(ADDRESS, ret, count=5)
        assert machine.reg_read(arm.UC_ARM_REG_PC) == ret
        assert machine.reg_read(arm.UC_ARM_REG_SP) == stack
        after = bytes(machine.mem_read(receiver - 8, len(seed)))
        stored, = struct.unpack_from("<I", after, 16)
        assert stored == handles[index]
        assert after[:16] == before[:16] and after[20:] == before[20:]
        assert [write for write in writes if write[0] >= 0x200000
                and write[0] < 0x202000] == [(receiver + 8, 4, stored)]
        cases.append({"argument": handles[index], "handler": handles.index(stored),
                      "receiver_before": before.hex(), "receiver_after": after.hex(),
                      "changed_offsets": [i - 8 for i, (a, b) in enumerate(zip(before, after))
                                          if a != b],
                      "writes": [list(write) for write in writes]})
    return {"elf_sha256": ELF_HASH, "range_sha256": RANGE_HASH, "address": ADDRESS,
            "file_offset": OFFSET, "size": SIZE, "section": SECTION,
            "unicorn": u.__version__, "cases": cases}


if __name__ == "__main__":
    observations = observe()
    fixture = Path(sys.argv[1])
    if len(sys.argv) == 3 and sys.argv[2] == "--record":
        with fixture.open("x") as stream:
            json.dump(observations, stream, indent=2)
            stream.write("\n")
    elif observations != json.loads(fixture.read_text()):
        raise SystemExit("Native observations differ from frozen fixtures")
    print(f"Native ARM executions: {len(observations['cases'])}")
