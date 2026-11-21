"""Compare original draw code and ARM arithmetic at isolated CCL boundaries."""
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

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
    for w, h, focus, present, value in [(100, 80, 1, 0, 0.5), (100, 80, 0, 1, 0),
                                        (101, 79, 1, 1, 0.5), (100, 80, 0, 1, 1),
                                        (30, 80, 1, 1, 1), (100, 29, 1, 1, 0.75),
                                        (10, 50, 0, 1, 0.75), (32, 33, 0, 1, 0.25)]:
        u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        lo = min(a for a, _, _ in segments)&~0xfff
        hi = max(a+s for a, s, _ in segments)
        u.mem_map(lo, (hi-lo+0xfff)&~0xfff)
        for addr, _, data in segments:
            u.mem_write(addr, data)
        base = 0x3000000
        u.mem_map(base, 0x10000)
        obj, event, graphics, graphics_table, param, param_table, style, stop = (base+i*0x100 for i in range(8))
        def put(addr, number):
            u.mem_write(addr, struct.pack("<I", number))
        put(obj+0x48, param if present else 0)
        put(obj+0x40, 8 if focus else 0)
        put(event, graphics)
        put(graphics, graphics_table)
        put(graphics_table+0x14, 0x1018e8)
        put(graphics_table+0x18, 0x100370)
        put(param, param_table)
        put(param_table+0x60, 0x11fef4)
        put(style, 0xff030201)
        put(style+0x10, 0xff090807)
        for register, value_ in [(UC_ARM_REG_R0, obj), (UC_ARM_REG_R1, event),
                                  (UC_ARM_REG_SP, base+0xff00), (UC_ARM_REG_LR, stop)]:
            u.reg_write(register, value_)
        trace = []
        arithmetic = set()
        def observe(cpu, addr, _size, _context):
            r0, r1, r2 = (cpu.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
            if addr == 0x10e9bc:
                assert r0 == obj
                cpu.mem_write(r1, struct.pack("<iiii", 0, 0, w, h))
                cpu.reg_write(UC_ARM_REG_R0, r1)
            elif addr == 0x10f4b4:
                assert r0 == obj
                cpu.reg_write(UC_ARM_REG_R0, style)
            elif addr == 0x11fef4:
                assert r0 == param
                cpu.reg_write(UC_ARM_REG_R0, struct.unpack("<I", struct.pack("<f", value))[0])
            elif addr in (0x1018e8, 0x100370):
                assert r0 == graphics
                color = struct.unpack("<I", cpu.mem_read(r2, 4))[0]
                if addr == 0x100370:
                    assert r2 == 2555628
                    # Colors::kWhite is runtime-initialized in the original.
                    color = 0xffffffff
                trace.extend([1 if addr == 0x1018e8 else 2, *struct.unpack("<iiii", cpu.mem_read(r1, 16)), color])
            else:
                if not entry <= addr < entry+size:
                    assert 0x187000 <= addr < 0x189000, hex(addr)
                    arithmetic.add(addr)
                return
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE, observe)
        u.emu_start(entry, stop, count=3000)
        assert u.reg_read(UC_ARM_REG_PC) == stop
        cases.append({"input": [w, h, focus, present, value], "observed": trace,
                      "native_arithmetic_addresses": sorted(arithmetic)})
    return {"elf": str(elf_path), "target": target, "section": section.name,
            "file_offset": offset, "range_sha256": digest(body), "cases": cases}


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
