"""Execute one sealed ARM constructor with a mapped original ELF."""
import hashlib
import io
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import arm_const as arm


def observe(packet, image):
    original = json.loads(packet.read_text())["originals"][0]["original"]
    blob = image.read_bytes()
    assert hashlib.sha256(blob).hexdigest() == original["elf"]
    elf = ELFFile(io.BytesIO(blob))
    section = elf.get_section(original["section"])
    symbol = elf.get_section_by_name(".symtab").get_symbol_by_name(original["mangled"])[0]
    address, size = original["address"], original["size"]
    assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (
        address, size, original["section"]
    )
    offset = section["sh_offset"] + address - section["sh_addr"]
    assert offset == original["file_offset"] and section.name == original["section_name"]
    assert section["sh_addr"] <= address and address + size <= section["sh_addr"] + section["sh_size"]
    data = blob[offset:offset + size]
    assert data.hex() == original["range_hex"]
    assert hashlib.sha256(data).hexdigest() == original["range_sha256"]
    vtable = elf.get_section_by_name(".symtab").get_symbol_by_name(
        "_ZTVN8Presonus17BackgroundPainterE"
    )[0]["st_value"]
    cases = []
    for seed in (0x10203040, 0xC7E3F82B):
        vm = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
        segments = list(elf.iter_segments(type="PT_LOAD"))
        start = min(s["p_vaddr"] for s in segments) & ~4095
        end = (max(s["p_vaddr"] + s["p_memsz"] for s in segments) + 4095) & ~4095
        vm.mem_map(start, end - start)
        for segment in segments:
            vm.mem_write(segment["p_vaddr"], segment.data())
        receiver, stack, stop = 0x10001010, 0x10002900, 0x10003000
        vm.mem_map(0x10001000, 0x3000)
        initial = bytes(range(64))
        before = initial[:16] + struct.pack("<I", seed) + initial[20:]
        vm.mem_write(receiver - 16, before)
        stack_bytes = bytes(range(64))
        vm.mem_write(stack - 32, stack_bytes)
        vm.reg_write(arm.UC_ARM_REG_R0, receiver)
        vm.reg_write(arm.UC_ARM_REG_SP, stack)
        vm.reg_write(arm.UC_ARM_REG_LR, stop)
        writes, instructions = [], []
        vm.hook_add(unicorn.UC_HOOK_MEM_WRITE, lambda _, __, a, n, v, ___: writes.append([a, n, v]))
        vm.hook_add(unicorn.UC_HOOK_CODE, lambda _, a, n, __: instructions.append(a))
        vm.emu_start(address, stop, count=32)
        after = bytes(vm.mem_read(receiver - 16, 64))
        stack_after = bytes(vm.mem_read(stack - 32, 64))
        assert vm.reg_read(arm.UC_ARM_REG_PC) == stop
        assert vm.reg_read(arm.UC_ARM_REG_SP) == stack
        # APCS frame push stores fp, incoming sp, lr and the pipeline-adjusted PC.
        frame = (0, stack, stop, address + 16)
        assert writes == [
            [stack - 16 + 4 * index, 4, value] for index, value in enumerate(frame)
        ] + [[receiver, 4, vtable + 8]], writes
        assert instructions == list(range(address, address + 24, 4))
        assert after == before[:16] + struct.pack("<I", vtable + 8) + before[20:]
        assert stack_after == stack_bytes[:16] + struct.pack("<4I", *frame) + stack_bytes[32:]
        cases.append(dict(receiver=receiver, before=before.hex(), after=after.hex(),
                          stack_bytes=stack_after.hex(), writes=writes, instructions=instructions))
    return dict(original=original, unicorn=unicorn.__version__, address_point=vtable + 8,
                cases=cases)


if __name__ == "__main__":
    print(json.dumps(observe(Path(sys.argv[1]), Path(sys.argv[2])), indent=2))
