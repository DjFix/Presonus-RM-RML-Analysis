"""Execute the selected original MixerLCD instructions with named boundaries."""
import hashlib
import json
from pathlib import Path
from struct import pack

import elftools
import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

CONTROL = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11")
TASK = "cycle20_g06_s08"
PACKET = CONTROL / "packeting/panel-first02-batch02/packets" / TASK
INPUT_MAP = CONTROL / "packeting/READ_INPUTS-panel-first02-batch02-cycle20_g06-actual01-wave20-scoped03.json"
RECEIVER, FRONT, MIXER, NAME, STACK, STOP = (0x40000000, 0x40001000, 0x40002000,
                                           0x40003000, 0x40004000, 0x40005000)
PAGE = 4096
BOUNDS = {0x1a134: "CString128 constructor", 0xad18: "strstr",
          0xae98: "strlen", 0xae68: "memcpy", 0x11b968: "Component::lookupParameter"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def run(target, code, prefix, query):
    start = target["address"]
    arm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    pages = {start & -PAGE, *(address & -PAGE for address in BOUNDS),
             RECEIVER, FRONT, MIXER, NAME, STACK, STOP}
    for address in sorted(pages):
        arm.mem_map(address, PAGE)
    arm.mem_write(start, code)
    arm.mem_write(RECEIVER + 0x104, pack("<II", FRONT, MIXER))
    name_bytes = prefix.encode() + b"\0"
    assert len(name_bytes) <= 32
    arm.mem_write(FRONT + 8, name_bytes.ljust(32, b"\0"))
    query_bytes = query.encode() + b"\0"
    arm.mem_write(NAME, query_bytes)
    fixtures = {FRONT: ("front", 0x54000100), MIXER: ("mixer", 0x54000200)}
    provider_calls = []
    trace = []
    return_value = None

    def read_string(cpu, pointer):
        page_end = (pointer & -PAGE) + PAGE
        return bytes(cpu.mem_read(pointer, page_end - pointer)).split(b"\0", 1)[0]

    def instruction(cpu, pc, _size, _):
        nonlocal return_value
        if start <= pc < start + len(code):
            return
        assert pc in BOUNDS
        left = cpu.reg_read(UC_ARM_REG_R0)
        right = cpu.reg_read(UC_ARM_REG_R1)
        item = {"callee": BOUNDS[pc], "address": pc,
                "call_site": cpu.reg_read(UC_ARM_REG_LR) - 4}
        if pc == 0x1a134:
            contents = read_string(cpu, right)[:127] if right else b""
            assert STACK <= left <= STACK + PAGE - 128
            cpu.mem_write(left, contents + b"\0")
            item["contents"] = contents.decode()
        elif pc == 0xad18:
            hit = read_string(cpu, left).find(read_string(cpu, right))
            cpu.reg_write(UC_ARM_REG_R0, left + hit if hit >= 0 else 0)
            item["match_offset"] = hit
        elif pc == 0xae98:
            size = len(read_string(cpu, left))
            cpu.reg_write(UC_ARM_REG_R0, size)
            item["length"] = size
        elif pc == 0xae68:
            size = cpu.reg_read(UC_ARM_REG_R2)
            assert 0 < size <= 127 and STACK <= left <= STACK + PAGE - size
            cpu.mem_write(left, bytes(cpu.mem_read(right, size)))
            item["size"] = size
        else:
            role, return_value = fixtures[left]
            path = read_string(cpu, right).decode()
            if path == "missing":
                return_value = 0  # Controlled miss also tests propagation without fallback.
            provider_calls.append([role, path])
            item["original_input_pointer"] = right == NAME
            cpu.reg_write(UC_ARM_REG_R0, return_value)
        trace.append(item)
        cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

    def guard_writes(_, _kind, address, size, _value, __):
        assert STACK <= address <= STACK + PAGE - size

    for register, value in ((UC_ARM_REG_R0, RECEIVER), (UC_ARM_REG_R1, NAME),
                            (UC_ARM_REG_SP, STACK + PAGE - 16), (UC_ARM_REG_LR, STOP)):
        arm.reg_write(register, value)
    arm.hook_add(UC_HOOK_CODE, instruction)
    arm.hook_add(UC_HOOK_MEM_WRITE, guard_writes)
    arm.emu_start(start, STOP, count=200)
    assert arm.reg_read(UC_ARM_REG_PC) == STOP
    assert arm.reg_read(UC_ARM_REG_SP) == STACK + PAGE - 16
    assert len(provider_calls) == 1 and arm.reg_read(UC_ARM_REG_R0) == return_value
    assert bytes(arm.mem_read(NAME, len(query_bytes))) == query_bytes
    assert bytes(arm.mem_read(FRONT + 8, 32)) == name_bytes.ljust(32, b"\0")
    return {"front_name": prefix, "query": query, "lookup": provider_calls[0],
            "opaque_result": return_value, "boundaries": trace}


def generate():
    request = json.loads((PACKET / "request.json").read_text())
    target, = request["targets"]
    release, = request["work_binding"]["binary_releases"]
    context = json.loads((PACKET / "native-context.json").read_text())
    native_id, = context["roots"]
    native_body = context["bodies"][native_id]
    frozen = json.loads(INPUT_MAP.read_text())[release["original_path"]]
    original_path = Path(frozen["frozen_read_path"])
    assert digest(original_path.read_bytes()) == target["original_elf_sha256"] == frozen["sha256"]
    with original_path.open("rb") as stream:
        elf = ELFFile(stream)
        assert elf["e_machine"] == "EM_ARM" and elf.elfclass == 32 and elf.little_endian
        section = elf.get_section(target["section"])
        symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(target["mangled"])
        assert symbol["st_shndx"] == target["section"] and section.name == ".text"
        assert (symbol["st_value"], symbol["st_size"]) == (target["address"], target["size"])
        displacement = target["address"] - section["sh_addr"]
        assert 0 <= displacement <= section["sh_size"] - target["size"]
        offset = section["sh_offset"] + displacement
        stream.seek(offset)
        code = stream.read(target["size"])
    assert len(code) == target["size"]
    assert offset == native_body["file_offset"] and digest(code) == native_body["bytes_sha256"]
    names = [
        ("panel", "panel/fader"), ("panel", "other/panel/fader"), ("panel", "fader"),
        ("panel", "panel"), ("panel", "panel/"), ("panel", ""),
        ("panel", "panel:fader"), ("panel", "panelXfader"), ("panel", "panelfader"),
        ("panel", "panel//fader"), ("panel", "Panel/fader"), ("panel", "panel/missing"),
        ("panel", "panel/" + "x" * 121), ("panel", "panel/" + "x" * 122),
        ("panel", "panel/" + "x" * 140), ("panel", "mixer/" + "y" * 140),
        ("", "/fader"), ("", ""), ("renamed", "renamed/fader"),
        ("renamed", "panel/fader"), ("p" * 31, "p" * 31 + "/fader"),
    ]
    return {"task_id": TASK, **target, "original_path": str(original_path),
            "file_offset": offset, "range_sha256": digest(code),
            "unicorn_version": unicorn.__version__, "pyelftools_version": elftools.__version__,
            "scope": "Only original application instructions run. Exact Core and libc call targets are capture and bounded semantic shims. No ARM Core bodies run. Opaque results test unchanged R0 propagation.",
            "cases": [run(target, code, prefix, query) for prefix, query in names]}


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2, sort_keys=True))
