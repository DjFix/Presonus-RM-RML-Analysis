"""Execute MeterControl destruction, substituting the exact Control provider boundary."""
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R4, UC_ARM_REG_SP,
)

TEST = Path(__file__).resolve().parent
TASK = TEST.name
PROJECT = Path("/home/rs/projects/opencs/ai-line-analysis")
PACKET = PROJECT / "temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/meter_worker07/packet/tasks" / TASK / "CONTEXT.json"
VTABLE = "_ZTVN8Presonus5Panel12MeterControlE"
CONSTRUCTOR = "_ZN8Presonus5Panel12MeterControlC1Ei"
CONTROL_D2 = "_ZN8Presonus5Panel7ControlD2Ev"
DELETING = TASK.endswith("deleting_destroy")
CASES = ((-2147483648, 0, 0), (-4, 1, 1), (0, 2, 0), (3, 4, 1),
         (91, 7, 0), (2147483647, 7, 1))


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


def bindings(original, evidence):
    raw = (PROJECT / original["elf_path"]).read_bytes()
    assert digest(raw) == original["elf"]
    elf = ELFFile(io.BytesIO(raw))
    assert elf.little_endian and elf["e_machine"] == "EM_ARM"
    symtab = elf.get_section_by_name(".symtab")
    target = record(elf, raw, symtab, original["mangled"])
    assert target["data"] == original["range_hex"] and target["sha256"] == original["range_sha256"]
    for field in ("address", "size", "file_offset", "section"):
        assert target[field] == original[field]
    assert elf.get_section(target["section"]).name == original["section_name"]
    constructor = record(elf, raw, symtab, CONSTRUCTOR)
    control = record(elf, raw, symtab, CONTROL_D2)
    table, = symtab.get_symbol_by_name(VTABLE)
    contents, table_offset = section_data(elf, raw, table)
    point = table["st_value"] + 8
    literal, = struct.unpack_from("<I", bytes.fromhex(target["data"]), target["size"] - 4)
    assert point == literal
    assert point == evidence[0]["value"]
    assert control["address"] == evidence[1]["destination"] and CONTROL_D2 in evidence[1]["names"]
    slot = 20 if DELETING else 16
    assert struct.unpack_from("<I", contents, slot)[0] == target["address"]
    deallocator = delete_plt(elf, raw, evidence[2]["destination"]) if DELETING else None
    return constructor, control, deallocator, dict(
        mangled=VTABLE, address_point=point, slot_offset=slot,
        slot_file_offset=table_offset + slot, target=target["address"])


