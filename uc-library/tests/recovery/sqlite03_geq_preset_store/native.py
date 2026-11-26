"""Run the original application body with typed, instrumented ARM boundaries."""
import hashlib
import json
import pathlib
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP,
)

ROOT = pathlib.Path(__file__).resolve().parents[4]
PACKET = "temp/recovery-work/sqlite-issued/packet/sqlite03_geq_preset_store/CONTEXT.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def generate():
    target = json.loads((ROOT / PACKET).read_text())["originals"][0]["original"]
    elf = ROOT / target["elf_path"]
    blob = elf.read_bytes()
    assert sha(blob) == target["elf"]
    with elf.open("rb") as file:
        parsed = ELFFile(file)
        symbol, = parsed.get_section_by_name(".symtab").get_symbol_by_name(target["mangled"])
        address, size, index = (symbol[key] for key in ("st_value", "st_size", "st_shndx"))
        assert (address, size, index) == (target["address"], target["size"], target["section"])
        section = parsed.get_section(index)
        offset = section["sh_offset"] + address - section["sh_addr"]
        assert offset == target["file_offset"] and section.name == target["section_name"]
        body = blob[offset:offset + size]
        assert sha(body) == target["range_sha256"] and body.hex() == target["range_hex"]

        def elf_bytes(address, count):
            for section in parsed.iter_sections():
                start = section["sh_addr"]
                if start <= address and address + count <= start + section["sh_size"]:
                    assert section["sh_type"] != "SHT_NOBITS"
                    offset = section["sh_offset"] + address - start
                    return blob[offset:offset + count]
            raise AssertionError(hex(address))

        mode, category, builder_vtable, error = struct.unpack("<IIII", body[-16:])
        mode_bytes = elf_bytes(mode, 16)
        category_bytes = elf_bytes(category, 1)

    seeds = [
        (None, [], True, "Empty"),
        (None, [0, 1], True, "Default"),
        (None, [None, 1], True, "Null"),
        (1.9, [0, 1], True, "Second"),
        (-0.9, [0, 1], False, "SaveReturnedFalse"),
        (-1.2, [0, 1], True, "Negative"),
        (2, [0, 1], True, "UpperBound"),
        (1.1, [0, None], True, "SelectedNull"),
        (0, [1], True, ""),
    ]
    cases = [execute(address, body, mode, mode_bytes, category, category_bytes,
                     builder_vtable, error, *seed) for seed in seeds]
    return {"original": {k: v for k, v in target.items() if k != "range_hex"}, "cases": cases}


def execute(address, body, mode, mode_bytes, category, category_bytes,
            builder_vtable, error, selection, roster, save_result, name):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    pages = set()

    def map_page(address):
        page = address & ~4095
        if page not in pages:
            uc.mem_map(page, 4096)
            pages.add(page)

    def write(address, value):
        uc.mem_write(address, struct.pack("<I", value))

    def read(address):
        return struct.unpack("<I", uc.mem_read(address, 4))[0]

    def string(address, limit=256):
        result = bytes(uc.mem_read(address, limit)).split(b"\0", 1)
        assert len(result) == 2
        return result[0].decode()

    obj, mixer, items = 0x10000000, 0x10001000, 0x10002000
    selector, name_param, table = 0x10003000, 0x10004000, 0x10005000
    eq = [0x10006000, 0x10007000]
    stop, sp = 0x10008000, 0x1000a800
    get_value, save, to_string = stop + 4, stop + 8, stop + 12
    allocator, attributes, builder = 0x121dbc, 0x121a68, 0x117950
    tag, do_save, cleanup, destroy = 0x119c4c, 0x83f3c, 0x2f178, 0x1228b0
    convert = 0x157958
    for point in [obj, mixer, items, selector, name_param, table, *eq, stop, sp,
                  address, mode, category, error, allocator, attributes, builder, tag,
                  do_save, cleanup, destroy, convert]:
        map_page(point)
    uc.mem_write(address, body)
    uc.mem_write(mode, mode_bytes)
    uc.mem_write(category, category_bytes)
    write(obj + 0xc4, mixer)
    write(obj + 0xc8, selector if selection is not None else 0)
    write(mixer + 0x2b0, items)
    write(mixer + 0x2b4, len(roster))
    for i, entry in enumerate(roster):
        write(items + 4*i, eq[entry] if entry is not None else 0)
    for instance in [selector, name_param, *eq]:
        write(instance, table)
    write(table + 0x44, get_value)
    write(table + 0x24, save)
    write(table + 0x70, to_string)
    assert read(error) == 0
    trace, pcs = [], []
    state = {}

    def hook(uc, pc, _, __):
        if pc == stop:
            uc.emu_stop()
            return
        if address <= pc < address + len(body) - 16:
            pcs.append(pc - address)
            return
        r0, r1, r2, r3 = [uc.reg_read(reg) for reg in (
            UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)]
        result = 0
        if pc == get_value:
            assert r0 == selector
            result = struct.unpack("<I", struct.pack("<f", selection))[0]
            trace.append(["selector", selection])
        elif pc == convert:
            result = int(struct.unpack("<f", struct.pack("<I", r0))[0])
            trace.append(["truncate", result])
        elif pc == allocator:
            result = table + 0x200
        elif pc == attributes:
            assert r1 == table + 0x200
            state["attributes"] = r0
        elif pc == builder:
            assert r1 == state["attributes"] and r2 == 1
            state["builder"] = r0
        elif pc == save:
            assert read(r1 + 44) == state["builder"]
            assert [read(r1 + p) for p in (32, 36, 40)] == [0, 0, 0]
            trace.append(["save", eq.index(r0), string(r1, 32)])
            write(state["attributes"], 71 + eq.index(r0))
            result = int(save_result)
        elif pc == tag:
            assert r0 == obj and r1 == 2
            trace.append(["tag", r1])
            result = name_param
        elif pc == to_string:
            assert r0 == name_param and r2 == 256 and uc.mem_read(r1, 1) == b"\0"
            trace.append(["name", r2, name])
            uc.mem_write(r1, name.encode() + b"\0")
        elif pc == do_save:
            assert r0 == obj and r3 == state["attributes"]
            trace.append(["persist", string(r1), string(r2, 1), read(r3)])
        elif pc == cleanup:
            assert r0 == state["builder"] + 4 and read(r0 - 4) == builder_vtable
        elif pc == destroy:
            assert r0 == state["attributes"]
        else:
            raise AssertionError(hex(pc))
        uc.reg_write(UC_ARM_REG_R0, result & 0xffffffff)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    uc.hook_add(UC_HOOK_CODE, hook)
    uc.reg_write(UC_ARM_REG_SP, sp)
    uc.reg_write(UC_ARM_REG_LR, stop)
    uc.reg_write(UC_ARM_REG_R0, obj)
    uc.emu_start(address, stop + 0x100, count=1000)
    assert uc.reg_read(UC_ARM_REG_PC) == stop
    assert uc.reg_read(UC_ARM_REG_SP) == sp
    return {
        "input": dict(selection=selection, roster=roster, save_result=save_result, name=name),
        "result": uc.reg_read(UC_ARM_REG_R0),
        "trace": trace,
        "pcs": pcs,
    }


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
