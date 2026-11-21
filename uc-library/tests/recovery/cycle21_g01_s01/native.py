"""Execute one exact original ARM mixer method per fixture case."""
import hashlib
import io
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_LR,
    UC_ARM_REG_SP, UC_ARM_REG_PC,
)

SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
MIXER = 0x300000
BUFFER = 0x301000
CALL = 0x302000
STOP = 0x303000
VTABLE = 0x304000
OBJECT = 0x305000
MASTER = 0x30A000
ARGUMENT = 0x30B000
PARAM = 0x30C000
WORD = struct.Struct("<I")

METHODS = {
    1: (0x2FAFC, 76, "cf474405535012ac7de2ff2ff695f554477834b03b75a2df0a11b20467b1c15f",
        [("", "a"), ("a", "a"), ("aba", "z"), ("bca", "a")]),
    2: (0x313DC, 108, "211d9f0f5671d9d4350ad7d9214d094bfffb525a51d54ce622a5382842396443",
        [("", ""), ("nbb", ""), ("bnabt", ""), ("natt", ""), ("tt", "")]),
    3: (0x31378, 100, "81e428642eb99895feee47a8dab63bbb8ec8642a160fd359d02a45ffa945bbf9",
        [("", ""), ("azb", ""), ("z", ""), ("cab", "")]),
    4: (0x31314, 100, "8ffeb4835a495203de26d0373080916151e453be5bbe519fca7c7bd1b81e4dfb",
        [("", ""), ("azb", ""), ("z", ""), ("cab", "")]),
    5: (0x31ACC, 148, "8157393f38073abb7acf6b5c621e27db1d0bbc8418f085e934ac14dde4ce8c8d",
        [("", ""), ("abc", "ac"), ("abc", ""), ("ab", "ab")]),
}


