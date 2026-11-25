"""Execute the hash-bound ARM reverb/base lifecycle and real deleting branch."""
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R4, UC_ARM_REG_SP,
)

TEST = Path(__file__).resolve().parent
TASK = TEST.name
PROJECT = Path("/home/rs/projects/opencs/ai-line-analysis")
PACKET = PROJECT / "temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/slreverb_worker07/packet/tasks" / TASK / "CONTEXT.json"
REVERB_TABLE = "_ZTVN8Presonus3Dsp18SLReverbControllerE"
CONTROL_TABLE = "_ZTVN8Presonus3Dsp10ControllerE"
CONTROL_D2 = "_ZN8Presonus3Dsp10ControllerD2Ev"
SET_TARGET = "_ZN8Presonus3Dsp10Controller9setTargetEPN4Core16IPropertyHandlerE"
DELETING = TASK.endswith("d0")
CASES = [(borrow, target, owner) for borrow in (0, 1)
         for target in (0, 1) for owner in (0, 1)]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def section_data(elf, raw, symbol):
    section = elf.get_section(symbol["st_shndx"])
    displacement = symbol["st_value"] - section["sh_addr"]
    size = symbol["st_size"]
    assert 0 <= displacement <= section["sh_size"] - size
    offset = section["sh_offset"] + displacement
    return raw[offset:offset + size], offset


def record(elf, raw, symtab, name):
    symbol, = symtab.get_symbol_by_name(name)
    assert symbol["st_info"]["type"] == "STT_FUNC"
    body, offset = section_data(elf, raw, symbol)
    return dict(mangled=name, address=symbol["st_value"], data=body.hex(),
                sha256=digest(body), size=symbol["st_size"], file_offset=offset,
                section=symbol["st_shndx"])


def delete_plt(elf, raw, address):
    plt = elf.get_section_by_name(".plt")
    displacement = address - plt["sh_addr"]
    index, remainder = divmod(displacement - 20, 12)
    assert index >= 0 and remainder == 0
    relocations = elf.get_section_by_name(".rel.plt")
    entry = relocations.get_relocation(index)
    dynamic_symbols = elf.get_section(relocations["sh_link"])
    name = dynamic_symbols.get_symbol(entry["r_info_sym"]).name
    assert name == "_ZdlPv"
    offset = plt["sh_offset"] + displacement
    return dict(mangled=name, address=address, offset=offset,
                sha256=digest(raw[offset:offset + 12]), got=entry["r_offset"])


def branch(entry, body, offset):
    word, = struct.unpack_from("<I", body, offset)
    assert word >> 24 == 0xeb
    signed_immediate = ((word & 0xffffff) ^ 0x800000) - 0x800000
    return entry + offset + 8 + signed_immediate * 4


def bindings(original, review):
    raw = (PROJECT / original["elf_path"]).read_bytes()
    assert digest(raw) == original["elf"]
    elf = ELFFile(io.BytesIO(raw))
    assert elf.little_endian and elf["e_machine"] == "EM_ARM"
    symtab = elf.get_section_by_name(".symtab")
    reverb = record(elf, raw, symtab, original["mangled"])
    assert reverb["data"] == original["range_hex"] and reverb["sha256"] == original["range_sha256"]
    for field in ("address", "size", "file_offset", "section"):
        assert reverb[field] == original[field]
    assert elf.get_section(reverb["section"]).name == original["section_name"]
    control = record(elf, raw, symtab, CONTROL_D2)
    base = review["real_base"]
    assert (control["mangled"], control["address"], control["size"]) == (
        base["mangled"], int(base["address"], 16), base["size"])
    target = record(elf, raw, symtab, SET_TARGET)
    assert branch(reverb["address"], bytes.fromhex(reverb["data"]), 28) == control["address"]
    assert branch(control["address"], bytes.fromhex(control["data"]), 32) == target["address"]
    tables = {}
    for name, code in ((REVERB_TABLE, reverb), (CONTROL_TABLE, control)):
        table, = symtab.get_symbol_by_name(name)
        contents, offset = section_data(elf, raw, table)
        point = table["st_value"] + 8
        literal, = struct.unpack_from("<I", bytes.fromhex(code["data"]), code["size"] - 4)
        assert point == literal
        tables[name] = dict(address_point=point, file_offset=offset, sha256=digest(contents))
    deallocator = None
    if DELETING:
        destination = branch(reverb["address"], bytes.fromhex(reverb["data"]), 36)
        assert destination == int(review["original_deleting_boundary"]["plt"], 16)
        deallocator = delete_plt(elf, raw, destination)
    return reverb, control, target, tables, deallocator


