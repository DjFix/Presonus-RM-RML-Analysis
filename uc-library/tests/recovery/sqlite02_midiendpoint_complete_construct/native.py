"""Execute sealed MidiEndpoint ARM ranges and their bounded local providers."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP,
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
)

PAGE = 4096
BASE = 0x71000000
(RECEIVER, STACK, STOP, ITEMS, NEW_ITEMS, OBJECTS, CALLBACKS, INFO) = range(BASE, BASE + 8 * PAGE, PAGE)
ENDPOINT = "_ZN8Presonus2UC12MidiEndpoint"
VECTOR = "_ZN4Core6VectorIPN8Presonus2UC14MidiConnectionEE"
CONNECTION = "_ZN8Presonus2UC14MidiConnection"
HELPERS = (ENDPOINT + "C2Ev", "_ZN4Core13CStringBufferILi32EEC1EPKc", VECTOR + "6resizeEi",
           VECTOR + "D1Ev", CONNECTION + "C2Ev", CONNECTION + "7deliverERKNS0_9MidiEventE",
           "__divsi3", "__aeabi_idivmod")
CASES = {
    "complete_construct": [0, 1],
    "base_construct": [0, 1],
    "complete_destroy": [0, 1],
    "base_destroy": [0, 1],
    "deleting_destroy": [0, 1],
    "get_info": [0, 1, 2],
    "find_connection_for_handler": [0, 1, 2, 3, 4],
    "send_from": [0, 1, 2, 3],
    "add_connection": [0, 1, 2, 3],
    "remove_connection": [0, 1, 2, 3, 4],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Image:
    def __init__(self, origin):
        self.raw = Path(origin["elf_path"]).read_bytes()
        assert sha(self.raw) == origin["elf"]
        self.elf = ELFFile(io.BytesIO(self.raw))
        self.symtab = self.elf.get_section_by_name(".symtab")
        self.symbols = {name: self.range(name) for name in HELPERS}
        reloc = self.elf.get_section_by_name(".rel.plt")
        dyn = self.elf.get_section(reloc["sh_link"])
        plt = self.elf.get_section_by_name(".plt")["sh_addr"]
        self.imports = {dyn.get_symbol(row["r_info_sym"]).name: plt + 20 + 12 * i
                        for i, row in enumerate(reloc.iter_relocations())}

    def symbol(self, name):
        symbol, = self.symtab.get_symbol_by_name(name)
        return symbol

    def range(self, name):
        symbol = self.symbol(name)
        section_id = symbol["st_shndx"]
        section = self.elf.get_section(section_id)
        address, size = symbol["st_value"], symbol["st_size"]
        start = address - section["sh_addr"]
        assert 0 <= start <= start + size <= section["sh_size"]
        offset = section["sh_offset"] + start
        assert offset + size <= len(self.raw)
        body = self.raw[offset:offset + size]
        return {"address": address, "size": size, "file_offset": offset, "section": section_id,
                "section_name": section.name, "range_sha256": sha(body), "range_hex": body.hex()}

    def map(self, uc):
        load = [s for s in self.elf.iter_segments() if s["p_type"] == "PT_LOAD"]
        low = min(s["p_vaddr"] for s in load) & -PAGE
        high = (max(s["p_vaddr"] + s["p_memsz"] for s in load) + PAGE - 1) & -PAGE
        uc.mem_map(low, high - low)
        for segment in load:
            uc.mem_write(segment["p_vaddr"], segment.data())


def word(uc, address, signed=False):
    return int.from_bytes(uc.mem_read(address, 4), "little", signed=signed)


def put(uc, address, value):
    uc.mem_write(address, struct.pack("<I", value & 0xffffffff))


def invoke(uc, address, receiver, argument=0):
    for reg, value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, argument),
                       (UC_ARM_REG_SP, STACK + PAGE // 2), (UC_ARM_REG_LR, STOP)):
        uc.reg_write(reg, value)
    uc.emu_start(address, STOP, count=3000)
    assert uc.reg_read(UC_ARM_REG_PC) == STOP
    assert uc.reg_read(UC_ARM_REG_SP) == STACK + PAGE // 2
    return uc.reg_read(UC_ARM_REG_R0)


def observe(image, original, operation, case):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    image.map(uc)
    for address in range(BASE, BASE + 8 * PAGE, PAGE):
        uc.mem_map(address, PAGE)
    if case:
        uc.mem_write(RECEIVER, b"\xa5" * 0x68)
    connections = {index: OBJECTS + index * 0x20 for index in (1, 2, 3)}
    handlers = {index: OBJECTS + 0x100 + index * 0x20 for index in (1, 3)}
    callback = {"type": CALLBACKS, "connect": CALLBACKS + 4, "event": CALLBACKS + 8}
    vtable = CALLBACKS + 0x100
    handler_vtable = CALLBACKS + 0x200
    put(uc, vtable + 8, callback["type"])
    put(uc, vtable + 0x2c, callback["connect"])
    put(uc, handler_vtable, callback["event"])
    for addr in handlers.values():
        put(uc, addr, handler_vtable)

    addr = original["address"]
    allowed = [original, *image.symbols.values()]
    imports = {image.imports[key]: key for key in ("_Znaj", "_ZdaPv", "_ZdlPv")}
    writes, calls = [], []
    dead = set()
    tracking = False

    def roster():
        count, items = word(uc, RECEIVER + 0x5c), word(uc, RECEIVER + 0x58)
        ids = {pointer: index for index, pointer in connections.items()}
        return [ids[word(uc, items + 4 * i)] for i in range(count)]

    def handle(machine, pc, size, _):
        r0 = machine.reg_read(UC_ARM_REG_R0)
        r1 = machine.reg_read(UC_ARM_REG_R1)
        if pc in imports:
            meaning = imports[pc]
            if meaning == "_Znaj":
                assert tracking and operation == "add_connection" and r0 in (20, 40)
                calls.append(["allocate", r0 // 4])
                machine.reg_write(UC_ARM_REG_R0, 0 if case == 3 else NEW_ITEMS)
            else:
                key = "receiver" if meaning == "_ZdlPv" else "vector"
                assert r0 == RECEIVER if key == "receiver" else r0 in (ITEMS, NEW_ITEMS)
                dead.add(r0)
                machine.mem_unmap(r0, PAGE)
                if tracking:
                    calls.append(["release", key])
        elif pc == callback["type"]:
            assert r0 == RECEIVER
            calls.append(["type"])
            machine.reg_write(UC_ARM_REG_R0, (0, 13, -17)[case] & 0xffffffff)
        elif pc == callback["connect"]:
            assert r0 == RECEIVER
            connection, = [i for i, pointer in connections.items() if pointer == r1]
            calls.append(["connect", connection, machine.reg_read(UC_ARM_REG_R2), roster()])
        elif pc == callback["event"]:
            assert r1 == INFO and word(machine, INFO + 4) == 0x903c7f
            handler, = [i for i, pointer in handlers.items() if pointer == r0]
            calls.append(["event", handler])
        else:
            assert any(a["address"] <= pc < a["address"] + a["size"] for a in allowed), hex(pc)
            return
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    def on_write(machine, kind, address, size, value, _):
        if tracking and not STACK <= address < STACK + PAGE:
            writes.append([address, size, value & ((1 << (size * 8)) - 1)])

    uc.hook_add(UC_HOOK_CODE, handle)
    uc.hook_add(UC_HOOK_MEM_WRITE, on_write)
    if operation.endswith("construct"):
        tracking = True
        invoke(uc, addr, RECEIVER)
        assert word(uc, RECEIVER) == image.symbol("_ZTVN8Presonus2UC12MidiEndpointE")["st_value"] + 8
        result = [word(uc, RECEIVER + offset) for offset in range(0x44, 0x54, 4)]
        assert result[1::2] == [0, 0]
        return {"case": case, "result": [uc.mem_read(RECEIVER + 4, 1)[0],
                 uc.mem_read(RECEIVER + 0x24, 1)[0], result[0], result[2],
                 word(uc, RECEIVER + 0x5c), word(uc, RECEIVER + 0x60),
                 word(uc, RECEIVER + 0x64)], "calls": calls, "writes": writes}

    invoke(uc, image.symbols[ENDPOINT + "C2Ev"]["address"], RECEIVER)
    if not operation.endswith("destroy"):
        put(uc, RECEIVER, vtable)
    for index, pointer in connections.items():
        invoke(uc, image.symbols[CONNECTION + "C2Ev"]["address"], pointer)
        # First and third connections share handler identity for the search.
        handler = handlers.get(index, 0) if operation == "send_from" else handlers[1] if index != 2 else 0
        put(uc, pointer + 4, handler)
    roster_cases = {
        "find_connection_for_handler": [[], [2, 3], [2, 1, 3], [2, 1], [1, 3]],
        "send_from": [[], [2, 1, 3], [3, 1], [2]],
        "add_connection": [[], [2], [1, 2, 1, 2, 1], [2, 1, 2, 1, 2]],
        "remove_connection": [[], [2, 3], [2, 1, 3], [1, 2, 1], [2, 1]],
    }
    entries = roster_cases.get(operation, [[], [2, 1]])[case] if operation != "get_info" else []
    if entries:
        put(uc, RECEIVER + 0x58, ITEMS)
        put(uc, RECEIVER + 0x5c, len(entries))
        put(uc, RECEIVER + 0x60, 5)
        for index, item in enumerate(entries):
            put(uc, ITEMS + 4 * index, connections[item])

    if operation == "get_info":
        names = [(b"", b""), (b"Input", b"Output"), (b"Q" * 31, b"Secondary")][case]
        for offset, name in zip((4, 0x24), names):
            uc.mem_write(RECEIVER + offset, name + b"\0")
        put(uc, RECEIVER + 0x44, (0, 17, -2147483648)[case])
        put(uc, RECEIVER + 0x4c, (0, -31, 2147483647)[case])
        uc.mem_write(INFO, b"\x35" * 24)
    if operation == "send_from":
        put(uc, INFO, 20)
        put(uc, INFO + 4, 0x903c7f)
    argument = {"get_info": INFO, "send_from": INFO,
                "find_connection_for_handler": [handlers[1], handlers[1], handlers[1], handlers[3], 0][case]
                if operation == "find_connection_for_handler" else 0,
                "add_connection": connections[3], "remove_connection": connections[1]}.get(operation, 0)
    tracking = True
    ret = invoke(uc, addr, RECEIVER, argument)
    if operation.endswith("destroy"):
        assert (RECEIVER in dead) == (operation == "deleting_destroy")
        assert (ITEMS in dead) == bool(entries)
        assert all(word(uc, obj) for obj in connections.values())
        result = []
    elif operation == "get_info":
        lengths = [len(n) for n in names]
        pointers = [word(uc, INFO + off) for off in (16, 20)]
        assert pointers == [RECEIVER + 4, RECEIVER + 0x24]
        result = [*(word(uc, INFO + off, signed=True) for off in (0, 4, 8, 12)),
                  *(bytes(uc.mem_read(pointer, length)).decode() for pointer, length in zip(pointers, lengths))]
    elif operation == "find_connection_for_handler":
        result = {0: 0, **{v: k for k, v in connections.items()}}[ret]
        assert not writes
    elif operation == "send_from":
        result = ret
        assert ret in (0, 1) and not writes
    else:
        result = roster()
    return {"case": case, "result": result, "calls": calls, "writes": writes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text())
    operation = packet["task"]["id"].removeprefix("sqlite02_midiendpoint_")
    value = []
    for entry in packet["originals"]:
        original = entry["original"]
        image = Image(original)
        assert image.range(original["mangled"]) == {k: original[k] for k in image.range(original["mangled"])}
        rows = [observe(image, original, operation, case) for case in CASES[operation]]
        value.append({"original": original, "cases": rows, "executed_provider_ranges": list(image.symbols.values())})
    if args.generate:
        args.fixture.write_text(json.dumps(value, indent=2) + "\n")
    else:
        assert json.loads(args.fixture.read_text()) == value
    print(f"ARM cases: {sum(len(origin['cases']) for origin in value)}")


if __name__ == "__main__":
    main()
