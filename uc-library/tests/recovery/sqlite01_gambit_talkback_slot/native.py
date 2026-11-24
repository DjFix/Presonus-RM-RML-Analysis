"""Collect bounded observations by executing the verified ARM function."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

import elftools
from elftools.elf.elffile import ELFFile
import unicorn as uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

TASK = "sqlite01_gambit_talkback_slot"
TEST = Path("uc-library/tests/recovery") / TASK
PACKET = Path("temp/recovery-work/sqlite-issued/prepared-eight") / TASK / "CONTEXT.json"
ELF = Path("/home/rs/projects/opencs/ai-line-analysis/rootfs/RML16AI_Rack_13731/home/root/mixer")
MANGLED = "_ZN8Presonus5Mixer20GambitMixerComponent20getDanteTalkbackSlotEv"


def digest(data):
    return sha256(data).hexdigest()


def run_arm(address, body, seed):
    receiver_page = 0x100000
    stack_page = 0x200000
    stop = 0x300000
    stack_top = stack_page + 0x800
    arm = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_ARM)
    arm.mem_map(address & ~0xFFF, 0x1000)
    arm.mem_write(address, body)
    arm.mem_map(receiver_page, 0x1000)
    receiver = receiver_page + 0x100
    receiver_image = bytes((seed + i * 29) & 255 for i in range(0x1000))
    arm.mem_write(receiver_page, receiver_image)
    arm.mem_protect(receiver_page, 0x1000, uc.UC_PROT_READ)
    arm.mem_map(stack_page, 0x1000)
    stack_image = bytes([seed ^ 0xFF]) * 0x1000
    arm.mem_write(stack_page, stack_image)
    arm.reg_write(UC_ARM_REG_R0, receiver)
    arm.reg_write(UC_ARM_REG_SP, stack_top)
    arm.reg_write(UC_ARM_REG_LR, stop)
    trace = []
    writes = []
    arm.hook_add(uc.UC_HOOK_CODE, lambda _, pc, size, data: trace.append(pc))
    arm.hook_add(uc.UC_HOOK_MEM_WRITE,
                 lambda _, kind, at, size, value, data: writes.append([at, size, value]))
    arm.emu_start(address, stop, count=16)
    assert arm.reg_read(UC_ARM_REG_PC) == stop
    assert arm.reg_read(UC_ARM_REG_SP) == stack_top
    assert trace and all(address <= pc < address + len(body) for pc in trace)
    assert all(stack_top - 16 <= at and at + size <= stack_top for at, size, _ in writes)
    assert bytes(arm.mem_read(receiver_page, len(receiver_image))) == receiver_image
    final_stack = bytes(arm.mem_read(stack_page, len(stack_image)))
    assert final_stack[:0x7f0] == stack_image[:0x7f0]
    assert final_stack[0x800:] == stack_image[0x800:]
    return dict(seed=seed, result=arm.reg_read(UC_ARM_REG_R0), receiver_unchanged=True,
                stack_canaries_unchanged=True, instruction_trace=trace, memory_writes=writes,
                external_calls=0)


def observe(elf_path):
    packet_bytes = PACKET.read_bytes()
    expected, = json.loads(packet_bytes)["originals"]
    original = expected["original"]
    data = elf_path.read_bytes()
    assert digest(data) == original["elf"]
    elf = ELFFile(BytesIO(data))
    assert elf["e_machine"] == "EM_ARM" and elf.elfclass == 32 and elf.little_endian
    sym, = elf.get_section_by_name(".symtab").get_symbol_by_name(MANGLED)
    assert sym["st_info"]["type"] == "STT_FUNC"
    assert sym["st_shndx"] == original["section"]
    assert sym["st_size"] == original["size"] and sym["st_value"] == original["address"]
    section = elf.get_section(sym["st_shndx"])
    entry = int(sym["st_value"])
    size = int(sym["st_size"])
    assert section.name == original["section_name"] and section["sh_type"] == "SHT_PROGBITS"
    relative = entry - section["sh_addr"]
    assert 0 <= relative and relative + size <= section["sh_size"]
    offset = section["sh_offset"] + relative
    assert offset == original["file_offset"]
    body = data[offset:offset + size]
    assert body == section.data()[relative:relative + size]
    assert body.hex() == original["range_hex"] and digest(body) == original["range_sha256"]
    return dict(original=original, packet_sha256=digest(packet_bytes),
                engines=dict(unicorn=uc.__version__, pyelftools=elftools.__version__),
                instruction_limit=16, cases=[run_arm(entry, body, seed) for seed in (19, 202)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, default=ELF)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    observations = observe(args.elf)
    if args.record:
        with args.fixtures.open("x") as output:
            json.dump(observations, output, indent=2)
            output.write("\n")
    elif json.loads(args.fixtures.read_bytes()) != observations:
        raise SystemExit("ARM observations differ from the sealed fixture")
    print(f'{len(observations["cases"])} native cases passed')
