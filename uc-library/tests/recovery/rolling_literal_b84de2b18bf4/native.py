"""Execute the exact original ARM getter offline in an isolated address space."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
import unicorn as uc
from unicorn.arm_const import UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

MANGLED = "_ZN8Presonus5Panel20GambitPanelRegistrar16getPanelPortNameEv"
ELF_HASH = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
BODY_HASH = "a572376e0ee06bc343b7da8c80c3ad7485494648223905bde63169a725321b0a"
ADDRESS, SIZE, SECTION = 0x7C2A0, 24, 12
PAGE, STACK, STOP = 0x1000, 0x700000, 0x800000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def observe(path):
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == ELF_HASH, "Original ELF hash mismatch")
    elf = ELFFile(BytesIO(raw))
    require(elf.little_endian and elf["e_machine"] == "EM_ARM", "Expected little-endian ARM")
    matching = elf.get_section_by_name(".symtab").get_symbol_by_name(MANGLED)
    require(len(matching) == 1, "Original symbol is ambiguous")
    symbol = matching[0]
    require((symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) ==
            (ADDRESS, SIZE, SECTION), "Original symbol range mismatch")
    text = elf.get_section(SECTION)
    offset = text["sh_offset"] + ADDRESS - text["sh_addr"]
    body = raw[offset:offset + SIZE]
    require(sha256(body).hexdigest() == BODY_HASH, "Original function range hash mismatch")
    rodata = elf.get_section_by_name(".rodata")
    begin = rodata["sh_addr"]
    end = begin + rodata["sh_size"]
    require(rodata["sh_flags"] & 3 == 2, "Expected allocated read-only literal section")
    cases = []
    for receiver, fill in ((0x900000, 0x31), (0x901000, 0xA9), (0x900000, 0x31)):
        machine = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_ARM)
        code_page = ADDRESS & -PAGE
        machine.mem_map(code_page, PAGE, uc.UC_PROT_READ | uc.UC_PROT_EXEC)
        machine.mem_write(ADDRESS, body)
        machine.mem_map(STACK, PAGE)
        machine.mem_map(receiver, PAGE, uc.UC_PROT_READ)
        sentinel = bytes([fill]) * 32
        machine.mem_write(receiver, sentinel)
        sp = STACK + PAGE - 16
        machine.reg_write(UC_ARM_REG_R0, receiver)
        machine.reg_write(UC_ARM_REG_SP, sp)
        machine.reg_write(UC_ARM_REG_LR, STOP)
        machine.reg_write(UC_ARM_REG_FP, 0x1234)
        trace, writes = [], []
        machine.hook_add(uc.UC_HOOK_CODE, lambda _, address, size, data: trace.append(address))
        machine.hook_add(uc.UC_HOOK_MEM_WRITE,
                         lambda _, access, address, size, value, data: writes.append((address, size)))
        machine.emu_start(ADDRESS, STOP, count=16)
        require(machine.reg_read(UC_ARM_REG_PC) == STOP and
                machine.reg_read(UC_ARM_REG_SP) == sp and
                machine.reg_read(UC_ARM_REG_FP) == 0x1234, "Return control or frame changed")
        require(trace == list(range(ADDRESS, ADDRESS + SIZE - 4, 4)), "Unexpected native execution path")
        require(all(sp - 16 <= addr and addr + size <= sp for addr, size in writes),
                "Native writes escaped the stack frame")
        require(machine.mem_read(receiver, len(sentinel)) == sentinel, "Receiver changed")
        word = machine.reg_read(UC_ARM_REG_R0)
        require(begin <= word < end, "Returned word is outside read-only literal section")
        literal_offset = rodata["sh_offset"] + word - begin
        nul = raw.index(b"\0", literal_offset, rodata["sh_offset"] + rodata["sh_size"])
        cases.append(dict(receiver=receiver, sentinel=fill, return_word=word,
                          literal=raw[literal_offset:nul].decode("ascii"),
                          literal_hex=raw[literal_offset:nul + 1].hex(),
                          literal_offset=literal_offset, instruction_trace=trace,
                          stack_writes=[list(write) for write in writes], receiver_preserved=True))
    require(len({case["return_word"] for case in cases}) == 1, "Native pointer identity changed")
    return dict(elf_sha256=ELF_HASH, firmware="RM/RML mixer 13731", role="server",
                mangled=MANGLED, address=ADDRESS, size=SIZE, section=SECTION,
                section_name=text.name, range_sha256=BODY_HASH, file_offset=offset,
                literal_section=rodata.name, unicorn_version=uc.__version__, cases=cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--write", type=Path)
    actions.add_argument("--compare", type=Path)
    args = parser.parse_args()
    result = observe(args.elf)
    if args.write:
        with args.write.open("x") as output:
            json.dump(result, output, indent=2)
            output.write("\n")
    else:
        require(result == json.loads(args.compare.read_text()), "Fresh native observations differ")
    print(f"PASS {len(result['cases'])} exact original ARM invocations")


if __name__ == "__main__":
    main()
