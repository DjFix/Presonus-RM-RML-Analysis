import hashlib
import io
import json
from pathlib import Path
import sys

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP


def sha(data):
    return hashlib.sha256(data).hexdigest()


ctx = json.loads(Path(sys.argv[1]).read_bytes())
outputs = []
for row in ctx["originals"]:
    original = row["original"]
    blob = Path(original["elf_path"]).read_bytes()
    assert sha(blob) == original["elf"]
    elf = ELFFile(io.BytesIO(blob))
    sym, = elf.get_section_by_name(".symtab").get_symbol_by_name(original["mangled"])
    a, n, index = sym["st_value"], sym["st_size"], sym["st_shndx"]
    section = elf.get_section(index)
    offset = section["sh_offset"] + a - section["sh_addr"]
    assert section.name == original["section_name"] == ".text"
    assert (a, n, index, offset) == tuple(original[k] for k in ("address", "size", "section", "file_offset"))
    code = blob[offset:offset+n]
    assert sha(code) == original["range_sha256"]
    cases = []
    for receiver in (0x800020, 0x800100):
        args = (0x810020, 0) if ctx["task"]["id"].endswith("subscription_reply") else (0x810020, 0x810100)
        for arg in args:
            u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
            code_page = a & ~4095
            u.mem_map(code_page, 8192)
            u.mem_write(a,code)
            stack, stop = 0x820000, 0x830000
            for page in (0x800000, 0x810000, stack, stop):
                u.mem_map(page,4096)
            receiver_bytes = bytes(range(96))
            payload_bytes = bytes(range(112))
            u.mem_write(receiver, receiver_bytes)
            if arg:
                u.mem_write(arg, payload_bytes)
            u.reg_write(UC_ARM_REG_SP, stack+2048)
            u.reg_write(UC_ARM_REG_LR, stop)
            u.reg_write(UC_ARM_REG_R0, receiver)
            u.reg_write(UC_ARM_REG_R1, arg)
            touched = []
            u.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE,
                       lambda mc, access, address, size, value, state: touched.append((address, size)))
            u.emu_start(a, stop, count=32)
            assert u.reg_read(UC_ARM_REG_PC) == stop
            assert all(stack <= addr < stack+4096-size for addr,size in touched)
            assert bytes(u.mem_read(receiver, 96)) == receiver_bytes
            assert not arg or bytes(u.mem_read(arg, 112)) == payload_bytes
            cases.append(dict(receiver=receiver, argument=arg, stack_access_count=len(touched), unchanged=True))
    outputs.append(dict(original=original, cases=cases))
print(json.dumps(outputs, indent=2))
