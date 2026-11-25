"""Observe bound ARM ranges while substituting pinned CCL source boundaries."""

import hashlib
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

ROOT = Path(__file__).resolve().parents[4]
PACKETS = Path("temp/recovery-work/sqlite-issued/packet")
SEALED_PACKET = Path("temp/recovery-work/rolling-c001-20261124/packeting/"
                     "sqlite-cycle02/gui_meter_control_r2/packet/tasks")
PREFIX = "sqlite03_gui_meter_control_"
VERTICAL = ((0, 0, 22, 11), (1, -2, 4, 17), (-20, 8, 0, 28),
            (12, 12, 12, 12), (12, 12, 12, 13), (12, 12, 13, 12),
            (-30, -20, -50, -30), (-1000, -1000, 1000, 999))
ATTRIBUTE_CASES = (
    (0, ((25, 0, 0, 0, 0, 0, 0),
         (41, 2, 2, 1, 2**32, -2**32, 2**63 - 1),
         (42, 3, 0, 1, 0, -1, 0),
         (43, 1, 3, 1, -(2**63), 0, -9),
         (44, 2, 4, 0, 1, 0, 0),
         (45, 2, 5, 1, 0, 0, 1))),
    (1, ((9, 1, 1, 1, 7, 0, 0),
         (12, 2, 0, 0, 0, 8, 0),
         (27, 3, 3, 1, 0, 0, -3))),
    (0, ((65, 2, 5, 1, 0, 0, 0),)),
)
ARENA, STACK, STOP = 0x1000000, 0x2000000, 0x3000000
RECEIVER, INTERP, PEAK, ATTRS = (ARENA + i * 0x1000 for i in range(4))
CONTROLLER, CTRL_VT, LOOKUP = ATTRS + 0x200, ATTRS + 0x280, STOP + 4
INTERP_VT, VIRTUAL_DELETE = ATTRS + 0x300, STOP + 8
HEAP_DELETE = STOP + 12


def digest(data):
    return hashlib.sha256(data).hexdigest()


def provider(exe, mode, inputs):
    process = subprocess.run([str(exe.resolve()), mode], cwd=ROOT, input=inputs,
                             capture_output=True, text=True, check=True)
    return [list(map(int, line.split())) for line in process.stdout.splitlines()]


def line(values):
    return " ".join(map(str, values)) + "\n"


class Firmware:
    def __init__(self, original):
        self.original = original
        self.raw = (ROOT / original["elf_path"]).read_bytes()
        assert digest(self.raw) == original["elf"]
        self.elf = ELFFile(io.BytesIO(self.raw))
        assert self.elf.little_endian and self.elf["e_machine"] == "EM_ARM"
        self.symbols = self.elf.get_section_by_name(".symtab")
        target = self.symbol(original["mangled"])
        for key in ("address", "section", "file_offset", "size"):
            assert target[key] == original[key]
        assert target["range_sha256"] == original["range_sha256"]
        assert target["range_hex"] == original["range_hex"]
        assert self.elf.get_section(target["section"]).name == original["section_name"]
        self.target = target

    def symbol(self, name):
        sym, = self.symbols.get_symbol_by_name(name)
        section = self.elf.get_section(sym["st_shndx"])
        address, size = sym["st_value"], sym["st_size"]
        displacement = address - section["sh_addr"]
        assert 0 <= displacement <= section["sh_size"] - size
        offset = section["sh_offset"] + displacement
        data = self.raw[offset:offset + size]
        return dict(mangled=name, address=address, section=sym["st_shndx"],
                    file_offset=offset, size=size, range_sha256=digest(data),
                    range_hex=data.hex())

    def plt(self, address, name):
        plt = self.elf.get_section_by_name(".plt")
        displacement = address - plt["sh_addr"]
        index, remainder = divmod(displacement - 20, 12)
        assert index >= 0 and remainder == 0
        relocations = self.elf.get_section_by_name(".rel.plt")
        relocation = relocations.get_relocation(index)
        assert self.elf.get_section(relocations["sh_link"]).get_symbol(
            relocation["r_info_sym"]).name == name
        offset = plt["sh_offset"] + displacement
        return dict(mangled=name, address=address, file_offset=offset,
                    range_sha256=digest(self.raw[offset:offset + 12]),
                    got=relocation["r_offset"])

    def machine(self):
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        segments = [s for s in self.elf.iter_segments() if s["p_type"] == "PT_LOAD"]
        first = min(s["p_vaddr"] for s in segments) & ~0xfff
        last = (max(s["p_vaddr"] + s["p_memsz"] for s in segments) + 0xfff) & ~0xfff
        uc.mem_map(first, last - first)
        for segment in segments:
            uc.mem_write(segment["p_vaddr"], segment.data())
        uc.mem_map(ARENA, 0x4000)
        uc.mem_map(STACK, 0x1000)
        uc.mem_map(STOP, 0x1000)
        return uc


