"""Execute the native SevenSeg lookup and firmware's ARM C++ RTTI provider."""
import importlib.util
from pathlib import Path

from elftools.elf.elffile import ELFFile

spec = importlib.util.spec_from_file_location(
    "frontpanel_oracle", Path(__file__).resolve().parent.parent /
    "sqlite02_frontpanel_get_local_fader_style" / "native.py")
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)

CASES = {
    "missing-group": [(12, [(0, 2, None)])],
    "empty-group": [(16, [])],
    "tag-missing": [(16, [(5, 2, None), (1, 1, None)])],
    "wrong-base-type": [(16, [(0, 1, None)])],
    "wrong-sibling-type": [(16, [(0, 3, None)])],
    "exact-pointer": [(16, [(0, 2, None)])],
    "scan-tags": [(16, [(1, 1, None), (3, 2, None), (0, 2, None)])],
    "first-wrong-type": [(16, [(0, 1, None), (0, 2, None)])],
    "first-exact-pointer": [(12, [(0, 2, None)]),
                            (16, [(2, 1, None), (0, 2, None), (0, 2, None)])],
    "first-group": [(16, [(0, 3, None)]), (16, [(0, 2, None)])],
}


def bind_rtti(oracle, path):
    elf = ELFFile(path.open("rb"))
    symbols = elf.get_section_by_name(".dynsym")
    bias = 0x10000000
    oracle.uc.mem_map(bias, 0x100000)
    oracle.map_image(elf, bias)
    for section_name in (".rel.dyn", ".rel.plt"):
        for reloc in elf.get_section_by_name(section_name).iter_relocations():
            target = bias + reloc["r_offset"]
            kind = reloc["r_info_type"]
            symbol = symbols.get_symbol(reloc["r_info_sym"])
            addend = oracle.read_word(target)
            if kind == 23:  # R_ARM_RELATIVE
                oracle.word(target, bias + addend)
            elif symbol["st_shndx"] != "SHN_UNDEF":
                assert kind in (2, 21, 22)
                oracle.word(target, bias + symbol["st_value"] +
                            (addend if kind == 2 else 0))
            else:
                # Any unresolved import reached in this bounded runtime fails
                # the emulation. No behavior is supplied for those imports.
                oracle.word(target, 0)
    for name in ("__class_type_info", "__si_class_type_info",
                 "__vmi_class_type_info"):
        symbol_name = f"_ZTVN10__cxxabiv1{len(name)}{name}E"
        source = symbols.get_symbol_by_name(symbol_name)[0]
        target = oracle.image.get_section_by_name(".dynsym").get_symbol_by_name(symbol_name)[0]
        assert source["st_size"] == target["st_size"]
        oracle.uc.mem_write(target["st_value"], bytes(oracle.uc.mem_read(
            bias + source["st_value"], source["st_size"])))
    dynamic_cast = symbols.get_symbol_by_name("__dynamic_cast")[0]
    oracle.cast_address = bias + dynamic_cast["st_value"]
    oracle.word(0x453884, oracle.cast_address)
    oracle.rtti = {kind: oracle.symbols.get_symbol_by_name(
        f"_ZTVN8Presonus5Panel{len(name)}{name}E")[0]["st_value"] + 8
        for kind, name in ((1, "Control"), (2, "SevenSegControl"),
                           (3, "SwitchControl"))}
    source = oracle.symbols.get_symbol_by_name("_ZTIN8Presonus5Panel7ControlE")[0]
    dest = oracle.symbols.get_symbol_by_name("_ZTIN8Presonus5Panel15SevenSegControlE")[0]
    assert oracle.read_word(0x64374) == source["st_value"]
    assert oracle.read_word(0x64378) == dest["st_value"]
    return {"path": "rootfs/RML32AI_Rack_13731/usr/lib/libstdc++.so.6.0.10",
            "sha256": shared.digest(path), "entry": dynamic_cast["st_value"],
            "source_typeinfo": source["st_value"], "destination_typeinfo": dest["st_value"]}


def generate(firmware, context, evidence):
    oracle = shared.PanelOracle(firmware, context, evidence)
    rtti = bind_rtti(oracle, firmware /
        "rootfs/RML32AI_Rack_13731/usr/lib/libstdc++.so.6.0.10")
    observations = shared.collect(oracle, CASES)
    observations["rtti"] = rtti
    for case in observations["cases"]:
        for name, _, src, dst, hint in case["calls"]:
            if name in ("__dynamic_cast@plt", "libstdc++::__dynamic_cast"):
                assert (src, dst, hint) == (
                    rtti["source_typeinfo"], rtti["destination_typeinfo"], 0)
    return observations


if __name__ == "__main__":
    shared.cli(generate)
