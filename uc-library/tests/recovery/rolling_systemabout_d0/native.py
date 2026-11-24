"""Run the actual derived, Page D2, and child D0 ranges in offline ARM."""
import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc, UcError, __version__
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

ELF_HASH = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
VARIANT = 0
DERIVED = {
    1: (0x6f300, 52, "ad25ff5adb5086dd6d940357cfeee44e2888039dddbb3c03ce2a10f627ee11fd"),
    0: (0x6f2c4, 60, "f23fddc180adf072a4798f6728d1709de23eef7940083a1638bcf430b563f64c"),
}
PAGE = (0x975bc, 96, "965c1c6e8ee005eb656d6737bf484d10a81cc73056e0010b93273b40a7f8e9f3")
ELEMENT = (0x98428, 44, "cea01779360c14d39a7014eb9f954c535a1f4b6447332cc4f57ce77f163869d3")
ROOT, STACK, STOP = 0x40000000, 0x60000000, 0x70000000
DERIVED_VPTR = 0x329e90
PAGE_VPTR = 3512392
ELEMENT_VPTR = 0x3599f0


def sha(data):
    return hashlib.sha256(data).hexdigest()


def replay(ranges, slots, delete, seed, layout):
    emu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    pages = set()

    def map_bytes(address, content):
        for page in range(address & ~0xfff, ((address + len(content) - 1) & ~0xfff) + 1, 0x1000):
            if page not in pages:
                emu.mem_map(page, 0x1000)
                pages.add(page)
        emu.mem_write(address, content)

    def word(address):
        return struct.unpack("<I", emu.mem_read(address, 4))[0]

    for row in ranges:
        map_bytes(row["address"], bytes.fromhex(row["original_bytes"]))
    for address, data in slots.items():
        map_bytes(address, data)
    # The loader/runtime allocator boundary is modeled. Only an original branch
    # reaching this exact import with a live allocation can unmap a receiver.
    map_bytes(delete, bytes.fromhex("1eff2fe1"))
    map_bytes(STACK, b"\0" * 4096)
    map_bytes(STOP, b"\0")
    map_bytes(ROOT, struct.pack("<I", 0xdeadbeef))
    map_bytes(ROOT + 0x118, struct.pack("<I", 0xdecafbad))
    children, live = [], {ROOT: 99}
    for index, present in enumerate(layout):
        address = ROOT + 0x1000 * (index + 1) if present else 0
        if present:
            map_bytes(address, struct.pack("<I", ELEMENT_VPTR))
            live[address] = index
        children.append(address)
    storage = ROOT + 0x200
    map_bytes(ROOT + 0x48, struct.pack("<II", storage, len(children)))
    if children:
        map_bytes(storage, struct.pack(f"<{len(children)}I", *children))
    calls, writes, deallocations = [], [], []
    target = ranges[0]["address"]

    def entered(uc, pc, _size, _data):
        receiver = uc.reg_read(UC_ARM_REG_R0)
        if pc == target:
            assert receiver == ROOT
            calls.append([pc, live[receiver]])
        elif pc == PAGE[0]:
            assert receiver == ROOT
            assert (word(ROOT), word(ROOT + 0x118)) == (DERIVED_VPTR, DERIVED_VPTR + 0x44)
            calls.append([pc, live[receiver]])
        elif pc == ELEMENT[0]:
            assert word(ROOT) == PAGE_VPTR and receiver != ROOT
            calls.append([pc, live[receiver]])
        elif pc == delete:
            label = live.pop(receiver)
            assert word(receiver) == (PAGE_VPTR if receiver == ROOT else ELEMENT_VPTR)
            deallocations.append(label)
            uc.mem_unmap(receiver, 0x1000)
            try:
                uc.mem_read(receiver, 1)
            except UcError:
                pass
            else:
                raise AssertionError("Allocator boundary did not release the mapped object")

    def writes_memory(_uc, _access, address, size, value, _data):
        if ROOT <= address < ROOT + 0x1000:
            writes.append([address - ROOT, size, value])

    emu.hook_add(UC_HOOK_CODE, entered)
    emu.hook_add(UC_HOOK_MEM_WRITE, writes_memory)
    emu.reg_write(UC_ARM_REG_SP, STACK + 0xff0)
    emu.reg_write(UC_ARM_REG_LR, STOP)
    emu.reg_write(UC_ARM_REG_R0, ROOT)
    emu.emu_start(target, STOP, count=1000)
    assert emu.reg_read(UC_ARM_REG_PC) == STOP
    assert emu.reg_read(UC_ARM_REG_R0) == ROOT
    assert emu.reg_read(UC_ARM_REG_SP) == STACK + 0xff0
    indices = [index for index, present in enumerate(layout) if present]
    assert calls == [[target, 99], [PAGE[0], 99], *([ELEMENT[0], i] for i in indices)]
    assert writes[:3] == [[0x118, 4, DERIVED_VPTR + 0x44], [0, 4, DERIVED_VPTR], [0, 4, PAGE_VPTR]]
    assert deallocations == indices + ([99] if VARIANT == 0 else [])
    assert live == ({ROOT: 99} if VARIANT == 1 else {})
    return {"seed": seed, "layout": layout, "entry_trace": calls, "root_writes": writes,
            "deallocation_order": deallocations, "contract": deallocations}


