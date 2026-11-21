"""Replay the original D1 or D0 body against explicit provider boundaries."""
import hashlib
import json
import struct
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc, UcError
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

ROOT = Path("/home/rs/projects/opencs/ai-line-analysis")
RUN = ROOT / "temp/recovery-work/reconstruction10x10-20261121"
PACKETS = RUN / "packeting/post15-wave-compatible35-batch04/packets"
READ_MAP = RUN / "packeting/READ_INPUTS-post15-wave-compatible35-batch04-cycle21_g07.json"
def sha(data):
    return hashlib.sha256(data).hexdigest()


def observe(task):
    request = json.loads((PACKETS / task / "request.json").read_text())
    target = request["targets"][0]
    release = request["work_binding"]["binary_releases"][0]
    entry = json.loads(READ_MAP.read_text())[release["original_path"]]
    data = Path(entry["frozen_read_path"]).read_bytes()
    assert sha(data) == target["original_elf_sha256"] == entry["sha256"]
    start, size = target["address"], target["size"]
    with Path(entry["frozen_read_path"]).open("rb") as fp:
        elf = ELFFile(fp)
        section = elf.get_section(target["section"])
        assert section["sh_addr"] <= start and start + size <= section["sh_addr"] + section["sh_size"]
        offset = section["sh_offset"] + start - section["sh_addr"]
        segments = [(s["p_vaddr"], s["p_memsz"], s.data()) for s in elf.iter_segments()
                    if s["p_type"] == "PT_LOAD"]
        section_name = section.name
    deleting = target["mangled"].endswith("D0Ev")
    expected_range = (
        "c1741c13ef37814a6172f3ed4be27a4f3f12af041f8e60cb019ae0b198b29b9e" if deleting
        else "0c8804a34c3fb2374ce8f7f1ddd8bd23cfcdea5f69e97596a128c0364d4d41dd"
    )
    assert sha(data[offset:offset + size]) == expected_range
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    lo = min(a for a, n, b in segments) & ~4095
    hi = (max(a + n for a, n, b in segments) + 4095) & ~4095
    machine.mem_map(lo, hi - lo)
    for address, _, content in segments:
        machine.mem_write(address, content)
    obj, aliases, child, borrowed, stack, stop = (0x3000000 + i * 4096 for i in range(6))
    for address in (obj, aliases, child, borrowed, stack, stop):
        machine.mem_map(address, 4096)
    machine.mem_write(aliases, struct.pack("<I", borrowed))
    machine.mem_write(borrowed, b"borrowed")
    machine.reg_write(UC_ARM_REG_R0, obj)
    machine.reg_write(UC_ARM_REG_SP, stack + 0x800)
    machine.reg_write(UC_ARM_REG_LR, stop)
    calls, stores = [], []

    def record_store(_machine, _access, address, size, value, _data):
        if obj <= address < obj + 4096:
            stores.append([address - obj, size, value])

    def enter(uc, address, _size, _data):
        if address == stop:
            uc.emu_stop()
            return
        if start <= address < start + size:
            return
        arg = uc.reg_read(UC_ARM_REG_R0)
        return_site = uc.reg_read(UC_ARM_REG_LR)
        if address == 0x5D36C:
            assert arg == obj + 0xB4
            calls.append(["alias vector", return_site])
            # Explicit Core-provider boundary: release modeled vector storage.
            # The vector contains one borrowed alias which must survive.
            assert bytes(uc.mem_read(aliases, 4)) == struct.pack("<I", borrowed)
            uc.mem_unmap(aliases, 4096)
        elif address == 0x11B5E0:
            assert arg == obj
            calls.append(["component", return_site])
            # Model one CCL-owned child at this provider boundary.
            uc.mem_unmap(child, 4096)
        elif address == 0xAD5C:
            assert arg == obj
            calls.append(["operator delete", return_site])
            # Allocator boundary: make the tracked allocation inaccessible.
            uc.mem_unmap(arg, 4096)
        else:
            raise AssertionError(f"Unexpected boundary {address:#x}")
        uc.reg_write(UC_ARM_REG_PC, return_site)

    def released(address):
        try:
            machine.mem_read(address, 1)
            return False
        except UcError:
            return True

    machine.hook_add(UC_HOOK_CODE, enter)
    machine.hook_add(UC_HOOK_MEM_WRITE, record_store)
    machine.emu_start(start, stop + 4, count=1000)
    assert machine.reg_read(UC_ARM_REG_PC) == stop
    observation = dict(calls=calls, writes=stores, vector_storage_released=released(aliases),
                       child_destroyed=released(child), receiver_released=released(obj),
                       borrowed_preserved=bytes(machine.mem_read(borrowed, 8)) == b"borrowed")
    assert observation["receiver_released"] == deleting
    assert [event[0] for event in calls] == (
        ["alias vector", "component", "operator delete"] if deleting else ["alias vector", "component"])
    return dict(task=task, elf_sha256=sha(data), section=section_name, file_offset=offset, address=start,
                size=size, mangled=target["mangled"], range_sha256=expected_range, cases=[observation],
                oracle="Original ARM application instructions. Core destructor and allocator bodies are "
                       "explicit modeled boundaries. Delete reaches its exact ELF PLT target and unmaps "
                       "the tracked allocation at that invocation; host replay observes real delete.")


if __name__ == "__main__":
    print(json.dumps(observe(sys.argv[1]), indent=2))
