"""Run the original PanelComponent membership predicate and its app callees."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

import unicorn as uc
from elftools.elf.elffile import ELFFile
from unicorn import arm_const as arm

ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
RANGES = {
    "predicate": ("_ZNK8Presonus5Panel14PanelComponent9isInGroupEiRKN4Core8Portable9ParameterE", 0x527EC, 100),
    "findGroup": ("_ZNK8Presonus5Panel16ControlRegistrar9findGroupEi", 0x8E4AC, 196),
    "at": ("_ZNK8Presonus5Panel12ControlGroup2atEi", 0x8D9A8, 68),
    "count": ("_ZNK8Presonus5Panel12ControlGroup5countEv", 0x8DB08, 20),
    "getParameter": ("_ZNK8Presonus5Panel7Control12getParameterEv", 0x8F580, 20),
}
# Provider stubs are restricted to the single-threaded sentinel runtime edges.
RUNTIME = {0xB030: "guard_acquire", 0xAA3C: "guard_release", 0xADB4: "atexit"}
CASES = (
    ([], 0, 0, "cold"),
    ([], 7, 0, "warm"),
    ([(0, [])], 0, 0, "warm"),
    ([(7, [0, 1, 2])], 7, 0, "warm"),
    ([(7, [0, 1, 2])], 7, 1, "warm"),
    ([(7, [0, None, 2])], 7, 2, "warm"),
    ([(7, [0, None, 2])], 7, 1, "warm"),
    ([(7, [0]), (7, [1])], 7, 1, "warm"),
    ([(7, [1]), (7, [0])], 7, 1, "warm"),
    ([(7, [0]), (-8, [1]), (0, [2])], -8, 1, "warm"),
    ([(3, [0]), (4, [1]), (5, [2])], 5, 2, "warm"),
    ([(7, [0]), (8, [1])], 9, 0, "cold"),
)
PANEL, REGISTRAR, ARRAY = 0xC00000, 0xC01000, 0xC02000
GROUP, CONTROL, PARAMETER = 0xC03000, 0xC04000, 0xC05000
STACK, STOP = 0xE00000, 0xF00000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_ranges(path):
    assert sha(path.read_bytes()) == ELF_SHA
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        assert elf["e_machine"] == "EM_ARM" and elf.little_endian
        section, symbols = elf.get_section(12), elf.get_section_by_name(".symtab")
        assert section.name == ".text"
        result = {}
        for label, (mangled, address, size) in RANGES.items():
            symbol, = symbols.get_symbol_by_name(mangled)
            assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (
                address, size, 12,
            )
            offset = address - section["sh_addr"]
            assert 0 <= offset and offset + size <= section["sh_size"]
            data = section.data()[offset:offset + size]
            result[label] = (data, {
                "address": address, "size": size, "mangled": mangled,
                "section": 12, "section_name": section.name,
                "file_offset": section["sh_offset"] + offset, "sha256": sha(data),
            })
    assert result["predicate"][1]["sha256"] == (
        "74a087da61fd18bb5b8815f59f42845f6766e214aba5b73ba5fc66c3d327365b"
    )
    return result


def observe(ranges, roster, query, parameter, state):
    u = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_ARM)
    u.mem_map(0x1000, 0x1000000)
    entries, valid_pc = {}, set()
    for label, (data, info) in ranges.items():
        address = info["address"]
        u.mem_write(address, data)
        size = info["size"] - (20 if label == "findGroup" else 4 if label == "at" else 0)
        valid_pc.update(range(address, address + size, 4))
        entries[address] = label
    guard, empty, vtable, dtor, dso = struct.unpack("<5I", ranges["findGroup"][0][-20:])

    def store(address, value):
        u.mem_write(address, struct.pack("<I", value & 0xFFFFFFFF))

    def word(address):
        return struct.unpack("<I", u.mem_read(address, 4))[0]

    def parameter_ptr(index):
        return 0 if index is None else PARAMETER + 32 * index

    store(PANEL + 0x90, REGISTRAR)
    store(REGISTRAR + 0x18, ARRAY)
    store(REGISTRAR + 0x1C, len(roster))
    store(guard, int(state == "warm"))
    if state == "warm":
        for offset, value in enumerate((vtable, 0, empty + 16, 0)):
            store(empty + 4 * offset, value)
    else:
        u.mem_write(empty, b"\xA5" * 16)

    for i, (group_id, params) in enumerate(roster):
        group = GROUP + 0x100 * i
        store(ARRAY + 4 * i, group)
        store(group + 4, group_id)
        store(group + 8, group + 16)
        store(group + 12, len(params))
        for j, param in enumerate(params):
            control = CONTROL + 0x100 * i + 16 * j
            store(group + 16 + 4 * j, control)
            store(control + 8, parameter_ptr(param))
    before = bytes(u.mem_read(PANEL, 0x6000))
    calls, runtime_calls, nonstack_writes = [], [], []

    def on_code(machine, pc, _size, _opaque):
        r0, r1, r2 = (machine.reg_read(reg) for reg in (
            arm.UC_ARM_REG_R0, arm.UC_ARM_REG_R1, arm.UC_ARM_REG_R2,
        ))
        if pc in RUNTIME:
            name = RUNTIME[pc]
            runtime_calls.append(name)
            if name == "guard_acquire":
                assert r0 == guard and word(guard) == 0
                machine.reg_write(arm.UC_ARM_REG_R0, 1)
            elif name == "guard_release":
                assert r0 == guard and word(empty + 12) == 0
                store(guard, 1)
            elif name == "atexit":
                assert (r0, r1, r2) == (empty, dtor, dso)
                machine.reg_write(arm.UC_ARM_REG_R0, 0)
            machine.reg_write(arm.UC_ARM_REG_PC, machine.reg_read(arm.UC_ARM_REG_LR))
            return
        assert pc in valid_pc, hex(pc)
        if pc in entries:
            name = entries[pc]
            call = {"method": name, "receiver": r0}
            if name == "at":
                call["index"] = r1
            if name == "count":
                call["observed_count_word"] = word(r0 + 12)
            calls.append(call)

    def on_write(_machine, _kind, address, _size, _value, _opaque):
        if not STACK - 0x1000 <= address < STACK:
            assert empty <= address < empty + 16
            nonstack_writes.append(address - empty)

    u.hook_add(uc.UC_HOOK_CODE, on_code)
    u.hook_add(uc.UC_HOOK_MEM_WRITE, on_write)
    for reg, value in (
        (arm.UC_ARM_REG_R0, PANEL), (arm.UC_ARM_REG_R1, query & 0xFFFFFFFF),
        (arm.UC_ARM_REG_R2, parameter_ptr(parameter)), (arm.UC_ARM_REG_SP, STACK),
        (arm.UC_ARM_REG_LR, STOP),
    ):
        u.reg_write(reg, value)
    u.emu_start(RANGES["predicate"][1], STOP, count=1000)
    assert u.reg_read(arm.UC_ARM_REG_PC) == STOP
    assert u.reg_read(arm.UC_ARM_REG_SP) == STACK
    assert bytes(u.mem_read(PANEL, 0x6000)) == before
    observed = u.reg_read(arm.UC_ARM_REG_R0)
    assert observed in (0, 1)
    miss = not any(group_id == query for group_id, _ in roster)
    if miss:
        assert calls[2] == {"method": "count", "receiver": empty, "observed_count_word": 0}
        assert len(calls) == 3 and observed == 0
        assert runtime_calls == (["guard_acquire", "guard_release", "atexit"] if state == "cold" else [])
    else:
        assert not runtime_calls and not nonstack_writes
    return {
        "groups": roster, "query": query, "parameter": parameter, "sentinel_state": state,
        "member": bool(observed), "app_calls": calls, "runtime_stubs": runtime_calls,
        "native_sentinel_writes": nonstack_writes, "input_state_unchanged": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", required=True, type=Path)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--write", type=Path)
    target.add_argument("--check", type=Path)
    args = parser.parse_args()
    ranges = checked_ranges(args.elf)
    result = {
        "elf_sha256": ELF_SHA, "unicorn": uc.__version__,
        "ranges": {name: info for name, (_, info) in ranges.items()},
        "cases": [observe(ranges, *case) for case in CASES],
    }
    encoded = json.dumps(result, indent=2) + "\n"
    if args.write:
        args.write.write_text(encoded)
    else:
        assert json.loads(args.check.read_text()) == json.loads(encoded)
    print(f"Original predicate and app callees matched {len(CASES)} roster cases")


if __name__ == "__main__":
    main()
