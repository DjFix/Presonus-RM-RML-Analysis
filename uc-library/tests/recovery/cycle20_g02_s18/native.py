"""Run exact ARM indicator methods and compiler helpers at verified provider boundaries."""
import hashlib
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_LR as LR, UC_ARM_REG_PC as PC, UC_ARM_REG_R0 as R0,
    UC_ARM_REG_R1 as R1, UC_ARM_REG_R2 as R2, UC_ARM_REG_SP as SP,
)

MODE = int(Path(__file__).parent.name[-2:])
QUERY = MODE == 18
SLOT_OFFSET = 0x38 if MODE == 16 else 0x3c
PLAN, REVIEW, *ELFS = map(Path, sys.argv[1:])
targets = json.loads(PLAN.read_text())["targets"]
review = json.loads(REVIEW.read_text())["exact_originals"]
NUMERIC = "_ZN4Core8Portable12NumericParam8setValueEfb"
GET_VALUE = "_ZNK4Core8Portable12NumericParam8getValueEv"
HELPERS = ("__aeabi_fcmpgt", "__aeabi_cfrcmple", "__aeabi_cfcmple", "__cmpsf2") if QUERY else (
    "__aeabi_ui2f", "__aeabi_i2f", "__aeabi_ul2f",
)
OBJ, PARAM, STACK, STOP = 0x21000000, 0x22000000, 0x23000000, 0x24000000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def packed(*values):
    return struct.pack(f"<{len(values)}I", *values)


def observe(target, path):
    identity = target["original_elf_sha256"], target["mangled"]
    [old] = [r for r in review.values() if (r["elf_sha256"], r["original_mangled"]) == identity]
    native_provider = old["true_typed_numeric_provider"]
    with path.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == identity[0]
        stream.seek(0)
        elf = ELFFile(stream)
        symbols = elf.get_section_by_name(".symtab")
        segments = [(s["p_vaddr"], s["p_memsz"], s.data())
                    for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]

        def extent(name):
            symbol, = symbols.get_symbol_by_name(name)
            index = symbol["st_shndx"]
            section = elf.get_section(index)
            start, size = symbol["st_value"], symbol["st_size"]
            offset = start - section["sh_addr"]
            body = section.data()[offset:offset + size]
            assert len(body) == size
            return dict(mangled=name, address=start, size=size, section=section.name,
                        section_index=index, file_offset=section["sh_offset"] + offset,
                        sha256=sha(body))

        original = extent(identity[1])
        assert (original["address"], original["size"], original["section_index"],
                original["sha256"], original["file_offset"]) == (
            target["address"], target["size"], target["section"],
            old["range_sha256"], old["file_offset"])
        table = extent("_ZTVN4Core8Portable12NumericParamE")
        assert (table["address"], table["sha256"]) == (
            native_provider["vtable_elf_address"], native_provider["range_sha256"])
        provider = extent(GET_VALUE if QUERY else NUMERIC)
        assert provider["address"] == native_provider["getValue_elf_address" if QUERY else "setValue_elf_address"]
        helpers = [extent(name) for name in HELPERS]
    vectors = [(x["bound"], x["input_bits"], x["events"]) for x in old["cases"]]
    if QUERY:
        vectors.extend((bound, 0xbf000000, None) for bound in (False, True))
    cases = []
    for bound, value, old_events in vectors:
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        low = min(a for a, _, _ in segments) & ~4095
        top = max(a + n for a, n, _ in segments)
        uc.mem_map(low, (top - low + 4095) & ~4095)
        for address, _, data in segments:
            uc.mem_write(address, data)
        for address in (OBJ, PARAM, STACK, STOP):
            uc.mem_map(address, 4096)
        for row in [original, table, provider, *helpers]:
            assert sha(bytes(uc.mem_read(row["address"], row["size"]))) == row["sha256"]
        uc.mem_write(OBJ, b"\xa5" * 96)
        for place in (0x38, 0x3c):
            uc.mem_write(OBJ + place, packed(PARAM if bound and place == SLOT_OFFSET else 0))
        before = bytes(uc.mem_read(OBJ, 96))
        vptr = table["address"] + 8
        actual, = struct.unpack("<I", uc.mem_read(vptr + native_provider["vtable_slot"], 4))
        assert actual == provider["address"]
        uc.mem_write(PARAM, packed(vptr))
        events, path_trace = [], []

        def on_code(machine, address, _size, _data):
            path_trace.append(address)
            if address == actual:
                assert machine.reg_read(R0) == PARAM and bound
                if QUERY:
                    events.append("actual_NumericParam_getValue_slot")
                    machine.reg_write(R0, value)
                else:
                    assert machine.reg_read(R2) == 0
                    events.append(["actual_NumericParam_setValue_slot", machine.reg_read(R1), False])
                machine.reg_write(PC, machine.reg_read(LR))
            else:
                assert any(row["address"] <= address < row["address"] + row["size"]
                           for row in [original, *helpers]), hex(address)
                if address == helpers[0]["address"]:
                    if QUERY:
                        assert machine.reg_read(R0) == value and machine.reg_read(R1) == 0
                    else:
                        assert machine.reg_read(R0) == value

        for reg, val in ((R0, OBJ), (R1, value if not QUERY else 0),
                         (SP, STACK + 2048), (LR, STOP)):
            uc.reg_write(reg, val)
        uc.hook_add(UC_HOOK_CODE, on_code)
        uc.emu_start(original["address"], STOP, count=500)
        assert uc.reg_read(PC) == STOP and uc.reg_read(SP) == STACK + 2048
        assert bytes(uc.mem_read(OBJ, 96)) == before
        assert (helpers[0]["address"] in path_trace) == bound
        if old_events is not None:
            assert events == ([x for x in old_events if x != "float_compare_ne_zero"] if QUERY
                              else old_events)
        result = uc.reg_read(R0) if QUERY else len(events)
        assert result in (0, 1)
        cases.append(dict(bound=bound, input_bits=value, events=events,
                          result=result, trace=path_trace, receiver_unchanged=True))
    return dict(elf=dict(path=str(path), sha256=identity[0]), target=original,
                vtable=table, virtual_slot=native_provider["vtable_slot"],
                provider=provider, helpers=helpers, cases=cases)


roles = dict(zip(("server", "client"), ELFS, strict=True))
print(json.dumps(dict(originals=[observe(row, roles[row["role"]]) for row in targets]), indent=2))
