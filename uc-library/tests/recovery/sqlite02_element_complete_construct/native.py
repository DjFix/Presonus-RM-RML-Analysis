"""Execute native UC Element app ranges with pinned CCL provider observations."""
import argparse
import ctypes
from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_SP)

PAGE = 0x1000
TREE = 0x1000000
HEAP = 0x1100000
STACK = 0x1200000
STOP = 0x1300000
NAME = STOP + PAGE
PREFIX = "_ZN8Presonus2UC7Element"
CONST_PREFIX = "_ZNK8Presonus2UC7Element"
SUFFIX = {
    "complete_construct": "C1ERKNS0_11MetaElementE",
    "base_construct": "C2ERKNS0_11MetaElementE",
    "complete_destroy": "D1Ev",
    "base_destroy": "D2Ev",
    "deleting_destroy": "D0Ev",
    "is_empty": "7isEmptyEv",
    "get_meta_element": "14getMetaElementEv",
    "get_index": "8getIndexEPKS1_",
    "add_child": "8addChildEPS1_",
    "find_child": "9findChildEPKc",
}
LIBC = ctypes.CDLL(None)
LIBC.strcmp.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
LIBC.strcmp.restype = ctypes.c_int

CASES = {
    "complete_construct": [[0], [1]],
    "base_construct": [[0], [1]],
    "complete_destroy": [[0], [1], [6]],
    "base_destroy": [[0], [1], [6]],
    "deleting_destroy": [[0], [1], [6]],
    "is_empty": [[0], [1], [6]],
    "get_meta_element": [[0], [1]],
    "get_index": [[0, -1], [0, 0], [3, -1], [3, 0], [3, 1], [3, 2], [3, 3]],
    "add_child": [[0, 0], [1, 0], [5, 0], [0, 1], [5, 1]],
    "find_child": [[0, None], [0, ""], [4, None], [4, ""], [4, "alpha"],
                   [4, "Alpha"], [4, "ALPHA"], [4, "missing"],
                   [4, "x" * 63], [4, "x" * 64]],
}
NAMES = ["", "alpha", "alpha", "x" * 63]


def provider(exe, *args):
    return subprocess.check_output([str(exe.resolve()), *map(str, args)], text=True).split()


def digest(data):
    return sha256(data).hexdigest()


