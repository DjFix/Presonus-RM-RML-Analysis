"""Execute exact RemoteEventSender ranges and record typed lifetime and dispatch observations."""

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

ROOT = Path(__file__).resolve().parents[4]
TASK = Path(__file__).resolve().parent.name


def digest(data):
    return hashlib.sha256(data).hexdigest()


def observe(original, firmware, task):
    data = (firmware / original["elf_path"]).read_bytes()
    assert digest(data) == original["elf"]
    elf = ELFFile(io.BytesIO(data))
    assert elf["e_machine"] == "EM_ARM" and elf.little_endian
    symbols = elf.get_section_by_name(".symtab")

    def symbol(name):
        entries = symbols.get_symbol_by_name(name)
        assert len(entries) == 1, name
        return entries[0]

    entry = symbol(original["mangled"])
    section = elf.get_section(entry["st_shndx"])
    address, size = entry["st_value"], entry["st_size"]
    offset = section["sh_offset"] + address - section["sh_addr"]
    assert section["sh_addr"] <= address
    assert address + size <= section["sh_addr"] + section["sh_size"]
    assert (address, size, entry["st_shndx"], section.name, offset) == (
        original["address"], original["size"], original["section"],
        original["section_name"], original["file_offset"],
    )
    body = data[offset:offset + size]
    assert body.hex() == original["range_hex"]
    assert digest(body) == original["range_sha256"]
    def bound(name):
        entry = symbol(name)
        sec = elf.get_section(entry["st_shndx"])
        ptr, length = entry["st_value"], entry["st_size"]
        off = sec["sh_offset"] + ptr - sec["sh_addr"]
        assert sec["sh_addr"] <= ptr and ptr + length <= sec["sh_addr"] + sec["sh_size"]
        return {"mangled": name, "address": ptr, "size": length, "section": sec.name,
                "file_offset": off, "range_sha256": digest(data[off:off + length])}

    prefix = "_ZN8Presonus2UC17RemoteEventSender"
    table = bound("_ZTVN8Presonus2UC17RemoteEventSenderE")
    rtti = bound("_ZTIN8Presonus2UC17RemoteEventSenderE")
    base_info = bound("_ZTIN8Presonus2UC13IEventHandlerE")
    c1 = bound(prefix + "C1ERNS0_11IConnectionE")
    c2 = bound(prefix + "C2ERNS0_11IConnectionE")
    d1 = bound(prefix + "D1Ev")
    d0 = bound(prefix + "D0Ev")
    handle = bound(prefix + "11handleEventEPvRKNS0_5EventE")
    add_sender = bound("_ZN8Presonus2UC10Connection9addSenderEi")
    queue = bound("_ZN8Presonus2UC15BasicConnection10queueEventEPv")
    connection_table = bound("_ZTVN8Presonus2UC15BasicConnectionE")
    allocator = symbol("_ZdlPv@@GLIBCXX_3.4")["st_value"]
    table_words = struct.unpack_from("<5I", data, table["file_offset"])
    assert table_words == (0, rtti["address"], handle["address"], d1["address"], d0["address"])
    assert struct.unpack_from("<I", data, rtti["file_offset"] + 8)[0] == base_info["address"]
    assert c1["address"] != c2["address"]
    assert struct.unpack_from("<I", data, connection_table["file_offset"] + 8)[0] == queue["address"]

    method = task.rsplit("remoteeventsender_", 1)[1]
    fixtures = {
        "complete_construct": [(0x802000, 0x10203040), (0x803000, 0xFDDEAD30)],
        "base_construct": [(0x802000, 0x10203040), (0x803000, 0xFDDEAD30)],
        "complete_destroy": [(0x802000, 0x10203040), (0x803000, 0xFDDEAD30)],
        "deleting_destroy": [(0x802000, 0x10203040), (0x803000, 0xFDDEAD30)],
        "handle_event": [
            (0x802000, 0, "append", 1),
            (0x803000, 0x10203040, "append", 1),
            (0x803000, 0xFDDEAD30, "coalesce", 1),
            (0x802000, 0x9ABCDEFF, "reject", 0),
        ],
    }
    owner_page, stack, stop, event, item = 0xB00000, 0x901000, 0xA00000, 0x820000, 0x830000
    receiver = owner_page + 16
    vp = table["address"] + 8
    cases = []
    for values in fixtures[method]:
        connection, seed, *scenario = values
        cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        cpu.mem_map(0, 0xB00000)
        cpu.mem_map(owner_page, 0x1000)
        for segment in elf.iter_segments():
            if segment["p_type"] == "PT_LOAD":
                cpu.mem_write(segment["p_vaddr"], segment.data())
        original_connection = struct.pack("<4I", connection_table["address"] + 8, 0xEF, 0xFA, 0xB1)
        cpu.mem_write(connection, original_connection)
        if method.endswith("construct"):
            owner = [0xDEADBEEF, seed, 0xCCDD, 0xDEFE]
            argument = connection
        else:
            owner = [vp, seed, 0x89FE, connection]
            argument = 0 if scenario and scenario[0] == "reject" else item
        before = [0x12345, *owner, 0x87654]
        cpu.mem_write(receiver - 4, struct.pack("<6I", *before))
        event_before = [20566, 0x102938, 19, 0x88884444]
        cpu.mem_write(event, struct.pack("<4I", *event_before))
        for reg, value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, argument),
                           (UC_ARM_REG_R2, event), (UC_ARM_REG_SP, stack), (UC_ARM_REG_LR, stop)):
            cpu.reg_write(reg, value)
        calls, writes, owner_at_delete = [], [], None

        def code(cpu, pc, width, _):
            nonlocal owner_at_delete
            if pc == allocator:
                assert method == "deleting_destroy" and owner_at_delete is None
                assert cpu.reg_read(UC_ARM_REG_R0) == receiver
                owner_at_delete = list(struct.unpack("<6I", cpu.mem_read(receiver - 4, 24)))
                cpu.mem_unmap(owner_page, 0x1000)
                calls.append(["deallocate", "owner"])
            elif pc == queue["address"]:
                assert method == "handle_event" and not calls
                assert cpu.reg_read(UC_ARM_REG_R0) == connection
                assert cpu.reg_read(UC_ARM_REG_R1) == argument
                current = struct.unpack("<4I", cpu.mem_read(event, 16))
                calls.append(["queueEvent", "borrowed", "item" if argument else "null", list(current)])
                cpu.reg_write(UC_ARM_REG_R0, scenario[1])
            else:
                assert address <= pc < address + size, hex(pc)
                return
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

        def write(cpu, access, addr, width, value, _):
            if not stack - 96 <= addr < stack:
                area = "event" if event <= addr < event + 16 else "owner"
                writes.append([area, addr - (event if area == "event" else receiver), width, value])

        cpu.hook_add(UC_HOOK_CODE, code)
        cpu.hook_add(UC_HOOK_MEM_WRITE, write)
        cpu.emu_start(address, stop, count=96)
        assert cpu.reg_read(UC_ARM_REG_PC) == stop and cpu.reg_read(UC_ARM_REG_SP) == stack
        assert bytes(cpu.mem_read(connection, len(original_connection))) == original_connection
        owner_after = owner_at_delete
        if owner_after is None:
            owner_after = list(struct.unpack("<6I", cpu.mem_read(receiver - 4, 24)))
        assert owner_after[0] == before[0] and owner_after[-1] == before[-1]
        observed = {
            "calls": calls, "writes": writes,
            "owner_before": before, "owner_after_or_at_deallocation": owner_after,
        }
        if method.endswith("construct"):
            assert owner_after[1:5] == [vp, 0, 0, connection]
            observed["portable"] = {"ids": owner_after[2:4], "borrowed": owner_after[4] == connection}
        elif method.endswith("destroy"):
            assert owner_after[1:5] == owner and writes == [["owner", 0, 4, vp]]
            observed["portable"] = {"owner_deallocated": owner_at_delete is not None,
                                    "borrowed_preserved": True}
        else:
            assert owner_after == before
            event_after = list(struct.unpack("<4I", cpu.mem_read(event, 16)))
            assert event_after[:3] == event_before[:3] and writes == [["event", 12, 4, seed]]
            assert len(calls) == 1 and calls[0][3] == event_after
            observed["portable"] = {
                "case": scenario[0], "route_input": seed, "header": event_after,
                "return": cpu.reg_read(UC_ARM_REG_R0), "modeled_queue_result": scenario[1],
            }
        cases.append(observed)
    return {
        **original, "method": method, "table": table, "rtti": rtti,
        "verified_related": [base_info, connection_table, queue, c1, c2, d1, d0, add_sender],
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--task", default=TASK)
    args = parser.parse_args()
    fixture = Path(__file__).parent.parent / args.task / "fixtures.json"
    packet = ROOT / "temp/recovery-work/sqlite-issued/packet" / args.task / "CONTEXT.json"
    firmware = next(p for p in (ROOT, *ROOT.parents) if (p / "rootfs").is_dir())
    originals = json.loads(packet.read_text())["originals"]
    observations = [observe(item["original"], firmware, args.task) for item in originals]
    result = json.dumps({"observations": observations}, indent=2) + "\n"
    if args.verify:
        assert fixture.read_text() == result
    else:
        fixture.write_text(result)
    print(f"{len(observations)} ELF ranges, {sum(len(item['cases']) for item in observations)} native executions")


if __name__ == "__main__":
    main()
