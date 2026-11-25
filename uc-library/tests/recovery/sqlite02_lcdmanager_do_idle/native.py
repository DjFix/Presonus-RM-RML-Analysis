"""Execute selected ARM LCDManager entries against verified firmware images."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from capstone import CS_ARCH_ARM, CS_MODE_ARM, Cs
from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

MANAGER = "N8Presonus5Panel10LCDManager"
SINGLETON = "N4Core8Portable9SingletonIN8Presonus5Panel10LCDManagerE"
COMPONENT = "N8Presonus5Panel12LCDComponent"
RECEIVER = 0x800000
OTHER = 0x810000
DISPLAY = 0x820000
STACK = 0x901000
STOP = 0xA00000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def record(elf, raw, name):
    symbols = elf.get_section_by_name(".symtab")
    sym, = symbols.get_symbol_by_name(name)
    section = elf.get_section(sym["st_shndx"])
    address, size = sym["st_value"], sym["st_size"]
    displacement = address - section["sh_addr"]
    assert 0 <= displacement <= section["sh_size"] - size
    offset = section["sh_offset"] + displacement
    data = raw[offset:offset + size] if section["sh_type"] != "SHT_NOBITS" else b""
    return dict(mangled=name, address=address, size=size, file_offset=offset,
                section=sym["st_shndx"], section_name=section.name,
                range_hex=data.hex(), range_sha256=digest(data))


def delete_plt(elf, body):
    branch, = [op for op in Cs(CS_ARCH_ARM, CS_MODE_ARM).disasm(
        bytes.fromhex(body["range_hex"]), body["address"]) if op.mnemonic == "bl"]
    address = int(branch.op_str.removeprefix("#"), 16)
    plt = elf.get_section_by_name(".plt")
    displacement = address - plt["sh_addr"]
    index, remainder = divmod(displacement - 20, 12)
    assert index >= 0 and not remainder
    rel = elf.get_section_by_name(".rel.plt")
    entry = rel.get_relocation(index)
    name = elf.get_section(rel["sh_link"]).get_symbol(entry["r_info_sym"]).name
    assert name == "_ZdlPv"
    return dict(address=address, mangled=name, got=entry["r_offset"],
                file_offset=plt["sh_offset"] + displacement,
                range_sha256=digest(plt.data()[displacement:displacement + 12]))


def observe(original, firmware_root):
    raw = (firmware_root / original["elf_path"]).read_bytes()
    assert digest(raw) == original["elf"]
    elf = ELFFile(io.BytesIO(raw))
    assert elf["e_machine"] == "EM_ARM" and elf.little_endian
    body = record(elf, raw, original["mangled"])
    assert all(original[key] == value for key, value in body.items())

    idle = body["mangled"].endswith("doIdleEv")
    deleting = body["mangled"].endswith("D0Ev")
    manager_table = record(elf, raw, "_ZTV" + MANAGER + "E")
    table_base = manager_table["address"] + 8
    bindings = [manager_table]
    if idle:
        lcd_table = record(elf, raw, "_ZTV" + COMPONENT + "E")
        thunk = record(elf, raw, "_ZThn212_" + COMPONENT + "6doIdleEv")
        lcd_idle = record(elf, raw, "_Z" + COMPONENT + "6doIdleEv")
        lcd_on_idle = record(elf, raw, "_Z" + COMPONENT + "6onIdleEv")
        core_idle = record(elf, raw, "_ZN4Core8Portable9Component6onIdleEv")
        bindings += [lcd_table, thunk, lcd_idle, lcd_on_idle, core_idle]
        lcd_words = struct.unpack("<33I", bytes.fromhex(lcd_table["range_hex"]))
        assert lcd_words[32] == thunk["address"] and lcd_words[12] == lcd_on_idle["address"]
    else:
        slot = 12 if deleting else 8
        assert struct.unpack_from("<I", bytes.fromhex(manager_table["range_hex"]), slot)[0] == body["address"]
        instance = record(elf, raw, "_Z" + SINGLETON + "E11theInstanceE")
        singleton_table = record(elf, raw, "_ZTV" + SINGLETON + "EE")
        deletable_table = record(elf, raw, "_ZTVN4Core8Portable9DeletableE")
        bindings += [instance, singleton_table, deletable_table]
        if deleting:
            delete = delete_plt(elf, body)
            bindings.append(delete)

    cases = []
    for seed in (("unbound", "typed", "typed_twice") if idle else ("null", "other", "receiver")):
        cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        cpu.mem_map(0, 0xB00000)
        for segment in elf.iter_segments(type="PT_LOAD"):
            cpu.mem_write(segment["p_vaddr"], segment.data())

        def write(address, *values):
            cpu.mem_write(address, struct.pack(f"<{len(values)}I", *values))

        def read(address):
            return struct.unpack("<I", cpu.mem_read(address, 4))[0]

        delegate = 0
        instance_before = 0
        if idle and seed != "unbound":
            delegate = DISPLAY + 212
            write(DISPLAY, lcd_table["address"] + 8)
            write(delegate, lcd_table["address"] + 116)
        if not idle:
            # Keep a non-null borrowed delegate with an unmapped/trapping vtable.
            delegate = DISPLAY
            instance_before = {"null": 0, "other": OTHER, "receiver": RECEIVER}[seed]
            write(instance["address"], instance_before)
        write(RECEIVER, table_base, delegate)

        trace, writes, calls = [], [], []

        def invoke_boundary(emu, pc, _width, _data):
            trace.append(pc)
            if idle and pc == core_idle["address"]:
                assert emu.reg_read(UC_ARM_REG_R0) == DISPLAY
                calls.append("core_idle")
                emu.reg_write(UC_ARM_REG_PC, emu.reg_read(UC_ARM_REG_LR))
            if not idle and deleting and pc == delete["address"]:
                assert emu.reg_read(UC_ARM_REG_R0) == RECEIVER
                assert read(RECEIVER) == deletable_table["address"] + 8
                assert read(instance["address"]) == (0 if seed == "receiver" else instance_before)
                calls.append("operator_delete_receiver")
                # The verified native delete call transfers the receiver to the
                # substituted allocator; revoke access to that allocation.
                emu.mem_unmap(RECEIVER, 0x1000)
                emu.reg_write(UC_ARM_REG_PC, emu.reg_read(UC_ARM_REG_LR))

        def write_trace(_emu, _access, address, width, value, _data):
            if not STACK - 0x100 <= address < STACK:
                writes.append((address, width, value & 0xFFFFFFFF))

        cpu.hook_add(UC_HOOK_CODE, invoke_boundary)
        cpu.hook_add(UC_HOOK_MEM_WRITE, write_trace)
        for _ in range(2 if seed == "typed_twice" else 1):
            cpu.reg_write(UC_ARM_REG_R0, RECEIVER)
            cpu.reg_write(UC_ARM_REG_SP, STACK)
            cpu.reg_write(UC_ARM_REG_LR, STOP)
            cpu.emu_start(body["address"], STOP, count=64)
            assert cpu.reg_read(UC_ARM_REG_PC) == STOP
            assert cpu.reg_read(UC_ARM_REG_SP) == STACK
        if idle:
            assert not writes and read(RECEIVER + 4) == delegate
            assert calls == ["core_idle"] * {"unbound": 0, "typed": 1, "typed_twice": 2}[seed]
            projection = dict(idle_calls=len(calls))
        else:
            final_instance = read(instance["address"])
            expected_writes = [(RECEIVER, 4, singleton_table["address"] + 8)]
            if seed == "receiver":
                expected_writes.append((instance["address"], 4, 0))
            expected_writes.append((RECEIVER, 4, deletable_table["address"] + 8))
            assert writes == expected_writes
            assert final_instance == (0 if seed == "receiver" else instance_before)
            assert calls == (["operator_delete_receiver"] if deleting else [])
            if not deleting:
                assert read(RECEIVER + 4) == delegate
            projection = dict(singleton_is_null=final_instance == 0, deletes=len(calls),
                              delegate_callbacks=0)
        cases.append(dict(case=seed, executed_addresses=trace, nonstack_writes=writes,
                          boundary_calls=calls, portable=projection))
    return dict(original=original, native_bindings=bindings, cases=cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--firmware-root", type=Path, default=Path.cwd())
    parser.add_argument("--fixtures", type=Path, required=True)
    args = parser.parse_args()
    packet = args.packet.read_bytes()
    originals = json.loads(packet)["originals"]
    result = dict(packet_sha256=digest(packet), observations=[
        observe(item["original"], args.firmware_root) for item in originals
    ])
    captured = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.fixtures.is_file():
        assert args.fixtures.read_text() == captured
    else:
        args.fixtures.write_text(captured)
    print(f"Observed {sum(len(item['cases']) for item in result['observations'])} native cases")


if __name__ == "__main__":
    main()
