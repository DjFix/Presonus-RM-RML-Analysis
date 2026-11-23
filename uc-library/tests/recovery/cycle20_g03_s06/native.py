"""Independent ARM execution of bounded ChannelInfo list operations."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

ELF_SHA = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
TARGETS = {
    '06': ('_ZNK8Presonus7Surface24ChannelInfoPageComponent16getMaxListOffsetENS1_8ListTypeE', 630056, 736, '9a6824cddd76aa1c3bfc9dbda54a317689020e68e1424d2adcc5c779444b24e9'),
    '07': ('_ZN8Presonus7Surface24ChannelInfoPageComponent10updateListENS1_8ListTypeE', 630792, 1468, '9c90f6bb57a702e302498f9922f899017248c3107c00501ee74d403f4fdb0d14'),
    '08': ('_ZN8Presonus7Surface24ChannelInfoPageComponent13addListOffsetENS1_8ListTypeEi', 632952, 92, '49604a27028f606f15e73ae51417c4c42cdb8ba659ac9af1b86a5ff911026a8d'),
    '09': ('_ZN8Presonus7Surface24ChannelInfoPageComponent15categoryChangedEv', 632260, 692, '58ba6e0406585e803ef43975db9c5d02a18515796a5ea0b807b00516289b66f0'),
}
MANAGER_GUARD = 0x26A9D0
CATEGORY_GUARD = 0x26A9CC
MANAGER = 0x26A9D8
ROOT = 0x26A9EC
EMPTY = 0x26AAEC
RECEIVER = 0x300000
RECEIVER_VTABLE = 0x300400
PARAMETERS = 0x310000
PARAMETER_VTABLE = 0x311000
CATEGORIES = 0x320000
CATEGORY_ARRAY = 0x328000
ICON_ARRAYS = 0x330000
STOP = 0x3F0000
STACK = 0x410000


def read_ranges(image, elf):
    table = elf.get_section_by_name(".symtab")
    ranges = {}
    for name, address, size, expected in TARGETS.values():
        [symbol] = table.get_symbol_by_name(name)
        section = elf.get_section(symbol["st_shndx"])
        offset = section["sh_offset"] + address - section["sh_addr"]
        digest = hashlib.sha256(image[offset:offset + size]).hexdigest()
        assert (symbol["st_value"], symbol["st_size"], section.name, digest) == (
            address, size, ".text", expected)
        ranges[name] = dict(address=address, size=size, section=section.name,
                            file_offset=offset, sha256=digest)
    return ranges


def execute(elf, target, case):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(0x8000, 0x270000)
    for segment in elf.iter_segments():
        if segment["p_type"] == "PT_LOAD":
            uc.mem_write(segment["p_vaddr"], segment.data())
    uc.mem_map(RECEIVER, 0x80000)
    uc.mem_map(STOP, 4096)
    uc.mem_map(STACK - 8192, 12288)

    def word(address):
        return struct.unpack("<I", uc.mem_read(address, 4))[0]

    def put(address, value):
        uc.mem_write(address, struct.pack("<I", value & 0xffffffff))

    def string(address):
        if not address:
            return ""
        return bytes(uc.mem_read(address, 256)).split(b"\0", 1)[0].decode("ascii")

    def put_string(address, value):
        uc.mem_write(address, value.encode("ascii") + b"\0")

    def ret(value=None):
        if value is not None:
            uc.reg_write(UC_ARM_REG_R0, value & 0xffffffff)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    def category(index):
        return CATEGORIES + index * 0x200

    def register_categories(names, icons):
        put(MANAGER + 4, CATEGORY_ARRAY)
        put(MANAGER + 8, len(names))
        for index, name in enumerate(names):
            entry = category(index)
            items = ICON_ARRAYS + index * 0x1000
            put(CATEGORY_ARRAY + index * 4, entry)
            put_string(entry, name if index == 0 else name.lower())
            put(entry + 0x104, items)
            # The recursively populated All category includes directory names
            # after their entries. Cases accessing All use one directory.
            category_icons = [*icons, *names[1:]] if index == 0 else icons
            put(entry + 0x108, len(category_icons))
            for slot, icon in enumerate(category_icons):
                put_string(items + slot * 256, icon)

    names = case["names"]
    icons = case["icons"]
    warmed = case.get("warm", True)
    put(MANAGER_GUARD, int(warmed))
    put(CATEGORY_GUARD, int(warmed))
    put_string(EMPTY, "")
    put(EMPTY + 0x108, 0)
    if warmed:
        register_categories(names, icons)
    put(RECEIVER, RECEIVER_VTABLE)
    put(RECEIVER_VTABLE + 0x18, STOP + 0x10)
    put(PARAMETER_VTABLE + 0x58, STOP + 0x14)
    put(PARAMETER_VTABLE + 0x74, STOP + 0x18)
    put(PARAMETER_VTABLE + 0x70, STOP + 0x1C)
    for index in range(20):
        put(PARAMETERS + index * 16, PARAMETER_VTABLE)
    put(PARAMETERS + 20 * 16, PARAMETER_VTABLE)
    offsets = (0xD4, 0xD8, 0xDC, 0xE0)
    for field, value in zip(offsets, case["state"]):
        put(RECEIVER + field, value)

    def read_state():
        return [struct.unpack("<i", uc.mem_read(RECEIVER + field, 4))[0] for field in offsets]

    def tag_for(address):
        index = (address - PARAMETERS) // 16
        return 100 + index if index < 10 else 190 + index

    events = []

    def code(_, address, size, unused):
        r0 = uc.reg_read(UC_ARM_REG_R0)
        r1 = uc.reg_read(UC_ARM_REG_R1)
        r2 = uc.reg_read(UC_ARM_REG_R2)
        entry_names = {0x99D28: "max", 0x9A008: "update"}
        if address in entry_names:
            assert r0 == RECEIVER
            events.append([entry_names[address], r1, *read_state()])
        if any(start <= address < start + count for name, start, count, digest in TARGETS.values()):
            return
        if address in (0x24268, 0x24210, 0x12BB14):
            put_string(r0, string(r1))
        elif address == 0xB1C4:
            assert r0 in (MANAGER_GUARD, CATEGORY_GUARD)
            events.append(["guard_acquire", r0])
            ret(not word(r0))
            return
        elif address == 0xAB7C:
            assert r0 in (MANAGER_GUARD, CATEGORY_GUARD)
            events.append(["guard_release", r0])
            put(r0, 1)
        elif address == 0xAF24:
            assert r0 in (MANAGER, EMPTY)
            events.append(["register_cleanup", r0])
        elif address == 0x9B340:
            assert (r0, r1) == (MANAGER, 0)
            events.append(["resize", r1])
        elif address == 0xA6A7C:
            put_string(r0, "/media/skin")
            events.append(["skin_directory", "/media/skin"])
        elif address == 0xAFFC:
            uc.mem_write(r0, bytes(uc.mem_read(r1, r2)))
        elif address == 0x12A964:
            child = string(r1)
            assert r0 == ROOT and child in ("bitmaps", "trackicons")
            put_string(r0, string(r0).rstrip("/") + "/" + child)
            events.append(["descend", child])
        elif address == 0x9C84C:
            assert (r0, string(ROOT)) == (MANAGER, "/media/skin/bitmaps/trackicons")
            events.append(["load_icons", string(ROOT)])
            register_categories(names, icons)
        elif address == 0x9C358:
            assert (r0, string(r1), r2) == (EMPTY, "", 0)
            events.append(["empty_category"])
            put_string(EMPTY, "")
            put(EMPTY + 0x108, 0)
        elif address == 0x11F24C:
            assert r0 == RECEIVER + 0x28
            assert r1 in range(100, 110) or r1 in range(200, 210)
            index = r1 - 100 if r1 < 200 else r1 - 190
            events.append(["tag", r1])
            ret(0 if r1 in case.get("missing_tags", []) else PARAMETERS + index * 16)
            return
        elif address == STOP + 0x10:
            assert r0 == RECEIVER and string(r1) == "ch_icon"
            events.append(["find_parameter", string(r1)])
            ret(PARAMETERS + 20 * 16)
            return
        elif address == STOP + 0x14:
            assert r1 in (0, 0x3f800000) and r2 == 0
            events.append(["value", tag_for(r0), int(bool(r1)), r2])
        elif address == STOP + 0x18:
            assert r2 == 0
            events.append(["label", tag_for(r0), string(r1), r2])
        elif address == STOP + 0x1C:
            assert r0 == PARAMETERS + 20 * 16 and r2 == 256
            icon = case["ch_icon"]
            put_string(r1, icon)
            events.append(["read_icon", icon])
        elif address == 0x97334:
            value = string(r0)
            assert " " not in value  # Fixture labels use a single word.
            put_string(r0, value[:1].upper() + value[1:].lower())
        elif address == 0x12ADBC:
            assert not string(r1) and r2 == 1
            value = string(r0)
            put_string(r0, value.rsplit(".", 1)[0] if "." in value else value)
        elif address == 0x9B55C:
            put_string(r0, string(r0).lower())
        elif address == 0xB02C:
            ret(len(string(r0)))
            return
        elif address == 0xB170:
            uc.mem_write(r0, bytes(uc.mem_read(r1, r2)))
        elif address == 0x1299EC:
            value = string(r0)
            put_string(r0, value.rsplit("/", 1)[0] if "/" in value else value)
        elif address == 0x129A3C:
            put_string(r1, string(r0).rsplit("/", 1)[-1])
        elif address == 0xB0F8:
            left, right = string(r0), string(r1)
            ret((left > right) - (left < right))
            return
        elif address == 0x9BE6C:
            query = string(r1)
            values = ([] if r0 == EMPTY else [*icons, *names[1:]]
                      if r0 == category(0) else icons)
            stems = [icon.rsplit(".", 1)[0].lower() for icon in values]
            events.append(["icon_index", query])
            ret(stems.index(query) if query in stems else -1)
            return
        else:
            raise ValueError(f"Unexpected native boundary {address:#x} r0={r0:#x} r1={r1:#x} r2={r2:#x}")
        ret()

    def written(_, access, address, size, value, unused):
        if RECEIVER <= address < RECEIVER + 4096:
            assert address - RECEIVER in offsets and size == 4
            events.append(["offset_write", address - RECEIVER, value & 0xffffffff])

    uc.reg_write(UC_ARM_REG_R0, RECEIVER)
    uc.reg_write(UC_ARM_REG_R1, case.get("type", 0))
    uc.reg_write(UC_ARM_REG_R2, case.get("delta", 0) & 0xffffffff)
    uc.reg_write(UC_ARM_REG_LR, STOP)
    uc.reg_write(UC_ARM_REG_SP, STACK)
    uc.hook_add(UC_HOOK_CODE, code)
    uc.hook_add(UC_HOOK_MEM_WRITE, written)
    uc.emu_start(TARGETS[target][1], STOP, count=6000)
    assert uc.reg_read(UC_ARM_REG_PC) == STOP
    assert uc.reg_read(UC_ARM_REG_SP) == STACK
    return dict(inputs=case, events=events, final_state=read_state(),
                result=uc.reg_read(UC_ARM_REG_R0) if target == "06" else None)


def scenarios(target):
    names = ["All", "drums"]
    icons = ["Kick.png"]
    def case(type, state=(0, 0, 1, -1), **kwargs):
        return dict(type=type, state=list(state), names=kwargs.pop("names", names),
                    icons=kwargs.pop("icons", icons), **kwargs)
    many = ["All", "alpha", "beta", "delta", "drums", "guitar", "keys"]
    six = ["Kick.png", "Tom.png", "Snare.png", "Hat.png", "Ride.png", "Crash.png"]
    if target == "06":
        return [
            case(3), case(0, names=[], icons=[]), case(0, names=many, warm=False),
            case(0, names=many[:5]), case(0, names=many[:6]),
            case(1, state=(0, 0, -1, -1), warm=False), case(1, icons=six, warm=False),
            case(1, icons=six, state=(0, 0, 5, -1), warm=False),
            case(1, icons=six[:5]), case(1, icons=six, state=(0, 0, 0, -1)),
        ]
    if target == "07":
        return [case(0, state=(8, 0, 1, -1)), case(0, names=[], icons=[]),
                case(1, state=(0, 4, 1, 0)), case(1, state=(0, 0, 5, -1)),
                case(1, state=(0, 0, -1, -1)), case(1, missing_tags=[201])]
    if target == "08":
        # Equivalent display names keep these paging cases independent of
        # the host filesystem's unordered directory iteration.
        categories = ["All", "drums", "Drums", "DRums", "DRUms", "DRUMs", "DRUMS"]
        items = [f"{name}.png" for name in ("Kick", "kick", "KICK", "KIck", "KICk", "kicK")]
        return [case(0, delta=8, names=categories),
                case(0, delta=-10, state=(5, 0, 1, -1), names=categories),
                case(0, delta=0), case(0, delta=-7), case(1, delta=5, icons=items),
                case(1, delta=6, state=(0, 5, 1, -1), icons=items),
                case(1, delta=-1, state=(0, 5, 1, -1), icons=items)]
    return [case(1, state=(4, 3, category, 9), ch_icon=text)
            for category, text in ((1, ""), (1, "drums/kick"), (1, "drums/missing"),
                                   (1, "other/kick"), (0, "other/kick"), (5, "drums/kick"))]


def main(target):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", required=True, type=Path)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--write", type=Path)
    actions.add_argument("--verify", type=Path)
    args = parser.parse_args()
    image = args.elf.read_bytes()
    assert hashlib.sha256(image).hexdigest() == ELF_SHA
    elf = ELFFile(io.BytesIO(image))
    cases = [execute(elf, target, case) for case in scenarios(target)]
    data = dict(elf_sha256=ELF_SHA, ranges=read_ranges(image, elf), cases=cases)
    if args.write:
        with args.write.open("x") as file:
            file.write(json.dumps(data, indent=2) + "\n")
    elif json.loads(args.verify.read_text()) != data:
        raise SystemExit("Original observations differ from sealed fixture")
    print(f"Executed {len(cases)} exact ARM cases for task {target}")


NAME = TARGETS["06"][0]
if __name__ == "__main__":
    main("06")
