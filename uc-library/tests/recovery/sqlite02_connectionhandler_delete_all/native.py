"""Execute the ConnectionHandler ARM ranges with verified typed ownership boundaries."""

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

ROOT = Path(__file__).resolve().parents[4]
TASK = Path(__file__).resolve().parent.name

SCENARIOS = {
    "sqlite02_connectionhandler_delete_all": [
        ("empty", 0, [[], [], []], {}, 0, 0),
        ("null", 0, [[0], [], []], {}, 0, 0),
        ("single", 0, [[1], [], []], {}, 0, 0),
        ("mixed", 0, [[1, 0, 2, 3], [], []], {}, 0, 0),
    ],
    "sqlite02_connectionhandler_cleanup_all": [
        ("empty", 0, [[], [], []], {}, 0, 0),
        ("mixed", 0, [[1, 0], [], [2, 3]], {}, 0, 0),
        ("all", 1, [[1], [2], [3]], {}, 0, 0),
    ],
    "sqlite02_connectionhandler_stop_listening": [
        ("disabled", 0, [[1], [2], [3]], {}, 0, 1),
        ("empty", 1, [[], [2], [3]], {}, 0, 0),
        ("armed", 7, [[1, 0], [2], [3]], {}, 0, 1),
    ],
    "sqlite02_connectionhandler_remove_external": [
        ("empty", 0, [[], [], []], {}, 11, 0),
        ("miss", 0, [[], [], [1, 2]], {1: 3, 2: 4}, 11, 0),
        ("first", 0, [[], [], [1, 2, 3]], {1: 11, 2: 11, 3: 4}, 11, 0),
        ("middle", 0, [[], [], [1, 2, 3]], {1: 3, 2: 11, 3: 4}, 11, 0),
        ("null", 0, [[], [], [1, 2]], {1: 3, 2: 0}, 0, 0),
    ],
}


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
    local = {
        "deleteAll": "_ZN8Presonus2UC17ConnectionHandler9deleteAllERN4Core6VectorIPNS0_10ConnectionEEE",
        "connectionD0": "_ZN8Presonus2UC18ExternalConnectionD0Ev",
        "connectionD2": "_ZN8Presonus2UC10ConnectionD2Ev",
        "stopSocketBundle": "_ZN8Presonus2UC12SocketBundle9deleteAllEv",
        "multicastCleanup": "_ZN8Presonus2UC19MulticastConnection7cleanupEv",
    }
    provider = {
        "connectionDelete": "_ZdlPv@@GLIBCXX_3.4",
        "resize": "_ZN4Core6VectorIPN8Presonus2UC10ConnectionEE6resizeEi",
        "remove": "_ZN4Core13MutableVectorIPN8Presonus2UC10ConnectionENS_6VectorIS4_EEE6removeERKS4_",
        "senderVectorD1": "_ZN4Core6VectorIPN8Presonus2UC17RemoteEventSenderEED1Ev",
        "eventQueueD1": "_ZN8Presonus2UC10EventQueueD1Ev",
        "socketD1": "_ZN4Core7Sockets10CoreSocketD1Ev",
        "report": "UCReportMessage",
        "unicast": "_ZN8Presonus2UC19MulticastConnection18makeUnicastSocketsEb",
        "multicast": "_ZN8Presonus2UC19MulticastConnection20makeMulticastSocketsEb",
    }
    verified = {}
    for name, mangled in {**local, **provider}.items():
        ref = symbol(mangled)
        verified[name] = {"mangled": mangled, "address": ref["st_value"], "size": ref["st_size"]}
    starts = {r["address"]: n for n, r in verified.items()}
    allowed = [(address, address + size)]
    for name in local:
        ref = verified[name]
        allowed.append((ref["address"], ref["address"] + ref["size"]))
    table = symbol("_ZTVN8Presonus2UC18ExternalConnectionE")
    assert table["st_size"] >= 24
    address_point = table["st_value"] + 8

    receiver, vector, multicast, socket_array = 0x800000, 0x810000, 0x820000, 0x830000
    stack, stop, heap = 0x901000, 0xA00000, 0xB00000
    cases = []

    for description, initial_flag, rosters, channels, wanted, armed_socket in SCENARIOS[task]:
        cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        cpu.mem_map(0, 0xB00000)
        for segment in elf.iter_segments():
            if segment["p_type"] == "PT_LOAD":
                cpu.mem_write(segment["p_vaddr"], segment.data())

        def load(location):
            return struct.unpack("<I", cpu.mem_read(location, 4))[0]

        def store(location, word):
            cpu.mem_write(location, struct.pack("<I", word))

        def receiver_flag():
            return cpu.mem_read(receiver + 0x34, 1)[0]

        assert load(address_point + 12) == verified["connectionD0"]["address"]
        pool = {}
        for identifier in {n for values in rosters for n in values if n}:
            ptr = heap + identifier * 0x1000
            cpu.mem_map(ptr, 0x1000)
            store(ptr, address_point)
            store(ptr + 0x13C, channels.get(identifier, 0))
            pool[ptr] = identifier
        addresses = {identifier: ptr for ptr, identifier in pool.items()}
        addresses[0] = 0
        is_direct = task.endswith("delete_all")
        native_rosters = [receiver + n for n in (0x38, 0x4C, 0x60)]
        if is_direct:
            native_rosters[0] = vector
        for index, (vec, values) in enumerate(zip(native_rosters, rosters)):
            backing = 0x840000 + index * 0x1000
            cpu.mem_write(vec, struct.pack("<5I", 0xD00D, backing, len(values), 5, 5))
            for slot, identifier in enumerate(values):
                store(backing + slot * 4, addresses[identifier])
            store(backing + 16, 0xFADEBEEF)

        def roster(vec):
            table = load(vec + 4)
            return [pool.get(load(table + 4 * i), 0) for i in range(load(vec + 8))]

        socket_pointer = heap + 0x10000
        cpu.mem_write(receiver + 0x33, bytes([63, initial_flag, 99]))
        store(receiver + 0x74, multicast)
        store(receiver + 4, socket_array)
        store(receiver + 8, armed_socket)
        if armed_socket:
            cpu.mem_map(socket_pointer, 0x1000)
            store(socket_array, socket_pointer)

        input_r1 = vector if is_direct else wanted
        for register, value in (
            (UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, input_r1),
            (UC_ARM_REG_SP, stack), (UC_ARM_REG_LR, stop),
        ):
            cpu.reg_write(register, value)

        calls = []
        deleted = set()

        def code(cpu, pc, width, _):
            name = starts.get(pc)
            r0, r1 = cpu.reg_read(UC_ARM_REG_R0), cpu.reg_read(UC_ARM_REG_R1)
            if name is None:
                assert any(lo <= pc < hi for lo, hi in allowed), hex(pc)
                return
            if name == "deleteAll":
                assert r0 == receiver and r1 in native_rosters
                calls.append([name, native_rosters.index(r1), roster(r1)])
                return
            if name == "connectionD0":
                assert r0 in pool and r0 not in deleted
                calls.append(["destroy", pool[r0], [roster(v) for v in native_rosters]])
                return
            if name == "connectionD2":
                assert r0 in pool and load(r0 + 0x170) == 0
                calls.append([name, pool[r0]])
                return
            if name in ("senderVectorD1", "eventQueueD1"):
                assert any(r0 - base in (0x168, 0x144, 0xC) for base in pool)
                calls.append([name, r0 & 0xFFF])
            elif name == "connectionDelete":
                assert r0 not in deleted
                if r0 in pool:
                    calls.append(["deallocate", pool[r0]])
                else:
                    assert r0 == socket_pointer
                    calls.append(["socketDeallocate", receiver_flag()])
                cpu.mem_unmap(r0, 0x1000)
                deleted.add(r0)
            elif name == "resize":
                assert r0 in native_rosters and r1 == 0
                backing = load(r0 + 4)
                assert load(backing + 16) == 0xFADEBEEF
                calls.append([name, native_rosters.index(r0), roster(r0)])
                for offset in (4, 8, 12):
                    store(r0 + offset, 0)
            elif name == "remove":
                vec = r0 - 4
                assert vec == native_rosters[2]
                pointer = load(r1)
                assert pointer in pool
                items = roster(vec)
                calls.append([name, pool[pointer], items])
                items.remove(pool[pointer])
                backing = load(r0)
                for index, identifier in enumerate(items):
                    store(backing + index * 4, addresses[identifier])
                store(vec + 8, len(items))
                store(backing + len(items) * 4, 0)
            elif name == "stopSocketBundle":
                assert r0 == receiver + 4
                calls.append([name, receiver_flag(), load(r0 + 4)])
                return
            elif name == "socketD1":
                assert r0 == socket_pointer
                calls.append([name, receiver_flag()])
            elif name == "report":
                caption = bytes(cpu.mem_read(r1, 64)).split(b"\0", 1)[0].decode()
                calls.append([name, r0, caption, receiver_flag()])
            elif name == "multicastCleanup":
                assert r0 == multicast
                calls.append([name, [roster(v) for v in native_rosters]])
                return
            elif name in ("unicast", "multicast"):
                assert r0 == multicast
                calls.append([name, r1])
            else:
                raise AssertionError(name)
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

        cpu.hook_add(UC_HOOK_CODE, code)
        cpu.emu_start(address, stop, count=1200)
        assert cpu.reg_read(UC_ARM_REG_PC) == stop
        assert cpu.reg_read(UC_ARM_REG_SP) == stack
        assert list(cpu.mem_read(receiver + 0x33, 3))[::2] == [63, 99]
        assert {c[1] for c in calls if c[0] == "destroy"} == {
            pool[ptr] for ptr in deleted if ptr in pool
        }
        for index in range(3):
            assert load(0x840000 + index * 0x1000 + 16) == 0xFADEBEEF
        cases.append({
            "input": description, "setup": [initial_flag, rosters, channels, wanted, armed_socket],
            "calls": calls, "rosters": [roster(v) for v in native_rosters],
            "flag": receiver_flag(), "socket_count": load(receiver + 8),
            "return": cpu.reg_read(UC_ARM_REG_R0) if task.endswith("remove_external") else None,
        })

    return {
        **original, "boundaries": verified, "external_vtable_address_point": address_point,
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--task", default=TASK, choices=tuple(SCENARIOS))
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