def put(uc, address, *words):
    uc.mem_write(address, struct.pack("<" + "I" * len(words), *words))


def get(uc, address):
    return struct.unpack("<I", uc.mem_read(address, 4))[0]


def string(uc, address):
    value = bytearray()
    while byte := uc.mem_read(address + len(value), 1)[0]:
        value.append(byte)
        assert len(value) < 80
    return value.decode("ascii")


def run(fw, uc, callback, executable_end, second=0, extra=()):
    trace, writes = [], []
    start = fw.target["address"]

    def observe(cpu, address, _size, _):
        if start <= address < executable_end or address in extra:
            trace.append(address)
        else:
            callback(cpu, address)
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

    def capture(_cpu, _access, address, size, value, _):
        if not STACK <= address < STACK + 0x1000:
            writes.append([address, size, value])

    hooks = (uc.hook_add(UC_HOOK_CODE, observe),
             uc.hook_add(UC_HOOK_MEM_WRITE, capture))
    for reg, val in ((UC_ARM_REG_R0, RECEIVER), (UC_ARM_REG_R1, second),
                     (UC_ARM_REG_SP, STACK + 0x800), (UC_ARM_REG_LR, STOP)):
        uc.reg_write(reg, val)
    uc.emu_start(start, STOP, count=512)
    assert uc.reg_read(UC_ARM_REG_PC) == STOP
    assert uc.reg_read(UC_ARM_REG_SP) == STACK + 0x800
    for hook in hooks:
        uc.hook_del(hook)
    return trace, writes


def vertical(fw, exe):
    rects = provider(exe, "provider-rect", "".join(map(line, VERTICAL)))
    bound = fw.symbol("_ZNK4Core8Portable4View7getSizeEv")
    cases = []
    for inputs, rect in zip(VERTICAL, rects, strict=True):
        uc = fw.machine()
        uc.mem_write(ATTRS, struct.pack("<4i", *rect))

        def boundary(cpu, address):
            assert address == bound["address"]
            assert cpu.reg_read(UC_ARM_REG_R0) == RECEIVER
            cpu.reg_write(UC_ARM_REG_R0, ATTRS)

        trace, writes = run(fw, uc, boundary, fw.target["address"] + fw.target["size"])
        assert not writes
        cases.append(dict(input=list(inputs), provider_rect=rect, trace=trace,
                          output=[uc.reg_read(UC_ARM_REG_R0)]))
    return dict(boundaries=[bound], cases=cases)


