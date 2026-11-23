"""Replay exact original Element ARM entries in an offline controlled emulator."""
import hashlib
import json
import struct
from itertools import product
from pathlib import Path

import elftools
import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import (
    UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE,
    UC_MODE_ARM, Uc, UcError,
)
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

TASK = "cycle20_g06_s02"
CONTROL = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11")
PACKET = CONTROL / "packeting/panel-first02-batch02/packets" / TASK
INPUTS = CONTROL / "packeting/READ_INPUTS-panel-first02-batch02-cycle20_g06-actual01-wave20-scoped01.json"
RECEIVER, DISPLAY, STACK, STOP = (0x40000000, 0x40001000, 0x40002000, 0x40003000)
PAGE = 4096


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_range(stream, elf, target, native_body):
    assert elf["e_machine"] == "EM_ARM" and elf.elfclass == 32 and elf.little_endian
    section = elf.get_section(target["section"])
    displacement = target["address"] - section["sh_addr"]
    assert section.name == ".text"
    assert 0 <= displacement <= section["sh_size"] - target["size"]
    candidate_symbols = elf.get_section_by_name(".symtab").get_symbol_by_name(target["mangled"])
    assert any(symbol["st_value"] == target["address"]
               and symbol["st_size"] == target["size"]
               and symbol["st_shndx"] == target["section"]
               for symbol in candidate_symbols)
    offset = section["sh_offset"] + displacement
    stream.seek(offset)
    code = stream.read(target["size"])
    assert len(code) == target["size"]
    assert offset == native_body["file_offset"] and sha(code) == native_body["bytes_sha256"]
    return offset, code


def run_case(target, code, seed, force):
    start = target["address"]
    emulator = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    executable_page = start // PAGE * PAGE
    emulator.mem_map(executable_page, PAGE)
    emulator.mem_write(start, code)
    receiver = struct.pack("<I", seed) + bytes([seed & 255] * 60)
    display = bytes([(~seed) & 255] * 64)
    for address, content in ((RECEIVER, receiver), (DISPLAY, display),
                             (STACK, bytes(PAGE)), (STOP, bytes(4))):
        emulator.mem_map(address, PAGE)
        emulator.mem_write(address, content)
    emulator.reg_write(UC_ARM_REG_R0, RECEIVER)
    emulator.reg_write(UC_ARM_REG_R1, DISPLAY)
    emulator.reg_write(UC_ARM_REG_R2, force)
    emulator.reg_write(UC_ARM_REG_SP, STACK + PAGE - 16)
    emulator.reg_write(UC_ARM_REG_LR, STOP)
    instructions = []
    accesses = []

    def record_access(_, kind, address, size, value, __):
        if not STACK <= address < STACK + PAGE:
            accesses.append([kind, address, size, value])

    def trace(_, address, __, ___):
        assert start <= address < start + len(code)
        instructions.append(address)

    emulator.hook_add(UC_HOOK_CODE, trace)
    emulator.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, record_access)
    try:
        emulator.emu_start(start, STOP, count=32)
    except UcError as error:
        raise RuntimeError(f"render @ {start:#x} failed") from error
    assert emulator.reg_read(UC_ARM_REG_PC) == STOP
    assert emulator.reg_read(UC_ARM_REG_SP) == STACK + PAGE - 16
    assert emulator.reg_read(UC_ARM_REG_R0) == RECEIVER
    assert emulator.reg_read(UC_ARM_REG_R1) == DISPLAY
    assert emulator.reg_read(UC_ARM_REG_R2) == force
    assert bytes(emulator.mem_read(RECEIVER, len(receiver))) == receiver
    assert bytes(emulator.mem_read(DISPLAY, len(display))) == display
    assert not accesses
    return {"seed": seed, "force": force, "instructions": instructions,
            "non_stack_accesses": accesses, "external_calls": [],
            "receiver_unchanged": True, "display_unchanged": True}


def generate():
    request = json.loads((PACKET / "request.json").read_text())
    context = json.loads((PACKET / "native-context.json").read_text())
    inputs = json.loads(INPUTS.read_text())
    release_by_hash = {item["elf_sha256"]: item["original_path"]
                       for item in request["work_binding"]["binary_releases"]}
    cases = []
    for target, native_id in zip(request["targets"], context["roots"], strict=True):
        input_hash = target["original_elf_sha256"]
        frozen = inputs[release_by_hash[input_hash]]
        path = Path(frozen["frozen_read_path"])
        assert sha(path.read_bytes()) == frozen["sha256"] == input_hash
        with path.open("rb") as stream:
            elf = ELFFile(stream)
            offset, code = verify_range(stream, elf, target, context["bodies"][native_id])
            symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name("_ZTVN8Presonus5Panel7ElementE")
            vtable = symbol["st_value"]
            section = elf.get_section(symbol["st_shndx"])
            assert 0 <= vtable - section["sh_addr"] <= section["sh_size"] - 60
            stream.seek(section["sh_offset"] + vtable - section["sh_addr"])
            slots = stream.read(60)
        slot = 56
        assert struct.unpack_from("<I", slots, slot)[0] == target["address"]
        observations = [run_case(target, code, seed, force)
                        for seed, force in product((0xdeadbeef, 0x41826308), (0, 1))]
        cases.append({**target, "file_offset": offset, "range_sha256": sha(code),
                      "elf_input": str(path), "variant": "render", "original_slot_offset": slot,
                      "original_vtable": vtable, "observations": observations})
    return {"task_id": TASK, "unicorn": unicorn.__version__, "pyelftools": elftools.__version__,
            "scope": 'Original ARM instructions. Base-entry effects with two receiver/provider states and both bool arguments.', "originals": cases}


if __name__ == "__main__":
    print(json.dumps(generate(), sort_keys=True, indent=2))
