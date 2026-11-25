"""Observe each exact ARM MIDI output lifecycle entry and actual Mackie reset."""
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R4, UC_ARM_REG_SP,
)

TASK = Path(__file__).resolve().parent.name
PROJECT = Path("/home/rs/projects/opencs/ai-line-analysis")
PACKET = PROJECT / "temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/midioutput_worker07/packet/tasks" / TASK / "CONTEXT.json"
FADER = PROJECT / "evidence/recovery/2026-11-21/reconstruction10x10/g06-s04-native-fader-sink01.json"
FADER_SHA = "dbe5133ba3cfc5bc9f3c0cdc26cc743254230836d58d7423ca67225a2aae948d"
VTABLE = "_ZTVN8Presonus7Surface19UCMidiOutputAdapterE"
DESTRUCTOR = TASK.split("_")[-1].startswith("d")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(elf, image, symtab, name, section_index, address, size, offset):
    if name:
        symbol, = symtab.get_symbol_by_name(name)
        assert (symbol["st_shndx"], symbol["st_value"], symbol["st_size"]) == (
            section_index, address, size)
    section = elf.get_section(section_index)
    displacement = address - section["sh_addr"]
    assert 0 <= displacement <= section["sh_size"] - size
    assert offset == section["sh_offset"] + displacement
    return section.name, image[offset:offset + size]


def fader_binding(elf, raw, symtab, identity):
    receipt = FADER.read_bytes()
    assert digest(receipt) == FADER_SHA
    evidence = json.loads(receipt)
    assert evidence["elf_sha256"] == identity
    records = {}
    for key in ("concrete", "model"):
        item = evidence[key]
        section, data = read(elf, raw, symtab, item.get("mangled"),
                             item["section_index"], item["address"], item["size"],
                             item["file_offset"])
        assert section == item["section"] and digest(data) == item["sha256"]
        records[key] = {**{k: v for k, v in item.items() if k != "instructions"},
                        "body": data.hex()}
    table = bytes.fromhex(records["model"]["body"])
    assert struct.unpack_from("<I", table, 24)[0] == records["concrete"]["address"]
    return records


