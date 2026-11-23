"""Compare an exact original application range with typed portable observations."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

import unicorn as uc
from elftools.elf.elffile import ELFFile
from unicorn import arm_const as arm

TASK = "20"
CASES = {
    "13": [[], [0.0], [1.75], [-8.875], [127.25]],
    "14": [[], [0], [0xFF573412], [0x7FAB00EF]],
    "16": [[-1, 0], [0, 1], [1, 3], [2, 3], [4, 3]],
    "19": [[], [1], [1, 0, 1], [0, 1, 0, 1]],
    "20": [[], [1], [1, 0, 1], [0, 1, 0, 1]],
}
THIS, OWNER, ITEMS, CONTROL, PARAM, TABLE = range(0x40000000, 0x40006000, 0x1000)
STACK, STOP, VIRTUAL = 0x50000800, 0x71000F00, 0x71000000
ARG_REGS = (arm.UC_ARM_REG_R0, arm.UC_ARM_REG_R1, arm.UC_ARM_REG_R2, arm.UC_ARM_REG_R3)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_symbol(elf, name):
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    section = elf.get_section(symbol["st_shndx"])
    addr, size = symbol["st_value"], symbol["st_size"]
    offset = addr - section["sh_addr"]
    assert 0 <= offset <= offset + size <= section["sh_size"]
    data = section.data()[offset:offset + size]
    return data, {
        "mangled": name, "address": addr, "size": size, "section": symbol["st_shndx"],
        "file_offset": section["sh_offset"] + offset, "sha256": sha(data),
    }


def branch_targets(data, address):
    targets = []
    for offset in range(0, len(data), 4):
        word, = struct.unpack_from("<I", data, offset)
        if word >> 24 == 0xEB:
            imm = word & 0xFFFFFF
            targets.append(address + offset + 8 + 4 * (imm - 0x1000000 if imm & 0x800000 else imm))
    return targets


def replay(code, target, values, dependencies):
    m = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_ARM)
    body_ranges = [(code, target), *dependencies]
    pages = {THIS, OWNER, ITEMS, CONTROL, PARAM, TABLE, STACK & ~4095, STOP & ~4095}
    boundaries = {}
    if TASK in ("13", "14"):
        callee, = branch_targets(code, target["address"])
        pages.add(callee & ~4095)
        boundaries[callee] = "float_truncate" if TASK == "13" else "color_value"
        boundaries[VIRTUAL] = "numeric_value" if TASK == "13" else "color_parameter"
    if TASK in ("19", "20"):
        boundaries[VIRTUAL] = "set_parameter" if TASK == "19" else "reset_value"
    for data, info in body_ranges:
        start = info["address"]
        pages.update(range(start & ~4095, (start + len(data) + 4095) & ~4095, 4096))
    for page in sorted(pages):
        m.mem_map(page, 4096)
    for data, info in body_ranges:
        m.mem_write(info["address"], data)

    def put(addr, value):
        m.mem_write(addr, struct.pack("<I", value))

    if TASK == "13" and values:
        put(THIS + 0x1D4, PARAM)
        put(PARAM, TABLE)
        put(TABLE + 0x44, VIRTUAL)
    if TASK == "14":
        put(THIS, TABLE)
        put(TABLE + 0x40, VIRTUAL)
    if TASK == "16":
        index, count = values
        if index != -1:
            put(THIS + 0x50, OWNER)
            put(OWNER + 0x58, ITEMS)
            put(OWNER + 0x5C, count)
            for i in range(count):
                put(ITEMS + i * 4, THIS if i == index else CONTROL + i * 16)
    if TASK in ("19", "20"):
        put(THIS + 8, ITEMS)
        put(THIS + 12, len(values))
        for i, bound in enumerate(values):
            control, parameter = CONTROL + i * 32, PARAM + i * 32
            put(ITEMS + 4 * i, control)
            put(control, TABLE)
            put(control + 8, parameter if bound else 0)
            put(parameter, TABLE)
        put(TABLE + (16 if TASK == "19" else 0x5C), VIRTUAL)

    observed, writes = [], []
    allowed = {i for _, row in body_ranges for i in range(row["address"], row["address"] + row["size"], 4)}

    def visit(u, pc, _size, _data):
        if pc not in boundaries:
            assert pc in allowed, hex(pc)
            return
        name = boundaries[pc]
        first, second, third, _ = (u.reg_read(reg) for reg in ARG_REGS)
        if name == "numeric_value":
            assert first == PARAM
            ret, = struct.unpack("<I", struct.pack("<f", values[0]))
        elif name == "float_truncate":
            value, = struct.unpack("<f", struct.pack("<I", first))
            ret = int(value) & 0xFFFFFFFF
        elif name == "color_parameter":
            assert first == THIS
            ret = PARAM if values else 0
        elif name == "color_value":
            assert first == PARAM and values
            ret = values[0]
        elif name == "set_parameter":
            assert (second, third) == (0, 0)
            observed.append((first - CONTROL) // 32)
            ret = 0
        else:
            assert second == 1
            observed.append((first - PARAM) // 32)
            ret = 0
        u.reg_write(arm.UC_ARM_REG_R0, ret)
        u.reg_write(arm.UC_ARM_REG_PC, u.reg_read(arm.UC_ARM_REG_LR))

    def memory(_u, _kind, addr, size, value, _data):
        if not (STACK & ~4095) <= addr < STACK:
            writes.append([addr, size, value])

    m.hook_add(uc.UC_HOOK_CODE, visit)
    m.hook_add(uc.UC_HOOK_MEM_WRITE, memory)
    for reg, value in ((arm.UC_ARM_REG_R0, THIS), (arm.UC_ARM_REG_SP, STACK), (arm.UC_ARM_REG_LR, STOP)):
        m.reg_write(reg, value)
    m.emu_start(target["address"], STOP, count=250)
    assert m.reg_read(arm.UC_ARM_REG_PC) == STOP and not writes
    result = m.reg_read(arm.UC_ARM_REG_R0)
    if TASK == "13" and result >= 0x80000000:
        result -= 0x100000000
    return {
        "inputs": values,
        "output": result if TASK in ("13", "14", "16") else observed,
        "application_nonstack_writes": writes,
        "modeled_provider_boundaries": list(boundaries.values()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", required=True, type=Path)
    parser.add_argument("--server", required=True, type=Path)
    parser.add_argument("--packet", required=True, type=Path)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--write", type=Path)
    actions.add_argument("--check", type=Path)
    args = parser.parse_args()
    targets = json.loads((args.packet / "request.json").read_text())["targets"]
    ctx = json.loads((args.packet / "native-context.json").read_text())
    originals = []
    for expected in targets:
        path = getattr(args, expected["role"])
        elf_sha = sha(path.read_bytes())
        assert elf_sha == expected["original_elf_sha256"]
        with path.open("rb") as stream:
            elf = ELFFile(stream)
            assert elf["e_machine"] == "EM_ARM" and elf.little_endian
            code, target = read_symbol(elf, expected["mangled"])
            assert all(target[k] == expected[k] for k in ("address", "size", "section"))
            bound, = (b for b in ctx["bodies"].values() if b["address"] == target["address"])
            assert (bound["bytes_sha256"], bound["file_offset"]) == (target["sha256"], target["file_offset"])
            dependencies = []
            if TASK == "20":
                dependencies.append(read_symbol(elf, "_ZNK8Presonus5Panel7Control12getParameterEv"))
                assert branch_targets(code, target["address"]) == [dependencies[0][1]["address"]]
        originals.append({
            "role": expected["role"], "elf_sha256": elf_sha, "range": target,
            "provider_ranges": [row for _, row in dependencies],
            "cases": [replay(code, target, values, dependencies) for values in CASES[TASK]],
        })
    output = {"task": TASK, "unicorn": uc.__version__, "originals": originals}
    if args.write:
        args.write.write_text(json.dumps(output, indent=2) + "\n")
    else:
        assert output == json.loads(args.check.read_text())
    print(sum(len(row["cases"]) for row in originals), "exact ARM observations")


if __name__ == "__main__":
    main()
