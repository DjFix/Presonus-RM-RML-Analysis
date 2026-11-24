"""Execute the exact sealed ARM method with synthetic inputs offline."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import (UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ,
                     UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc, __version__)
from unicorn.arm_const import (
    UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP,
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
    UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10,
)

ORIGINAL = {'elf': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07', 'symbol': '_ZN8Presonus4Link9Messenger5startEv', 'address': 551552, 'size': 16, 'section': 12, 'file_offset': 518784, 'body_hash': '60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad'}
STACK = 0x701000
STATE = 0x710000
LOOKUP = 0x720000
CAST = 0xacf4
REGISTERS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
             UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
             UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_FP)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def observe(body, case, lookup_name):
    address = ORIGINAL["address"]
    end = address + len(body)
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    cpu.mem_map(address & ~0xfff, 0x1000)
    cpu.mem_write(address, body)
    cpu.mem_map(STACK - 0x1000, 0x1000)
    cpu.mem_map(STATE, 0x10000)
    receiver = STATE + 0x1000 * case
    sentinels = {receiver: bytes([0x40 + case]) * 256,
                 STATE + 0x4000: b"stagebox\0", STATE + 0x5000: b"concert\0"}
    if lookup_name:
        cpu.mem_map(LOOKUP, 0x1000)
        cpu.mem_map(CAST & ~0xfff, 0x1000)
        # The original function executes its actual indirect branch and tail
        # branch. Trap at the external boundaries and supply explicit results.
        ret = bytes.fromhex("1eff2fe1")
        cpu.mem_write(LOOKUP, ret)
        cpu.mem_write(CAST, ret)
        name_address, source_rtti, dest_rtti = struct.unpack_from("<3I", body, 56)
        cpu.mem_map(name_address & ~0xfff, 0x1000)
        cpu.mem_write(name_address, lookup_name)
        table = STATE + 0x6000
        sentinels[receiver] = struct.pack("<I", table) + sentinels[receiver][4:]
        cpu.mem_write(table + 0x14, struct.pack("<I", LOOKUP))
    for where, content in sentinels.items():
        cpu.mem_write(where, content)
    args = (receiver, (0, STATE + 0x4000, STATE + 0x5000)[case],
            (0, STATE + 0x5000, STATE + 0x4000)[case], (0, 1, 0xffffffff)[case])
    if ORIGINAL["symbol"].endswith("12panicMuteAllEb"):
        args = (receiver, case % 2, args[2], args[3])
    registers = dict(zip(REGISTERS, (*args, *range(0x120 + case, 0x128 + case))))
    registers.update({UC_ARM_REG_SP: STACK, UC_ARM_REG_LR: end})
    for register, value in registers.items():
        cpu.reg_write(register, value)
    writes, reads, trace, calls = [], [], [], []
    cpu.hook_add(UC_HOOK_MEM_WRITE, lambda _, access, where, size, value, data:
                 writes.append((where, size, value)))
    cpu.hook_add(UC_HOOK_MEM_READ, lambda _, access, where, size, value, data:
                 reads.append((where, size)))

    def code_hook(_, where, size, data):
        trace.append(where)
        call_args = [cpu.reg_read(register) for register in REGISTERS[:4]]
        if where == LOOKUP:
            require(call_args[:2] == [receiver, name_address], "lookup ABI")
            calls.append(["findChild", bytes(cpu.mem_read(name_address, 4)).decode("ascii")])
            cpu.reg_write(UC_ARM_REG_R0, 0 if case == 0 else STATE + 0x7000)
        elif where == CAST:
            require(call_args == [STATE + 0x7000, source_rtti, dest_rtti, 0], "cast ABI")
            calls.append(["dynamic_cast", *call_args])
            cpu.reg_write(UC_ARM_REG_R0, 0 if case == 1 else STATE + 0x7000)

    cpu.hook_add(UC_HOOK_CODE, code_hook)
    cpu.emu_start(address, end, count=24)
    require(cpu.reg_read(UC_ARM_REG_PC) == end, "did not return to LR")
    del registers[UC_ARM_REG_R0]
    if lookup_name:
        for register in (UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_LR):
            del registers[register]
        require(len(calls) == (1 if case == 0 else 2), "unexpected boundary calls")
    else:
        require(len(trace) == len(body) // 4 and all(STACK - 16 <= a < STACK for a, _ in reads),
                "unexpected control flow or non-frame reads")
    require(all(cpu.reg_read(register) == value for register, value in registers.items()),
            "register preservation")
    require([(a, n) for a, n, _ in writes] ==
            [(STACK + offset, 4) for offset in (-16, -12, -8, -4)], "non-frame writes")
    require(all(bytes(cpu.mem_read(a, len(s))) == s for a, s in sentinels.items()),
            "sentinel memory changed")
    r0 = cpu.reg_read(UC_ARM_REG_R0)
    if lookup_name:
        result = "match" if r0 else ("wrong-type" if len(calls) == 2 else "absent")
    elif len(body) == 20:
        result = str(struct.unpack("<i", struct.pack("<I", r0))[0])
    else:
        require(r0 == receiver, "r0 changed in void portable domain")
        result = "unchanged"
    return dict(register_args=args, stack_writes=writes, reads=reads, trace=trace,
                boundaries=calls, final_r0=r0, portable_observation=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    with args.elf.open("rb") as file:
        require(hashlib.file_digest(file, "sha256").hexdigest() == ORIGINAL["elf"], "ELF hash")
        file.seek(0)
        elf = ELFFile(file)
        section = elf.get_section(ORIGINAL["section"])
        symbols = elf.get_section_by_name(".symtab").get_symbol_by_name(ORIGINAL["symbol"])
        require([(row["st_value"], row["st_size"], row["st_shndx"]) for row in symbols] ==
                [(ORIGINAL["address"], ORIGINAL["size"], ORIGINAL["section"])], "symbol range")
        offset = ORIGINAL["address"] - section["sh_addr"]
        require(section.name == ".text" and 0 <= offset <= section["sh_size"] - ORIGINAL["size"],
                "section mapping")
        require(ORIGINAL["file_offset"] == section["sh_offset"] + offset, "file mapping")
        body = section.data()[offset: offset + ORIGINAL["size"]]
        require(hashlib.sha256(body).hexdigest() == ORIGINAL["body_hash"], "body hash")
        lookup_name = b""
        if ORIGINAL["size"] == 68:
            name_address = struct.unpack_from("<I", body, 56)[0]
            name_offset, = elf.address_offsets(name_address, 4)
            file.seek(name_offset)
            lookup_name = file.read(4)
            require(lookup_name == b"avb\0", "ELF lookup string")
    receipt = dict(elf_sha256=ORIGINAL["elf"], range_sha256=ORIGINAL["body_hash"],
                   file_offset=ORIGINAL["file_offset"], mangled=ORIGINAL["symbol"],
                   section=ORIGINAL["section"], address=ORIGINAL["address"], size=ORIGINAL["size"],
                   unicorn=__version__, cases=[observe(body, i, lookup_name) for i in range(3)])
    result = json.dumps(receipt, indent=2) + "\n"
    if args.verify:
        require(result == args.verify.read_text(), "fresh native replay differs")
        print(f"Verified {len(receipt['cases'])} original ARM executions")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
