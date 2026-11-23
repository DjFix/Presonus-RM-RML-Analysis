"""Execute each Storm entry and its two real ARM base bodies offline."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
STORM = "_ZN8Presonus5Panel24StormFrontPanelComponent"
FAT24 = "_ZN8Presonus5Panel24Fat24FrontPanelComponentD2Ev"
FRONT = "_ZN8Presonus5Panel19FrontPanelComponentD2Ev"
TARGETS = {
    "D0": (0x72A08, 116, "33a494a6d2bd55df99950cf09c991359e180f0693ad0ac91f30d3f71ea7c971a"),
    "D1": (0x72A7C, 108, "2c2ec6687093c2836a709a45be41a0b7f30382b77970067116423bba27fc18e1"),
    "D2": (0x72AE8, 108, "d2e780051e35d85dbef2522d9221d4a0e8301eea84f73c9d8001dda537bf4876"),
}
BASES = {
    FAT24: (0x70A30, 92, "726f34b6f64f75b43baacf80dfe92b9e865373db37b5995b5ea74566b6d287b0"),
    FRONT: (0x68FC8, 192, None),
}
BOUNDARIES = {
    0x8C630: "delay_timer",
    0x1228B0: "attributes",
    0x6A054: "vector",
    0x5292C: "panel_base",
    0xAC10: "unsized_delete",
}
PAGE = 0x1000
STACK, STOP = 0x4000000, 0x5000000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def observe(elf_path, variant):
    elf_bytes = elf_path.read_bytes()
    if digest(elf_bytes) != ELF_SHA:
        raise ValueError("ELF SHA-256 differs")
    target = STORM + variant + "Ev"
    with elf_path.open("rb") as stream:
        elf = ELFFile(stream)
        symbols = elf.get_section_by_name(".symtab")
        text = elf.get_section(12)
        ranges = {}
        for name, (address, size, expected) in {target: TARGETS[variant], **BASES}.items():
            rows = symbols.get_symbol_by_name(name)
            if not rows or any((s["st_value"], s["st_size"], s["st_shndx"]) !=
                               (address, size, 12) for s in rows):
                raise ValueError(f"Unexpected ELF range for {name}")
            offset = text["sh_offset"] + address - text["sh_addr"]
            contents = elf_bytes[offset:offset + size]
            sha = digest(contents)
            if len(contents) != size or (expected is not None and sha != expected):
                raise ValueError(f"Unexpected function bytes for {name}")
            ranges[name] = dict(address=address, size=size, file_offset=offset,
                                section=text.name, section_index=12, sha256=sha)
        if not any(s["st_value"] == 0xAC10 and s.name.startswith("_ZdlPv@")
                   for s in symbols.iter_symbols()):
            raise ValueError("Unsized operator delete PLT identity differs")
        loads = [(s["p_vaddr"], s["p_memsz"], s.data())
                 for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]

    result = []
    for receiver, seed in [(0x3000000, 0), (0x3010000, 0xA5), (0x3020000, 0x5A)]:
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        start = min(a for a, _, _ in loads) & -PAGE
        end = (max(a + n for a, n, _ in loads) + PAGE - 1) & -PAGE
        uc.mem_map(start, end - start)
        for address, _, contents in loads:
            uc.mem_write(address, contents)
        uc.mem_map(receiver, PAGE)
        uc.mem_write(receiver, bytes([seed]) * PAGE)
        uc.mem_map(STACK, PAGE)
        uc.mem_map(STOP, PAGE)
        uc.reg_write(UC_ARM_REG_SP, STACK + PAGE - 16)
        uc.reg_write(UC_ARM_REG_LR, STOP)
        uc.reg_write(UC_ARM_REG_R0, receiver)
        trace, writes, instructions = [], [], []
        returned = False

        def code(vm, address, _size, _data):
            nonlocal returned
            argument = vm.reg_read(UC_ARM_REG_R0) - receiver
            if address == STOP:
                returned = True
                vm.emu_stop()
                return
            if address in (BASES[FAT24][0], BASES[FRONT][0]):
                trace.append([FAT24 if address == BASES[FAT24][0] else FRONT,
                              address, argument])
            if address in BOUNDARIES:
                name = BOUNDARIES[address]
                trace.append([name, address, argument])
                if name == "unsized_delete":
                    if argument != 0:
                        raise ValueError("Wrong ARM receiver passed to _ZdlPv")
                    # Model deallocation at the external allocator boundary.
                    vm.mem_unmap(receiver, PAGE)
                vm.reg_write(UC_ARM_REG_PC, vm.reg_read(UC_ARM_REG_LR))
                return
            if not any(r["address"] <= address < r["address"] + r["size"]
                       for r in ranges.values()):
                raise ValueError(f"Unexpected ARM instruction at {address:#x}")
            instructions.append(address)

        def write(vm, _access, address, size, value, _data):
            if receiver <= address < receiver + PAGE:
                writes.append([vm.reg_read(UC_ARM_REG_PC), address - receiver, size, value])

        uc.hook_add(UC_HOOK_CODE, code)
        uc.hook_add(UC_HOOK_MEM_WRITE, write)
        uc.emu_start(ranges[target]["address"], STOP + 4, count=512)
        if not returned or uc.reg_read(UC_ARM_REG_R0) != receiver:
            raise ValueError("Expected normal ARM return with original receiver")
        try:
            uc.mem_read(receiver, 4)
            released = False
        except UcError:
            released = True
        offsets = [entry[2] for entry in trace]
        if offsets != [0, 0, 0x198, 0x144, 0x130, 0x11C, 0] + ([0] if variant == "D0" else []):
            raise ValueError(f"Unexpected base/subobject argument offsets: {offsets!r}")
        stages = [[w[1] for w in writes if r["address"] <= w[0] < r["address"] + r["size"]]
                  for r in ranges.values()]
        if sorted(stages[0]) != [0, 4, 0x84, 0xF0, 0xF4, 0xF8, 0xFC, 0x1BC, 0x1C0]:
            raise ValueError("Unexpected Storm receiver writes")
        if any(sorted(stage) != [0, 4, 0x84, 0xF0, 0xF4, 0xF8, 0xFC]
               for stage in stages[1:]):
            raise ValueError("Unexpected Fat24 or FrontPanel receiver writes")
        if released != (variant == "D0"):
            raise ValueError("Unexpected native delete boundary")
        result.append(dict(receiver=receiver, seed=seed, calls=trace, writes=writes,
                           instruction_count=len(instructions), receiver_released=released))
    return dict(elf_sha256=ELF_SHA, mangled=target, variant=variant, ranges=ranges,
                cases=result, boundary_model="Four named FrontPanel callees return at entry. "
                "The external unsized allocator boundary releases the mapped receiver page. "
                "The original allocator implementation and exception paths are excluded.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--variant", choices=TARGETS, required=True)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    result = observe(args.elf, args.variant)
    if args.check:
        if json.loads(args.check.read_text()) != result:
            raise SystemExit("Fresh native observations differ from sealed fixture")
        print(f"{args.variant}: {len(result['cases'])} original ARM executions matched")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