def execute(reverb, control, target, tables, deallocator, case):
    _, has_target, owns_target = case
    arena, outside, stack, stop = 0x1000000, 0x1100000, 0x2000000, 0x3000000
    receiver, handler, callback = arena + 0x100, outside + 0x100, outside + 0x400
    sp = stack + 0x800
    emu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    emu.mem_map(0x8000, 0x100000)
    for segment in (arena, outside, stack):
        emu.mem_map(segment, 4096)
    for code in (reverb, control, target):
        emu.mem_write(code["address"], bytes.fromhex(code["data"]))
    emu.mem_write(arena, b"\xa7" * 4096)
    emu.mem_write(outside, b"\x73" * 4096)

    def put(address, value):
        emu.mem_write(address, struct.pack("<I", value))

    def get(address):
        return struct.unpack("<I", emu.mem_read(address, 4))[0]

    put(receiver + 0x14, handler if has_target else 0)
    emu.mem_write(receiver + 0x1d, bytes((owns_target,)))
    put(handler, outside + 0x200)
    put(outside + 0x208, callback)
    outside_before = bytes(emu.mem_read(outside, 4096))
    before = bytes(emu.mem_read(arena, 4096))
    writes, calls, trace = [], [], []
    live = True

    def observe_code(cpu, address, size, _):
        nonlocal live
        if address == control["address"]:
            assert get(receiver) == tables[REVERB_TABLE]["address_point"]
            assert cpu.reg_read(UC_ARM_REG_R0) == receiver
            calls.append(CONTROL_D2)
        elif address == target["address"]:
            assert get(receiver) == tables[CONTROL_TABLE]["address_point"]
            assert cpu.reg_read(UC_ARM_REG_R0) == receiver and cpu.reg_read(UC_ARM_REG_R1) == 0
            calls.append(SET_TARGET)
        elif address == callback:
            assert calls == [CONTROL_D2, SET_TARGET]
            assert cpu.reg_read(UC_ARM_REG_R0) == handler and get(receiver + 0x14) == handler
            calls.append("borrowed_property_handler_release")
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
            return
        elif deallocator and address == deallocator["address"]:
            assert live and get(receiver + 0x14) == 0 and cpu.reg_read(UC_ARM_REG_R0) == receiver
            assert cpu.reg_read(UC_ARM_REG_LR) == reverb["address"] + 40
            calls.append("_ZdlPv")
            emu.mem_unmap(arena, 4096)
            live = False
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
            return
        assert any(code["address"] <= address < code["address"] + code["size"]
                   for code in (reverb, control, target)), hex(address)
        trace.append(address)

    def observe_write(cpu, access, address, size, value, _):
        if not stack <= address < stack + 4096:
            writes.append([address, size, value & 0xffffffff])

    emu.hook_add(UC_HOOK_CODE, observe_code)
    emu.hook_add(UC_HOOK_MEM_WRITE, observe_write)
    for reg, value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_SP, sp), (UC_ARM_REG_LR, stop),
                       (UC_ARM_REG_FP, 0x95), (UC_ARM_REG_R4, 0x45)):
        emu.reg_write(reg, value)
    emu.emu_start(reverb["address"], stop, count=128)
    assert emu.reg_read(UC_ARM_REG_PC) == stop and emu.reg_read(UC_ARM_REG_SP) == sp
    assert emu.reg_read(UC_ARM_REG_R0) == receiver
    expected_calls = [CONTROL_D2, SET_TARGET]
    if has_target and owns_target:
        expected_calls.append("borrowed_property_handler_release")
    if DELETING:
        expected_calls.append("_ZdlPv")
    assert calls == expected_calls
    expected_writes = [[receiver, 4, tables[name]["address_point"]]
                       for name in (REVERB_TABLE, CONTROL_TABLE)]
    if has_target:
        expected_writes.append([receiver + 0x14, 4, 0])
    assert writes == expected_writes
    assert live != DELETING
    if live:
        after = bytearray(before)
        for address, _, value in writes:
            struct.pack_into("<I", after, address - arena, value)
        assert bytes(emu.mem_read(arena, 4096)) == bytes(after)
    assert bytes(emu.mem_read(outside, 4096)) == outside_before
    return dict(inputs=case, calls=calls, writes=writes, instructions=trace,
                receiver_released=not live, borrowed_memory_preserved=True)


def generate():
    packet = json.loads(PACKET.read_text())
    binding, = packet["task"]["review"]["evidence"]
    source_evidence = (PROJECT / binding["path"]).read_bytes()
    assert digest(source_evidence) == binding["sha256"]
    review = json.loads(source_evidence)
    original, = [entry["original"] for entry in packet["originals"]]
    assert original in [row["original"] for row in review["originals"]]
    reverb, control, target, tables, delete = bindings(original, review)
    return dict(original=original, control_d2=control, set_target=target,
                tables=tables, delete=delete, cases=[
                    execute(reverb, control, target, tables, delete, case) for case in CASES])


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
