#!/usr/bin/env python3
"""Isolated AVB receive flow, original ARM and real sealed helper bodies."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import difflib
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import subprocess

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import arm_const as arm

RECEIVE = "_ZN8Presonus3AVB14AvbManagerBase7receiveERKNS_4NOAA11SysexPacketE"
HELPER = "_ZN8Presonus3AVB14AvbManagerBase15unpackAvbSpiMsgEPhPKhi"
LISTENER = "_ZN8Presonus3AVB11AvbListener6updateEhhh"
TALKER = "_ZN8Presonus3AVB9AvbTalker6updateEhh"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command(argv, log):
    scratch = log.parent / "temp"
    scratch.mkdir(exist_ok=True)
    result = subprocess.run(argv, capture_output=True, text=True, env=dict(os.environ, TMPDIR=str(scratch)))
    log.write_text("TMPDIR " + str(scratch) + "\nCOMMAND " + repr(argv) + "\n" + result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"command exit{result.returncode}: {log}")
    return result.stdout


def oracle(repository, library, output):
    directory = library / "recovered-all/server"
    manifest = json.loads((directory / "manifest.json").read_text())
    binary = repository / manifest["path"]
    raw = binary.read_bytes()
    assert sha(raw) == manifest["sha256"]
    rows = json.loads((directory / "symbols.json").read_text())
    by_mangle = {row["mangled"]: row for row in rows}
    functions = {name: by_mangle[name] for name in (RECEIVE, HELPER, LISTENER, TALKER)}
    with binary.open("rb") as stream:
        elf = ELFFile(stream)
        for row in functions.values():
            section = elf.get_section(int(row["section"]))
            assert section.name == ".text"
            assert int(section["sh_offset"]) + row["address"] - int(section["sh_addr"]) == row["file_offset"]
            assert row["address"] + row["size"] <= int(section["sh_addr"]) + int(section["sh_size"])
    for row in functions.values():
        data = (directory / row["export_path"]).read_bytes()
        assert data == raw[row["file_offset"]:row["file_offset"] + row["size"]]
        assert sha(data) == row["sha256"]
    table = next(row for row in rows if row["demangled"] == "vtable for Presonus::AVB::AvbManagerBase")
    data = (directory / table["export_path"]).read_bytes()
    assert data == raw[table["file_offset"]:table["file_offset"] + table["size"]] and sha(data) == table["sha256"]
    receive_slots = [index for index in range(8, len(data), 4) if struct.unpack_from("<I", data, index)[0] == functions[RECEIVE]["address"]]
    assert receive_slots
    (output / "original-vtable.bin").write_bytes(data)
    machine = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    pages = set()
    with binary.open("rb") as stream:
        for segment in ELFFile(stream).iter_segments():
            if segment["p_type"] != "PT_LOAD":
                continue
            start = int(segment["p_vaddr"])
            end = start + int(segment["p_memsz"])
            for page in range(start & ~4095, (end + 4095) & ~4095, 4096):
                if page not in pages:
                    machine.mem_map(page, 4096)
                    pages.add(page)
            machine.mem_write(start, segment.data())
    obj, packet, notice, vtable = 0x10000000, 0x10001000, 0x10002000, 0x10003000
    listeners, talkers, nodes = 0x10010000, 0x10020000, 0x10030000
    stack, stop, callback_l, callback_t = 0x20000000, 0x30000000, 0x30001000, 0x30002000
    sp = stack + 0xff00
    frame = sp - 88
    machine.mem_map(obj, 0x40000)
    machine.mem_map(stack, 0x10000)
    machine.mem_map(stop, 0x3000)
    machine.mem_write(notice, struct.pack("<I", vtable))
    machine.mem_write(vtable, struct.pack("<II", callback_l, callback_t))
    state = {}
    executed = set()

    def code(uc, address, size, user):
        if address in (callback_l, callback_t):
            kind = "L" if address == callback_l else "T"
            assert uc.reg_read(arm.UC_ARM_REG_R0) == notice
            assert state["update"] == kind and state["update_result"] == 1
            base = listeners if kind == "L" else talkers
            assert uc.reg_read(arm.UC_ARM_REG_R1) == base + state["index"] * 0x100
            state["notices"] += 1
            state["order"] += "N"
            if state["mutate"]:
                uc.mem_write(obj + 4, b"\x6e\x9a")
                uc.mem_write(obj + 0x6c, bytes(4))
                uc.mem_write(obj + 0x74, bytes(4))
                uc.mem_write(obj + 0x80, bytes(4))
            uc.reg_write(arm.UC_ARM_REG_R0, state["callback_return"])
            uc.reg_write(arm.UC_ARM_REG_PC, uc.reg_read(arm.UC_ARM_REG_LR))
            return
        assert any(row["address"] <= address < row["address"] + row["size"] for row in functions.values()), f"unapproved execution {address:#x}"
        executed.add(address)
        if address == functions[HELPER]["address"]:
            assert tuple(uc.reg_read(getattr(arm, f"UC_ARM_REG_R{index}")) for index in range(4)) == (obj, frame, packet + 8, state["length"])
            state["helper_calls"] += 1
            state["order"] += "H"
        elif address == 0xa6cf0:
            state["helper_status"] = uc.reg_read(arm.UC_ARM_REG_R0)
            state["decoded"] = bytes(uc.mem_read(frame, 64))
        elif address in (functions[LISTENER]["address"], functions[TALKER]["address"]):
            kind = "L" if address == functions[LISTENER]["address"] else "T"
            base = listeners if kind == "L" else talkers
            original_this = uc.reg_read(arm.UC_ARM_REG_R0)
            index = (original_this - base) // 0x100
            assert original_this == base + index * 0x100 and 0 <= index < state["counts"][kind]
            assert state["update"] == "-"
            state["update"] = kind
            state["index"] = index
            state["args"] = [uc.reg_read(getattr(arm, f"UC_ARM_REG_R{i}")) for i in (1, 2, 3)]
            if kind == "T":
                state["args"][2] = 0
            state["order"] += "U"
        elif address in (0xa6e20, 0xa6da4):
            state["update_result"] = uc.reg_read(arm.UC_ARM_REG_R0)
            assert state["update_result"] == 1

    def write(uc, access, address, size, value, user):
        if obj <= address and address + size <= obj + 0x90:
            state["object_writes"].append((address - obj, size, value & ((1 << (8 * size)) - 1)))
        else:
            assert stack <= address and address + size <= stack + 0x10000, f"unexpected write {address:#x}"

    machine.hook_add(unicorn.UC_HOOK_CODE, code)
    machine.hook_add(unicorn.UC_HOOK_MEM_WRITE, write)
    counts = Counter()
    fixture = output / "receive-vectors.txt.gz"
    rng = random.Random(0x52454345495645)
    base_packet = bytes((index * 37 ^ index >> 2 ^ 0xa5) & 255 for index in range(256))
    base_scratch = bytes((index * 19 + 0xa5) & 255 for index in range(64))
    with fixture.open("wb") as compressed:
        with gzip.GzipFile(filename="", fileobj=compressed, mode="wb", mtime=0) as zipped:
            def emit(group, length, command_byte, gate=1, listener_ids=(0x12, 0x34, 0x12), talker_ids=(0x56, 0x78, 0x56),
                     payload=None, scratch=base_scratch, prefix=0xa5, callback_return=0, mutate=0, initial_command=0x91, initial_status=0x82):
                content = bytearray(base_packet if payload is None else payload)
                content[1] = command_byte
                packet_storage = bytearray(b"\xa5" * 0x109)
                packet_storage[7] = prefix
                packet_storage[8:0x108] = content
                packet_storage[0x108] = length
                original = bytearray(b"\xa5" * 0x90)
                original[4:6] = bytes([initial_command, initial_status])
                struct.pack_into("<II", original, 0x68, notice, gate)
                struct.pack_into("<I", original, 0x74, nodes + 0x100 if talker_ids else 0)
                struct.pack_into("<I", original, 0x80, nodes if listener_ids else 0)
                machine.mem_write(obj, bytes(original))
                machine.mem_write(packet, bytes(packet_storage))
                model_before = []
                for kind, ids, stream_base, node_base in (("L", listener_ids, listeners, nodes), ("T", talker_ids, talkers, nodes + 0x100)):
                    for index, identifier in enumerate(ids):
                        storage = bytearray(b"\xa5" * 64)
                        storage[0] = identifier
                        if kind == "L":
                            value = 0x1122334455660000 | (identifier << 8) | index
                            struct.pack_into("<QQH", storage, 8, value, ((value << 16) | (0x1000 + index)) & 0xffffffffffffffff, 0x1000 + index)
                            struct.pack_into("<I", storage, 28, 0x80000000 | index)
                        else:
                            struct.pack_into("<I", storage, 8, 0x7fffffff - index)
                        address = stream_base + index * 0x100
                        machine.mem_write(address, bytes(storage))
                        next_ = node_base + (index + 1) * 8 if index + 1 < len(ids) else 0
                        link = struct.pack("<II", address, next_)
                        machine.mem_write(node_base + index * 8, link)
                        model_before += [(address, bytes(storage)), (node_base + index * 8, link)]
                machine.mem_write(frame, scratch)
                state.update(length=length, helper_calls=0, helper_status=0, decoded=scratch, update="-", index=0, args=[0, 0, 0],
                             notices=0, order="", counts={"L": len(listener_ids), "T": len(talker_ids)}, update_result=0,
                             callback_return=callback_return, mutate=mutate, object_writes=[])
                machine.reg_write(arm.UC_ARM_REG_CPSR, 0x10)
                for register in range(13):
                    machine.reg_write(getattr(arm, f"UC_ARM_REG_R{register}"), 0)
                machine.reg_write(arm.UC_ARM_REG_R0, obj)
                machine.reg_write(arm.UC_ARM_REG_R1, packet)
                machine.reg_write(arm.UC_ARM_REG_SP, sp)
                machine.reg_write(arm.UC_ARM_REG_LR, stop)
                machine.emu_start(functions[RECEIVE]["address"], stop, count=10000)
                assert machine.reg_read(arm.UC_ARM_REG_PC) == stop and machine.reg_read(arm.UC_ARM_REG_SP) == sp
                assert bytes(machine.mem_read(packet, len(packet_storage))) == packet_storage
                for address, storage in model_before:
                    assert bytes(machine.mem_read(address, len(storage))) == storage
                expected = bytearray(original)
                ack = bool(gate < 0x80000000 and gate > 0 and length > 1 and command_byte >= 0x23 and command_byte <= 0x2f and (0x1c3f & (1 << (command_byte - 0x23))))
                if ack:
                    expected[4:6] = bytes([command_byte, content[2]])
                    assert state["object_writes"] == [(4, 1, command_byte), (5, 1, content[2])]
                else:
                    assert state["object_writes"] == []
                if state["notices"] and mutate:
                    expected[4:6] = b"\x6e\x9a"
                    struct.pack_into("<I", expected, 0x6c, 0)
                    struct.pack_into("<I", expected, 0x74, 0)
                    struct.pack_into("<I", expected, 0x80, 0)
                assert bytes(machine.mem_read(obj, len(expected))) == expected
                assert state["helper_calls"] <= 1 and state["notices"] <= 1
                assert state["order"] == ("H" if state["helper_calls"] else "") + ("U" if state["update"] != "-" else "") + ("N" if state["notices"] else "")
                expected_gate = struct.unpack_from("<I", expected, 0x6c)[0]
                expected_l = 0 if state["notices"] and mutate else len(listener_ids)
                expected_t = 0 if state["notices"] and mutate else len(talker_ids)
                fields = [f"{gate:08x}", f"{initial_command:x}", f"{initial_status:x}", f"{prefix:x}", f"{length:x}",
                          f"{len(listener_ids):x}", f"{len(talker_ids):x}", bytes(listener_ids).ljust(4, b"\0").hex(), bytes(talker_ids).ljust(4, b"\0").hex(),
                          f"{callback_return:08x}", f"{mutate:x}", bytes(content).hex(), scratch.hex(), f"{expected_gate:08x}",
                          f"{expected[4]:x}", f"{expected[5]:x}", f"{expected_l:x}", f"{expected_t:x}", f"{state['helper_calls']:x}", f"{state['helper_status']:08x}",
                          state["decoded"].hex(), state["update"], f"{state['index']:x}", *[f"{value:x}" for value in state["args"]],
                          f"{state['notices']:x}", f"{machine.reg_read(arm.UC_ARM_REG_R0):08x}"]
                zipped.write((" ".join(fields) + "\n").encode())
                counts[group] += 1
                if state["update"] != "-":
                    counts["listener_notifications" if state["update"] == "L" else "talker_notifications"] += 1
                if ack:
                    counts["acknowledgments"] += 1

            for length in range(256):
                for command_byte in range(256):
                    emit("length_command_grid", length, command_byte)
            print("ARM length/command grid", counts["length_command_grid"], flush=True)

            def notification(command_byte, identifier, first, second, third=0):
                values = [identifier, first, second] + ([third] if command_byte == 0x2a else [])
                result = bytearray(base_packet)
                result[0:2] = bytes([0xf0, command_byte])
                for index, value in enumerate(values):
                    result[2 + 2 * index:4 + 2 * index] = bytes([value >> 4, value & 15])
                length = 3 + 2 * len(values)
                result[length - 1] = 0xf7
                return result, length

            for command_byte in (0x2a, 0x2b):
                for identifier in range(256):
                    arrangements = [(), (identifier,), (identifier ^ 255, identifier), (identifier, identifier), (identifier ^ 255, identifier ^ 127, identifier, identifier)]
                    for pattern in range(5):
                        content, length = notification(command_byte, identifier, (identifier + pattern) & 255, identifier ^ 255, (identifier * 17 + pattern) & 255)
                        for ids in arrangements:
                            emit("valid_notifications", length, command_byte,
                                 listener_ids=ids if command_byte == 0x2a else (0x12, 0x34),
                                 talker_ids=ids if command_byte == 0x2b else (0x56, 0x78), payload=content,
                                 callback_return=(0, 1, 0xffffffff, 0x80000000, 0x7fc00000)[pattern], mutate=pattern & 1)
            print("ARM valid notifications", counts["valid_notifications"], flush=True)
            for gate in (0, 1, 2, 0x7fffffff, 0x80000000, 0xfffffffe, 0xffffffff):
                for length in (0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 64, 65, 255):
                    for command_byte in (0x23, 0x29, 0x2a, 0x2b, 0x2c, 0xff):
                        emit("gate_edges", length, command_byte, gate=gate)
            for command_byte in (0x2a, 0x2b):
                for length in range(13):
                    for scratch in (bytes(64), b"\xff" * 64, b"\xa5" * 64, bytes(rng.getrandbits(8) for _ in range(64))):
                        for mutate in (0, 1):
                            ids = (command_byte, base_packet[2], base_packet[3], ((base_packet[2] << 4) | base_packet[3]) & 255)
                            emit("truncated_known_scratch", length, command_byte, listener_ids=ids, talker_ids=ids,
                                 scratch=scratch, prefix=rng.randrange(256), mutate=mutate, callback_return=rng.getrandbits(32))
            for prefix in range(256):
                emit("length_zero_prefix", 0, 0x2a, prefix=prefix)
            for _ in range(2048):
                content = bytes(rng.getrandbits(8) for _ in range(256))
                emit("random", rng.randrange(256), rng.randrange(256), gate=rng.getrandbits(32),
                     listener_ids=tuple(rng.randrange(256) for _ in range(rng.randrange(5))),
                     talker_ids=tuple(rng.randrange(256) for _ in range(rng.randrange(5))), payload=content,
                     scratch=bytes(rng.getrandbits(8) for _ in range(64)), prefix=rng.randrange(256),
                     callback_return=rng.getrandbits(32), mutate=rng.randrange(2), initial_command=rng.randrange(256), initial_status=rng.randrange(256))
    report = dict(role="server", original_elf_sha256=manifest["sha256"], functions=functions, vtable=table,
                  original_receive_vtable_offsets=receive_slots, cases=dict(counts), fixture_sha256=sha(fixture.read_bytes()),
                  unicorn_version=unicorn.__version__, executed_addresses=sorted(executed),
                  original_field_mapping={"command":4,"status":5,"notice_pointer":104,"signed_gate_word":108,"talker_head":116,"listener_head":128},
                  execution="Original receive/unpack/listenerupdate/talkerupdate bodies only; two explicit notice gateway addresses. No Core/device/clock/firmware programming execution.",
                  scratch="Original64byte frame at callerSP-88 initialized from fixture, packetdata[-1] initialized prefix. Exact decoded64byte intermediate recorded; malformed undefined historical stack behavior not generalized.")
    (output / "arm-oracle.json").write_text(json.dumps(report, indent=2) + "\n")
    return report, fixture


if __name__ == "__main__":
    import sys
    output=Path(sys.argv[1]); output.mkdir(parents=True, exist_ok=True)
    oracle(Path.cwd(), Path.cwd()/"uc-library", output)
