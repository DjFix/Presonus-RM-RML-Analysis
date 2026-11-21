"""Observe actual original adapter and Mackie sink setter instructions."""
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
RECEIPT = Path("/home/rs/projects/opencs/ai-line-analysis/evidence/recovery/2026-11-21/reconstruction10x10/g06-s04-native-fader-sink01.json")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def generate():
    request = json.loads((PACKET / "request.json").read_text())
    target, = request["targets"]
    release, = request["work_binding"]["binary_releases"]
    record = json.loads(INPUTS.read_text())[release["original_path"]]
    elf_path = Path(record["frozen_read_path"])
    assert digest(elf_path.read_bytes()) == record["sha256"] == target["original_elf_sha256"]
    receipt_bytes = RECEIPT.read_bytes()
    assert digest(receipt_bytes) == "dbe5133ba3cfc5bc9f3c0cdc26cc743254230836d58d7423ca67225a2aae948d"
    receipt = json.loads(receipt_bytes)
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    with elf_path.open("rb") as stream:
        elf = ELFFile(stream)
        for key in ("call", "concrete", "model"):
            verified = receipt[key]
            section = elf.get_section(verified["section_index"])
            address, size = verified["address"], verified["size"]
            displacement = address-section["sh_addr"]
            assert 0 <= displacement <= section["sh_size"]-size
            offset = section["sh_offset"]+displacement
            assert offset == verified["file_offset"]
            stream.seek(offset)
            body = stream.read(size)
            assert digest(body) == verified["sha256"]
            page = address & ~0xfff
            u.mem_map(page, (address+size-page+0xfff)&~0xfff)
            u.mem_write(address, body)
    adapter, first, second, stop = (0x3000000+i*0x1000 for i in range(4))
    actors = [0, first, second]
    u.mem_map(adapter, 0x10000)
    def put(address, value):
        u.mem_write(address, struct.pack("<I", value))
    def get(address):
        return struct.unpack("<I", u.mem_read(address, 4))[0]
    for receiver in actors[1:]:
        put(receiver, receipt["model"]["address"]+8)
    entry = target["address"]
    receiver_entry = receipt["concrete"]["address"]
    assert get(get(first)+16) == receiver_entry
    calls = []
    def observe(cpu, address, _size, _context):
        if address == receiver_entry:
            receiver, sink, index = (cpu.reg_read(reg) for reg in
                                     (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
            assert sink in (0, adapter)
            calls.extend([actors.index(receiver), int(sink == adapter), index])
        else:
            assert (entry <= address < entry+target["size"]
                    or receiver_entry <= address < receiver_entry+receipt["concrete"]["size"])
    u.hook_add(UC_HOOK_CODE, observe)
    cases = []
    for next_unit, index in [(0, 9), (1, -7), (1, 2147483647), (2, -2147483648), (0, 6), (0, 0)]:
        calls.clear()
        for register, value in ((UC_ARM_REG_R0, adapter), (UC_ARM_REG_R1, actors[next_unit]),
                                (UC_ARM_REG_R2, index & 0xffffffff),
                                (UC_ARM_REG_SP, adapter+0xff00), (UC_ARM_REG_LR, stop)):
            u.reg_write(register, value)
        u.emu_start(entry, stop, count=150)
        assert u.reg_read(UC_ARM_REG_PC) == stop
        state = [actors.index(get(adapter+8)), *(int(get(r+0xae0) == adapter) for r in actors[1:])]
        cases.append({"next_unit": next_unit, "index": index, "observed": [*calls, *state]})
    return {"elf": str(elf_path), "target": target, "section": receipt["call"]["section"],
            "file_offset": receipt["call"]["file_offset"], "range_sha256": receipt["call"]["sha256"],
            "receiver": receipt["concrete"], "receiver_vtable": receipt["model"], "cases": cases}


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
