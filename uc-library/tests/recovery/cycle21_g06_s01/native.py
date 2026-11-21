"""Run the original FX prompt routine and its application type query."""
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

TASK = Path(__file__).parent.name
BASE = Path("temp/recovery-work/reconstruction10x10-20261121/packeting")
PACKET = BASE / "post32-next-batch02/packets" / TASK
INPUTS = BASE / "READ_INPUTS-post32-next-batch02-cycle21_g06-post32-next39-scoped01-dispatch02.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fbits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def floating(word):
    return struct.unpack("<f", struct.pack("<I", word))[0]


def load_target():
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
        assert digest(body) in (PACKET/"ELF_CONTEXT.md").read_text()
        segments = [(s["p_vaddr"], s["p_memsz"], s.data()) for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
        symbol_table = elf.get_section_by_name(".symtab")
        symbols = {s.name: (s["st_value"], s["st_size"]) for s in symbol_table.iter_symbols()
                   if s.name == "_ZNK8Presonus5Mixer11FXComponent10getTypeNumEv"}
    return ({"elf": str(elf_path), "target": target, "section": section.name,
             "file_offset": offset, "range_sha256": digest(body)}, segments, symbols)


def make_cpu(segments):
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    lo = min(a for a, _, _ in segments)&~0xfff
    hi = max(a+n for a, n, _ in segments)
    cpu.mem_map(lo, (hi-lo+0xfff)&~0xfff)
    for addr, _, data in segments:
        cpu.mem_write(addr, data)
    cpu.mem_map(0x3000000, 0x10000)
    return cpu


def generate():
    proof, segments, symbols = load_target()
    entry = proof["target"]["address"]
    query, query_size = symbols["_ZNK8Presonus5Mixer11FXComponent10getTypeNumEv"]
    assert (query, query_size) == (0x3a9e8, 40)
    cases = []
    for present, type_, recalled in [(0, 3, 4), (1, 3, 3), (1, 3, 5), (1, 3.75, 3),
                                     (1, -1, -1), (1, 0, -0.0), (1, 10, 10.5)]:
        u = make_cpu(segments)
        obj, live, shown, saved, prompt, table, stop = (0x3000000+i*0x200 for i in range(7))
        def put(addr, value):
            u.mem_write(addr, struct.pack("<I", value))
        for offset, pointer in [(0x11c, shown), (0x120, live), (0x128, saved)]:
            put(obj+offset, pointer)
        for slot in (live, shown, saved, prompt):
            put(slot, table)
        for offset, target in [(0x44, table+0x100), (0x58, table+0x104), (0x74, table+0x108)]:
            put(table+offset, target)
        u.reg_write(UC_ARM_REG_R0, obj)
        u.reg_write(UC_ARM_REG_SP, 0x300ff00)
        u.reg_write(UC_ARM_REG_LR, stop)
        trace = []
        text = ["previous" if present else "missing"]
        displayed = [42.]
        def observe(cpu, addr, _size, _context):
            r0, r1, r2 = (cpu.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
            if addr == 0x11b968:
                assert r0 == obj and bytes(cpu.mem_read(r1, 13)) == b"recallprompt\x00"
                cpu.reg_write(UC_ARM_REG_R0, prompt if present else 0)
            elif addr == table+0x100:
                assert r0 in (live, saved)
                value = type_ if r0 == live else recalled
                trace.extend([1 if r0 == live else 3, value])
                cpu.reg_write(UC_ARM_REG_R0, fbits(value))
            elif addr == table+0x104:
                assert r0 == shown and r2 == 1
                displayed[0] = floating(r1)
                trace.extend([2, displayed[0], r2])
            elif addr == table+0x108:
                assert r0 == prompt and r2 == 0
                text[0] = bytes(cpu.mem_read(r1, 9)).split(b"\x00",1)[0].decode("ascii")
            else:
                assert (entry <= addr < entry+proof["target"]["size"]
                        or query <= addr < query+query_size or 0x157000 <= addr < 0x157a00), hex(addr)
                return
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE, observe)
        u.emu_start(entry, stop, count=2000)
        assert u.reg_read(UC_ARM_REG_PC) == stop
        cases.append({"input": [present, type_, recalled], "observed": [*trace, displayed[0], text[0]]})
    proof["cases"] = cases
    proof["type_query"] = {"address": query, "size": query_size,
                         "range_sha256": digest(bytes(make_cpu(segments).mem_read(query, query_size)))}
    return proof


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