def execute(original, task, firmware_root, exe):
    path = firmware_root / original["elf_path"]
    raw = path.read_bytes()
    assert digest(raw) == original["elf"]
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        symbol_table = elf.get_section_by_name(".symtab")
        symbols = {symbol.name: symbol for symbol in symbol_table.iter_symbols()}

        def bind(name):
            symbol = symbols[name]
            index = symbol["st_shndx"]
            section = elf.get_section(index)
            address, size = symbol["st_value"], symbol["st_size"]
            offset = section["sh_offset"] + address - section["sh_addr"]
            data = raw[offset:offset + size]
            return {"mangled": name, "address": address, "size": size,
                    "section": index, "section_name": section.name,
                    "file_offset": offset, "range_sha256": digest(data),
                    "range_hex": data.hex()}

        target = bind(original["mangled"])
        assert all(original[key] == value for key, value in target.items())
        ctor = bind(PREFIX + SUFFIX["complete_construct"])
        d0 = bind(PREFIX + SUFFIX["deleting_destroy"])
        adopt = bind(PREFIX + SUFFIX["add_child"])
        unknown = bind("_ZN8Presonus2UC11MetaElement7UnknownEv")
        vector = "_ZN4Core6VectorIPN8Presonus2UC7ElementEE"
        resize = bind(vector + "6resizeEi")
        vector_d1 = bind(vector + "D1Ev")
        string_ctor = bind("_ZN4Core13CStringBufferILi64EEC1EPKc")
        vtable = bind("_ZTVN8Presonus2UC7ElementE")
        dispatch = vtable["address"] + 8
        assert struct.unpack_from("<I", bytes.fromhex(vtable["range_hex"]), 12)[0] == d0["address"]
        relocations = elf.get_section_by_name(".rel.plt")
        plt = elf.get_section_by_name(".plt")
        dynsym = elf.get_section(relocations["sh_link"])
        plt_entries = {dynsym.get_symbol(relocation["r_info_sym"]).name:
                       plt["sh_addr"] + 20 + 12 * index
                       for index, relocation in enumerate(relocations.iter_relocations())}
        delete = plt_entries["_ZdlPv"]
        guard_acquire = plt_entries["__cxa_guard_acquire"]
        guard_release = plt_entries["__cxa_guard_release"]
        strcmp = plt_entries["strcmp"]
        unknown_storage = symbols["_ZZN8Presonus2UC11MetaElement7UnknownEvE18unknownMetaElement"]
        unknown_address = unknown_storage["st_value"]
        metadata_size = unknown_storage["st_size"]
        segments = [(seg["p_vaddr"], seg.data(), seg["p_memsz"])
                    for seg in elf.iter_segments() if seg["p_type"] == "PT_LOAD"]

    cases = []
    for inputs in CASES[task]:
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        image_end = max(address + n for address, _, n in segments)
        uc.mem_map(0, (image_end + PAGE - 1) & -PAGE)
        for address, data, _ in segments:
            uc.mem_write(address, data)
        for address in [STACK, STOP, NAME, TREE, *[TREE + PAGE * n for n in range(1, 8)]]:
            uc.mem_map(address, PAGE)
        names = {TREE + PAGE * n: n for n in range(8)}
        live_nodes = set(names)
        children_storage = {}
        sequence = 0
        armed = False
        writes, calls, freed, pcs = [], [], [], []
        allowed = [unknown, ctor, adopt, target, d0]
        failing = False

        def load(address):
            return struct.unpack("<I", uc.mem_read(address, 4))[0]

        def store(address, value):
            uc.mem_write(address, struct.pack("<I", value & 0xffffffff))

        def read_string(address):
            return bytes(uc.mem_read(address, 64)).split(b"\0", 1)[0]

        def ret(value):
            uc.reg_write(UC_ARM_REG_R0, value)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

        def call(body, x=0, y=0):
            uc.reg_write(UC_ARM_REG_SP, STACK + PAGE - 16)
            uc.reg_write(UC_ARM_REG_LR, STOP)
            uc.reg_write(UC_ARM_REG_R0, x)
            uc.reg_write(UC_ARM_REG_R1, y)
            uc.emu_start(body["address"], STOP, count=10000)
            assert uc.reg_read(UC_ARM_REG_PC) == STOP
            return uc.reg_read(UC_ARM_REG_R0)

        def event(*event_data):
            if armed:
                calls.append(list(event_data))

        def on_code(machine, address, size, _):
            nonlocal sequence
            x = machine.reg_read(UC_ARM_REG_R0)
            y = machine.reg_read(UC_ARM_REG_R1)
            if address == guard_acquire:
                assert not armed
                ret(1)
            elif address == guard_release:
                assert not armed
                store(x, 1)
                ret(0)
            elif address == string_ctor["address"]:
                assert y == 0 and x - 4 in names
                empty, = provider(exe, "provider-name")
                assert empty == "0"
                uc.mem_write(x, b"\0")
                event("pinned CString64 default", names[x - 4])
                ret(x)
            elif address == resize["address"]:
                node = x - 0x4c
                assert node in live_nodes
                old_count = load(node + 0x54)
                old_cap = load(node + 0x58)
                if armed and task == "add_child":
                    assert load(TREE + PAGE * (old_count + 1) + 0x44) == TREE
                    event("parent set before vector resize", old_count)
                if failing and y > 0:
                    event("native resize failure boundary", y)
                    ret(0)
                    return
                capacity, = map(int, provider(exe, "provider-capacity", old_count, y))
                if capacity != old_cap:
                    prior = children_storage.pop(node, 0)
                    sequence += 1
                    block = HEAP + sequence * PAGE
                    uc.mem_map(block, PAGE)
                    if prior:
                        uc.mem_write(block, bytes(uc.mem_read(prior, 4 * old_count)))
                        uc.mem_unmap(prior, PAGE)
                    children_storage[node] = block
                    store(node + 0x50, block)
                    store(node + 0x58, capacity)
                event("pinned Vector resize", names[node], old_cap, capacity)
                ret(1)
            elif address == vector_d1["address"]:
                node = x - 0x4c
                assert node in live_nodes
                prior = children_storage.pop(node, 0)
                if prior:
                    uc.mem_unmap(prior, PAGE)
                store(node + 0x50, 0)
                store(node + 0x54, 0)
                store(node + 0x58, 0)
                event("Vector storage release", names[node], bool(prior))
                ret(x)
            elif address == delete:
                assert x in live_nodes and (x != TREE or task == "deleting_destroy")
                live_nodes.remove(x)
                freed.append(names[x])
                uc.mem_unmap(x, PAGE)
                ret(x)
            elif address == strcmp:
                assert x - 4 in live_nodes
                lhs, rhs = read_string(x), read_string(y)
                event("strcmp", names[x - 4], lhs.decode(), rhs.decode())
                ret(LIBC.strcmp(lhs, rhs) & 0xffffffff)
            else:
                assert any(body["address"] <= address < body["address"] + body["size"]
                           for body in allowed), hex(address)
                if armed:
                    pcs.append(address)
                    if address == d0["address"] and x != TREE:
                        event("original Element D0", names[x])

        def on_write(_, _kind, address, size, value, _aux):
            if not armed or STACK <= address < STACK + PAGE:
                return
            page = address & -PAGE
            assert page in live_nodes or page in children_storage.values(), hex(address)
            logical = names.get(page, "roster")
            value = names.get(value, value) if page not in live_nodes or address - page == 0x44 else value
            writes.append([logical, address - page, size, value])

        uc.hook_add(UC_HOOK_CODE, on_code)
        uc.hook_add(UC_HOOK_MEM_WRITE, on_write)
        meta = call(unknown)
        assert meta == unknown_address and metadata_size == 8
        # An independent byte copy of the original app-initialized descriptor.
        alternate = NAME + 0x100
        metadata = bytes(uc.mem_read(meta, metadata_size))
        uc.mem_write(alternate, metadata)
        selected = (meta, alternate)[inputs[0]] if task in (
            "complete_construct", "base_construct", "get_meta_element") else meta

        if task in ("complete_construct", "base_construct"):
            armed = True
            assert call(target, TREE, selected) == TREE
            assert load(TREE) == dispatch and load(TREE + 0x48) == selected
            output = [load(TREE + 0x44), load(TREE + 0x54), load(TREE + 0x58),
                      read_string(TREE + 4).decode(), inputs[0]]
        else:
            call(ctor, TREE, selected)
            count = 0 if task == "get_meta_element" else inputs[0]
            if task == "is_empty":
                uc.mem_write(TREE + 4, b"parent\0")
            for n in range(count + int(task == "add_child")):
                child = TREE + PAGE * (n + 1)
                call(ctor, child, meta)
                if task == "find_child":
                    uc.mem_write(child + 4, NAMES[n].encode() + b"\0")
                if n < count:
                    call(adopt, TREE, child)
            before = bytes(uc.mem_read(TREE, 96))
            second_argument = 0
            if task == "get_index":
                second_argument = (TREE + PAGE * (inputs[1] + 1)
                                   if inputs[1] >= 0 else 0)
                if inputs[1] >= count and inputs[1] >= 0:
                    call(ctor, second_argument, meta)
            elif task == "find_child" and inputs[1] is not None:
                uc.mem_write(NAME, inputs[1].encode() + b"\0")
                second_argument = NAME
            elif task == "add_child":
                second_argument = TREE + PAGE * (count + 1)
                failing = bool(inputs[1])
            armed = True
            result = call(target, TREE, second_argument)
            if task.endswith("destroy"):
                output = {"free": freed, "retained": TREE in live_nodes,
                          "receiver_vector_released": TREE not in children_storage}
                assert load(meta) == struct.unpack("<I", metadata[:4])[0]
            elif task == "add_child":
                output = [load(TREE + 0x54), load(TREE + 0x58),
                          load(second_argument + 0x44) == TREE,
                          [names[load(load(TREE + 0x50) + 4 * n)]
                           for n in range(load(TREE + 0x54))]]
            else:
                assert bytes(uc.mem_read(TREE, 96)) == before and not writes
                if task == "get_meta_element":
                    assert result == selected
                    output = inputs[0]
                elif task == "get_index":
                    output = struct.unpack("<i", struct.pack("<I", result))[0]
                elif task == "find_child":
                    output = names[result] if result else 0
                else:
                    output = result
        cases.append({"inputs": inputs, "output": output, "native_calls": calls,
                      "native_writes": writes, "executed_pcs": pcs})

    support = {body["mangled"]: body for body in
               (ctor, d0, adopt, unknown, resize, vector_d1, string_ctor, vtable)}
    return {"elf_sha256": original["elf"], "firmware": original["firmware"],
            "role": original["role"], "target": target, "support": support,
            "runtime_plt": {"strcmp": strcmp, "operator_delete": delete,
                            "guard_acquire": guard_acquire, "guard_release": guard_release},
            "cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("context", type=Path)
    parser.add_argument("firmware_root", type=Path)
    parser.add_argument("executable", type=Path)
    args = parser.parse_args()
    contract = json.loads(args.context.read_text())
    task = contract["task"]["id"].removeprefix("sqlite02_element_")
    print(json.dumps([execute(row["original"], task, args.firmware_root, args.executable)
                      for row in contract["originals"]], indent=2))


if __name__ == "__main__":
    main()
