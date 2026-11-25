"""Hash-bound ARM observations for the seven MeterLevelControl packets."""

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP,
)

PAGE = 4096
RECEIVER, STACK, STOP, TIMER, PARAM, ITEMS = range(0x71000000, 0x71006000, PAGE)
METER = "_ZN8Presonus5Panel17MeterLevelControl"
CONTROL = "_ZN8Presonus5Panel7Control"
CASTS = (0x4d4c436c, 0x4d43746c, 0x4374726c, 0x4d4c436b, 0x4d4c436d,
         0x4d43746b, 0x4d43746d, 0x4374726b, 0x4374726d, 0, -1)
SIGNED = (0, -1, -2147483648, 2147483647, 17)


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Image:
    def __init__(self, original):
        self.raw = Path(original["elf_path"]).read_bytes()
        assert digest(self.raw) == original["elf"]
        self.elf = ELFFile(io.BytesIO(self.raw))
        self.symtab = self.elf.get_section_by_name(".symtab")

    def symbol(self, name):
        symbol, = self.symtab.get_symbol_by_name(name)
        return symbol

    def code(self, name):
        symbol = self.symbol(name)
        section_index = symbol["st_shndx"]
        section = self.elf.get_section(section_index)
        start, size = symbol["st_value"], symbol["st_size"]
        relative = start - section["sh_addr"]
        assert 0 <= relative <= relative + size <= section["sh_size"]
        offset = section["sh_offset"] + relative
        assert 0 <= offset <= offset + size <= len(self.raw)
        return start, self.raw[offset:offset + size], offset, section_index, section.name

    def rtti(self, name):
        address, data, offset, section, section_name = self.code("_ZTIN8Presonus5Panel" + name + "E")
        _, _, base = struct.unpack("<III", data)
        return {"address": address, "file_offset": offset, "section": section,
                "section_name": section_name, "bytes": data.hex(), "base_rtti": base}

    def delete_plt(self):
        reloc = self.elf.get_section_by_name(".rel.plt")
        symbols = self.elf.get_section(reloc["sh_link"])
        index, = (i for i, r in enumerate(reloc.iter_relocations())
                  if symbols.get_symbol(r["r_info_sym"]).name == "_ZdlPv")
        return self.elf.get_section_by_name(".plt")["sh_addr"] + 20 + 12 * index


def read_word(uc, addr):
    return struct.unpack("<I", uc.mem_read(addr, 4))[0]


def put_word(uc, addr, value):
    uc.mem_write(addr, struct.pack("<I", value & 0xffffffff))


def receiver_state(uc, vtable):
    return [read_word(uc, RECEIVER) == vtable, *[
        struct.unpack("<i", uc.mem_read(RECEIVER + off, 4))[0]
        for off in (0x18, 4, 8, 12, 16, 20, 0x20, 0x24, 0x28)],
        uc.mem_read(RECEIVER + 0x30, 1)[0]]


