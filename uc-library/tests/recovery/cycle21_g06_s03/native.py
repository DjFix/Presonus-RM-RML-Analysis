"""Compare original draw code and ARM arithmetic at isolated CCL boundaries."""
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP

TASK = Path(__file__).parent.name
BASE = Path("temp/recovery-work/reconstruction10x10-20261121/packeting")
PACKET = BASE / "wave03040607-compatible24-batch01/packets" / TASK
INPUTS = BASE / "READ_INPUTS-wave03040607-compatible24-batch01-cycle21_g06.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def generate():
    request = json.loads((PACKET / "request.json").read_text())
    target, = request["targets"]
    release, = request["work_binding"]["binary_releases"]
    record = json.loads(INPUTS.read_text())[release["original_path"]]
    elf_path = Path(record["frozen_read_path"])
    assert digest(elf_path.read_bytes()) == record["sha256"] == target["original_elf_sha256"]
    with elf_path.open("rb") as stream:
        elf = ELFFile(stream)
        section = elf.get_section(target["section"])
        entry, size = target["address"], target["size"]
        offset = section["sh_offset"] + entry - section["sh_addr"]
        assert 0 <= entry-section["sh_addr"] <= section["sh_size"]-size
        stream.seek(offset)
        body = stream.read(size)
        context = (PACKET/"ELF_CONTEXT.md").read_text()
        assert digest(body) in context
        segments = [(s["p_vaddr"], s["p_memsz"], s.data()) for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
    cases = []
    for w, h, font_height, scale, ticks in [(36, 83, -1, 0, []),
                                            (36, 83, -1, 0, [-60, -40, -30, 0]),
                                            (35, 82, 15, 0, [-60, -1, 0, 10]),
                                            (24, 60, 10, 0, [-20, -40, 0, 10, -5]),
                                            (32, 60, 11, 1, [-60, -30, 0]),
                                            (12, 50, -1, 1, [-60, -30, 0]),
                                            (9, 37, 8, 0, [7, 7, 7])]:
        u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        lo = min(a for a, _, _ in segments)&~0xfff
        hi = max(a+n for a, n, _ in segments)
        u.mem_map(lo, (hi-lo+0xfff)&~0xfff)
        for addr, _, data in segments:
            u.mem_write(addr, data)
        base = 0x3000000
        u.mem_map(base, 0x10000)
        obj, event, graphics, table, interp, font, style, stop, vec, storage = (base+i*0x100 for i in range(10))
        def put(addr, number):
            u.mem_write(addr, struct.pack("<I", number & 0xffffffff))
        def get(addr, signed=False):
            return struct.unpack("<i" if signed else "<I", u.mem_read(addr, 4))[0]
        def fbits(value):
            return struct.unpack("<I", struct.pack("<f", value))[0]
        def c_string(addr):
            return bytes(u.mem_read(addr, 32)).split(b"\0", 1)[0]
        put(obj+0x58, interp if scale else 0)
        put(obj+0x5c, vec if ticks else 0)
        put(vec, storage)
        put(vec+4, len(ticks))
        for i, tick in enumerate(ticks):
            put(storage+4*i, tick)
        put(event, graphics)
        u.mem_write(event+4, struct.pack("<iiii", 1, 2, w-1, h-2))
        put(graphics, table)
        put(table+0x14, 0x1018e8)
        put(table+0x1c, 0x100438)
        put(table+0x20, 0x101f60)
        put(table+0x2c, 0x1029e8)
        put(interp, 0x19bd40)
        assert get(0x19bd40+0x10) == 0xe8654
        put(font+0x44, font_height)
        put(style+8, 0xff090807)
        put(style+12, 0xff131211)
        put(style, 0xff030201)
        u.mem_write(style+20, b"fixture\0")
        put(style+52, 5)
        for register, value in [(UC_ARM_REG_R0, obj), (UC_ARM_REG_R1, event),
                                 (UC_ARM_REG_SP, base+0xff00), (UC_ARM_REG_LR, stop)]:
            u.reg_write(register, value)
        trace = []
        arithmetic = set()
        def observe(cpu, addr, _size, _context):
            r0, r1, r2, r3, sp = (cpu.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP))
            if addr == 0x10e9bc:
                assert r0 == obj
                cpu.mem_write(r1, struct.pack("<iiii", 0, 0, w, h))
                cpu.reg_write(UC_ARM_REG_R0, r1)
            elif addr == 0x10f4b4:
                assert r0 == obj
                cpu.reg_write(UC_ARM_REG_R0, style)
            elif addr == 0xe8654:
                assert r0 == interp
                normalized = {fbits(-60): 0.0, fbits(-30): 0.25, fbits(0): 1.0}
                cpu.reg_write(UC_ARM_REG_R0, fbits(normalized[r1]))
            elif addr == 0x6a134:
                assert c_string(r1) == b"%i "
                number = struct.unpack("<i", struct.pack("<I", r2))[0]
                cpu.mem_write(r0, f"{number} ".encode("ascii")+b"\0")
            elif addr == 0xaffc:
                assert r2 == 4
                cpu.mem_write(r0, bytes(cpu.mem_read(r1, r2)))
            elif addr == 0x1029e8:
                assert r0 == graphics and c_string(r1) == b"fixture"
                trace.extend([4, 1])
                cpu.reg_write(UC_ARM_REG_R0, font if font_height >= 0 else 0)
            elif addr == 0x1018e8:
                assert r0 == graphics
                trace.extend([1, get(r2), *struct.unpack("<iiii", cpu.mem_read(r1, 16))])
            elif addr == 0x100438:
                assert r0 == graphics
                trace.extend([2, get(r3), *struct.unpack("<ii", cpu.mem_read(r1, 8)), *struct.unpack("<ii", cpu.mem_read(r2, 8))])
            elif addr == 0x101f60:
                assert r0 == graphics and c_string(get(sp)) == b"fixture"
                trace.extend([3, get(r3), *struct.unpack("<iiii", cpu.mem_read(r1, 16)), get(sp+4), *c_string(r2), 0])
            else:
                if not entry <= addr < entry+size:
                    assert 0x187000 <= addr < 0x189000, hex(addr)
                    arithmetic.add(addr)
                return
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE, observe)
        u.emu_start(entry, stop, count=20000)
        assert u.reg_read(UC_ARM_REG_PC) == stop
        cases.append({"input": [w, h, font_height, scale, len(ticks), *ticks], "observed": trace,
                      "native_arithmetic_addresses": sorted(arithmetic)})
    return {"elf": str(elf_path), "target": target, "section": section.name,
            "file_offset": offset, "range_sha256": digest(body), "cases": cases}


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
