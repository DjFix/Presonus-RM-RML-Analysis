"""Observe the exact offline ARM encoder pointer replacement."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

ROLES = (
    ("304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0",
     "rootfs/CS18_v13840/home/root/surface", "client", "CS18AI surface 13840", 118060),
    ("9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07",
     "rootfs/RML16AI_Rack_13731/home/root/mixer", "server", "RM/RML mixer 13731", 614972),
)
MANGLED = "_ZN8Presonus5Panel12LCDComponent14setEditEncoderEPNS0_7ControlE"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def put_word(value):
    return struct.pack("<I", value)


class OriginalELF:
    def __init__(self, path, digest):
        self.data = path.read_bytes()
        assert sha(self.data) == digest
        self.elf = ELFFile(io.BytesIO(self.data))
        assert self.elf.elfclass == 32 and self.elf.little_endian and self.elf["e_machine"] == "EM_ARM"

    def symbol(self, name):
        symbols = self.elf.get_section_by_name(".symtab")
        sym, = symbols.get_symbol_by_name(name)
        index, address, size = sym["st_shndx"], sym["st_value"], sym["st_size"]
        sec = self.elf.get_section(index)
        displacement = address - sec["sh_addr"]
        assert 0 <= displacement <= displacement + size <= sec["sh_size"]
        offset = sec["sh_offset"] + displacement
        code = self.data[offset:offset + size]
        return {"mangled": name, "address": address, "size": size, "section": index,
                "range_sha256": sha(code), "file_offset": offset}, code


class Trial:
    stack, stop = 0x60000000, 0x70000000

    def __init__(self, original, code):
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.pages = set()
        self.entry = original["address"]
        self.put(self.entry, code)
        self.put(self.stack, b"\0")
        self.put(self.stop, b"\0")

    def put(self, address, data):
        for page in range(address & ~4095, ((address + len(data) - 1) & ~4095) + 1, 4096):
            if page not in self.pages:
                self.uc.mem_map(page, 4096)
                self.pages.add(page)
        self.uc.mem_write(address, data)

    def run(self, receiver, arg):
        self.uc.reg_write(UC_ARM_REG_R0, receiver)
        self.uc.reg_write(UC_ARM_REG_R1, arg)
        self.uc.reg_write(UC_ARM_REG_SP, self.stack + 4080)
        self.uc.reg_write(UC_ARM_REG_LR, self.stop)
        self.uc.emu_start(self.entry, self.stop, count=200)
        assert self.uc.reg_read(UC_ARM_REG_PC) == self.stop
        assert self.uc.reg_read(UC_ARM_REG_SP) == self.stack + 4080
        return self.uc.reg_read(UC_ARM_REG_R0)


def observe(row, code, old, new):
    trial = Trial(row, code)
    receiver = 0x41000000
    pointers = (0, 0x44000000, 0x45000000)
    baseline = bytearray([0x5a] * 260)
    baseline[0xf8:0xfc] = put_word(pointers[old])
    trial.put(receiver, bytes(baseline))
    writes, reads = [], []
    trial.uc.hook_add(UC_HOOK_MEM_WRITE, lambda _u, _a, where, size, value, _p:
                      writes.append((where, size, value)) if where < trial.stack else None)
    trial.uc.hook_add(UC_HOOK_MEM_READ, lambda _u, _a, where, size, _v, _p:
                      reads.append((where, size)) if where < trial.stack else None)
    trial.run(receiver, pointers[new])
    baseline[0xf8:0xfc] = put_word(pointers[new])
    assert trial.uc.mem_read(receiver, len(baseline)) == baseline
    assert writes == [(receiver + 0xf8, 4, pointers[new])] and not reads
    return {"old": old, "new": new, "stored": new, "receiver_writes": [[0xf8, 4, pointers[new]]],
            "other_receiver_bytes_preserved": True, "nonstack_reads": reads}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for digest, path, role, firmware, address in ROLES:
        row, code = OriginalELF(args.snapshot / path, digest).symbol(MANGLED)
        assert row["address"] == address and row["size"] == 20 and row["section"] == 12
        assert row["range_sha256"] == "bbd530977167671e4d3522f722a5c05e37493cf9583847153ed14574a7339182"
        rows.append(row | {"elf_sha256": digest, "role": role, "firmware": firmware,
            "cases": [observe(row, code, old, new) for old in range(3) for new in range(3)]})
    args.out.write_text(json.dumps({"originals": rows}, indent=2) + "\n")


if __name__ == "__main__":
    main()
