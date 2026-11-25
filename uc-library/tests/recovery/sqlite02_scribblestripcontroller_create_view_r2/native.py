"""Execute the two original ARM methods with explicit provider boundaries."""

import hashlib
import io
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP,
)


ELF = Path("rootfs/CS18_v13840/home/root/surface")
DATA = 0x400000
STOP = DATA + 0xF000
STACK = DATA + 0xE000
VIEW = DATA + 0x1000
MAPPING = DATA + 0x2000
ROOT = DATA + 0x3000
ROOT_SLOT = 0xB189C
PARAMETERS = DATA + 0x5000
CALLS = {
    148072: "cstring",
    308348: "append_format",
    361296: "equal",
    423516: "dot",
    423600: "style",
    423852: "number",
    424104: "linked",
    424936: "vpot",
    425096: "pan",
    43276: "allocate",
    45304: "strcmp",
    45664: "strchr",
    484080: "lookup",
    573012: "control_name",
    ROOT_SLOT: "root",
}
PREFIXES = (
    "scribble_arm", "scribble_dot", "scribble_encoderInfo", "scribble_info",
    "scribble_label", "scribble_left", "scribble_linked", "scribble_number",
    "scribble_pan", "scribble_style",
)


def case_inputs(mode):
    if mode == "create_view":
        for index, keys in [(2, PREFIXES), (11, ("scribble_dot", "scribble_number")), (-2, ())]:
            for name in ["ScribblePanControl", "ScribbleMcuVpotControl",
                         "scribblepancontrol", "", None]:
                yield dict(index=index, keys=[f"{key}_{index + 1:02d}" for key in keys], name=name)
        return
    for name in ["number", "label", "recordEnable", "info", "pan",
                 "encoderInfo", "leftSide", "linked", "style", "dot",
                 "", None, "unmatched", "Number", "linked/dot", "number/"]:
        for index, keys in [(2, PREFIXES), (11, ("scribble_dot", "scribble_number"))]:
            yield dict(index=index, keys=[""] + [f"{key}_{index + 1:02d}" for key in keys],
                       name=name, type="Param")
    for name, kind in [("/rootProbe", "Param"), ("/missing", "Param"),
                       ("/rootProbe", "Controller"), ("/rootProbe", None),
                       ("number", "param"), ("number", ""), ("number", None)]:
        yield dict(index=2, keys=[], name=name, type=kind)


def checked_range(elf, original, data):
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(original["mangled"])
    address, size, section_index = (symbol[k] for k in ("st_value", "st_size", "st_shndx"))
    section = elf.get_section(section_index)
    offset = section["sh_offset"] + address - section["sh_addr"]
    assert (address, size, section_index, section.name, offset) == (
        original["address"], original["size"], original["section"],
        original["section_name"], original["file_offset"])
    assert offset >= section["sh_offset"] and offset + size <= section["sh_offset"] + section["sh_size"]
    code = data[offset:offset + size]
    assert hashlib.sha256(code).hexdigest() == original["range_sha256"]
    assert code.hex() == original["range_hex"]


