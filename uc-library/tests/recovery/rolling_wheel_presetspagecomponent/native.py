"""Execute the original wheel handler and its application list-update path."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

ELF_SHA = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
SYMBOL = "_ZN8Presonus7Surface20PresetsPageComponent12onWheelInputERKN4Core8Portable10WheelEventE"
RANGE_SHA = "c543770e8ad2ce3722e585441de30813eeb0c563236d775c584cdd0a5f580795"
WHEEL, ADD = 0xB45D4, 0xB4588
PAGE, MIXER, HANDLER, EVENT = 0x400000, 0x401000, 0x402000, 0x404000
VT, PARAMS, TEXT = 0x430000, 0x410000, 0x440000
STOP = 0x5FF000


def require(condition, description):
    if not condition:
        raise ValueError(description)


def run(segments, cases):
    count, rows, offset, selected, visible, delta, axis = cases
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for address, size in ((0, 0x300000), (PAGE, 0x50000), (0x500000, 0x100000),
                          (0x600000, 0x20000)):
        u.mem_map(address, size)
    for address, data in segments:
        u.mem_write(address, data)

    def put(address, number):
        u.mem_write(address, struct.pack("<I", number & 0xFFFFFFFF))

    trace = []
    forwarded = []

    def capture(text, result=0):
        trace.append(text)
        return result

    put(PAGE, VT)
    put(HANDLER, VT + 0x400)
    for off, val in ((0xD4, 0), (0xD8, rows), (0xDC, offset), (0xE0, selected),
                     (0xE4, MIXER)):
        put(PAGE + off, val)
    put(EVENT, delta)
    put(EVENT + 4, axis)
    u.mem_write(TEXT, b"Alpha\0")
    tags = {tag: PARAMS + tag * 0x100 for row in range(rows)
            for tag in (row * 3, row * 3 + 1)}
    inverse_tags = {address: tag for tag, address in tags.items()}
    for address in inverse_tags:
        put(address, VT + 0x600)
    put(VT + 0x404, 0x500000)
    put(VT + 0x408, 0x500004)
    put(VT + 0x674, 0x500008)
    put(VT + 0x658, 0x50000C)

    def copy_string(dst, src, _):
        text = bytes(u.mem_read(src, 128)).split(b"\0", 1)[0] if src else b""
        u.mem_write(dst, text + b"\0")
        return dst

    def value(receiver, bits, _):
        decoded = struct.unpack("<f", struct.pack("<I", bits))[0]
        return capture(f"value:{inverse_tags[receiver]}:{int(decoded)}")

    def text(receiver, address, _):
        name = bytes(u.mem_read(address, 128)).split(b"\0", 1)[0].decode()
        return capture(f"text:{inverse_tags[receiver]}:{name}")

    # Existing bounded app oracle models the preset name as an inline CCL string
    # at displacement 0x100 and external parameter operations at their boundary.
    preset = TEXT - 0x100
    hooks = {
        0x500000: lambda _, category, arg: capture(f"count:{category}", count),
        0x500004: lambda _, category, index: capture(
            f"preset:{category}:{index}", preset if index < count else 0),
        0x500008: text,
        0x50000C: value,
        0x5C330: lambda *_: capture("handler", HANDLER),
        0x1864B8: lambda dividend, divisor, _: int(dividend / divisor),
        0x681D4: lambda *_: capture(f"visible:{visible}", visible),
        0x11F24C: lambda _, tag, arg: tags.get(tag, 0),
        0x11ACF0: lambda _, tag, arg: tags.get(tag, 0),
        **{address: copy_string for address in (0x24210, 0x24268, 0x11E78)},
    }
    for target in hooks:
        if target >= 0x500000:
            put(target, 0xE1A00000)

    def code(vm, address, _size, _data):
        if address == STOP:
            vm.emu_stop()
            return
        if address == ADD:
            forwarded.append((vm.reg_read(UC_ARM_REG_R0), vm.reg_read(UC_ARM_REG_R1)))
        if address in hooks:
            regs = (vm.reg_read(reg) for reg in
                    (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
            vm.reg_write(UC_ARM_REG_R0, hooks[address](*regs) & 0xFFFFFFFF)
            vm.reg_write(UC_ARM_REG_PC, vm.reg_read(UC_ARM_REG_LR))
        elif not (0xB43E0 <= address < WHEEL + 24):
            raise ValueError(f"Unmodeled native entry {address:#x}")

    u.hook_add(UC_HOOK_CODE, code)
    for register, value in ((UC_ARM_REG_R0, PAGE), (UC_ARM_REG_R1, EVENT),
                            (UC_ARM_REG_LR, STOP), (UC_ARM_REG_SP, 0x61F000)):
        u.reg_write(register, value)
    u.emu_start(WHEEL, STOP + 4, count=20000)
    require(u.reg_read(UC_ARM_REG_PC) == STOP, "Original did not return to sentinel")
    require(forwarded == [(PAGE, delta & 0xFFFFFFFF)], "Original forwarding differs")
    require(bytes(u.mem_read(EVENT, 8)) == struct.pack("<ii", delta, axis),
            "Original mutated wheel event")
    offset, selected = struct.unpack("<ii", u.mem_read(PAGE + 0xDC, 8))
    return {"offset": offset, "selected": selected, "events": trace}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args()
    raw = args.elf.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == ELF_SHA, "Wrong original ELF")
    elf = ELFFile(io.BytesIO(raw))
    targets = elf.get_section_by_name(".symtab").get_symbol_by_name(SYMBOL)
    require(len(targets) == 1, "Expected one exact original symbol")
    symbol = targets[0]
    require((symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) ==
            (WHEEL, 24, 12), "Original symbol identity differs")
    section = elf.get_section(12)
    offset = section["sh_offset"] + WHEEL - section["sh_addr"]
    require(offset == 706004 and hashlib.sha256(raw[offset:offset+24]).hexdigest()
            == RANGE_SHA, "Original mapped range differs")
    segments = [(s["p_vaddr"], s.data()) for s in elf.iter_segments()
                if s["p_type"] == "PT_LOAD"]
    inputs = [
        [7, 3, 2, 3, 1, 1, 0], [7, 3, 3, 1, 1, -2, 1],
        [7, 3, 3, 3, 1, 0, 0], [7, 3, 3, 1, 1, -20, 0],
        [7, 3, 3, 6, 1, 20, 1], [7, 3, 6, 6, 1, 5, 0],
        [7, 3, 2, 4, 0, 2, 1], [7, 3, 0, 0, 0, -1, 0],
        [7, 3, 9, 6, 1, 0, 1], [7, 3, 1, 0, 1, 2147483647, 1],
    ]
    observed = [{"argv": case, "expected": run(segments, case)} for case in inputs]
    data = {"elf_sha256": ELF_SHA, "range_sha256": RANGE_SHA,
            "section": section.name, "file_offset": offset, "cases": observed}
    if args.generate:
        with args.fixtures.open("x") as output:
            output.write(json.dumps(data, indent=2) + "\n")
    else:
        require(json.loads(args.fixtures.read_text()) == data, "Native fixture differs")
    print(f"{len(inputs)} native wheel/list observations")


if __name__ == "__main__":
    main()
