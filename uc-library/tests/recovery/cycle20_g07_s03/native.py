"""Replay original Book, Page, and Element teardown with checked disposal."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import UC_ERR_READ_UNMAPPED, UcError


def sha(data):
    return hashlib.sha256(data).hexdigest()


class DisposalProbe:
    """Observe the frozen lifecycle driver's actual emulator mappings."""

    def __init__(self, emu):
        self.emu = emu
        self.disposed = []
        self.unmap = emu.mem_unmap
        emu.mem_unmap = self.mem_unmap

    def mem_unmap(self, address, size):
        self.unmap(address, size)
        self.disposed.append(address)

    def verify_after_return(self):
        for address in self.disposed:
            try:
                self.emu.mem_read(address, 1)
            except UcError as error:
                assert error.errno == UC_ERR_READ_UNMAPPED
            else:
                raise AssertionError(f"Disposed receiver is still readable: {address:#x}")
        return self.disposed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    evidence = args.snapshot / "temp/recovery-work/control10x20-after-4fed70d11/selection/panel-foundation"
    producer = evidence / "observe_lifecycle_groups.py"
    assert sha(producer.read_bytes()) == "3b47f7ee161b9a43af9b9ec28c521ff8c35191a341cf762fc5f69312e1d735ff"
    spec = importlib.util.spec_from_file_location("lifecycle_oracle", producer)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    blob = (evidence / "LIFECYCLE_NATIVE_OBSERVATIONS.json").read_bytes()
    assert sha(blob) == "e4f59bdec00122285ad58fc017a1a1a887e126da6e515f7301205d4ff49f23fe"
    comparisons = json.loads(blob)["comparisons"]
    real_emulator = oracle.Uc
    probes = []

    def tracked_emulator(*params):
        probe = DisposalProbe(real_emulator(*params))
        probes.append(probe)
        return probe.emu

    oracle.Uc = tracked_emulator
    originals = []
    for digest, book in comparisons["Book"]["0"].items():
        path = args.snapshot / book["source_elf"]
        data = path.read_bytes()
        assert sha(data) == digest
        stream = io.BytesIO(data)
        elf = ELFFile(stream)
        assert elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM"
        symbols = elf.get_section_by_name(".symtab")
        dynsym = elf.get_section_by_name(".dynsym")
        unsized, = dynsym.get_symbol_by_name("_ZdlPv")
        plt_target = unsized["st_value"]
        rel, = [r for r in elf.get_section_by_name(".rel.plt").iter_relocations()
                if dynsym.get_symbol(r["r_info_sym"]).name == "_ZdlPv"]
        assert rel["r_info_type"] == 22
        plt = elf.get_section_by_name(".plt")
        assert plt["sh_addr"] <= plt_target < plt["sh_addr"] + plt["sh_size"]
        assert plt_target == book["unsized_delete"]
        functions = {}
        for owner, variants in comparisons.items():
            for variant, per_elf in variants.items():
                row = per_elf[digest]
                member = row["member"]
                mangled = member["original_mangled"]
                symbol, = symbols.get_symbol_by_name(mangled)
                address, size = member["original_address"], member["original_size"]
                assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (address, size, 12)
                offset, code = oracle.original_range(elf, stream, address, size, 12)
                assert offset == member["range_confirmation"]["file_offset"]
                assert sha(code) == member["content_sha256"] and code.hex() == row["code"]
                vptr, = struct.unpack("<I", code[-4:])
                assert vptr == row["vptr"]
                slots = oracle.file_bytes_at(elf, stream, vptr, 8)
                assert struct.unpack("<II", slots) == (variants["1"][digest]["address"],
                                                       variants["0"][digest]["address"])
                branch = None
                if variant == "0":
                    branch_address = address + size - 16
                    word, = struct.unpack("<I", code[-16:-12])
                    assert word >> 24 == 0xeb
                    displacement = word & 0xffffff
                    if displacement & 0x800000:
                        displacement -= 1 << 24
                    assert branch_address + 8 + displacement * 4 == plt_target == row["unsized_delete"]
                    branch = {"address": branch_address, "target": plt_target,
                              "got_relocation": rel["r_offset"], "provider": "_ZdlPv"}
                functions[owner, int(variant)] = row | {"mangled": mangled, "size": size,
                    "section": 12, "range_sha256": sha(code), "file_offset": offset,
                    "vtable_slots": slots.hex(), "allocator_branch": branch}
        for variant in (0, 1, 2):
            target = functions["Book", variant]
            observations = []
            for previous in target["native_cases"]:
                trial = oracle.replay(functions, "Book", variant, previous["layout"])
                assert trial == previous
                probe = probes.pop()
                disposed = probe.verify_after_return()
                assert len(disposed) == len(trial["deallocation_order"])
                assert (0x4000_0000 in disposed) == (variant == 0)
                if variant != 0:
                    assert probe.emu.mem_read(0x4000_0000, 4) == struct.pack("<I", target["vptr"])
                observations.append(trial | {"disposal_unreadable_after_return": disposed})
            original = {key: target[key] for key in ("mangled", "file_offset", "address", "size", "section",
                        "role", "firmware", "range_sha256", "vptr", "vtable_slots", "allocator_branch")}
            originals.append(original | {"elf_sha256": digest, "variant": variant, "cases": observations,
                "page_d0": functions["Page", 0]["address"], "element_d0": functions["Element", 0]["address"]})
    assert len(originals) == 6
    args.out.write_text(json.dumps({"originals": originals}, indent=2) + "\n")


if __name__ == "__main__":
    main()