def execute(original, constructor, control, deallocator, table, case, exe):
    code = original["address"]
    body = bytes.fromhex(original["range_hex"])
    tag, mask, has_timer = case
    arena, stack, stop = 0x1000000, 0x2000000, 0x3000000
    receiver = arena + 0x100
    emu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    emu.mem_map(0x8000, 0x100000)
    emu.mem_map(arena, 4096)
    emu.mem_map(stack, 4096)
    emu.mem_write(code, body)
    emu.mem_write(constructor["address"], bytes.fromhex(constructor["data"]))
    emu.mem_write(arena, b"\xa7" * 4096)
    sp = stack + 0x800
    for register, value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, tag & 0xffffffff),
                            (UC_ARM_REG_SP, sp), (UC_ARM_REG_FP, 0x135),
                            (UC_ARM_REG_R4, 0x247), (UC_ARM_REG_LR, stop)):
        emu.reg_write(register, value)
    emu.emu_start(constructor["address"], stop, count=32)
    assert emu.reg_read(UC_ARM_REG_PC) == stop
    assert struct.unpack("<IiIIIIiIII", emu.mem_read(receiver, 40)) == (
        table["address_point"], -1, 0, 0, 0, 0, tag, 0, 0, 0)
    # The boundary's initialized observer/timer state lives in the real source provider.
    # Guest scratch fields are only observed prior to native cleanup dispatch.
    for i in range(3):
        if mask & (1 << i):
            emu.mem_write(receiver + 8 + 4 * i, struct.pack("<I", arena + 0x400 + i * 4))
    borrowed = arena + 0x2000
    emu.mem_map(borrowed, 4096)
    emu.mem_write(borrowed, struct.pack("<i", 17))
    emu.mem_write(receiver + 0x1c, struct.pack("<II", 1, borrowed))
    before = bytes(emu.mem_read(receiver, 40))
    calls, trace, writes = [], [], []
    cleanup = []
    live = True

    def observe_code(uc, address, size, _):
        nonlocal live
        if address == control["address"]:
            assert not calls and uc.reg_read(UC_ARM_REG_R0) == receiver
            assert uc.reg_read(UC_ARM_REG_LR) == code + 32
            assert bytes(uc.mem_read(receiver, 40)) == before
            output = subprocess.run([str(exe.resolve()), "provider"],
                                    input=f"{tag} {mask} {has_timer}\n", text=True,
                                    capture_output=True, check=True).stdout
            cleanup.extend(map(int, output.split()))
            assert cleanup == [mask, has_timer, 0, 1]
            calls.append(dict(address=address, target=CONTROL_D2, receiver=receiver))
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        elif deallocator and address == deallocator["address"]:
            assert len(calls) == 1 and live and uc.reg_read(UC_ARM_REG_R0) == receiver
            assert uc.reg_read(UC_ARM_REG_LR) == code + 40
            assert struct.unpack("<i", uc.mem_read(borrowed, 4))[0] == 17
            calls.append(dict(address=address, target="_ZdlPv", receiver=receiver))
            live = False
            uc.mem_unmap(arena, 4096)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        else:
            assert code <= address < code + len(body) - 4
            trace.append(address)

    def observe_write(uc, access, address, size, value, _):
        if not stack <= address < stack + 4096:
            writes.append([address, size, value])
        assert receiver <= address < receiver + 40 or stack <= address < stack + 4096

    emu.hook_add(UC_HOOK_CODE, observe_code)
    emu.hook_add(UC_HOOK_MEM_WRITE, observe_write)
    emu.emu_start(code, stop, count=32)
    assert emu.reg_read(UC_ARM_REG_PC) == stop
    assert emu.reg_read(UC_ARM_REG_SP) == sp and emu.reg_read(UC_ARM_REG_R0) == receiver
    assert trace == list(range(code, code + len(body) - 4, 4))
    assert writes == [[receiver, 4, table["address_point"]]]
    assert live == (not DELETING) and len(calls) == (2 if DELETING else 1)
    assert struct.unpack("<i", emu.mem_read(borrowed, 4))[0] == 17
    if live:
        assert bytes(emu.mem_read(receiver, 40)) == before
        assert struct.unpack("<i", emu.mem_read(borrowed, 4))[0] == 17
    return dict(inputs=list(case), receiver=receiver, instructions=trace, writes=writes,
                calls=calls, receiver_released=not live,
                provider_observations=cleanup)


def generate(exe):
    packet = json.loads(PACKET.read_text())
    binding, = packet["task"]["review"]["evidence"]
    source_evidence = (PROJECT / binding["path"]).read_bytes()
    assert digest(source_evidence) == binding["sha256"]
    observations = []
    for entry, evidence in zip(packet["originals"], json.loads(source_evidence)["native"], strict=True):
        original = entry["original"]
        assert original == evidence["original"]
        ctor, control, delete, table = bindings(original, evidence["site_evidence"])
        observations.append(dict(original=original, ctor=ctor, control_d2=control,
                                 deallocator=delete, literal=table, cases=[
            execute(original, ctor, control, delete, table, case, exe) for case in CASES]))
    return observations


if __name__ == "__main__":
    print(json.dumps(generate(Path(sys.argv[1])), indent=2))