def attributes(fw, exe):
    names = [
        "_ZN4Core8Portable4View13setAttributesERKNS0_10AttributesE",
        "_ZNK4Core8Portable10Attributes9getStringEPKc",
        "_ZNK4Core8Portable10Attributes6getIntEPKc",
        "_ZN4Core19InterpolatorFactory6createEPKc",
        "_ZN8Presonus12MeterControl16setPeakParameterEPN4Core8Portable9ParameterE",
    ]
    bounds = [fw.symbol(name) for name in names]
    view, get_string, get_int, create, set_peak = [row["address"] for row in bounds]
    tables = [fw.symbol(name) for name in (
        "_ZTVN4Core8Portable4ViewE", "_ZTVN4Core8Portable7ControlE",
        "_ZTVN8Presonus12MeterControlE")]
    slot = 72
    for table, expected in zip(tables, (view, view, fw.target["address"]), strict=True):
        observed, = struct.unpack_from("<I", bytes.fromhex(table["range_hex"]), slot)
        assert observed == expected
    cases = []
    for borrowed, steps in ATTRIBUTE_CASES:
        inputs = line((borrowed, len(steps))) + "".join(map(line, steps))
        results = provider(exe, "provider-attributes", inputs)
        uc = fw.machine()
        code = fw.target["address"]
        assert get(uc, code + 0x1a8) == 0x2691ac
        guard = get(uc, code + 0x1a8)
        builder = get(uc, code + 0x1ac)
        put(uc, guard, 1)
        put(uc, CONTROLLER, CTRL_VT)
        put(uc, CTRL_VT + 12, LOOKUP)
        put(uc, RECEIVER + 0x5c, borrowed, 1)
        observations = []
        for step, result in zip(steps, results, strict=True):
            _, peak_code, interp_code, with_controller, *_ = step
            peak_present, interp_present, r, u, h, parameter, named, default, w, height, calls, when = result
            put(uc, builder + 0x2c, CONTROLLER if with_controller else 0)
            input_strings = {}
            if peak_present:
                input_strings["peak"] = (ATTRS + 0x20, ("", "", "matched", "missing")[peak_code])
            if interp_present:
                input_strings["interpolator"] = (
                    ATTRS + 0x40, ("", "", "linear", "missing", "linrev", "audiometer")[interp_code])
            for ptr, s in input_strings.values():
                uc.mem_write(ptr, s.encode() + b"\0")
            trace_calls, base_size = [], None
            lookup_count = lookup_height = 0

            def boundary(cpu, address):
                nonlocal base_size, lookup_count, lookup_height
                r0, r1, r2 = [cpu.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
                if address == view:
                    assert (r0, r1) == (RECEIVER, ATTRS)
                    base_size = [w, height]
                    trace_calls.append(["View::setAttributes", w, height])
                elif address == get_string:
                    key = string(cpu, r1)
                    assert r0 == ATTRS and key in ("peak", "interpolator")
                    trace_calls.append(["getString", key])
                    cpu.reg_write(UC_ARM_REG_R0, input_strings.get(key, (0, ""))[0])
                elif address == get_int:
                    key = string(cpu, r1)
                    assert r0 == ATTRS
                    value = {"reversed": r, "unoptimized": u, "hidepeaks": h}[key]
                    trace_calls.append(["getInt", key, value])
                    cpu.reg_write(UC_ARM_REG_R0, value & 0xffffffff)
                    cpu.reg_write(UC_ARM_REG_R1, (value >> 32) & 0xffffffff)
                elif address == LOOKUP:
                    assert r0 == CONTROLLER and string(cpu, r1) == input_strings["peak"][1]
                    assert string(cpu, r2) == "Param" and base_size is not None
                    lookup_count += 1
                    lookup_height = base_size[1]
                    trace_calls.append(["controller", string(cpu, r1), string(cpu, r2)])
                    cpu.reg_write(UC_ARM_REG_R0, parameter)
                elif address == set_peak:
                    assert (r0, r1) == (RECEIVER, parameter)
                    trace_calls.append(["setPeakParameter", r1])
                    put(cpu, RECEIVER + 0x60, r1)
                else:
                    assert address == create
                    requested = string(cpu, r0)
                    trace_calls.append(["factory", requested])
                    if requested == "audiometer":
                        answer = default
                    else:
                        assert requested == input_strings["interpolator"][1]
                        answer = named
                    cpu.reg_write(UC_ARM_REG_R0, answer)

            trace, writes = run(fw, uc, boundary, code + 0x18c, ATTRS)
            assert trace_calls[0][0] == "View::setAttributes"
            assert base_size is not None and (lookup_count, lookup_height) == (calls, when)
            assert all(RECEIVER + 0x58 <= address <= RECEIVER + 0x5c
                       for address, _, _ in writes)
            flags = sum(flag << index for index, flag in enumerate(uc.mem_read(RECEIVER + 0x58, 3)))
            output = [flags, get(uc, RECEIVER + 0x60), get(uc, RECEIVER + 0x5c),
                      *base_size, lookup_count, lookup_height]
            observations.append(dict(input=list(step), output=output, calls=trace_calls,
                                     writes=writes, trace=trace, provider=result))
        cases.append(dict(input=inputs, steps=observations))
    return dict(boundaries=bounds, virtual_tables=tables, virtual_slot=slot, cases=cases)


def destructor(fw, exe, variant):
    rem = fw.symbol("_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE")
    control = fw.symbol("_ZN4Core8Portable7ControlD2Ev")
    vtable = fw.symbol("_ZTVN8Presonus12MeterControlE")
    code = fw.target["address"]
    if variant == 0:
        delete = fw.plt(0xad5c, "_ZdlPv")
        assert get(fw.machine(), vtable["address"] + 16) == code
    elif variant == 1:
        delete = None
        assert get(fw.machine(), vtable["address"] + 12) == code
    else:
        delete = None
    inputs = [case for case in itertools.product((0, 1), repeat=4) if not (case[0] and case[3])]
    provider_results = provider(exe, "provider-lifecycle", "".join(map(line, inputs)))
    cases = []
    for (owns, peak, primary, borrowed), expected in zip(inputs, provider_results, strict=True):
        uc = fw.machine()
        put(uc, RECEIVER + 0x5c, INTERP if owns else 0, PEAK if peak else 0)
        put(uc, INTERP, INTERP_VT)
        put(uc, INTERP_VT + 4, VIRTUAL_DELETE)
        plt_instructions = tuple(range(delete["address"], delete["address"] + 12, 4)) if delete else ()
        if delete:
            put(uc, delete["got"], HEAP_DELETE)
        calls, digits = [], []
        receiver_live = True

        def boundary(cpu, address):
            nonlocal receiver_live
            r0, r1 = [cpu.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1)]
            if address == VIRTUAL_DELETE:
                assert owns and r0 == INTERP
                calls.append(["Interpolator virtual D0", r0, address])
                digits.append(1)
                cpu.mem_unmap(INTERP, 0x1000)
            elif address == rem["address"]:
                assert peak and (r0, r1) == (PEAK, RECEIVER + 0x44)
                calls.append([rem["mangled"], r0, r1, address])
                digits.append(2)
            elif address == control["address"]:
                assert r0 == RECEIVER
                calls.append([control["mangled"], r0, address])
                if primary:
                    digits.append(3)
                assert int("0" + "".join(map(str, digits))) == expected[0]
            else:
                assert delete and address == HEAP_DELETE and r0 == RECEIVER
                assert calls[-1][0] == control["mangled"] and receiver_live
                calls.append([delete["mangled"], r0, delete["address"]])
                digits.append(4)
                cpu.mem_unmap(RECEIVER, 0x1000)
                receiver_live = False

        trace, writes = run(fw, uc, boundary, code + fw.target["size"] - 4, extra=plt_instructions)
        point = vtable["address"] + 8
        assert struct.unpack_from("<I", bytes.fromhex(fw.target["range_hex"]),
                                  fw.target["size"] - 4)[0] == point
        assert writes == [[RECEIVER+4, 4, point+0x6c],
                          [RECEIVER+0x44, 4, point+0x88], [RECEIVER, 4, point]]
        assert receiver_live == (variant != 0)
        if delete:
            assert all(address in trace for address in plt_instructions)
        cases.append(dict(input=[owns, peak, primary, borrowed], writes=writes,
                          trace=trace, calls=calls, receiver_released=not receiver_live,
                          provider=expected,
                          output=[int("0" + "".join(map(str, digits))), expected[1]]))
    return dict(cases=cases, boundaries=[rem, control, vtable] + ([delete] if delete else []))


