"""Execute the original meter deleting destructor through its native table."""
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
        assert digest(body) == "8d4097502672ce586eea36a31857176ac7ce703baedaa934ebb2cb5fb66cc314"
        segments = [(s["p_vaddr"], s["p_memsz"], s.data()) for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    lo = min(a for a, _, _ in segments)&~0xfff
    hi = max(a+s for a, s, _ in segments)
    u.mem_map(lo, (hi-lo+0xfff)&~0xfff)
    for addr, _, data in segments:
        u.mem_write(addr, data)
    obj, scratch, stop = 0x3000000, 0x3001000, 0x3002000
    u.mem_map(obj, 0x1000)
    u.mem_map(scratch, 0x2000)
    table = 0x19bd40
    u.mem_write(obj, struct.pack("<I", table))
    (called,) = struct.unpack("<I", u.mem_read(table+4, 4))
    assert called == entry
    u.reg_write(UC_ARM_REG_R0, obj)
    u.reg_write(UC_ARM_REG_SP, scratch+0xff0)
    u.reg_write(UC_ARM_REG_LR, stop)
    deletes = []
    def release_page(cpu, addr, _size, _context):
        if addr != 0xad5c:
            assert entry <= addr < entry+size
            return
        assert cpu.reg_read(UC_ARM_REG_R0) == obj
        (vptr,) = struct.unpack("<I", cpu.mem_read(obj, 4))
        assert vptr == 0x19bd88
        cpu.mem_unmap(obj, 0x1000)
        deletes.append({"site": addr, "receiver": obj, "vptr_before_release": vptr})
        cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE, release_page)
    u.emu_start(called, stop, count=100)
    assert u.reg_read(UC_ARM_REG_PC) == stop and len(deletes) == 1
    try:
        u.mem_read(obj, 1)
    except UcError as error:
        assert error.errno == UC_ERR_READ_UNMAPPED
    else:
        raise AssertionError("Destructor did not release the emulated heap allocation")
    return {"elf": str(elf_path), "target": target, "section": section.name,
            "file_offset": offset, "range_sha256": digest(body),
            "cases": [{"native_delete": deletes, "observed": [len(deletes)]}],
            "allocator_boundary": "Actual original import reached; emulated allocator unmaps its receiver page."}


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