def run(text, index, address, body, sequence, option):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(address & ~0xFFF, 0x2000)
    uc.mem_write(address, body)
    uc.mem_map(MIXER, 0x20000)
    write = lambda at, value: uc.mem_write(at, WORD.pack(value))
    read = lambda at: WORD.unpack(uc.mem_read(at, 4))[0]
    events = []
    writes = []
    identities = {}
    channel = 0 if option == "z" else ARGUMENT
    if index == 1:
        write(MIXER + 0x370, BUFFER)
        write(MIXER + 0x374, len(sequence))
        uc.mem_map(0x52000, 0x1000)
        uc.mem_write(0x52BEC, text(0x52BEC, 16))
        uc.mem_map(0x65000, 0x1000)
        uc.mem_write(0x651CC, text(0x651CC, 12))
        for i, destination in enumerate((CALL, 0x651CC, 0x52BEC)):
            write(VTABLE + i * 0x100 + 0x10, destination)
        for i, name in enumerate(sequence):
            receiver = OBJECT + (ord(name) - ord("a")) * 0x100
            adjustment = 132 if name == "b" else 0
            identities[receiver] = name
            write(BUFFER + 4*i, receiver + adjustment)
            write(receiver + adjustment, VTABLE + (ord(name) - ord("a")) * 0x100)
        uc.reg_write(UC_ARM_REG_R1, channel)
    elif index == 2:
        write(MIXER + 0x148, BUFFER)
        write(MIXER + 0x14C, len(sequence))
        for i, name in enumerate(sequence):
            receiver = OBJECT + i * 0x100
            identities[receiver] = (i, name)
            write(BUFFER + 4*i, 0 if name == "n" else receiver)
        uc.mem_map(0xA000, 0x1000)
        uc.mem_write(0xACF4, text(0xACF4, 4))
    elif index in (3, 4):
        storage = 0x120 if index == 3 else 0x134
        write(MIXER + storage, BUFFER)
        write(MIXER + storage + 4, len(sequence))
        write(MIXER + 0x2D8, MASTER)
        write(VTABLE + 0x58, CALL)
        for i, name in enumerate(sequence):
            receiver = OBJECT + i * 0x100
            parameter = PARAM + i * 0x100
            identities[parameter] = i
            write(parameter, VTABLE)
            write(BUFFER + 4*i, receiver)
            write(receiver + 0xF8, 0 if name == "z" else parameter)
        uc.mem_map(0x4B000, 0x1000)
        uc.mem_write(0x4BF24, text(0x4BF24, 4))
    else:
        write(MIXER + 0x210, BUFFER)
        write(MIXER + 0x214, len(sequence))
        write(ARGUMENT, VTABLE)
        write(VTABLE, CALL)
        uc.reg_write(UC_ARM_REG_R1, ARGUMENT)
        for i, name in enumerate(sequence):
            receiver = OBJECT + i * 0x100
            identities[receiver] = (i, name)
            write(BUFFER + 4*i, receiver)
            uc.mem_write(receiver + 8, name.encode() + b"\0")
        uc.mem_map(0x11A000, 0x1000)
        uc.mem_write(0x11ADD4, text(0x11ADD4, 4))

    def hook(machine, pc, size, data):
        if address <= pc < address + len(body):
            return
        r0, r1, r2, r3, lr = [machine.reg_read(reg) for reg in
                               (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                                UC_ARM_REG_R3, UC_ARM_REG_LR)]
        if index == 1 and (0x52BEC <= pc < 0x52BFC or 0x651CC <= pc < 0x651D4):
            return
        if index == 1 and pc in (CALL, 0x651D4):
            events.append(f"{identities[r0]}:{'a' if r1 == ARGUMENT else 'z'}")
            assert r1 == channel
        elif index == 2 and pc == 0xACF4:
            assert (r1, r2, r3) == (0x173594, 0x174388, 0)
            result = r0 + 4 if identities[r0][1] == "t" else 0
            machine.reg_write(UC_ARM_REG_R0, result)
        elif index in (3, 4) and pc == CALL:
            events.append(f"p{identities[r0]}:{r1}:{r2}")
        elif index in (3, 4) and pc == 0x4BF24:
            assert r0 == MASTER
            events.append("master")
        elif index == 5 and pc == CALL:
            position, name = identities[r3]
            assert (r0, r1, r2) == (ARGUMENT, 0x436F6D70, r3 + 8)
            assert machine.mem_read(r2, 2) == name.encode() + b"\0"
            events.append(f"f{position}:{name}")
            machine.reg_write(UC_ARM_REG_R0, int(name in option))
        elif index == 5 and pc == 0x11ADD4:
            events.append(f"r{identities[r0][0]}:{r1}:{r2}")
        else:
            raise ValueError(f"Unexpected control flow 0x{pc:x}")
        machine.reg_write(UC_ARM_REG_PC, lr)

    def memory_write(machine, access, at, size, value, data):
        if not MIXER + 0x10000 <= at < MIXER + 0x20000:
            writes.append([at, size, value])

    if index != 2:
        uc.mem_write(CALL, bytes.fromhex("1eff2fe1"))
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.hook_add(UC_HOOK_MEM_WRITE, memory_write)
    uc.reg_write(UC_ARM_REG_R0, MIXER)
    uc.reg_write(UC_ARM_REG_SP, MIXER + 0x1FF00)
    uc.reg_write(UC_ARM_REG_LR, STOP)
    uc.emu_start(address, STOP, count=10000)
    assert uc.reg_read(UC_ARM_REG_PC) == STOP and not writes
    if index == 2:
        selected = uc.reg_read(UC_ARM_REG_R0)
        events.append(str(identities[selected][0]) if selected else "-1")
    return {"sequence": sequence, "option": option, "events": events,
            "native_nonstack_writes": writes}


def main():
    index = int(sys.argv[1])
    data = Path(sys.argv[2]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == SHA
    elf = ELFFile(io.BytesIO(data))
    section = elf.get_section(12)
    assert section.name == ".text"
    address, size, expected, cases = METHODS[index]
    offset = section["sh_offset"] + address - section["sh_addr"]
    def text(at, count):
        for candidate in elf.iter_sections():
            start = at - candidate["sh_addr"]
            if candidate["sh_flags"] & 4 and 0 <= start <= candidate["sh_size"] - count:
                origin = candidate["sh_offset"] + start
                return data[origin:origin + count]
        raise ValueError(f"Address 0x{at:x} has no executable section")
    body = text(address, size)
    digest = hashlib.sha256(body).hexdigest()
    assert digest == expected
    fixtures = {"elf_sha256": SHA, "section": 12, "address": address, "size": size,
                "file_offset": offset, "range_sha256": digest,
                "cases": [run(text, index, address, body, *case) for case in cases]}
    print(json.dumps(fixtures, indent=2))


if __name__ == "__main__":
    main()