def invoke(uc, address, arg):
    for reg, value in ((UC_ARM_REG_R0, RECEIVER), (UC_ARM_REG_R1, arg & 0xffffffff),
                       (UC_ARM_REG_LR, STOP), (UC_ARM_REG_SP, STACK + PAGE // 2)):
        uc.reg_write(reg, value)
    uc.emu_start(address, STOP, count=250)
    assert uc.reg_read(UC_ARM_REG_PC) == STOP
    assert uc.reg_read(UC_ARM_REG_SP) == STACK + PAGE // 2
    return uc.reg_read(UC_ARM_REG_R0)


def execute(image, name, address, body, arg):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    pages = set()

    def mapped(address, size=1):
        for page in range(address & -PAGE, ((address + size - 1) & -PAGE) + PAGE, PAGE):
            if page not in pages:
                uc.mem_map(page, PAGE)
                pages.add(page)

    for addr in (RECEIVER, STACK, STOP, TIMER, PARAM, ITEMS):
        mapped(addr)
    uc.mem_write(RECEIVER, b"\xa5" * 0x40)

    def load(start, code):
        mapped(start, len(code))
        uc.mem_write(start, code)

    load(address, body)
    ctor, ctor_body, *_ = image.code(METER + "C1Ei")
    load(ctor, ctor_body)
    vtable = image.symbol("_ZTVN8Presonus5Panel17MeterLevelControlE")["st_value"] + 8
    base, base_body, base_offset, base_section, base_section_name = image.code(CONTROL + "D2Ev")
    meter_base_vtable = image.symbol("_ZTVN8Presonus5Panel12MeterControlE")["st_value"] + 8
    destructor = name.startswith(METER + "D")
    ctor_case = name.startswith(METER + "C")
    mode_case = name.endswith("16getParameterModeEv")
    boundaries = {}
    lifecycles, writes = [], []
    immediate, indirect = image.rtti("17MeterLevelControl"), image.rtti("12MeterControl")
    assert immediate["base_rtti"] == indirect["address"]
    assert indirect["base_rtti"] == image.symbol("_ZTIN8Presonus5Panel7ControlE")["st_value"]
    trace = {"meter_level_rtti": immediate, "meter_control_rtti": indirect,
             "initialization_range": {"address": ctor, "range_sha256": digest(ctor_body)},
             "meter_level_vtable": vtable, "meter_control_vtable": meter_base_vtable}

    if not ctor_case:
        invoke(uc, ctor, 23)
        assert read_word(uc, RECEIVER) == vtable
    if mode_case and arg != 0:
        put_word(uc, RECEIVER + 0x28, arg)

    if destructor:
        load(base, base_body)
        timers = image.symbol(CONTROL + "6timersE")["st_value"]
        mapped(timers, 12)
        put_word(uc, RECEIVER + 8, PARAM)
        put_word(uc, RECEIVER + 12, PARAM + 0x40)
        put_word(uc, RECEIVER + 16, PARAM + 0x80)
        put_word(uc, TIMER, RECEIVER)
        put_word(uc, ITEMS, TIMER)
        put_word(uc, timers + 4, ITEMS)
        put_word(uc, timers + 8, arg)
        remove = image.symbol("_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE")["st_value"]
        # ControlD2's verified callable body performs both cleanup traversals.
        # Hook its provider leaves at their resolved call targets.
        calls = [int(i.op_str[1:], 16) for i in Cs(CS_ARCH_ARM, CS_MODE_ARM).disasm(base_body, base)
                 if i.mnemonic == "bl"]
        deletes = image.delete_plt()
        assert calls[:3] == [remove] * 3 and calls[-1] == deletes and len(calls) == 5
        boundaries = {remove: "unregister", calls[3]: "remove_timer", deletes: "delete"}
        for entry in boundaries:
            mapped(entry)
        trace.update(base_address=base, base_size=len(base_body), base_file_offset=base_offset,
                     base_section=base_section, base_section_name=base_section_name,
                     base_range_sha256=digest(base_body), boundary_addresses=boundaries)

    def at_code(machine, pc, size, _):
        if destructor and pc == base:
            assert machine.reg_read(UC_ARM_REG_R0) == RECEIVER
            assert read_word(machine, RECEIVER) == meter_base_vtable
            lifecycles.append("control")
        boundary = boundaries.get(pc)
        if boundary is None:
            assert address <= pc < address + len(body) or destructor and base <= pc < base + len(base_body)
            return
        r0 = machine.reg_read(UC_ARM_REG_R0)
        r1 = machine.reg_read(UC_ARM_REG_R1)
        if boundary == "unregister":
            assert r1 == RECEIVER and r0 in (PARAM, PARAM + 0x40, PARAM + 0x80)
            lifecycles.append(f"unregister_{(r0 - PARAM) // 0x40}")
        elif boundary == "remove_timer":
            assert r0 == timers + 4 and read_word(machine, r1) == TIMER
            put_word(machine, timers + 8, 0)
            lifecycles.append(boundary)
        elif r0 == TIMER:
            machine.mem_unmap(TIMER, PAGE)
            lifecycles.append("delete_timer")
        else:
            assert r0 == RECEIVER
            machine.mem_unmap(RECEIVER, PAGE)
            lifecycles.append("delete_receiver")
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    def at_write(machine, access, addr, size, value, _):
        if RECEIVER <= addr < RECEIVER + 0x40:
            writes.append([addr - RECEIVER, size, value & ((1 << (size * 8)) - 1)])

    uc.hook_add(UC_HOOK_CODE, at_code)
    uc.hook_add(UC_HOOK_MEM_WRITE, at_write)
    output = invoke(uc, address, arg)
    if ctor_case:
        result = receiver_state(uc, vtable)
    elif destructor:
        assert ("delete_receiver" in lifecycles) == name.endswith("D0Ev")
        assert read_word(uc, timers + 8) == 0
        if not name.endswith("D0Ev"):
            assert read_word(uc, RECEIVER + 8) == 0
        result = lifecycles
    elif mode_case:
        result = struct.unpack("<i", struct.pack("<I", output))[0]
        assert not writes
    else:
        assert output in (0, RECEIVER) and not writes
        result = output == RECEIVER
    return {"arg": arg, "result": result, "writes": writes, **trace}


def observations(original):
    image = Image(original)
    name = original["mangled"]
    address, body, offset, section, section_name = image.code(name)
    assert (address, len(body), offset, section, section_name, digest(body), body.hex()) == (
        original["address"], original["size"], original["file_offset"], original["section"],
        original["section_name"], original["range_sha256"], original["range_hex"])
    args = ((0, 1) if name.startswith(METER + "D") else CASTS
            if name.endswith("6castToEi") else SIGNED)
    return [execute(image, name, address, body, arg) for arg in args]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text())
    value = []
    for entry in packet["originals"]:
        origin = entry["original"]
        value.append({"original": origin, "cases": observations(origin)})
    value = json.loads(json.dumps(value))
    if args.generate:
        args.fixture.write_text(json.dumps(value, indent=2) + "\n")
    else:
        assert json.loads(args.fixture.read_text()) == value
    print(f"ARM cases: {sum(len(origin['cases']) for origin in value)}")


if __name__ == "__main__":
    main()
