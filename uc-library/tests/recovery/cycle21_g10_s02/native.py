"""Execute verified ARM range and retain explicit dependency-boundary traces."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import struct

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP)

ROOT = Path("/home/rs/projects/opencs/ai-line-analysis")
RUN = ROOT / "temp/recovery-work/reconstruction10x10-20261121/packeting"
TASK = Path(__file__).resolve().parent.name
PACKET = RUN / "post39-tail-batch02/packets" / TASK
READS = RUN / "READ_INPUTS-post39-tail-batch02-cycle21_g10-post39-tail-scoped01-dispatch02.json"
ELF = "rootfs/RML16AI_Rack_13731/home/root/mixer"
OBJ, SUB, PAR, STACK, STOP = [0x1000000 + 0x1000 * i for i in range(5)]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def word(machine, address, value=None):
    if value is not None:
        machine.mem_write(address, struct.pack("<I", value & 0xFFFFFFFF))
    else:
        return struct.unpack("<I", machine.mem_read(address, 4))[0]


def run(image, address, argument, init, intercept):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    machine.mem_map(0x8000, 0x500000)
    for segment in image.iter_segments():
        if segment["p_type"] == "PT_LOAD":
            machine.mem_write(segment["p_vaddr"], segment.data())
    machine.mem_map(OBJ, 0x5000)
    for register, value in ((UC_ARM_REG_R0, OBJ), (UC_ARM_REG_R1, argument),
                            (UC_ARM_REG_SP, STACK + 0x800), (UC_ARM_REG_LR, STOP)):
        machine.reg_write(register, value)
    init(machine)
    trace = []

    def hook(uc, site, size, _):
        assert address <= site < address + TARGET["size"] or site in BOUNDARIES or site in RUNTIME, hex(site)
        if site not in BOUNDARIES:
            return
        a, b, c = (uc.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        result = intercept(uc, trace, site, a, b, c)
        if result is not None:
            uc.reg_write(UC_ARM_REG_R0, result)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    machine.hook_add(UC_HOOK_CODE, hook)
    machine.emu_start(address, STOP, count=20000)
    assert machine.reg_read(UC_ARM_REG_PC) == STOP, (hex(machine.reg_read(UC_ARM_REG_PC)), trace[-12:])
    return machine, trace


def generate():
    read_map = json.loads(READS.read_text())
    path = Path(read_map[ELF]["frozen_read_path"])
    binary = path.read_bytes()
    assert sha(binary) == TARGET["original_elf_sha256"] == read_map[ELF]["sha256"]
    e = ELFFile(BytesIO(binary))
    sect = e.get_section(TARGET["section"])
    assert sect.name == ".text"
    address, size = TARGET["address"], TARGET["size"]
    assert sect["sh_addr"] <= address and address + size <= sect["sh_addr"] + sect["sh_size"]
    offset = sect["sh_offset"] + address - sect["sh_addr"]
    exact = sha(binary[offset:offset + size])
    packet_hash = re.search(r"section \.text; SHA256 `([0-9a-f]{64})`",
                            (PACKET / "ELF_CONTEXT.md").read_text())[1]
    assert exact == packet_hash
    symbols = e.get_section_by_name(".symtab").get_symbol_by_name(TARGET["mangled"])
    assert any(s["st_value"] == address and s["st_size"] == size
               and s["st_shndx"] == TARGET["section"] for s in symbols)
    rows = cases(e, address)
    return dict(original=TARGET, elf_path=str(path), section=sect.name, file_offset=offset,
                range_sha256=exact, cases=rows)


TARGET = json.loads((PACKET / "request.json").read_text())["targets"][0]


def cstr(uc, ptr, max_size=96):
    return bytes(uc.mem_read(ptr, max_size)).split(b"\0", 1)[0]


def native_bytes(image, address, size):
    for segment in image.iter_segments():
        if segment["p_type"] != "PT_LOAD":
            continue
        offset = address - segment["p_vaddr"]
        if 0 <= offset and offset + size <= segment["p_filesz"]:
            return segment.data()[offset:offset + size]
    raise ValueError(f"No mapped file bytes at {address:#x}")

import ctypes

LIBC = ctypes.CDLL("libc.so.6")
LIBC.strlen.argtypes = [ctypes.c_char_p]
LIBC.strlen.restype = ctypes.c_size_t
for name in ("strchr", "strstr", "memcpy", "strncat"):
    getattr(LIBC, name).restype = ctypes.c_void_p
LIBC.strchr.argtypes = [ctypes.c_void_p, ctypes.c_int]
LIBC.strstr.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
LIBC.strncat.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
LIBC.memcpy.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
GROUP_TABLE, CAT_TABLE = 0x1001800, 0x1003800
CAT_METADATA, INIT_CATEGORY_POINTERS = 0x494708, 0x31C468
PARAM_TYPE, STRING_TYPE = 0x41B268, 0x41B1EC
GET, SET, TEXT, FROM = [0x1004200 + 4 * i for i in range(4)]
GET_PARAM, CAST, DEBUG, RESET, SUBSTRING = 0x119C4C, 0xACF4, 0x116A38, 0x11ADD4, 0x45C48
MEMCPY, STRLEN, STRCHR, STRSTR, LOWER, UPPER, STRNCAT = (
    0xAE68, 0xAE98, 0xB0E4, 0xAD18, 0xAFC4, 0xAF7C, 0xAE08)
BOUNDARIES = {GET, SET, TEXT, FROM, GET_PARAM, CAST, DEBUG, RESET, SUBSTRING,
              MEMCPY, STRLEN, STRCHR, STRSTR, LOWER, UPPER, STRNCAT}
RUNTIME = range(0x157800, 0x157AA0)
GROUPS = [SUB + 0x40 * i for i in range(9)]
TAG = 648
ARGS = [
    ("drum/tom", -1, False, True, True),
    ("xdrum/tom", 2, False, True, True),
    ("keyboard/synth", 2, True, True, True),
    ("xxbrass/cornet", -1, False, True, True),
    ("BRASS/cornet", -1, False, True, True),
    ("vocals/mic", -1, False, True, False),
    ("drum/tom", 0, False, False, True),
    ("", 8, True, True, True),
    ("wind", -1, False, True, True),
]


def cases(elf, address):
    pointers = struct.unpack("<9I", native_bytes(elf, INIT_CATEGORY_POINTERS, 36))
    categories = [native_bytes(elf, ptr, 20).split(b"\0", 1)[0] for ptr in pointers]
    assert categories == [b"Drum", b"Perc", b"Guit", b"Keys", b"Vocal", b"String", b"Brass", b"Wind", b"Other"]
    cases = []
    for icon, current, other, is_string, label_string in ARGS:
        integers = [i == current for i in range(9)]
        second = [other and i == current for i in range(9)]
        labels = ["old"] * 9
        types = {}
        parameters = {}
        for index, g in enumerate(GROUPS):
            for slot, tag in enumerate([TAG, TAG + 1, 600]):
                pointer = PAR + index * 0x60 + slot * 0x10
                parameters[g, tag] = pointer
                kind = ["member", "other", "label"][slot]
                types[pointer] = (index, kind, kind == "label" and label_string)
        input_icon = PAR + 0xF00
        types[input_icon] = (-1, "icon", is_string)
        parameters[SUB + 0x300, 25] = input_icon

        def init(uc):
            word(uc, OBJ + 0x58, GROUP_TABLE)
            word(uc, OBJ + 0x5C, 9)
            word(uc, SUB + 0x300 + 0x170, TAG - 646)
            word(uc, CAT_METADATA + 4, CAT_TABLE)
            word(uc, CAT_METADATA + 8, 9)
            for i, (group, category) in enumerate(zip(GROUPS, categories)):
                word(uc, GROUP_TABLE + 4 * i, group)
                uc.mem_write(group + 8, f"Group{i}".encode() + b"\0")
                uc.mem_write(CAT_TABLE + i * 64, category + b"\0")
            for parameter in types:
                word(uc, parameter, STOP + 0x300)
            for offset, callback in [(0x44, GET), (0x58, SET), (0x70, TEXT), (0x74, FROM)]:
                word(uc, STOP + 0x300 + offset, callback)

        def provider(uc, trace, pc, a, b, c):
            if pc == GET_PARAM:
                return parameters.get((a, b), 0)
            if pc == CAST:
                assert (b, c) == (PARAM_TYPE, STRING_TYPE)
                trace.append(["cast", types[a][1], types[a][2]])
                return a if types[a][2] else 0
            if pc == GET:
                index, kind, _ = types[a]
                assert kind in ("member", "other")
                return 0x3F800000 if (integers if kind == "member" else second)[index] else 0
            if pc == SET:
                index, kind, _ = types[a]
                assert kind == "member" and c == 1 and b in (0, 0x3F800000)
                integers[index] = bool(b)
                trace.append(["set", index, int(bool(b)), c])
                return None
            if pc == TEXT:
                assert a == input_icon and c == 32
                uc.mem_write(b, icon.encode() + b"\0")
                return None
            if pc == FROM:
                index, kind, _ = types[a]
                assert kind == "label" and c == 1
                labels[index] = cstr(uc, b).decode()
                trace.append(["label", index, labels[index], c])
                return None
            if pc == RESET:
                index = GROUPS.index(a)
                assert b == 0 and c == 1
                labels[index] = "default"
                trace.append(["reset", index, b, c])
                return None
            if pc == DEBUG:
                trace.append(["format", cstr(uc, a).decode(), cstr(uc, b).decode(), c])
                return None
            if pc == SUBSTRING:
                length = struct.unpack("<i", struct.pack("<I", uc.reg_read(UC_ARM_REG_R3)))[0]
                source = cstr(uc, a, 32)
                if c < len(source) and length != 0:
                    raw = source[c:] if length < 0 else source[c:c + length]
                    uc.mem_write(b, raw + b"\0")
                return None
            if pc == MEMCPY:
                buf = ctypes.create_string_buffer(c)
                LIBC.memcpy(buf, bytes(uc.mem_read(b, c)), c)
                uc.mem_write(a, buf.raw)
                return a
            if pc == STRLEN:
                return LIBC.strlen(cstr(uc, a))
            if pc in (LOWER, UPPER):
                return (LIBC.tolower if pc == LOWER else LIBC.toupper)(a)
            if pc in (STRCHR, STRSTR):
                buf = ctypes.create_string_buffer(cstr(uc, a))
                result = LIBC.strchr(buf, b) if pc == STRCHR else LIBC.strstr(buf, cstr(uc, b))
                return 0 if not result else a + result - ctypes.addressof(buf)
            assert pc == STRNCAT
            buf = ctypes.create_string_buffer(cstr(uc, a), 32)
            LIBC.strncat(buf, cstr(uc, b), c)
            uc.mem_write(a, buf.value + b"\0")
            return a

        _, trace = run(elf, address, SUB + 0x300, init, provider)
        cases.append(dict(icon=icon, current=current, other=other, is_string=is_string,
                          label_string=label_string, events=trace, labels=labels,
                          member=[int(i) for i in integers], other_members=[int(i) for i in second]))
    return cases


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
