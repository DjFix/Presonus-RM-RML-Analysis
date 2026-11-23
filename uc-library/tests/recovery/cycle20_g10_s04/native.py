"""Execute the original ARM hooks and dispatch on isolated synthetic receivers."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

import unicorn as uc
from elftools.elf.elffile import ELFFile
from unicorn import arm_const as arm

ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
BODY_SHA = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
TABLE_SHA = "e620c890984a198c2542229f60ffa3fc04ee0a67b3acd2a790bbecb35d85b4b8"
VIRTUAL_TABLE = "_ZTVN8Presonus5Panel14PanelComponentE"
RECEIVER, STACK, STUB, STOP = 0x40000000, 0x50000000, 0x71000000, 0x71000040
STACK_TOP = STACK + 0x800
HOOKS = {
    "doActivate": ("10doActivateEv", 338940, 56),
    "cleanup": ("7cleanupEv", 337104, 48),
}
RELATED = {
    "start": (
        "5startEv", 337148, 20,
        "916cbf8ab21f18283895d4913ef51613ecab7695dcd43245171ec2ab6c675bda",
    ),
    "activateAll": (
        "11activateAllEv", 337120, 28,
        "2620db362d0ff0f5f2e0561bc25ca9ebfc78c4593bea0467637e70fbd9a0200c",
    ),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_range(elf, name, address, size, sha, expected_section=None):
    rows = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    assert rows
    row = rows[0]
    assert (row["st_value"], row["st_size"]) == (address, size)
    index = row["st_shndx"]
    section = elf.get_section(index)
    assert expected_section is None or index == expected_section
    section_offset = address - section["sh_addr"]
    assert 0 <= section_offset and section_offset + size <= section["sh_size"]
    body = section.data()[section_offset:section_offset + size]
    assert len(body) == size and digest(body) == sha
    mapping = {
        "mangled": name, "address": address, "size": size,
        "section": index, "section_name": section.name,
        "file_offset": section["sh_offset"] + section_offset,
        "sha256": sha,
    }
    return body, mapping


def observe(ranges, entry, slot, table_address, seed, allowed_code):
    machine = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_ARM)
    pages = {RECEIVER, STACK, STUB}
    for _, mapping in ranges:
        address = mapping["address"]
        end = address + mapping["size"]
        pages.update(range(address & ~4095, (end + 4095) & ~4095, 4096))
    for page in sorted(pages):
        machine.mem_map(page, 4096)
    for body, mapping in ranges:
        machine.mem_write(mapping["address"], body)

    # Synthetic indirect caller: ldr r1,[r0]; ldr pc,[r1,#slot].
    machine.mem_write(STUB, struct.pack("<II", 0xe5901000, 0xe591f000 | slot))
    initial = struct.pack("<I", table_address) + bytes(
        (seed + offset * 37) % 256 for offset in range(252)
    )
    machine.mem_write(RECEIVER, initial)
    machine.reg_write(arm.UC_ARM_REG_R0, RECEIVER)
    machine.reg_write(arm.UC_ARM_REG_SP, STACK_TOP)
    machine.reg_write(arm.UC_ARM_REG_LR, STOP)
    trace, outside_reads, outside_writes = [], [], []

    def visit(_machine, pc, _size, _opaque):
        assert pc in allowed_code, f"unexpected instruction at {pc:#x}"
        trace.append(pc)

    def observe_memory(_machine, kind, address, size, value, _opaque):
        if not STACK <= address < STACK + 4096:
            if kind == uc.UC_MEM_READ:
                outside_reads.append([address, size])
            else:
                outside_writes.append([address, size, value])

    machine.hook_add(uc.UC_HOOK_CODE, visit)
    machine.hook_add(uc.UC_HOOK_MEM_READ | uc.UC_HOOK_MEM_WRITE, observe_memory)
    machine.emu_start(entry, STOP, count=64)
    assert machine.reg_read(arm.UC_ARM_REG_PC) == STOP
    assert machine.reg_read(arm.UC_ARM_REG_SP) == STACK_TOP
    return {
        "seed": seed, "trace": trace, "external_calls": 0,
        "outside_stack_reads": outside_reads, "outside_stack_writes": outside_writes,
        "receiver_unchanged": machine.mem_read(RECEIVER, len(initial)) == initial,
        "return_register_unchanged": machine.reg_read(arm.UC_ARM_REG_R0) == RECEIVER,
    }


def generate(path, hook):
    assert digest(path.read_bytes()) == ELF_SHA
    suffix, address, slot = HOOKS[hook]
    prefix = "_ZN8Presonus5Panel14PanelComponent"
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        assert elf["e_machine"] == "EM_ARM" and elf.little_endian
        body, mapping = checked_range(elf, prefix + suffix, address, 16, BODY_SHA, 12)
        table, table_mapping = checked_range(elf, VIRTUAL_TABLE, 3250376, 116, TABLE_SHA)
        table_address = table_mapping["address"] + 8
        assert struct.unpack_from("<I", table, slot + 8)[0] == address
        related = {}
        if hook == "doActivate":
            for name, (suffix, pc, size, sha) in RELATED.items():
                related[name] = checked_range(elf, prefix + suffix, pc, size, sha, 12)

    cases = []
    for route, entry in {
        "direct": address, "vtable": STUB,
        **{name: info["address"] for name, (_, info) in related.items()},
    }.items():
        used = [mapping]
        if route == "start":
            used.append(related["start"][1])
        if route in related:
            used.append(related["activateAll"][1])
        allowed = {pc for info in used
                   for pc in range(info["address"], info["address"] + info["size"], 4)}
        if route == "vtable":
            allowed.update([STUB, STUB + 4])
        for seed in (0, 79, 246):
            result = observe(
                [(body, mapping), (table, table_mapping), *related.values()],
                entry, slot, table_address, seed, allowed,
            )
            assert result["receiver_unchanged"] and result["return_register_unchanged"]
            assert not result["outside_stack_writes"]
            assert result["outside_stack_reads"] == (
                [] if route == "direct" else [[RECEIVER, 4], [table_address + slot, 4]]
            )
            hook_trace = [pc for pc in result["trace"] if address <= pc < address + 16]
            assert hook_trace == list(range(address, address + 16, 4))
            cases.append({"route": route, **result})
    return {
        "elf": {"path": "rootfs/RML16AI_Rack_13731/home/root/mixer", "sha256": ELF_SHA},
        "unicorn": uc.__version__,
        "target": mapping, "vtable": table_mapping, "related": [info for _, info in related.values()],
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--hook", choices=HOOKS, required=True)
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--write", type=Path)
    options.add_argument("--check", type=Path)
    args = parser.parse_args()
    result = generate(args.elf, args.hook)
    if args.write:
        args.write.write_text(json.dumps(result, indent=2) + "\n")
    else:
        assert json.loads(args.check.read_text()) == result
    print(f"original ARM replay: {len(result['cases'])} {args.hook} routes/seeds matched")


if __name__ == "__main__":
    main()
