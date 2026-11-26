"""ARM application replay with verified ABI call targets and modeled Core boundaries."""

import hashlib
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MANGLED = "_ZN8Presonus7Surface19PageHeaderComponent16updateFocusParamEPN4Core8Portable9ParameterE"
SHA = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
ELF = Path("rootfs/CS18_v13840/home/root/surface")
TABLE = "_ZN8Presonus22AssignmentHandlerTable17getParamFocusInfoERNS_22MixerAssignmentHandler9FocusInfoEPN4Core8Portable9ParameterE"
CAST = "_ZN8Presonus22MixerAssignmentHandler6castToEi"
FOCUS = "_ZN8Presonus7Surface14SLMixerHandler17getParamFocusInfoERNS_22MixerAssignmentHandler9FocusInfoEPN4Core8Portable9ParameterE"
PARAM_ORIGINAL = "_ZN4Core8Portable9Parameter11getOriginalEv"
ALIAS_ORIGINAL = "_ZN4Core8Portable10AliasParam11getOriginalEv"
BIND = "_ZN4Core8Portable10AliasParam11setOriginalEPNS0_9ParameterE"
TEXT = "_ZN4Core8Portable11StringParam10fromStringEPKcb"
GUARD = "_ZGVZN4Core8Portable15StaticSingletonIN8Presonus22AssignmentHandlerTableEE8instanceEvE11theInstance"
INSTANCE = "_ZZN4Core8Portable15StaticSingletonIN8Presonus22AssignmentHandlerTableEE8instanceEvE11theInstance"
HANDLER_VT = "_ZTVN8Presonus7Surface14SLMixerHandlerE"
PARAM_VT = "_ZTVN4Core8Portable9ParameterE"
ALIAS_VT = "_ZTVN4Core8Portable10AliasParamE"
LABEL_VT = "_ZTVN4Core8Portable11StringParamE"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def observe():
    firmware = next(parent / ELF for parent in (ROOT, *ROOT.parents)
                    if (parent / ELF).is_file())
    with firmware.open("rb") as stream:
        assert digest(stream.read()) == SHA
        elf = ELFFile(stream)
        symtab = elf.get_section_by_name(".symtab")
        records = {}
        bodies = {}

        def capture(name):
            matches = symtab.get_symbol_by_name(name)
            assert len(matches) == 1, name
            s = matches[0]
            section = elf.get_section(s["st_shndx"])
            address, size = s["st_value"], s["st_size"]
            delta = address - section["sh_addr"]
            assert 0 <= delta and delta + size <= section["sh_size"]
            data = section.data()[delta:delta + size]
            records[name] = {
                "address": address, "size": size, "section": s["st_shndx"],
                "section_name": section.name, "sha256": digest(data),
                "file_offset": section["sh_offset"] + delta,
            }
            bodies[name] = data

        for name in (MANGLED, TABLE, CAST, FOCUS, PARAM_ORIGINAL, ALIAS_ORIGINAL,
                     BIND, TEXT, HANDLER_VT, PARAM_VT, ALIAS_VT, LABEL_VT):
            capture(name)
        original = records[MANGLED]
        assert original == {
            "address": 592104, "size": 344, "section": 12,
            "section_name": ".text", "file_offset": 559336,
            "sha256": "9c7d4f6368dfe24ed30af80ff25e47d441e02471f0623700424b95f4dd40c4db",
        }
        packet_path = ROOT / "temp/recovery-work/sqlite-issued/packet" / HERE.name / "CONTEXT.json"
        if packet_path.is_file():
            exact = json.loads(packet_path.read_text())["originals"][0]["original"]
            assert exact["range_hex"] == bodies[MANGLED].hex()
        guard = symtab.get_symbol_by_name(GUARD)[0]["st_value"]
        instance = symtab.get_symbol_by_name(INSTANCE)[0]["st_value"]
        literal = 2041456
        section = next(s for s in elf.iter_sections()
                       if s["sh_addr"] <= literal < s["sh_addr"] + s["sh_size"])
        delta = literal - section["sh_addr"]
        assert section.data()[delta:delta + 1] == b"\0"
        literal_offset = section["sh_offset"] + delta

    def address(name):
        return records[name]["address"]

    slots = ((PARAM_VT, 0x0c, PARAM_ORIGINAL), (ALIAS_VT, 0x0c, ALIAS_ORIGINAL),
             (LABEL_VT, 0x74, TEXT), (HANDLER_VT, 0, CAST), (HANDLER_VT, 0x3c, FOCUS))
    for vt, slot, function in slots:
        assert struct.unpack_from("<I", bodies[vt], 8 + slot)[0] == address(function)

    page, focus, label, alias, plain, old, alternate, items, handler, stop = (
        0x400000 + index * 0x100 for index in range(10))
    pointer_name = {0: "-", old: "old", plain: "new", alternate: "alternate"}
    starts = {v: k for k, v in pointer_name.items()}

    def run(parameter, current, response, new_label, has_alias=True, has_label=True,
            initial_label="previous"):
        emu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        mapped = set()

        def map_range(start, size):
            for base in range(start & ~4095, (start + size + 4095) & ~4095, 4096):
                if base not in mapped:
                    emu.mem_map(base, 4096)
                    mapped.add(base)

        for name in (MANGLED, TABLE, CAST, HANDLER_VT, PARAM_VT, ALIAS_VT, LABEL_VT):
            map_range(address(name), len(bodies[name]))
            emu.mem_write(address(name), bodies[name])
        for name in (PARAM_ORIGINAL, ALIAS_ORIGINAL, BIND, FOCUS, TEXT):
            map_range(address(name), 4)
        map_range(page, 0x3000)
        map_range(guard, instance + 8 - guard)
        map_range(literal, 1)
        emu.mem_write(literal, b"\0")

        def write(where, *values):
            emu.mem_write(where, struct.pack("<" + "I" * len(values), *values))

        def read(where):
            return struct.unpack("<I", emu.mem_read(where, 4))[0]

        def read_text(where):
            return bytes(emu.mem_read(where, 32)).split(b"\0", 1)[0].decode("ascii")

        def reg(register):
            return emu.reg_read(register)

        def return_from_boundary(value=None):
            if value is not None:
                emu.reg_write(UC_ARM_REG_R0, value)
            emu.reg_write(UC_ARM_REG_PC, reg(UC_ARM_REG_LR))

        write(page + 0xc8, focus if has_alias else 0, label if has_label else 0)
        write(focus, address(ALIAS_VT) + 8)
        write(alias, address(ALIAS_VT) + 8)
        write(label, address(LABEL_VT) + 8)
        for p in (plain, old, alternate):
            write(p, address(PARAM_VT) + 8)
        write(handler, address(HANDLER_VT) + 8)
        write(handler + 32, address(HANDLER_VT) + 8)
        write(guard, 1)
        write(instance, items, 3)
        write(items, 0, handler, handler + 32)
        incoming = {"null": 0, "unbound": alias, "alias-new": alias,
                    "alias-old": alias, "new": plain, "old": old}[parameter]
        alias_bindings = {
            focus: starts[current],
            alias: {"alias-new": plain, "alias-old": old}.get(parameter, 0),
        }
        trace = []
        label_value = initial_label
        info_location = None

        def hook(uc, pc, size, user_data):
            nonlocal label_value, info_location
            r0, r1, r2 = (reg(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
            if pc == address(ALIAS_ORIGINAL):
                trace.append(["get", "focus" if r0 == focus else "input"])
                assert r0 in alias_bindings
                return_from_boundary(alias_bindings[r0])
            elif pc == address(PARAM_ORIGINAL):
                trace.append(["get", "input"])
                assert r0 in (plain, old)
                return_from_boundary(r0)
            elif pc == address(TABLE):
                assert r0 == instance and r2 in (plain, old)
                assert bytes(emu.mem_read(r1, 1)) == b"\0"
                assert bytes(emu.mem_read(r1 + 32, 1)) == b"\0"
                assert read(r1 + 64) == 0
                info_location = r1
                trace.append(["table", pointer_name[r2]])
            elif pc == address(CAST):
                assert r0 in (handler, handler + 32)
                trace.append(["cast", (r0 - handler) // 32, r1])
            elif pc == address(FOCUS):
                index = (r0 - handler) // 32
                assert r0 in (handler, handler + 32) and r1 == info_location
                trace.append(["focus", index, pointer_name[r2]])
                claimed = response != "miss" and index == 1
                if claimed:
                    emu.mem_write(r1 + 32, new_label.encode("ascii") + b"\0")
                    write(r1 + 64, alternate if response == "alternate" else 0)
                return_from_boundary(int(claimed))
            elif pc == address(BIND):
                assert r0 == focus and r1 in pointer_name
                trace.append(["bind", pointer_name[r1]])
                alias_bindings[r0] = r1
                return_from_boundary()
            elif pc == address(TEXT):
                assert r0 == label and r2 == 0
                assert r1 == (literal if incoming == 0 else info_location + 32)
                label_value = read_text(r1)
                trace.append(["label", label_value, r2])
                return_from_boundary()
            else:
                assert any(address(n) <= pc < address(n) + len(bodies[n])
                           for n in (MANGLED, TABLE, CAST)), hex(pc)

        emu.hook_add(UC_HOOK_CODE, hook)
        for register, value in ((UC_ARM_REG_R0, page), (UC_ARM_REG_R1, incoming),
                                (UC_ARM_REG_SP, page + 0x2ff0), (UC_ARM_REG_LR, stop)):
            emu.reg_write(register, value)
        before = bytes(emu.mem_read(page, 0x200))
        emu.emu_start(address(MANGLED), stop, count=2000)
        assert reg(UC_ARM_REG_PC) == stop and bytes(emu.mem_read(page, 0x200)) == before
        return {
            "inputs": [parameter, current, response, new_label, int(has_alias),
                       int(has_label), initial_label],
            "trace": trace, "original_after": pointer_name[alias_bindings[focus]],
            "label_after": label_value,
        }

    cases = [run(*args) for args in (
        ("alias-old", "old", "new", "ignored"),
        ("old", "old", "new", "ignored"),
        ("unbound", "old", "new", "ignored"),
        ("new", "old", "miss", "ignored"),
        ("alias-new", "old", "new", "selected gain"),
        ("new", "old", "alternate", "alternate gain"),
        ("new", "alternate", "alternate", "new label only"),
        ("alias-new", "-", "new", ""),
        ("null", "old", "new", "ignored"),
        ("null", "-", "miss", "ignored", True, True, ""),
        ("new", "old", "new", "ignored", False, True),
        ("new", "old", "new", "ignored", True, False),
    )]
    return {
        "original": {"mangled": MANGLED, "elf_sha256": SHA, **original},
        "native_application_bodies": [MANGLED, TABLE, CAST],
        "boundary_ranges": {name: entry for name, entry in records.items() if name != MANGLED},
        "dispatch_slots": slots,
        "empty_literal": {"address": literal, "file_offset": literal_offset, "hex": "00"},
        "singleton": {"guard": guard, "state": "initialized", "instance": instance},
        "unicorn_version": unicorn.__version__,
        "cases": cases,
    }


if __name__ == "__main__":
    result = json.dumps(observe(), indent=2) + "\n"
    if len(sys.argv) == 2:
        assert Path(sys.argv[1]).read_text() == result
        print("Native PageHeader focus: 12 cases")
    else:
        print(result, end="")