def run_case(segments, address, size, case):
    machine = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    machine.mem_map(0x8000, 0x2F8000)
    for virtual, data in segments:
        machine.mem_write(virtual, data)
    machine.mem_map(DATA, 0x10000)

    def word(address):
        return struct.unpack("<I", machine.mem_read(address, 4))[0]

    def put(address, *values):
        machine.mem_write(address, struct.pack(f"<{len(values)}I", *values))

    def string(address):
        if not address:
            return ""
        value = bytes(machine.mem_read(address, 256)).split(b"\0", 1)[0]
        return value.decode("ascii")

    def put_string(address, value, limit):
        machine.mem_write(address, value.encode("ascii")[:limit-1] + b"\0")

    def input_string(address, value):
        if value is None:
            return 0
        put_string(address, value, 256)
        return address

    put(DATA, 0, case["index"] & 0xffffffff, ROOT, MAPPING)
    put(ROOT + 0x104, DATA + 0x4100)
    put(DATA + 0x410C, ROOT_SLOT)
    ids = {key: index for index, key in enumerate(case["keys"], 1)}
    for register, value in {
        UC_ARM_REG_R0: DATA, UC_ARM_REG_R1: input_string(DATA + 0x100, case["name"]),
        UC_ARM_REG_R2: input_string(DATA + 0x200, case.get("type")),
        UC_ARM_REG_LR: STOP, UC_ARM_REG_SP: STACK,
    }.items():
        machine.reg_write(register, value)
    events = []
    memory_writes = []

    def hook(uc, at, _, __):
        if address <= at < address + size:
            return
        call = CALLS[at]
        a, b, c, d = [uc.reg_read(register) for register in
                      (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)]
        out = 0
        if call == "allocate":
            events.append([call, a])
            out = VIEW
        elif call in ("vpot", "pan"):
            assert a == VIEW
            events.append([call, [word(b + 4 * i) for i in range(4)], c])
        elif call == "append_format":
            assert string(b) == "%s_%02d"
            number = struct.unpack("<i", struct.pack("<I", d))[0]
            put_string(a, f"{string(c)}_{number:02d}", 32)
        elif call == "control_name":
            number = struct.unpack("<i", struct.pack("<I", (c + 1) & 0xffffffff))[0]
            put_string(a, f"{string(b)}_{number:02d}", 32)
        elif call == "cstring":
            put_string(a, string(b), 32)
        elif call == "equal":
            out = int(string(word(a)) == string(b))
        elif call == "strcmp":
            out = int(string(a) != string(b))
        elif call == "strchr":
            index = string(a).find(chr(b))
            out = a + index if index >= 0 else 0
        elif call == "lookup":
            assert a == MAPPING
            key = string(b)
            identity = ids.get(key, 0)
            events.append([call, key, identity])
            out = PARAMETERS + identity if identity else 0
        elif call == "root":
            assert a == ROOT + 0x104
            # Boundary-injected return identity from the fixture's root slot.
            # The portable replay delegates to an actual pinned CCL provider.
            identity = 100 if string(b) == "/rootProbe" else 0
            events.append([call, string(b), string(c), identity])
            out = PARAMETERS + identity if identity else 0
        else:
            assert call in ("linked", "number", "style", "dot") and a == VIEW
            events.append([call, b - PARAMETERS if b else 0])
        uc.reg_write(UC_ARM_REG_R0, out)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    def write(_, __, at, count, ___, ____):
        assert STACK - 0x200 <= at and at + count <= STACK
        memory_writes.append([at - STACK, count])

    machine.hook_add(unicorn.UC_HOOK_CODE, hook)
    machine.hook_add(unicorn.UC_HOOK_MEM_WRITE, write)
    machine.emu_start(address, STOP, count=2000)
    assert machine.reg_read(UC_ARM_REG_PC) == STOP
    assert machine.reg_read(UC_ARM_REG_SP) == STACK
    result = machine.reg_read(UC_ARM_REG_R0)
    return dict(input=case, events=events, stack_writes=memory_writes,
                result="view" if result == VIEW else result - PARAMETERS if result else 0)


def observe(context, mode):
    original = json.loads(context.read_text())["originals"][0]["original"]
    data = ELF.read_bytes()
    assert hashlib.sha256(data).hexdigest() == original["elf"]
    elf = ELFFile(io.BytesIO(data))
    checked_range(elf, original, data)
    root_slot, = elf.get_section_by_name(".symtab").get_symbol_by_name(
        "_ZN4Core8Portable23ComponentViewControllerIN8Presonus7Surface20SurfaceRootComponentEE16getObjectForViewEPKcS7_")
    assert root_slot["st_value"] == ROOT_SLOT
    segments = [(seg["p_vaddr"], seg.data()) for seg in elf.iter_segments()
                if seg["p_type"] == "PT_LOAD"]
    assert struct.unpack("<I", data[0x1E4C18 - 0x8000:0x1E4C1C - 0x8000])[0] == ROOT_SLOT
    cases = [run_case(segments, original["address"], original["size"], case)
             for case in case_inputs(mode)]
    return dict(original={k: v for k, v in original.items() if k != "range_hex"},
                unicorn=unicorn.__version__, cases=cases)


if __name__ == "__main__":
    import sys
    print(json.dumps(observe(Path(sys.argv[1]), sys.argv[2]), indent=2))