def execute(original, body, address_point, provider, offset, endpoint_bound, fader_bound):
    entry = original["address"]
    arena, stop = 0x3000000, 0x3100000
    receiver, fader, endpoint = arena + offset, arena + 0x1000, arena + 0x2000
    emu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    mapped = set()

    def map_code(address, data):
        for page in range(address & ~0xfff, address + len(data), 4096):
            if page not in mapped:
                emu.mem_map(page, 4096)
                mapped.add(page)
        emu.mem_write(address, data)

    def put(address, value):
        emu.mem_write(address, struct.pack("<I", value))

    def get(address):
        return struct.unpack("<I", emu.mem_read(address, 4))[0]

    map_code(entry, body)
    emu.mem_map(arena, 0x10000)
    emu.mem_write(arena, bytes((19 * n + offset) & 255 for n in range(0x10000)))
    fader_code = None
    if DESTRUCTOR:
        for data in provider.values():
            map_code(data["address"], bytes.fromhex(data["body"]))
        fader_code = provider["concrete"]
        put(receiver + 4, endpoint if endpoint_bound else 0)
        put(receiver + 8, fader if fader_bound else 0)
        put(fader, provider["model"]["address"] + 8)
        put(fader + 0xae0, receiver)
    receiver_before = bytes(emu.mem_read(receiver - 4, 64))
    endpoint_before = bytes(emu.mem_read(endpoint, 4096))
    fader_before = bytes(emu.mem_read(fader, 4096))
    writes, entries, instructions = [], [], []

    def observe_code(cpu, address, size, _):
        if fader_code and address == fader_code["address"]:
            assert get(receiver) == address_point
            inputs = [cpu.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
            assert inputs == [fader, 0, 0]
            entries.append(inputs)
        assert (entry <= address < entry + len(body) - 4 or
                fader_code and fader_code["address"] <= address <
                fader_code["address"] + fader_code["size"])
        instructions.append(address)

    def observe_write(cpu, access, address, size, value, _):
        if address < arena + 0xf000:
            writes.append([address, size, value & 0xffffffff])

    emu.hook_add(UC_HOOK_CODE, observe_code)
    emu.hook_add(UC_HOOK_MEM_WRITE, observe_write)
    sp = arena + 0xff00
    for reg, val in ((UC_ARM_REG_SP, sp), (UC_ARM_REG_LR, stop),
                     (UC_ARM_REG_FP, 0x2424), (UC_ARM_REG_R4, 0x1818),
                     (UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, 0x12345678)):
        emu.reg_write(reg, val)
    emu.emu_start(entry, stop, count=64)
    assert emu.reg_read(UC_ARM_REG_PC) == stop and emu.reg_read(UC_ARM_REG_SP) == sp
    after = struct.unpack("<III", emu.mem_read(receiver, 12))
    assert bytes(emu.mem_read(receiver - 4, 4)) == receiver_before[:4]
    assert bytes(emu.mem_read(receiver + 12, 48)) == receiver_before[16:]
    assert bytes(emu.mem_read(endpoint, 4096)) == endpoint_before
    assert after[0] == address_point
    if DESTRUCTOR:
        assert after[1:] == (endpoint if endpoint_bound else 0, fader if fader_bound else 0)
        assert len(entries) == fader_bound
        expected = [[receiver, 4, address_point]]
        if fader_bound:
            expected.append([fader + 0xae0, 4, 0])
        assert writes == expected
    else:
        assert after[1:] == (0, 0) and not entries
        assert writes == [[receiver, 4, address_point], [receiver + 8, 4, 0],
                          [receiver + 4, 4, 0]]
    fader_after = bytes(emu.mem_read(fader, 4096))
    if fader_bound:
        assert fader_after == fader_before[:0xae0] + bytes(4) + fader_before[0xae4:]
    else:
        assert fader_after == fader_before
    return dict(inputs=[int(endpoint_bound), int(fader_bound)], receiver=receiver,
                receiver_after=after, calls=entries, instructions=instructions,
                writes=writes, endpoint_preserved=True, fader_sink_reset=bool(entries))


def generate():
    packet = json.loads(PACKET.read_text())
    original, = [entry["original"] for entry in packet["originals"]]
    evidence, = packet["task"]["review"]["evidence"]
    data = (PROJECT / evidence["path"]).read_bytes()
    assert digest(data) == evidence["sha256"]
    item, = [row for row in json.loads(data)["observations"]
             if row["original"]["mangled"] == original["mangled"]]
    for key in original.keys() & item["original"].keys():
        assert original[key] == item["original"][key]
    raw = (PROJECT / original["elf_path"]).read_bytes()
    assert digest(raw) == original["elf"]
    elf = ELFFile(io.BytesIO(raw))
    assert elf.little_endian and elf["e_machine"] == "EM_ARM"
    symtab = elf.get_section_by_name(".symtab")
    section, body = read(elf, raw, symtab, original["mangled"], original["section"],
                         original["address"], original["size"], original["file_offset"])
    assert section == original["section_name"]
    assert digest(body) == original["range_sha256"] and body.hex() == original["range_hex"]
    table, = symtab.get_symbol_by_name(VTABLE)
    literal, = struct.unpack_from("<I", body, len(body) - 4)
    assert table["st_value"] + 8 == literal
    provider = fader_binding(elf, raw, symtab, original["elf"]) if DESTRUCTOR else {}
    inputs = [(False, False), (True, False), (False, True), (True, True)] if DESTRUCTOR else [(False, False)] * 4
    cases = [execute(original, body, literal, provider, 0x100 + i * 0x44, *case)
             for i, case in enumerate(inputs)]
    return dict(original=original, vtable_address_point=literal, provider=provider, cases=cases)


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
