"""Run attenuateChannel with the original ARM firmware log10f DSO."""
import importlib.util
import io
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
shared_file = Path(__file__).parents[1] / "sqlite09_pcm4104_open/native.py"
spec = importlib.util.spec_from_file_location("pcm_oracle", shared_file)
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)

LIBM_SHA256 = "5f651c4af3c87b0e65b4d8294117dedc29864cf711f4c9536e9d7a0de4efdb7a"
LIBM_BASE = 0x03000000


class MathProvider:
    errno_entry = 0x04000000

    def __init__(self, source):
        data = Path(source).read_bytes()
        assert shared.native.digest(data) == LIBM_SHA256
        self.elf = shared.native.ELFFile(io.BytesIO(data))
        assert self.elf["e_machine"] == "EM_ARM" and self.elf["e_type"] == "ET_DYN"
        entry, = self.elf.get_section_by_name(".dynsym").get_symbol_by_name("log10f")
        assert entry["st_shndx"] != "SHN_UNDEF"
        self.entry = LIBM_BASE + entry["st_value"]
        self.executable = []
        section = self.elf.get_section(entry["st_shndx"])
        start = entry["st_value"] - section["sh_addr"]
        payload = section.data()[start:start + entry["st_size"]]
        assert len(payload) == entry["st_size"]
        self.metadata = {"path": "rootfs/CS18_v13840/lib/libm-2.9.so",
                         "soname": "libm.so.6", "sha256": LIBM_SHA256,
                         "symbol": "log10f@@GLIBC_2.4", "address": entry["st_value"],
                         "size": entry["st_size"], "section": section.name,
                         "file_offset": section["sh_offset"] + start,
                         "range_sha256": shared.native.digest(payload),
                         "external_boundary": "__errno_location returns isolated ARM errno storage"}

    def install(self, uc):
        uc.mem_map(self.errno_entry, 4096)
        for seg in self.elf.iter_segments():
            if seg["p_type"] != "PT_LOAD":
                continue
            address = seg["p_vaddr"] + LIBM_BASE
            start = address & ~4095
            end = (address + seg["p_memsz"] + 4095) & ~4095
            uc.mem_map(start, end - start)
            uc.mem_write(address, seg.data())
            if seg["p_flags"] & 1:
                self.executable.append((address, address + seg["p_filesz"]))
        for name in (".rel.dyn", ".rel.plt"):
            section = self.elf.get_section_by_name(name)
            symbols = self.elf.get_section(section["sh_link"])
            for rel in section.iter_relocations():
                address = LIBM_BASE + rel["r_offset"]
                rel_type = rel["r_info_type"]
                if rel_type == 23:  # R_ARM_RELATIVE
                    addend = shared.native.WORD.unpack(uc.mem_read(address, 4))[0]
                    target = LIBM_BASE + addend
                else:
                    assert rel_type in (21, 22), rel_type  # GLOB_DAT and JUMP_SLOT
                    sym = symbols.get_symbol(rel["r_info_sym"])
                    if sym["st_shndx"] != "SHN_UNDEF":
                        target = LIBM_BASE + sym["st_value"]
                    else:
                        # Only errno TLS is supported. Unexpected external
                        # calls stop replay at inaccessible/unrecognized code.
                        target = self.errno_entry if sym.name == "__errno_location" else 0
                uc.mem_write(address, shared.w(target))

    def is_code(self, address):
        return any(start <= address < end for start, end in self.executable)


if __name__ == "__main__":
    oracle = MathProvider(sys.argv[2])
    print(json.dumps(shared.fixtures(Path(sys.argv[1]), oracle), separators=(",", ":")))
