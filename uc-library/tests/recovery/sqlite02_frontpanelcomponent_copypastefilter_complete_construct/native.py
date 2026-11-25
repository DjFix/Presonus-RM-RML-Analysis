"""Execute exact ARM filter ranges with separately queried typed CCL inputs."""
import argparse
from hashlib import sha256
import itertools
import json
from pathlib import Path
import struct
import subprocess

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                               UC_ARM_REG_SP)

FILTER = "N8Presonus5Panel19FrontPanelComponent15CopyPasteFilter"
LIFECYCLE = ["C1", "C2", "D1", "D2"]
PREFIX = "_Z" + FILTER
METHOD = "_ZNK" + FILTER[1:]
PAGE = 0x1000
RECEIVER = 0x1000000
PARAM = 0x1010000
META = PARAM + 0x100
CONTROLLER = PARAM + 0x200
NAME = PARAM + 0x300
STACK = 0x1100000
STOP = 0x1200000
PARAM_TYPE = 0x50617261


def body_record(elf, symbols, raw, name):
    symbol, = symbols.get_symbol_by_name(name)
    section = elf.get_section(symbol["st_shndx"])
    address, size = symbol["st_value"], symbol["st_size"]
    offset = section["sh_offset"] + address - section["sh_addr"]
    data = raw[offset:offset + size]
    return {"mangled": name, "address": address, "size": size,
            "section": symbol["st_shndx"], "section_name": section.name,
            "file_offset": offset, "range_sha256": sha256(data).hexdigest(),
            "range_hex": data.hex()}


def data_word(body, offset):
    return struct.unpack_from("<I", bytes.fromhex(body["range_hex"]), offset)[0]


def query(executable, inputs):
    command = [str(executable.resolve()), "describe", *map(str, inputs)]
    return list(map(int, subprocess.check_output(command, text=True).split()))


