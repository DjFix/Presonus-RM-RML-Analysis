"""Execute the verified application and ARM conversion bytes with recorded CCL boundaries."""
import hashlib
import itertools
import json
import pathlib
import struct
import sys

import unicorn
from elftools.elf.elffile import ELFFile
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                               UC_ARM_REG_SP)

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PACKET = (ROOT / "temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02"
          / "mcu_vpot_draw01/packet/tasks/sqlite03_mcu_vpot_draw/CONTEXT.json")
SPEC = json.loads(PACKET.read_text())["originals"][0]["original"]
ORIGINAL = ROOT / SPEC["elf_path"]
OBJ = 0x400000
VIRTUAL = 0x401000
PARAM = 0x402000
EVENT = 0x403000
GRAPHICS = 0x404000
STYLE = 0x405000
STACK = 0x500000
STOP = 0x600000
VIRTUAL_CALLS = {STOP + 4: "enabled", STOP + 8: "value",
                 STOP + 12: "fill", STOP + 16: "line"}
DIRECT_CALLS = {0xf7e7c: "background", 0xf76b4: "focus",
                0x10e9bc: "client", 0x10f4b4: "style"}
CALLS = VIRTUAL_CALLS | DIRECT_CALLS
COLOR = 0x78563412


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_ranges():
    assert sha(PACKET.read_bytes()) == "53c5bd748429c86887e49858638f6c4e330a11eb75bc3de8383033f3e3f6337f"
    assert sha(ORIGINAL.read_bytes()) == SPEC["elf"]
    with ORIGINAL.open("rb") as fd:
        elf = ELFFile(fd)

        def load(name):
            matches = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
            symbol, = matches
            index = symbol["st_shndx"]
            section = elf.get_section(index)
            address, size = symbol["st_value"], symbol["st_size"]
            relative = address - section["sh_addr"]
            assert 0 <= relative < relative + size <= section["sh_size"]
            value = section.data()[relative:relative + size]
            return dict(mangled=name, address=address, size=size, section=index,
                        section_name=section.name,
                        file_offset=section["sh_offset"] + relative,
                        range_sha256=sha(value)), value

        body, arm = load(SPEC["mangled"])
        assert all(body[k] == SPEC[k] for k in body)
        assert arm.hex() == SPEC["range_hex"]
        converter, conversion = load("__aeabi_f2iz")
        assert converter["address"] == 0x1877f8
        table, enum_data = load("_ZN4Core8Portable8ValueBar15valueBarOptionsE")
        attributes, attribute_bytes = load("_ZN4Core8Portable8ValueBar13setAttributesERKNS0_10AttributesE")
        is_enabled, enabled_bytes = load("_ZNK4Core8Portable4View9isEnabledEv")
        enable, _ = load("_ZN4Core8Portable4View6enableEb")
        style, style_bytes = load("_ZN4Core8Portable14ViewAttributes8getStyleERNS0_5StyleERKNS0_10AttributesE")
        vtable, vtable_data = load("_ZTVN8Presonus14McuVpotControlE")
        pointer, flag = struct.unpack_from("<II", enum_data)
        rodata = elf.get_section_by_name(".rodata")
        key_offset = pointer - rodata["sh_addr"]
        assert rodata.data()[key_offset:key_offset + 9] == b"vertical\0"
        assert flag == 0x10000
        # ValueBar::setAttributes loads valueBarOptions and ORs the result
        # into View+0x40. Validate the option table pointer and store words.
        assert struct.unpack_from("<I", attribute_bytes, 0x38)[0] == table["address"]
        assert struct.unpack_from("<II", attribute_bytes, 0x2c) == (0xe1800004, 0xe5850040)
        # The native style attribute loader maps forecolor to Style+4.
        forecolor_op = 0x114338 - style["address"]
        forecolor_key, = struct.unpack_from("<I", style_bytes, forecolor_op + 8 + 0x2dc)
        forecolor_offset = forecolor_key - rodata["sh_addr"]
        assert rodata.data()[forecolor_offset:forecolor_offset + 10] == b"forecolor\0"
        assert struct.unpack_from("<I", style_bytes, 0x11438c - style["address"])[0] == 0xe5873004
        assert struct.unpack_from("<I", vtable_data, 8 + 0x64)[0] == 0xf7e7c
        assert bytes.fromhex("010020e2010000e2") in enabled_bytes
        evidence = dict(target=body, runtime_conversion=converter, vertical_table=table,
                        vertical_attribute_consumer=attributes, view_enable=enable,
                        view_is_enabled=is_enabled, style_attributes=style,
                        vtable=vtable, native_flags=dict(vertical=flag, disabled=1, focus=8),
                        native_forecolor_offset=4)
        return evidence, arm, conversion


