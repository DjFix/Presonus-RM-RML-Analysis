"""Execute both original applyRange bodies with bounded CCL call doubles."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from struct import pack, unpack

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP,
)

ROOT = Path(__file__).resolve().parents[4]
TASK = Path(__file__).parent.name
PACKET = ROOT / "temp/recovery-work/sqlite-issued/packet" / TASK / "CONTEXT.json"
CALL_NAMES = {
    "_ZN4Core17FormatterRegistry4findEPKc": "formatter",
    "_ZN4Core19InterpolatorFactory6createEPKc": "factory",
    "_ZN4Core8Portable12NumericParam15setInterpolatorEPNS_12InterpolatorE": "install",
}
PARAM, EVENT, INTERP, FORMAT = (0x3000000 + x * 0x1000 for x in range(4))
VTABLE, INTERP_VTABLE, STACK, STOP = (0x3004000 + x * 0x1000 for x in range(4))
VIRTUALS = {STOP + x * 4: kind for x, kind in enumerate(
    ["cast", "range", "min", "max", "default"], start=1
)}
REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)


def original_image(row):
    blob = (ROOT / row["elf_path"]).read_bytes()
    assert sha256(blob).hexdigest() == row["elf"]
    elf = ELFFile(BytesIO(blob))
    symtab = elf.get_section_by_name(".symtab")
    symbol, = symtab.get_symbol_by_name(row["mangled"])
    entry, length, index = (symbol[x] for x in ("st_value", "st_size", "st_shndx"))
    assert (entry, length, index) == (row["address"], row["size"], row["section"])
    section = elf.get_section(index)
    shift = entry - section["sh_addr"]
    offset = section["sh_offset"] + shift
    assert 0 <= shift <= section["sh_size"] - length
    assert section.name == row["section_name"] and offset == row["file_offset"]
    body = blob[offset:offset + length]
    assert body.hex() == row["range_hex"]
    assert sha256(body).hexdigest() == row["range_sha256"]
    direct = {}
    for name, kind in CALL_NAMES.items():
        symbol, = symtab.get_symbol_by_name(name)
        direct[symbol["st_value"]] = kind
    return entry, body, direct


def case(numeric, curve, formatter, values, unused):
    words = [unused] + [unpack("<I", pack("<f", x))[0] for x in values]
    return {"numeric": numeric, "curve": curve, "formatter": formatter, "words": words}


CASES = [
    case(True, "observeCurve", "observeFormatter", (-5.5, 12.25, 2.75, 6.5), 0x7fc05301),
    case(True, "observeCurve", "missing", (1.25, 15.5, 8.125, 11.5), 0x80000000),
    case(True, "missing", "observeFormatter", (-2.25, 10.5, 4.75, 1.5), 0x7f800000),
    case(True, "", "", (-1.375, 3.25, 0.5, 2.25), 0x01020304),
    case(False, "observeCurve", "observeFormatter", (-7.5, 9.25, 2.5, 0.75), 0xffffffff),
    case(False, "observeCurve", "missing", (-8.5, 7.75, 1.25, 0.5), 0x40506070),
]


def execute(entry, body, direct, inputs):
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    page = entry & ~0xfff
    cpu.mem_map(page, 0x2000)
    cpu.mem_write(entry, body)
    for address in direct:
        target_page = address & ~0xfff
        if not page <= target_page < page + 0x2000:
            cpu.mem_map(target_page, 0x1000)
    cpu.mem_map(PARAM, 0x8000)
    for addr, value in [(PARAM, VTABLE), (PARAM + 16, FORMAT),
                        (INTERP, INTERP_VTABLE)]:
        cpu.mem_write(addr, pack("<I", value))
    for slot, address in zip((VTABLE, INTERP_VTABLE + 8, VTABLE + 0x4c,
                              VTABLE + 0x50, VTABLE + 0x54), VIRTUALS):
        cpu.mem_write(slot, pack("<I", address))
    cpu.mem_write(EVENT + 0x94, pack("<5I", *inputs["words"]))
    for key, offset in (("curve", 0xa8), ("formatter", 0xc8)):
        cpu.mem_write(EVENT + offset, inputs[key].encode() + b"\x00")
    trace = []

    def hook(machine, address, size, unused):
        kind = direct.get(address) or VIRTUALS.get(address)
        if kind is None:
            assert entry <= address < entry + len(body), hex(address)
            return
        a, b, c, d = [machine.reg_read(reg) for reg in REGS]
        result = 0
        if kind in ("formatter", "factory"):
            label = bytes(machine.mem_read(a, 32)).split(b"\x00", 1)[0].decode()
            assert a == EVENT + (0xc8 if kind == "formatter" else 0xa8)
            trace.append([kind, label])
            if kind == "formatter" and label == "observeFormatter":
                result = FORMAT
            elif kind == "factory" and label == "observeCurve":
                result = INTERP
        elif kind == "cast":
            assert a == PARAM and b == 0x4e506172
            result = PARAM if inputs["numeric"] else 0
            formatter_written, = unpack("<I", machine.mem_read(PARAM + 16, 4))
            trace.append([kind, int(formatter_written == FORMAT)])
        elif kind == "range":
            assert a == INTERP
            trace.append([kind, b, c, d])
        elif kind == "install":
            assert a == PARAM and b in (0, INTERP)
            trace.append([kind, int(b == INTERP)])
        else:
            assert a == PARAM
            trace.append([kind, b])
        machine.reg_write(UC_ARM_REG_R0, result)
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    for reg, value in ((UC_ARM_REG_R0, PARAM), (UC_ARM_REG_R1, EVENT),
                       (UC_ARM_REG_SP, STACK + 0xf00), (UC_ARM_REG_LR, STOP)):
        cpu.reg_write(reg, value)
    cpu.hook_add(UC_HOOK_CODE, hook)
    cpu.emu_start(entry, STOP, count=256)
    assert cpu.reg_read(UC_ARM_REG_PC) == STOP
    final, = unpack("<I", cpu.mem_read(PARAM + 16, 4))
    return {"trace": trace, "formatter": int(final == FORMAT)}


def observe():
    packet = json.loads(PACKET.read_text())
    roles = {}
    for item in packet["originals"]:
        row = item["original"]
        image = original_image(row)
        roles[row["role"]] = [{"inputs": case, "observed": execute(*image, case)} for case in CASES]
    assert roles["client"] == roles["server"]
    return roles


if __name__ == "__main__":
    print(json.dumps(observe(), indent=2))
