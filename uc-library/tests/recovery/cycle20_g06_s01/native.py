"""Replay exact original Element ARM entries in an offline controlled emulator."""
import hashlib
import json
import struct
from pathlib import Path

import elftools
import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import (
    UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE,
    UC_MEM_WRITE, UC_MODE_ARM, Uc, UcError,
)
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_SP,
)

TASK = "cycle20_g06_s01"
CONTROL = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11")
PACKET = CONTROL / "packeting/panel-first02-batch02/packets" / TASK
INPUTS = CONTROL / "packeting/READ_INPUTS-panel-first02-batch02-cycle20_g06-actual01-wave20-scoped01.json"
RECEIVER, DISPLAY, STACK, STOP = (0x40000000, 0x40001000, 0x40002000, 0x40003000)
PAGE = 4096


def sha(data):
    return hashlib.sha256(data).hexdigest()


def word(emulator, address):
    return struct.unpack("<I", emulator.mem_read(address, 4))[0]


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


def run_case(target, code, table, seed, delete_plt):
    start = target["address"]
    variant = target["mangled"][-4:-2]
    emulator = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    pages = set()

    def map_bytes(address, data):
        for page in range(address // PAGE * PAGE,
                          ((address + len(data) - 1) // PAGE + 1) * PAGE, PAGE):
            if page not in pages:
                emulator.mem_map(page, PAGE)
                pages.add(page)
        emulator.mem_write(address, data)

    map_bytes(start, code)
    map_bytes(table[0], table[1])
    if delete_plt is not None:
        map_bytes(delete_plt, bytes.fromhex("1eff2fe1"))  # Controlled implementation of the import.
    receiver = struct.pack("<I", seed) + bytes([seed & 255] * 60)
    display = bytes([(~seed) & 255] * 64)
    map_bytes(RECEIVER, receiver)
    map_bytes(DISPLAY, display)
    map_bytes(STACK, bytes(PAGE))
    map_bytes(STOP, bytes(4))
    emulator.reg_write(UC_ARM_REG_R0, RECEIVER)
    emulator.reg_write(UC_ARM_REG_R1, DISPLAY)
    emulator.reg_write(UC_ARM_REG_SP, STACK + PAGE - 16)
    emulator.reg_write(UC_ARM_REG_LR, STOP)
    addresses = []
    external = []
    accesses = []

    def record_access(_, kind, address, size, value, __):
        if not STACK <= address < STACK + PAGE:
            accesses.append([kind, address, size, value])

    def trace(cpu, address, _, __):
        addresses.append(address)
        if start <= address < start + len(code):
            return
        assert address == delete_plt and variant == "D0"
        assert cpu.reg_read(UC_ARM_REG_R0) == RECEIVER
        assert cpu.reg_read(UC_ARM_REG_LR) == start + 32
        assert word(cpu, RECEIVER) == table[0]
        assert bytes(cpu.mem_read(RECEIVER + 4, 60)) == receiver[4:]
        external.append({"symbol": "operator delete(void*)", "plt": address,
                         "argument": RECEIVER, "vptr_before_delete": word(cpu, RECEIVER)})
        cpu.mem_unmap(RECEIVER, PAGE)

    emulator.hook_add(UC_HOOK_CODE, trace)
    emulator.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, record_access)
    try:
        emulator.emu_start(start, STOP, count=32)
    except UcError as error:
        raise RuntimeError(f"{variant} @ {start:#x}: {[hex(x) for x in addresses]} PC={emulator.reg_read(UC_ARM_REG_PC):#x}") from error
    assert emulator.reg_read(UC_ARM_REG_PC) == STOP
    assert emulator.reg_read(UC_ARM_REG_SP) == STACK + PAGE - 16
    assert emulator.reg_read(UC_ARM_REG_R0) == RECEIVER
    assert emulator.reg_read(UC_ARM_REG_R1) == DISPLAY
    assert bytes(emulator.mem_read(DISPLAY, len(display))) == display
    assert [entry for entry in accesses if DISPLAY <= entry[1] < DISPLAY + PAGE] == []
    receiver_accesses = [entry for entry in accesses if RECEIVER <= entry[1] < RECEIVER + PAGE]
    assert receiver_accesses == [[UC_MEM_WRITE, RECEIVER, 4, table[0]]]
    released = False
    try:
        after = bytes(emulator.mem_read(RECEIVER, len(receiver)))
    except UcError as error:
        assert error.errno == unicorn.UC_ERR_READ_UNMAPPED
        released = True
    else:
        assert after == struct.pack("<I", table[0]) + receiver[4:]
    assert released == (variant == "D0")
    assert len(external) == int(released)
    return {"seed": seed, "instructions": addresses,
            "non_stack_accesses": accesses, "external_calls": external,
            "controlled_heap_released": released, "display_unchanged": True}


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
        variant = target["mangled"][-4:-2]
        slot = {"D1": 8, "D0": 12}.get(variant)
        if slot is not None:
            assert struct.unpack_from("<I", slots, slot)[0] == target["address"]
        delete_plt = {"client": 0xad5c, "server": 0xac10}[target["role"]] if variant == "D0" else None
        seeds = (0xdeadbeef, 0x41826308)
        observations = [run_case(target, code, (vtable + 8, slots[8:]), seed, delete_plt)
                        for seed in seeds]
        cases.append({**target, "file_offset": offset, "range_sha256": sha(code),
                      "elf_input": str(path), "variant": variant, "original_slot_offset": slot,
                      "original_vtable": vtable, "observations": observations})
    return {"task_id": TASK, "unicorn": unicorn.__version__, "pyelftools": elftools.__version__,
            "scope": 'Original ARM instructions. D0 real branch to the exact unsized delete import, with a controlled allocator boundary that unmaps the receiver page. The original C++ runtime allocator is excluded.', "originals": cases}


if __name__ == "__main__":
    print(json.dumps(generate(), sort_keys=True, indent=2))
