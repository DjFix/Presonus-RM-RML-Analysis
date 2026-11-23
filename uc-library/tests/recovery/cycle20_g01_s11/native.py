"""Replay CS18 DAW controller routing and its real local dispatch offline."""
import argparse
import hashlib
import json
from pathlib import Path
from struct import pack, unpack

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR as LR, UC_ARM_REG_PC as PC, UC_ARM_REG_R0 as R0,
    UC_ARM_REG_R1 as R1, UC_ARM_REG_R2 as R2, UC_ARM_REG_R3 as R3,
    UC_ARM_REG_SP as SP,
)

BASE, STACK, STOP = (0x3000000, 0x4000000, 0x5000000)
RECEIVER, ARRAY, PAGES, CONTROLLER, PREVIOUS = (
    BASE + offset for offset in (0, 0x1000, 0x2000, 0x5000, 0x6000)
)
CASES = [(count, enabled) for count in (0, 1, 3) for enabled in (False, True)]
FX = "_ZN8Presonus7Surface18DawFxPageComponent20setMappingControllerEPNS_18IMappingControllerE"
RADIO = "_ZN8Presonus7Surface16MappingComponent13setRadioGroupEiiib"
LOOKUP = 0x11ACF0


def sha(data):
    return hashlib.sha256(data).hexdigest()


def capture(elf_path, contract_path):
    contract = json.loads(contract_path.read_text())
    with elf_path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
        assert digest == contract["elf"]["sha256"]
        stream.seek(0)
        elf = ELFFile(stream)
        segments = [(s["p_vaddr"], s["p_memsz"], s.data())
                    for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
        symbols = elf.get_section_by_name(".symtab")

        def exact(name, expected=None):
            matches = symbols.get_symbol_by_name(name)
            assert len(matches) == 1
            row = matches[0]
            address, size, index = (row[k] for k in ("st_value", "st_size", "st_shndx"))
            section = elf.get_section(index)
            relative = address - section["sh_addr"]
            assert 0 <= relative and relative + size <= section["sh_size"]
            offset = section["sh_offset"] + relative
            stream.seek(offset)
            body = stream.read(size)
            observed = dict(mangled=name, address=address, size=size, section=section.name,
                            file_offset=offset, sha256=sha(body))
            assert expected is None or observed == expected, observed
            return observed, body

        target, body = exact(contract["exact_target"]["mangled"], contract["exact_target"])
        fx, radio = (contract["real_original_interface_dispatch"][i] for i in (0, 3))
        ranges = [target]
        for adapter in (fx, radio):
            for kind in ("actual_vtable", "thunk"):
                expected = adapter[kind]
                row, data = exact(expected["mangled"], expected)
                if kind == "actual_vtable":
                    slot = adapter["relative_address_point_index"] + adapter["slot_relative_offset"]
                    assert unpack("<I", data[slot:slot + 4])[0] == adapter["thunk"]["address"]
                ranges.append(row)
        implementations = [exact(symbol)[0] for symbol in (FX, RADIO)]
        ranges.extend(implementations)

    def point(adapter):
        return adapter["actual_vtable"]["address"] + adapter["relative_address_point_index"]

    cases = []
    first = min(a for a, _, _ in segments) & ~4095
    end = max(a + length for a, length, _ in segments)
    for count, enabled in CASES:
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        uc.mem_map(first, (end - first + 4095) & ~4095)
        for address, _, data in segments:
            uc.mem_write(address, data)
        for area in (BASE, STACK, STOP):
            uc.mem_map(area, 0x10000)
        start = target["address"]
        assert bytes(uc.mem_read(start, len(body))) == body

        def put(address, value):
            uc.mem_write(address, pack("<I", value))

        def get(address):
            return unpack("<I", uc.mem_read(address, 4))[0]

        incoming = CONTROLLER if enabled else 0
        put(RECEIVER + 8, PREVIOUS)
        put(RECEIVER + 0x18, ARRAY)
        put(RECEIVER + 0x1C, count)
        put(CONTROLLER, point(radio))
        pages = [PAGES + i * 0x200 for i in range(count)]
        for i, page in enumerate(pages):
            put(ARRAY + i * 4, page + 176)
            put(page + 176, point(fx))
            put(page + 0xBC, PREVIOUS)

        trace = []
        def code(machine, address, size, _):
            if address == fx["thunk"]["address"]:
                page = machine.reg_read(R0) - 176
                value = machine.reg_read(R1)
                assert get(RECEIVER + 8) == incoming
                trace.append(["page", pages.index(page), int(value == CONTROLLER)])
                assert value == incoming
            elif address == radio["thunk"]["address"]:
                assert machine.reg_read(R0) == get(RECEIVER + 8) == CONTROLLER
                assert all(get(page + 0xBC) == incoming for page in pages)
                trace.append(["radio", machine.reg_read(R1), machine.reg_read(R2),
                              machine.reg_read(R3), get(machine.reg_read(SP))])
            elif address == LOOKUP:
                assert machine.reg_read(R0) == CONTROLLER - 132
                trace.append(["lookup", machine.reg_read(R1)])
                machine.reg_write(R0, 0)
                machine.reg_write(PC, machine.reg_read(LR))
            else:
                assert any(row["address"] <= address < row["address"] + row["size"]
                           for row in ranges if row["section"] == ".text"), hex(address)

        writes = []
        def write(machine, access, address, size, value, _):
            if address == RECEIVER + 8 or any(address == p + 0xBC for p in pages):
                assert size == 4
                writes.append([address - RECEIVER, value == CONTROLLER])

        uc.hook_add(UC_HOOK_CODE, code)
        # Thunks are expected dispatch entries, and their bodies run normally.
        uc.hook_add(UC_HOOK_MEM_WRITE, write)
        for register, value in ((R0, RECEIVER), (R1, incoming), (SP, STACK + 0x8000), (LR, STOP)):
            uc.reg_write(register, value)
        uc.emu_start(start, STOP, count=1600)
        assert uc.reg_read(PC) == STOP
        assert get(RECEIVER + 8) == incoming
        assert [get(p + 0xBC) for p in pages] == [incoming] * count
        assert writes == [[8, enabled]] + [[p + 0xBC - RECEIVER, enabled] for p in pages]
        assert trace == ([["page", i, int(enabled)] for i in range(count)] +
                         ([["radio", 34, 34, 37, 0]] +
                          [["lookup", tag] for tag in range(34, 38)] if enabled else []))
        cases.append(dict(page_count=count, enabled=enabled, trace=trace, writes=writes))
    return dict(elf_sha256=digest, contract_sha256=sha(contract_path.read_bytes()),
                ranges=ranges, cases=cases)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path)
    parser.add_argument("contract", type=Path)
    args = parser.parse_args()
    print(json.dumps(capture(args.elf, args.contract), indent=2))
