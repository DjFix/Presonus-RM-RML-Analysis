"""Replay original ARM SevenSegControl and Control constructor ranges offline."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
import unicorn as arm
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP,
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def symbol(elf, name):
    found = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    assert len(found) == 1
    return found[0]


def function(elf, image, name):
    row = symbol(elf, name)
    section = elf.get_section(row["st_shndx"])
    address, size = row["st_value"], row["st_size"]
    relative = address - section["sh_addr"]
    assert row["st_info"]["type"] == "STT_FUNC"
    assert section.name == ".text" and section["sh_type"] == "SHT_PROGBITS"
    assert 0 <= relative <= section["sh_size"] - size
    offset = section["sh_offset"] + relative
    code = image[offset:offset + size]
    identity = dict(mangled=name, address=address, size=size,
                    section=row["st_shndx"], file_offset=offset,
                    range_sha256=sha(code), range_hex=code.hex())
    return identity, code


def execute(address, code, seed, tag):
    start, stack, receiver, stop = address & ~4095, 0x800800, 0x900100, 0xa00000
    machine = arm.Uc(arm.UC_ARCH_ARM, arm.UC_MODE_ARM)
    for page, length in ((start, 8192), (stack & ~4095, 4096),
                         (receiver & ~4095, 4096), (stop, 4096)):
        machine.mem_map(page, length)
    machine.mem_write(address, code)
    initial = bytes((seed + index * 19) % 256 for index in range(64))
    machine.mem_write(receiver - 16, initial)
    for reg, value in ((UC_ARM_REG_SP, stack), (UC_ARM_REG_LR, stop),
                       (UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, tag & 0xffffffff)):
        machine.reg_write(reg, value)

    accesses = []
    pcs = []

    def record(_machine, kind, at, size, value, _data):
        if stack - 16 <= at <= stack - size:
            return
        if receiver <= at <= receiver + 32 - size:
            assert kind == arm.UC_MEM_WRITE and size == 4
            accesses.append(["receiver_write", at - receiver, value])
        else:
            assert kind == arm.UC_MEM_READ and at == address + len(code) - 4
            accesses.append(["literal_read", at, size])

    machine.hook_add(arm.UC_HOOK_MEM_WRITE | arm.UC_HOOK_MEM_READ, record)
    machine.hook_add(arm.UC_HOOK_CODE, lambda _m, pc, _size, _data: pcs.append(pc))
    machine.emu_start(address, stop, count=24)
    assert machine.reg_read(UC_ARM_REG_PC) == stop
    assert machine.reg_read(UC_ARM_REG_SP) == stack
    assert machine.reg_read(UC_ARM_REG_R0) == receiver
    assert pcs == list(range(address, address + len(code) - 4, 4))
    actual = bytes(machine.mem_read(receiver - 16, 64))
    assert actual[:16] == initial[:16] and actual[48:] == initial[48:]
    return dict(seed=seed, argument=tag, before=initial.hex(), after=actual.hex(),
                executed=pcs, accesses=accesses)


def observe(packet, rootfs):
    entries = []
    context = json.loads(packet.read_text())
    for item in context["originals"]:
        original = item["original"]
        image = (rootfs / Path(original["elf_path"]).relative_to("rootfs")).read_bytes()
        assert sha(image) == original["elf"]
        elf = ELFFile(io.BytesIO(image))
        assert elf.little_endian and elf.elfclass == 32 and elf["e_machine"] == "EM_ARM"
        identity, code = function(elf, image, original["mangled"])
        assert all(original[key] == value for key, value in identity.items())
        variant = identity["mangled"][-3]
        other, _ = function(elf, image, identity["mangled"][:-3] + ("2" if variant == "1" else "1") + "Ev")
        assert identity["address"] != other["address"]
        assert identity["range_sha256"] == other["range_sha256"]
        base, base_code = function(elf, image, f"_ZN8Presonus5Panel7ControlC{variant}Ei")
        point = symbol(elf, "_ZTVN8Presonus5Panel15SevenSegControlE")["st_value"] + 8
        base_point = symbol(elf, "_ZTVN8Presonus5Panel7ControlE")["st_value"] + 8
        baselines = []
        cases = []
        for seed, tag in ((17, -2147483648), (129, -7), (241, 2147483647)):
            base_case = execute(base["address"], base_code, seed, tag)
            baselines.append(base_case)
            base_words = struct.unpack_from("<IiIIIII", bytes.fromhex(base_case["after"]), 16)
            assert base_words == (base_point, -1, 0, 0, 0, 0, tag & 0xffffffff)
            assert base_case["before"][88:96] == base_case["after"][88:96]
            case = execute(identity["address"], code, seed, tag)
            words = struct.unpack_from("<IiIIII IHH", bytes.fromhex(case["after"]), 16)
            assert words == (point, *base_words[1:-1], 0, 0, 0)
            case["portable"] = list(words[1:])
            cases.append(case)
        entries.append(dict(original=original, sibling=other, base=base,
                            vtable_address_point=point, base_vtable_address_point=base_point,
                            cases=cases, base_cases=baselines))
    return dict(engine=f"Unicorn {arm.__version__}", entries=entries)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("rootfs", type=Path)
    args = parser.parse_args()
    print(json.dumps(observe(args.packet, args.rootfs), indent=2))
