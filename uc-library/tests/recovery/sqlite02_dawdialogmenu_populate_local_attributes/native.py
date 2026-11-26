"""Run exact DialogMenu ARM instructions with instrumented provider and allocator calls."""
import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_SP

PACKETS = Path("temp/recovery-work/sqlite-issued/packet")
TASK = "sqlite02_dawdialogmenu_populate_local_attributes"
CASE_TASKS = {
    "parse": TASK,
    "children": "sqlite02_dawdialogmenu_has_children",
    "separator": "sqlite02_dawdialogmenu_is_separator",
    "D1": "sqlite02_dawdialogmenu_complete_destroy",
    "D2": "sqlite02_dawdialogmenu_base_destroy",
}
ARM_BASE = 0x1000000
STACK = ARM_BASE + 0x40000
RETURN = STACK + 0x1000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def packet(mode):
    return PACKETS / CASE_TASKS[mode] / "CONTEXT.json"


def load_json(path):
    return json.loads(Path(path).read_text())


def observe(row, mode, packet_parse):
    data = Path(row["elf_path"]).read_bytes()
    assert digest(data) == row["elf"]
    elf = ELFFile(io.BytesIO(data))
    symbols = {symbol.name: symbol for symbol in elf.get_section_by_name(".symtab").iter_symbols()}
    evidence_paths = packet_parse["task"]["review"]["evidence"]
    for evidence in evidence_paths:
        assert digest(Path(evidence["path"]).read_bytes()) == evidence["sha256"]
    by_address = {
        item["original"]["address"]: item
        for item in load_json(evidence_paths[2]["path"])["items"]
        if item["original"]["elf"] == row["elf"]
    }
    expected_literals = load_json(evidence_paths[1]["path"])
    ranges = {}
    boundaries = {}
    for addr, item in by_address.items():
        original = item["original"]
        symbol = symbols[original["mangled"]]
        section = elf.get_section(symbol["st_shndx"])
        actual = symbol["st_value"], symbol["st_size"], symbol["st_shndx"]
        assert actual == (addr, original["size"], original["section"])
        offset = section["sh_offset"] + addr - section["sh_addr"]
        assert section.name == ".text" and 0 <= addr - section["sh_addr"] <= section["sh_size"] - actual[1]
        body = data[offset:offset + actual[1]]
        assert digest(body) == original["range_sha256"]
        ranges[original["mangled"]] = dict(original, file_offset=offset)
        for site in item["native_sites"]:
            if site["kind"] != "branch":
                continue
            instruction = struct.unpack_from("<I", body, site["code_offset"])[0]
            assert instruction & 0x0e000000 == 0x0a000000
            signed = ((instruction & 0xffffff) ^ 0x800000) - 0x800000
            target = addr + site["code_offset"] + 8 + signed * 4
            assert target == site["destination"]
            for name in site["names"]:
                if name in symbols and symbols[name]["st_value"]:
                    assert symbols[name]["st_value"] == target
                if name.startswith(("_ZN4Core", "_ZNK4Core", "strcmp", "_Znwj", "_ZdlPv")):
                    boundaries[target] = name

    vm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    segments = [s for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
    start = min(s["p_vaddr"] for s in segments) & ~4095
    stop = (max(s["p_vaddr"] + s["p_memsz"] for s in segments) + 4095) & ~4095
    vm.mem_map(start, stop - start)
    for segment in segments:
        vm.mem_write(segment["p_vaddr"], segment.data())
    vm.mem_map(ARM_BASE, RETURN - ARM_BASE)

    def word(address):
        return struct.unpack("<I", vm.mem_read(address, 4))[0]

    def string(address):
        assert address
        result = bytearray()
        while (value := vm.mem_read(address, 1)[0]) != 0:
            result.append(value)
            address += 1
            assert len(result) < 64
        return result.decode()

    for record in expected_literals:
        if record["elf"] != row["elf"]:
            continue
        address = ranges[record["mangled"]]["address"]
        for literal in record["literals"]:
            site = address + literal["offset"]
            instruction = word(site)
            assert instruction & 0x0f7f0000 == 0x051f0000
            displacement = instruction & 0xfff
            location = site + 8 + (displacement if instruction & 0x800000 else -displacement)
            assert word(location) == literal["address"]
            assert string(literal["address"]) == literal["text"]

    def target(task_mode):
        selected = next(item["original"] for item in load_json(packet(task_mode))["originals"]
                        if item["original"]["elf"] == row["elf"])
        observed = ranges[selected["mangled"]]
        for key in ("address", "size", "section", "file_offset", "range_sha256"):
            assert observed[key] == selected[key]
        return observed

    needed = {kind: target(kind) for kind in CASE_TASKS}
    constructor = next(value for name, value in ranges.items() if name.endswith("C1Ev"))
    child_destroy = needed["D1"]["address"]
    for kind in ("D1", "D2"):
        # Each role must recurse through the complete destructor, even for D2.
        assert any(site["code_offset"] == 80 and site["destination"] == child_destroy
                   for site in by_address[needed[kind]["address"]]["native_sites"]
                   if site["kind"] == "branch")

    def put(address, value):
        vm.mem_write(address, struct.pack("<I", value))

    cases = []
    output = []
    for scenario in range(5):
        cursor = ARM_BASE
        live = set()
        allocated = []
        vectors_destroyed = set()
        provider_objects = {}
        calls = []
        deletes = []

        def allocate(size):
            nonlocal cursor
            address = cursor
            cursor += (size + 63) & ~63
            assert cursor < STACK - 0x1000
            vm.mem_write(address, bytes(size))
            return address

        def attrs(**values):
            address = allocate(4)
            provider_objects[address] = values
            return address

        def text(value):
            if value is None:
                return 0
            raw = value.encode() + b"\0"
            address = allocate(len(raw))
            vm.mem_write(address, raw)
            return address

        def item(title=None, name=None, category=None, sub=0):
            return attrs(title=text(title), name=text(name), category=text(category), subMenu=sub)

        def queue(items):
            address, array = allocate(16), allocate(max(4, 4 * len(items)))
            put(address + 8, array)
            put(address + 12, len(items))
            for index, value in enumerate(items):
                entry = allocate(12)
                put(array + 4 * index, entry)
                put(entry + 4, 5 if value else 1)
                put(entry + 8, value or 7)
            return address

        items = []
        if scenario >= 2:
            items.append(item("-", "first", "category"))
        if scenario >= 3:
            nested = attrs(items=queue([item("", "blank", "more"), item("-x")]))
            items.extend([0, item(), item(".", "parent", sub=nested), item("+", category="category")])
        attributes = attrs(items=queue(items) if scenario else 0)
        root = allocate(36)

        def hook(uc, address, _size, _context):
            if address not in boundaries:
                assert any(x["address"] <= address < x["address"] + x["size"]
                           for x in ranges.values()), hex(address)
                return
            name = boundaries[address]
            r0 = uc.reg_read(UC_ARM_REG_R0)
            r1 = uc.reg_read(UC_ARM_REG_R1)
            result = r0
            if name.startswith("_ZNK4Core"):
                key = string(r1)
                calls.append([name, key])
                result = provider_objects[r0].get(key, 0)
            elif "resize" in name:
                calls.append([name, r1])
                capacity = word(r0 + 12)
                if r1 > capacity:
                    count = word(r0 + 8)
                    capacity = max(r1, capacity + word(r0 + 16))
                    block = allocate(capacity * 4)
                    if count:
                        vm.mem_write(block, bytes(vm.mem_read(word(r0 + 4), count * 4)))
                    put(r0 + 4, block)
                    put(r0 + 12, capacity)
                result = 1
            elif name.endswith("EED1Ev"):
                assert r0 - 16 == root or r0 - 16 in live
                assert r0 - 16 not in vectors_destroyed
                vectors_destroyed.add(r0 - 16)
                calls.append([name, r0 - 16])
            elif name.startswith("_Znwj"):
                assert r0 == 36
                result = allocate(r0)
                live.add(result)
                allocated.append(result)
                calls.append([name, r0, result])
            elif name.startswith("_ZdlPv"):
                assert r0 in vectors_destroyed and r0 in live
                live.remove(r0)
                deletes.append(r0)
                calls.append([name, r0])
            elif name.startswith("strcmp"):
                left, right = string(r0), string(r1)
                assert right == "-"
                calls.append([name, left, right])
                result = ((left > right) - (left < right)) & 0xffffffff
            else:
                raise AssertionError(name)
            uc.reg_write(UC_ARM_REG_R0, result)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

        def execute(address, obj, arg=0):
            vm.reg_write(UC_ARM_REG_R0, obj)
            vm.reg_write(UC_ARM_REG_R1, arg)
            vm.reg_write(UC_ARM_REG_SP, STACK)
            vm.reg_write(UC_ARM_REG_LR, RETURN)
            vm.emu_start(address, RETURN, count=12000)
            assert vm.reg_read(UC_ARM_REG_PC) == RETURN and vm.reg_read(UC_ARM_REG_SP) == STACK
            return vm.reg_read(UC_ARM_REG_R0)

        handle = vm.hook_add(UC_HOOK_CODE, hook)
        execute(constructor["address"], root)
        for _ in range(2 if scenario == 4 else 1):
            execute(needed["parse"]["address"], root, attributes)
        ordered = []
        rendered = []

        def menu_tree(address):
            assert address == root or address in live
            ordered.append(address)
            count = word(address + 24)
            if mode == "parse":
                fields = [string(value) if value else "~" for value in
                          (word(address + field) for field in (0, 4, 8))]
                rendered.append(":".join((str(word(address + 12)), *fields, str(count))))
            elif mode in ("children", "separator"):
                rendered.append(str(execute(needed[mode]["address"], address)))
            block = word(address + 20)
            for index in range(count):
                menu_tree(word(block + index * 4))

        menu_tree(root)
        assert set(ordered) == live | {root}
        if mode in ("D1", "D2"):
            execute(needed[mode]["address"], root)
            assert not live and vectors_destroyed == set(ordered)
            rendered.extend(str(ordered.index(address)) for address in deletes)
        vm.hook_del(handle)
        output.append(f"{scenario}|" + "".join(f"{value}," for value in rendered))
        cases.append(dict(scenario=scenario, receiver=root, tree_addresses=ordered,
                          calls=calls, allocated=allocated, deallocated=deletes,
                          observed=rendered))

    return dict(elf_sha256=row["elf"], firmware=row["firmware"], role=row["role"],
                target=needed[mode], ranges=list(ranges.values()), cases=cases, output=output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=CASE_TASKS)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    parse_context = load_json(packet("parse"))
    rows = [observe(item["original"], args.mode, parse_context)
            for item in load_json(packet(args.mode))["originals"]]
    observation = dict(unicorn=unicorn.__version__, role_observations=rows)
    rendered = json.dumps(observation, indent=2) + "\n"
    if args.record:
        args.fixtures.write_text(rendered)
    else:
        assert args.fixtures.read_text() == rendered
    print(f"{sum(len(row['cases']) for row in rows)} bounded native cases for {args.mode}")


if __name__ == "__main__":
    main()