def generate(task, exe):
    packet_path = ROOT / PACKETS / task / "CONTEXT.json"
    if not packet_path.exists():
        packet_path = ROOT / SEALED_PACKET / task / "CONTEXT.json"
    packet = json.loads(packet_path.read_text())
    for artifact in packet["task"]["review"]["evidence"]:
        assert digest((ROOT / artifact["path"]).read_bytes()) == artifact["sha256"]
    entry, = packet["originals"]
    original = entry["original"]
    fw = Firmware(original)
    if task.endswith("isvertical"):
        observed = vertical(fw, exe)
    elif task.endswith("setattributes"):
        observed = attributes(fw, exe)
    else:
        observed = destructor(fw, exe, int(original["mangled"][-3]))
    return dict(original=original, **observed)


def replay(task, exe, fixture):
    if task.endswith("setattributes"):
        for case in fixture["cases"]:
            assert provider(exe, "attributes", case["input"]) == [s["output"] for s in case["steps"]]
        return sum(len(case["steps"]) for case in fixture["cases"])
    cases = fixture["cases"]
    mode = "vertical" if task.endswith("isvertical") else fixture["original"]["mangled"][-4:-2]
    assert provider(exe, mode, "".join(line(c["input"]) for c in cases)) == [c["output"] for c in cases]
    return len(cases)
