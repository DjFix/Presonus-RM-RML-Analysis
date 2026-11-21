"""Run the exact original CS18 ARM adapter with an isolated byte-sink boundary."""
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
BODY_SHA = "41069ce3f3e11a5f039a3a7bc72a4914c4796ff215649d3a8d09e0bd1a3b25e1"


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
        entry = target["address"]
        offset = section["sh_offset"] + entry - section["sh_addr"]
        size = target["size"]
        assert 0 <= entry - section["sh_addr"] <= section["sh_size"] - size
        stream.seek(offset)
        body = stream.read(size)
        assert digest(body) == BODY_SHA
    cases = []
    for word, payload in [(0xef127f90, []), (0xffffffff, []), (0, []),
                          (0x12345678, [0xf0]), (0xfeadbeef, [0xf0, 0, 0x81, 0xf7]),
                          (0, [i % 256 for i in range(257)])]:
        u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        page = entry & ~0xfff
        u.mem_map(page, 0x1000)
        u.mem_write(entry, body)
        u.mem_map(0x3000000, 0x10000)
        base = 0x3000000
        adapter, event, sink, table, data, callback, stop = (base+i*0x100 for i in range(7))
        if payload:
            u.mem_write(data, bytes(payload))
        u.mem_write(adapter + 4, struct.pack("<I", sink))
        u.mem_write(sink, struct.pack("<I", table))
        u.mem_write(table, struct.pack("<I", callback))
        u.mem_write(event, struct.pack("<IIIH", 20, word, data, len(payload)))
        for register, value in ((UC_ARM_REG_R0, adapter), (UC_ARM_REG_R1, event),
                                (UC_ARM_REG_SP, base + 0xff00), (UC_ARM_REG_LR, stop)):
            u.reg_write(register, value)
        calls = []
        def record_call(cpu, address, _size, _context):
            if address != callback:
                assert entry <= address < entry + size
                return
            receiver, pointer, length, port = (cpu.reg_read(reg) for reg in
                                               (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3))
            assert receiver == sink
            calls.append([length, port, int(pointer == data), *cpu.mem_read(pointer, length)])
            cpu.reg_write(UC_ARM_REG_R0, 0xa5)
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE, record_call)
        u.emu_start(entry, stop, count=100)
        assert u.reg_read(UC_ARM_REG_PC) == stop and len(calls) == 1
        cases.append({"word": word, "payload": payload, "calls": calls,
                      "native_r0": u.reg_read(UC_ARM_REG_R0)})
    return {"elf": str(elf_path), "target": target, "section": section.name,
            "file_offset": offset, "range_sha256": BODY_SHA, "cases": cases}


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
