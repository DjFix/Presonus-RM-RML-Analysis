"""Replay the two ARM sort bodies and constructor forwarding, offline."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn import __version__ as unicorn_version
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

GROUP = "_ZN8Presonus5Panel16GPIOControlGroup"
TARGET = GROUP + "4sortEv"
TABLE = "_ZTVN8Presonus5Panel16GPIOControlGroupE"
BASE = "_ZN8Presonus5Panel12ControlGroupC2Eii"
RECEIVER, STACK, STOP = 0x70000000, 0x71000000, 0x72000000
CASES = ((-9, 271, (31, 7, 19)), (42, -17, (31,)), (0, 99, ()))
ORIGINALS = {
    "server": ("9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07",
               "RM/RML mixer 13731", 712404, 679636),
    "client": ("304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0",
               "CS18AI surface 13840", 812476, 779708),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def original(role, path):
    expected_hash, firmware, address, offset = ORIGINALS[role]
    elf_hash = sha(path.read_bytes())
    if elf_hash != expected_hash:
        raise ValueError(f"Unexpected {role} ELF SHA-256: {elf_hash}")
    vm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    pages = set()

    def map_range(start, size):
        for page in range(start & ~0xFFF, start + size, 0x1000):
            if page not in pages:
                vm.mem_map(page, 0x1000)
                pages.add(page)

    with path.open("rb") as handle:
        elf = ELFFile(handle)
        symbols = elf.get_section_by_name(".symtab")

        def bind(name):
            symbol, = symbols.get_symbol_by_name(name)
            start, size, index = (symbol[key] for key in ("st_value", "st_size", "st_shndx"))
            section = elf.get_section(index)
            displacement = start - section["sh_addr"]
            if not 0 <= displacement <= section["sh_size"] - size or not size:
                raise ValueError(f"Invalid section range for {name}")
            body = section.data()[displacement:displacement + size]
            map_range(start, size)
            vm.mem_write(start, body)
            return dict(mangled=name, address=start, size=size, section=index,
                        section_name=section.name, file_offset=section["sh_offset"] + displacement,
                        range_sha256=sha(body))

        target, table, base = (bind(name) for name in (TARGET, TABLE, BASE))
        constructors = [bind(GROUP + f"C{variant}Eii") for variant in (1, 2)]

    if (target["address"], target["size"], target["section"], target["file_offset"]) != (address, 16, 12, offset):
        raise ValueError(f"Target range mismatch: {target}")
    for addr in (RECEIVER, STACK, STOP):
        map_range(addr, 0x1000)
    reads, writes, calls, instructions = [], [], [], []

    def on_code(machine, addr, size, _):
        instructions.append(addr)
        if addr == base["address"]:
            calls.append([machine.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)])
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    def on_read(_, access, addr, size, value, __):
        reads.append([addr, size])

    def on_write(_, access, addr, size, value, __):
        writes.append([addr, size, value])

    vm.hook_add(UC_HOOK_CODE, on_code)
    vm.hook_add(UC_HOOK_MEM_READ, on_read)
    vm.hook_add(UC_HOOK_MEM_WRITE, on_write)

    def invoke(addr, group, auxiliary):
        for buffer in (reads, writes, calls, instructions):
            buffer.clear()
        for reg, value in ((UC_ARM_REG_R0, RECEIVER), (UC_ARM_REG_R1, group),
                           (UC_ARM_REG_R2, auxiliary), (UC_ARM_REG_SP, STACK + 0x800),
                           (UC_ARM_REG_LR, STOP)):
            vm.reg_write(reg, value & 0xFFFFFFFF)
        vm.emu_start(addr, STOP, count=40)
        if vm.reg_read(UC_ARM_REG_PC) != STOP or vm.reg_read(UC_ARM_REG_SP) != STACK + 0x800:
            raise ValueError("ARM target did not return through its caller frame")

    def word(addr):
        return struct.unpack("<I", vm.mem_read(addr, 4))[0]

    cases = []
    for ctor in constructors:
        for group, auxiliary, tags in CASES:
            vm.mem_write(RECEIVER, bytes(64))
            invoke(ctor["address"], group, auxiliary)
            expected = [RECEIVER, group & 0xFFFFFFFF, auxiliary & 0xFFFFFFFF]
            vptr = word(RECEIVER)
            if calls != [expected] or vptr != table["address"] + 8 or word(vptr + 12) != address:
                raise ValueError("Constructor forwarding or native slot differed")
            ctor_trace = dict(base_call=calls[0], instructions=instructions[:], installed_vptr=vptr)

            # Opaque synthetic receiver words let us detect access and mutation
            # without assigning the native ControlGroup any field layout.
            vm.mem_write(RECEIVER + 4, struct.pack("<6i", group, 1, len(tags), *tags,
                                                   *([0] * (3 - len(tags)))))
            before = bytes(vm.mem_read(RECEIVER, 64))
            invoke(word(vptr + 12), group, auxiliary)
            after = bytes(vm.mem_read(RECEIVER, 64))
            touched = reads + [item[:2] for item in writes]
            if calls or before != after or any(not STACK <= addr <= STACK + 4096 - size for addr, size in touched):
                raise ValueError("Sort touched non-frame state")
            result_id, owns, count, *result_tags = struct.unpack_from("<6i", after, 4)
            cases.append(dict(constructor=ctor["mangled"], group=group, auxiliary=auxiliary,
                              tag_count=len(tags), expected=[count, result_id, owns, *result_tags[:count]],
                              constructor_trace=ctor_trace, sort_trace=dict(instructions=instructions[:],
                                  reads=reads[:], writes=writes[:], receiver_before_sha256=sha(before),
                                  receiver_after_sha256=sha(after))))
    return dict(target, elf_sha256=elf_hash, firmware=firmware, role=role, constructors=constructors,
                base_boundary=base, vtable=table, address_point_slot_offset=12, cases=cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--client", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--out", type=Path)
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    result = {"unicorn_version": unicorn_version,
              "originals": [original(role, getattr(args, role)) for role in ORIGINALS]}
    if args.verify:
        if json.loads(args.verify.read_text()) != result:
            raise ValueError("Fresh ELF observations differ from fixture")
    else:
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Verified {sum(len(row['cases']) for row in result['originals'])} ARM cases")


if __name__ == "__main__":
    main()
