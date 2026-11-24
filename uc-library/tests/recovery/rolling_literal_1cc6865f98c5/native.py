"""Observe both original ARM bodies offline using frozen ELF inputs."""
import argparse
import hashlib
import io
import json
from pathlib import Path

import elftools
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import arm_const as arm

SYMBOL = "_ZNK8Presonus14IPresetHandler20getEmptyPresetStringEv"
CASES = (
    ("rootfs/RML16AI_Rack_13731/home/root/mixer",
     "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07",
     0x122C4, 0xA2C4, "6d994e2e66e08100d9436bafeb71cc422ce17363205f5e31692555b7fdd24ea0"),
    ("rootfs/CS18_v13840/home/root/surface",
     "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0",
     0x60FF4, 0x58FF4, "6b3c47f0f41633c9a294eef5f70f0915c39552cda4ae7079df4367ca40b36ed3"),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def observe(snapshot, case):
    relative, elf_sha, address, offset, body_sha = case
    path = snapshot / relative
    image = path.read_bytes()
    assert digest(image) == elf_sha
    elf = ELFFile(io.BytesIO(image))
    assert elf["e_machine"] == "EM_ARM" and elf.little_endian
    symbols = elf.get_section_by_name(".symtab").get_symbol_by_name(SYMBOL)
    assert [(s["st_value"], s["st_size"], s["st_shndx"]) for s in symbols] == [
        (address, 24, 12)
    ]
    section = elf.get_section(12)
    assert section.name == ".text"
    assert section["sh_offset"] + address - section["sh_addr"] == offset
    code = image[offset:offset + 24]
    assert digest(code) == body_sha

    uc = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    page = address & ~0xfff
    uc.mem_map(page, 8192, unicorn.UC_PROT_READ | unicorn.UC_PROT_EXEC)
    uc.mem_write(address, code)
    stack, sentinel = 0x70000000, 0x71000000
    uc.mem_map(stack, 4096, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
    receiver_page = 0x72000000
    uc.mem_map(receiver_page, 4096, unicorn.UC_PROT_READ)
    receiver_bytes = bytes(range(256)) * 16
    uc.mem_write(receiver_page, receiver_bytes)
    instructions, writes, reads = [], [], []
    uc.hook_add(unicorn.UC_HOOK_CODE, lambda _uc, pc, size, _: instructions.append(pc))
    uc.hook_add(unicorn.UC_HOOK_MEM_WRITE,
                lambda _uc, access, at, size, value, _: writes.append([at, size]))
    uc.hook_add(unicorn.UC_HOOK_MEM_READ,
                lambda _uc, access, at, size, value, _: reads.append([at, size]))
    returns = []
    for receiver in (receiver_page + 64, receiver_page + 280, receiver_page + 64):
        uc.reg_write(arm.UC_ARM_REG_R0, receiver)
        uc.reg_write(arm.UC_ARM_REG_SP, stack + 2048)
        uc.reg_write(arm.UC_ARM_REG_FP, 0xABCDEF00)
        uc.reg_write(arm.UC_ARM_REG_LR, sentinel)
        uc.emu_start(address, sentinel, count=8)
        assert uc.reg_read(arm.UC_ARM_REG_PC) == sentinel
        assert uc.reg_read(arm.UC_ARM_REG_SP) == stack + 2048
        assert uc.reg_read(arm.UC_ARM_REG_FP) == 0xABCDEF00
        returns.append(uc.reg_read(arm.UC_ARM_REG_R0))
    assert instructions == list(range(address, address + 20, 4)) * 3
    assert all(stack <= at and at + size <= stack + 4096 for at, size in writes)
    assert all(at == address + 20 or stack <= at < stack + 4096 for at, size in reads)
    assert uc.mem_read(receiver_page, 4096) == receiver_bytes
    pointer = returns[0]
    assert returns == [pointer] * 3
    assert pointer == int.from_bytes(code[-4:], "little")
    mappings = [
        seg for seg in elf.iter_segments()
        if seg["p_type"] == "PT_LOAD" and
        seg["p_vaddr"] <= pointer < seg["p_vaddr"] + seg["p_filesz"]
    ]
    assert len(mappings) == 1
    segment = mappings[0]
    assert segment["p_flags"] & 4 and not segment["p_flags"] & 2
    literal_offset = segment["p_offset"] + pointer - segment["p_vaddr"]
    literal = image[literal_offset:literal_offset + 1]
    assert literal == b"\0"
    return dict(path=str(path), elf_sha256=elf_sha, mangled=SYMBOL, section=12,
                section_name=section.name, address=address, size=24, offset=offset,
                range_sha256=body_sha, receiver_cases=3, return_words=returns,
                literal_offset=literal_offset, literal_hex=literal.hex(),
                literal_segment_flags=segment["p_flags"], instructions=instructions,
                writes=writes, reads=reads, external_calls=[], receiver_preserved=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    outputs = parser.add_mutually_exclusive_group(required=True)
    outputs.add_argument("--out", type=Path)
    outputs.add_argument("--check", type=Path)
    args = parser.parse_args()
    result = dict(unicorn=unicorn.__version__, pyelftools=elftools.__version__,
                  observations=[observe(args.snapshot, case) for case in CASES])
    if args.out:
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    else:
        if result != json.loads(args.check.read_text()):
            parser.exit(1, "Fresh native observations differ from sealed fixtures\n")
    print("Native ARM: 2 exact ELF ranges, 6 successful calls")


if __name__ == "__main__":
    main()