def observe(original, firmware_root, executable):
    path = firmware_root / original["elf_path"]
    raw = path.read_bytes()
    assert sha256(raw).hexdigest() == original["elf"]
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        symbols = elf.get_section_by_name(".symtab")
        def bind(name):
            return body_record(elf, symbols, raw, name)

        target = bind(original["mangled"])
        assert all(original[key] == value for key, value in target.items())
        variant = target["mangled"][-4:-2] if target["mangled"].startswith(PREFIX) else "load"
        ctor = bind(PREFIX + ("C2Ev" if variant == "D2" else "C1Ev"))
        load = bind(METHOD + "10shouldLoadEiPKcPv")
        save = bind(METHOD + "10shouldSaveEiPKcPv")
        vtable = bind("_ZTV" + FILTER + "E")
        rtti = bind("_ZTI" + FILTER + "E")
        base_rtti = bind("_ZTIN4Core8Portable14IStorageFilterE")
        assert data_word(rtti, 8) == base_rtti["address"]
        assert data_word(vtable, 4) == rtti["address"]
        assert data_word(vtable, 8) == load["address"]
        assert data_word(vtable, 12) == save["address"]
        getter = bind("_ZNK4Core8Portable9Parameter13getControllerEv")
        relocations = elf.get_section_by_name(".rel.plt")
        dynsym = elf.get_section(relocations["sh_link"])
        plt = elf.get_section_by_name(".plt")
        cast, = [plt["sh_addr"] + 20 + 12 * index
                 for index, relocation in enumerate(relocations.iter_relocations())
                 if dynsym.get_symbol(relocation["r_info_sym"]).name == "__dynamic_cast"]
        segments = [(segment["p_vaddr"], segment.data(), segment["p_memsz"])
                    for segment in elf.iter_segments() if segment["p_type"] == "PT_LOAD"]

    if variant == "load":
        cases = [
            [0, 0, 0, 0, 218], [0, 1, 1, 2, 219],
            [PARAM_TYPE, 0, 1, 0, 218], [PARAM_TYPE, 1, 0, 0, 219],
            [PARAM_TYPE, 1, 1, 1, 219],
            *([PARAM_TYPE, 1, name, 2, tag]
              for name, tag in itertools.product(range(2), [-1, 217, 218, 219, 220, 223, 224]))
        ]
    else:
        cases = [[0], [0x40]]
    observations = []
    for inputs in cases:
        receiver = RECEIVER + (0 if variant == "load" else inputs[0])
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        image_end = max(addr + size for addr, _, size in segments)
        uc.mem_map(0, (image_end + PAGE - 1) & -PAGE)
        for addr, data, _ in segments:
            uc.mem_write(addr, data)
        for page in (RECEIVER, PARAM, STACK, STOP):
            uc.mem_map(page, PAGE)
        initial = b"\xa5" * PAGE
        uc.mem_write(RECEIVER, initial)
        uc.mem_write(NAME, b"copy\0")

        def invoke(function, args):
            uc.reg_write(UC_ARM_REG_SP, STACK + PAGE - 16)
            uc.reg_write(UC_ARM_REG_LR, STOP)
            for register, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                                        UC_ARM_REG_R3), args):
                uc.reg_write(register, value)
            uc.emu_start(function["address"], STOP, count=1000)
            assert uc.reg_read(UC_ARM_REG_PC) == STOP
            return uc.reg_read(UC_ARM_REG_R0)

        if variant in ("D1", "D2", "load"):
            invoke(ctor, [receiver])
        if variant == "load":
            type_id, has_object, has_name, _, _ = inputs
            provider = query(executable, inputs)
            uc.mem_write(PARAM + 12, struct.pack("<I", META))
            uc.mem_write(META + 4, struct.pack("<i", provider[2]))
            registers = [receiver, type_id, NAME if has_name else 0,
                         PARAM if has_object else 0]
        else:
            registers = [receiver]

        calls, writes, pcs = [], [], []

        def on_code(machine, address, size, _):
            def reg(register):
                return machine.reg_read(register)

            if variant == "load" and address == getter["address"]:
                assert reg(UC_ARM_REG_R0) == PARAM
                calls.append("Parameter::getController")
                machine.reg_write(UC_ARM_REG_R0, CONTROLLER if provider[0] else 0)
            elif variant == "load" and address == cast:
                assert (reg(UC_ARM_REG_R0), reg(UC_ARM_REG_R1), reg(UC_ARM_REG_R2),
                        reg(UC_ARM_REG_R3)) == (CONTROLLER, data_word(save, 136),
                                               data_word(save, 140), 4)
                calls.append("__dynamic_cast")
                machine.reg_write(UC_ARM_REG_R0, CONTROLLER if provider[1] else 0)
            else:
                permitted = [target, save] if variant == "load" else [target]
                assert any(body["address"] <= address < body["address"] + body["size"]
                           for body in permitted), hex(address)
                pcs.append(address)
                if variant == "load" and address == save["address"]:
                    assert [reg(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1,
                                             UC_ARM_REG_R2, UC_ARM_REG_R3)] == registers
                    calls.append("original virtual shouldSave")
                return
            machine.reg_write(UC_ARM_REG_PC, reg(UC_ARM_REG_LR))

        def on_write(_, unused_type, address, size, value, unused_data):
            if STACK <= address and address + size <= STACK + PAGE:
                return
            assert address == receiver and size == 4 and variant != "load"
            writes.append([address - receiver, size, value])

        uc.hook_add(UC_HOOK_CODE, on_code)
        uc.hook_add(UC_HOOK_MEM_WRITE, on_write)
        returned = invoke(target, registers)
        dispatch = vtable["address"] + 8
        assert uc.mem_read(RECEIVER, PAGE) == (
            initial[:receiver - RECEIVER] + struct.pack("<I", dispatch) +
            initial[receiver - RECEIVER + 4:]
        )
        if variant == "load":
            assert not writes and calls[0] == "original virtual shouldSave"
            output = {"result": returned, "provider": provider}
        else:
            assert not calls and writes == [[0, 4, dispatch]] and returned == receiver
            output = {"dispatch_initialized": True, "receiver_retained": True}
        observations.append({"inputs": inputs, "output": output, "calls": calls,
                             "receiver_writes": writes, "instruction_pcs": pcs})
    ranges = {body["mangled"]: body for body in
              (ctor, load, save, rtti, vtable, base_rtti, getter)}
    return {"elf_sha256": original["elf"], "firmware": original["firmware"],
            "role": original["role"], "target": target, "variant": variant,
            "support_ranges": ranges, "dynamic_cast_plt": cast,
            "observations": observations}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("context", type=Path)
    parser.add_argument("firmware_root", type=Path)
    parser.add_argument("executable", type=Path)
    args = parser.parse_args()
    records = json.loads(args.context.read_text())["originals"]
    print(json.dumps([observe(row["original"], args.firmware_root, args.executable)
                      for row in records], indent=2))


if __name__ == "__main__":
    main()