def fixtures(path):
    data = path.read_bytes()
    assert sha(data) == ELF_HASH
    elf = ELFFile(io.BytesIO(data))
    assert elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM"
    symtab = elf.get_section_by_name(".symtab")

    def range_row(name, variant, spec):
        address, size, digest = spec
        mangled = f"_ZN8Presonus5Panel{len(name)}{name}D{variant}Ev"
        symbol, = symtab.get_symbol_by_name(mangled)
        assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (address, size, 12)
        section = elf.get_section(12)
        offset = section["sh_offset"] + address - section["sh_addr"]
        assert section.name == ".text" and 0 <= address - section["sh_addr"] <= section["sh_size"] - size
        code = data[offset:offset + size]
        assert sha(code) == digest
        return {"mangled": mangled, "address": address, "size": size, "section": 12, "file_offset": offset,
                "range_sha256": digest, "original_bytes": code.hex()}

    def table(name, address):
        symbol, = symtab.get_symbol_by_name(f"_ZTVN8Presonus5Panel{len(name)}{name}E")
        section = elf.get_section(symbol["st_shndx"])
        assert symbol["st_value"] + 8 == address
        offset = section["sh_offset"] + address - section["sh_addr"]
        return data[offset:offset + 8]

    derived = range_row("SystemAboutPage", VARIANT, DERIVED[VARIANT])
    page = range_row("Page", 2, PAGE)
    element = range_row("Element", 0, ELEMENT)
    slots = {DERIVED_VPTR: table("SystemAboutPage", DERIVED_VPTR),
             PAGE_VPTR: table("Page", PAGE_VPTR), ELEMENT_VPTR: table("Element", ELEMENT_VPTR)}
    assert struct.unpack("<II", slots[DERIVED_VPTR]) == (DERIVED[1][0], DERIVED[0][0])
    assert struct.unpack("<II", slots[ELEMENT_VPTR])[1] == ELEMENT[0]
    runtime, = elf.get_section_by_name(".dynsym").get_symbol_by_name("_ZdlPv")
    assert runtime["st_shndx"] == "SHN_UNDEF" and runtime["st_value"] == 0xac10
    delete = runtime["st_value"]
    layouts = [[], [False], [True], [False, True, False, True], [True, True, False, True]]
    return [derived | {"elf_sha256": ELF_HASH, "firmware": "RM/RML mixer 13731", "role": "server",
                       "variant": VARIANT, "native_dependencies": [page, element],
                       "import": {"mangled": "_ZdlPv", "address": delete},
                       "unicorn_version": __version__,
                       "cases": [replay([derived, page, element], slots, delete, index, layout)
                                 for index, layout in enumerate(layouts)]}]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--out", type=Path)
    output.add_argument("--verify", type=Path)
    args = parser.parse_args()
    result = fixtures(args.elf)
    if args.out:
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    else:
        assert json.loads(args.verify.read_text()) == result
    print(f"Verified D{VARIANT} original across {len(result[0]['cases'])} native teardown cases")