def run(case, evidence, arm, conversion, pcs):
    machine = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    machine.mem_map(0x66000, 0x1000)
    machine.mem_map(0x187000, 0x1000)
    machine.mem_map(OBJ, 0x10000)
    machine.mem_map(STACK, 0x10000)
    machine.mem_write(evidence["target"]["address"], arm)
    converter = evidence["runtime_conversion"]
    machine.mem_write(converter["address"], conversion)
    for address in set(address & ~0xfff for address in DIRECT_CALLS) | {STOP}:
        machine.mem_map(address, 0x1000)

    def write(address, *words):
        machine.mem_write(address, struct.pack("<" + "I" * len(words), *words))

    def read(address, count=1, code="I"):
        return struct.unpack("<" + code * count, machine.mem_read(address, 4 * count))

    write(OBJ, VIRTUAL)
    write(OBJ + 0x40, case["vertical"] * 0x10000 + case["focus"] * 8 + case["disabled"])
    write(OBJ + 0x48, PARAM if case["primary"] else 0)
    write(OBJ + 0x60, PARAM + 0x100 if case["hasStyle"] else 0,
          PARAM + 0x200 if case["hasDot"] else 0)
    write(VIRTUAL + 0x64, 0xf7e7c)
    trace = []
    for i, value in enumerate((case["value"], case["style"], case["dot"])):
        write(PARAM + i * 0x100, VIRTUAL + 0x100)
        machine.mem_write(PARAM + i * 0x100 + 4, struct.pack("<f", value))
    write(VIRTUAL + 0x120, STOP + 4)
    write(VIRTUAL + 0x144, STOP + 8)
    write(EVENT, GRAPHICS)
    write(GRAPHICS, VIRTUAL + 0x200)
    write(VIRTUAL + 0x214, STOP + 12)
    write(VIRTUAL + 0x21c, STOP + 16)
    write(STYLE, 0x11223344, COLOR, 0x55667788)

    def hook(emu, address, length, _):
        pcs.add(address)
        if address not in CALLS:
            assert any(r["address"] <= address <= r["address"] + r["size"] - length
                       for r in (evidence["target"], converter)), hex(address)
            return
        kind = CALLS[address]
        r0, r1, r2, r3 = [emu.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1,
                                                  UC_ARM_REG_R2, UC_ARM_REG_R3)]
        result = 0
        if kind == "enabled":
            assert r0 == PARAM
            result = case["enabled"]
        elif kind == "value":
            assert r0 in (PARAM, PARAM + 0x100, PARAM + 0x200)
            result, = read(r0 + 4)
        elif kind == "client":
            assert r0 == OBJ
            write(r1, 0, 0, case["width"], case["height"])
            result = r1
        elif kind == "style":
            assert r0 == OBJ
            result = STYLE
        elif kind == "fill":
            assert r0 == GRAPHICS
            trace.append([kind, *read(r1, 4, "i"), *read(r2)])
            result = 1
        elif kind == "line":
            assert r0 == GRAPHICS
            trace.append([kind, *read(r1, 2, "i"), *read(r2, 2, "i"), *read(r3)])
            result = 1
        elif kind in ("background", "focus"):
            assert (r0, r1) == (OBJ, EVENT)
            trace.append([kind])
        else:
            raise AssertionError(kind)
        emu.reg_write(UC_ARM_REG_R0, result)
        emu.reg_write(UC_ARM_REG_PC, emu.reg_read(UC_ARM_REG_LR))

    before = machine.mem_read(OBJ, 0x10000)
    machine.hook_add(unicorn.UC_HOOK_CODE, hook)
    for register, value in ((UC_ARM_REG_R0, OBJ), (UC_ARM_REG_R1, EVENT),
                            (UC_ARM_REG_SP, STACK + 0x8000), (UC_ARM_REG_LR, STOP)):
        machine.reg_write(register, value)
    machine.emu_start(evidence["target"]["address"], STOP, count=4000)
    assert machine.reg_read(UC_ARM_REG_PC) == STOP
    assert machine.mem_read(OBJ, 0x10000) == before
    return trace


def inputs():
    base = dict(width=105, height=21, primary=1, enabled=1, vertical=0, disabled=0,
                focus=0, hasStyle=1, hasDot=1, value=2.25, style=3.0, dot=-1.25)
    families = [
        dict(primary=(0, 1), enabled=(0, 1), vertical=(0, 1),
             disabled=(0, 1), focus=(0, 1)),
        dict(hasStyle=(0, 1), style=(-1.9, 0, 1.9, 2.9, 3.9, 4.5, 1e12),
             value=(-1e12, -8, -5, -2.9, -1, 0, 0.9, 1.9, 4, 5, 8, 1e12)),
        dict(width=(0, 1, 9, 10, 20, 21, 31, 32, 99, 100, 101, 105),
             height=(0, 1, 8, 9, 10, 20, 21), style=(1, 2, 3)),
        dict(hasDot=(0, 1), dot=(-1e12, -1.7, -0.9, 0, 0.9, 1.7, 1e12),
             focus=(0, 1), height=(1, 8, 40)),
    ]
    seen = set()
    for options in families:
        for values in itertools.product(*options.values()):
            case = base | dict(zip(options, values))
            key = tuple(case.values())
            if key not in seen:
                seen.add(key)
                yield case


def main():
    evidence, arm, conversion = load_ranges()
    pcs = set()
    cases = [case | {"expected": run(case, evidence, arm, conversion, pcs)}
             for case in inputs()]
    data = dict(elf_sha256=SPEC["elf"], packet_sha256=sha(PACKET.read_bytes()),
                oracle_sha256=sha(pathlib.Path(__file__).read_bytes()),
                unicorn=unicorn.__version__, ranges=evidence,
                executed_addresses=sorted(pcs), cases=cases)
    path = HERE / "fixtures.json"
    if "--verify" in sys.argv:
        assert json.loads(path.read_text()) == data
    else:
        path.write_text(json.dumps(data, separators=(",", ":")) + "\n")
    print(f"{len(cases)} native ARM executions matched; {len(pcs)} instruction and boundary addresses")


if __name__ == "__main__":
    main()
