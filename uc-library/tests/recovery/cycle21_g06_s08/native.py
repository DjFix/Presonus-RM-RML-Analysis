"""Execute the original LPF deleting destructor through its native table."""
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_ERR_READ_UNMAPPED
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

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
        assert digest(body) in (PACKET/"ELF_CONTEXT.md").read_text()
        segments = [(s["p_vaddr"], s["p_memsz"], s.data()) for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
    cases = []
    for connected in (False, True):
        u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        lo = min(a for a, _, _ in segments)&~0xfff
        hi = max(a+n for a, n, _ in segments)
        u.mem_map(lo, (hi-lo+0xfff)&~0xfff)
        for addr, _, data in segments:
            u.mem_write(addr, data)
        obj, scratch, stop = 0x3000000, 0x3001000, 0x3002000
        u.mem_map(obj, 0x1000)
        u.mem_map(scratch, 0x3000)
        parameter = 0x3003000
        table = 0x1a1998

        def put(address, value):
            u.mem_write(address, struct.pack("<I", value))

        def read(address):
            return struct.unpack("<I", u.mem_read(address, 4))[0]

        put(obj, table)
        put(obj+0x48, parameter if connected else 0)
        called = read(table+8)
        assert called == entry
        u.reg_write(UC_ARM_REG_R0, obj)
        u.reg_write(UC_ARM_REG_SP, scratch+0xff0)
        u.reg_write(UC_ARM_REG_LR, stop)
        trace = []
        observed = []

        def observe(cpu, addr, _size, _context):
            if addr == 0xfb15c:
                assert cpu.reg_read(UC_ARM_REG_R0) == obj
                vptrs = [read(obj+o) for o in (0, 4, 0x44)]
                assert vptrs[1:] == [vptrs[0]+0x70, vptrs[0]+0x8c]
                trace.append({"event": "original Control destructor boundary", "vptrs": vptrs})
                assert read(obj+0x48) == (parameter if connected else 0)
                observed.append(1)
            elif addr == 0xad5c:
                assert cpu.reg_read(UC_ARM_REG_R0) == obj
                cpu.mem_unmap(obj, 0x1000)
                trace.append({"event": "original delete import unmaps closed arena page", "receiver": obj})
                observed.append(2)
            else:
                assert entry <= addr < entry+size
                return
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

        u.hook_add(UC_HOOK_CODE, observe)
        u.emu_start(called, stop, count=100)
        assert u.reg_read(UC_ARM_REG_PC) == stop
        assert len(trace) == 2
        try:
            u.mem_read(obj, 1)
        except UcError as error:
            assert error.errno == UC_ERR_READ_UNMAPPED
        else:
            raise AssertionError("Original deleting path left the emulated receiver accessible")
        cases.append({"connected": connected, "trace": trace,
                      "observed": [int("".join(map(str, observed)))]})
    return {"elf": str(elf_path), "target": target, "section": section.name,
            "file_offset": offset, "range_sha256": digest(body), "cases": cases,
            "allocator_boundary": "Original delete import reached; emulated allocator unmaps receiver.",
            "core_boundary": "Observe original call to exact pinned provider without running legacy Core body; actual CCL cleanup is verified separately on host."}


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
