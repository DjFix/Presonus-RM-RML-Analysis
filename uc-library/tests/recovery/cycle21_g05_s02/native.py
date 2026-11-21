"""Run exact original IconManager application bodies offline on bounded fixture state."""
import hashlib
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
    UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC)

PACKETS = Path("temp/recovery-work/reconstruction10x10-20261121/packeting")
PACKET_ROOT = PACKETS / "post15-wave-compatible35-batch04/packets"
SOURCE = "rootfs/CS18_v13840/home/root/surface"
KEPT = (1, 2, 3, 4, 5, 6, 7, 8)
CATS = ("v/DRUMS", "v/keys")
DEFAULT_TREE = {
    "v/DRUMS": [("Snare Drum.PNG", False), ("SnareDrum.PNG", False),
                (".hidden.png", False), ("Nested", True), ("Kick.wav", False)],
    "v/DRUMS/Nested": [("Level2", True), ("Tom.PNG", False), (".cache", True)],
    "v/DRUMS/Nested/Level2": [("Deep", True), ("Cymbal.PNG", False)],
    "v/DRUMS/Nested/Level2/Deep": [("Hat.PNG", False)],
    "v/keys": [],
}
RECEIVER = 0x400000
INPUT = 0x401000
OUTPUT = 0x401400
ARRAY = 0x410000
CATEGORY = 0x402000
SECOND = 0x403000
ENTRIES = 0x420000
STACK = 0x4f0000
STOP = 0x4ff000
REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inputs():
    verified = json.loads((PACKETS / "READ_INPUTS-post15-wave-compatible35-batch04-cycle21_g05.json").read_text())
    elf_path = Path(verified[SOURCE]["frozen_read_path"])
    release_hash = sha(elf_path.read_bytes())
    assert release_hash == verified[SOURCE]["sha256"]
    records = {}
    with elf_path.open("rb") as fp:
        elf = ELFFile(fp)
        segments = [(p["p_vaddr"], p["p_memsz"], p.data()) for p in elf.iter_segments()
                    if p["p_type"] == "PT_LOAD"]
        for number in KEPT:
            task = f"cycle21_g05_s{number:02}"
            request = json.loads((PACKET_ROOT / task / "request.json").read_text())
            target = request["targets"][0]
            assert target["original_elf_sha256"] == release_hash
            section = elf.get_section(target["section"])
            address = target["address"]
            size = target["size"]
            delta = address - section["sh_addr"]
            assert section.name == ".text" and 0 <= delta <= section["sh_size"] - size
            offset = section["sh_offset"] + delta
            fp.seek(offset)
            body_hash = sha(fp.read(size))
            rendered = (PACKET_ROOT / task / "ELF_CONTEXT.md").read_text()
            assert f"SHA256 `{body_hash}`" in rendered
            records[number] = dict(target=target, section=section.name,
                                   file_offset=offset, range_sha256=body_hash)
    return segments, records


class Machine:
    def __init__(self, segments, records, tree):
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.uc.mem_map(0x8000, 0x300000)
        self.uc.mem_map(RECEIVER, 0x100000)
        for address, _, data in segments:
            self.uc.mem_write(address, data)
        self.bodies = [(r["target"]["address"], r["target"]["size"]) for r in records.values()]
        self.records = records
        self.tree = tree
        self.iterators = {}
        self.trace = []
        self.uc.hook_add(UC_HOOK_CODE, self.on_instruction)

    def put(self, address, value):
        self.uc.mem_write(address, struct.pack("<I", value))

    def word(self, address):
        return struct.unpack("<I", self.uc.mem_read(address, 4))[0]

    def cstr(self, address):
        return bytes(self.uc.mem_read(address, 256)).split(b"\0", 1)[0].decode("ascii") if address else ""

    def string(self, address, value):
        self.uc.mem_write(address, value.encode("ascii")[:255].ljust(256, b"\0"))

    def label(self, address):
        if not address:
            return None
        if address == CATEGORY:
            return "first"
        if address == SECOND:
            return "second"
        if address == 0x26aaec:
            return "fallback"
        raise AssertionError(hex(address))

    def on_instruction(self, uc, pc, size, _):
        if any(start <= pc < start + extent for start, extent in self.bodies):
            return
        a, b, c, _ = (uc.reg_read(reg) for reg in REGS)
        result = a
        if pc == 0x12bcbc:  # FileIterator construction
            directory = self.cstr(b)
            self.trace.append(["open", directory])
            self.iterators[a] = (directory, iter(self.tree.get(directory, [])))
        elif pc == 0x12bb6c:
            directory, entries = self.iterators[a]
            item = next(entries, None)
            if item is None:
                result = 0
            else:
                name, directory_entry = item
                result = ENTRIES + 0x200 * tuple(self.iterators).index(a)
                self.string(result, directory + "/" + name)
                uc.mem_write(result + 256, bytes([directory_entry, name.startswith(".")]))
        elif pc == 0x129994:
            self.trace.append(["close", self.iterators.pop(a)[0]])
        elif pc in (0x12bb14, 0x24210):  # filename and CString constructors
            self.string(a, self.cstr(b))
        elif pc == 0x129a3c:  # getName
            self.string(b, self.cstr(a).rsplit("/", 1)[-1])
        elif pc == 0x1299ec:  # ascend
            path = self.cstr(a)
            self.string(a, path.rsplit("/", 1)[0] if "/" in path else path)
        elif pc == 0x12adbc:  # setExtension
            path = self.cstr(a)
            if c and "." in path:
                path = path.rsplit(".", 1)[0]
            self.string(a, path + ("" if path.endswith(".") else ".") + self.cstr(b))
        elif pc == 0x9b55c:
            self.string(a, self.cstr(a).lower())
        elif pc == 0x97238:
            text = "".join(ch for ch in self.cstr(a) if not ch.isspace())
            self.string(a, text[:63])
        elif pc == 0x97334:
            text = self.cstr(a)
            self.string(a, "".join(ch.upper() if i == 0 or text[i-1].isspace() else ch
                                   for i, ch in enumerate(text)))
        elif pc == 0x722c8:  # Vector resize boundary
            self.trace.append(["resize", b])
            self.put(a + 4, ARRAY)
            self.put(a + 12, ((b + 4) // 5) * 5)
            result = 1
        elif pc == 0x72480:
            self.trace.append(["destroy_vector", a - RECEIVER, self.word(a + 8)])
            self.put(a + 4, 0)
            self.put(a + 8, 0)
            self.put(a + 12, 0)
        elif pc == 0xaffc:
            uc.mem_write(a, bytes(uc.mem_read(b, c)))
        elif pc == 0xb170:
            uc.mem_write(a, self.cstr(b).encode("ascii")[:c].ljust(c, b"\0"))
        elif pc == 0xb02c:
            result = len(self.cstr(a))
        elif pc == 0xb0f8:
            result = int(self.cstr(a) != self.cstr(b))
        elif pc == 0xb1c4:
            self.trace.append(["guard_acquire"])
            result = int(not self.word(a))
        elif pc == 0xab7c:
            self.trace.append(["guard_release"])
            self.put(a, 1)
        elif pc == 0xaf24:
            assert b == 0x9b4a8
            self.trace.append(["register_d1", self.label(a)])
            result = 0
        else:
            raise AssertionError(f"Unbound call {pc:#x}")
        uc.reg_write(UC_ARM_REG_R0, result)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    def run(self, number, *args, byvalue=None):
        self.uc.reg_write(UC_ARM_REG_SP, STACK)
        self.uc.reg_write(UC_ARM_REG_LR, STOP)
        if byvalue is not None:
            encoded = byvalue.encode("ascii").ljust(256, b"\0")
            self.uc.mem_write(STACK, encoded[12:])
            args = (*args, *struct.unpack("<III", encoded[:12]))
        for register, value in zip(REGS, args):
            self.uc.reg_write(register, value & 0xffffffff)
        self.uc.emu_start(self.records[number]["target"]["address"], STOP, count=20000)
        assert self.uc.reg_read(UC_ARM_REG_PC) == STOP
        assert self.uc.reg_read(UC_ARM_REG_SP) == STACK
        return self.uc.reg_read(UC_ARM_REG_R0)

    def seed_names(self, receiver, names):
        self.put(receiver + 0x104, ARRAY)
        self.put(receiver + 0x108, len(names))
        for number, name in enumerate(names):
            self.string(ARRAY + 256 * number, name)

    def names(self, receiver):
        data = self.word(receiver + 0x104)
        return [self.cstr(data + 256 * index)
                for index in range(self.word(receiver + 0x108))]

    def seed_manager(self, names):
        self.put(RECEIVER + 4, ARRAY + 0x5000)
        self.put(RECEIVER + 8, len(names))
        for index, name in enumerate(names):
            address = (CATEGORY, SECOND)[index]
            self.put(ARRAY + 0x5000 + 4 * index, address)
            self.string(address, name)


def generate(number, tree=DEFAULT_TREE):
    segments, originals = inputs()
    cases = []
    make = lambda: Machine(segments, originals, tree)
    if number == 1:
        for names in ([], ["Snare Drum.PNG", "Kick.wav"]):
            native = make()
            native.seed_names(RECEIVER, names)
            assert native.run(number, RECEIVER) == RECEIVER
            cases.append(dict(input=names, trace=native.trace,
                              post_count=native.word(RECEIVER + 0x108)))
    elif number in (2, 3):
        for path in (*CATS, "v/missing"):
            for recurse in (False, True):
                native = make()
                native.string(INPUT, path)
                if number == 2:
                    native.seed_names(RECEIVER, ["existing.PNG"])
                    native.put(RECEIVER + 0x10c, 5)
                else:
                    assert native.run(number, RECEIVER, INPUT, int(recurse)) == RECEIVER
                if number == 2:
                    native.run(number, RECEIVER, INPUT, int(recurse))
                cases.append(dict(path=path, recurse=recurse, names=native.names(RECEIVER),
                                  category=native.cstr(RECEIVER), trace=native.trace))
    elif number in (4, 5):
        names = ["Snare Drum.PNG", "SnareDrum.PNG", "Kick.wav", "one.two.PNG"]
        probes = [-5, -1, 0, 1, 2, 3, 4, 99] if number == 4 else [
            None, "", "snaredrum", "SnareDrum", "kick", "one.two", "absent"]
        for probe in probes:
            native = make()
            native.seed_names(RECEIVER, names)
            if number == 4:
                pointer = native.run(number, RECEIVER, probe)
                assert STACK - 0x200 <= pointer < STACK
                result = native.cstr(pointer)
            else:
                native.string(INPUT, probe or "")
                result = native.run(number, RECEIVER, INPUT if probe is not None else 0)
                if result == 0xffffffff:
                    result = -1
            cases.append(dict(input=probe, result=result))
    elif number == 6:
        for available in ([], ["drums", "keys"]):
            native = make()
            native.seed_manager(available)
            for index in [-1, 0, 1, 2, 300]:
                native.trace.clear()
                label = native.label(native.run(number, RECEIVER, index))
                cases.append(dict(available=available, input=index, result=label, trace=list(native.trace)))
    elif number in (7, 8):
        for probe in (None, "", "drums", "drums/snaredrum", "drums/kick",
                      "drums/absent", "keys/piano", "Drums/kick", "absent/path", "x" * 300):
            native = make()
            native.seed_manager(["drums", "keys"])
            native.seed_names(CATEGORY, ["Snare Drum.PNG", "Kick.wav"])
            if number == 7:
                if probe is None or len(probe) >= 256:
                    continue
                label = native.label(native.run(number, RECEIVER, byvalue=probe))
                cases.append(dict(input=probe, result=label))
            else:
                if probe is not None:
                    native.uc.mem_write(INPUT, probe.encode("ascii") + b"\0")
                native.run(number, RECEIVER, INPUT if probe is not None else 0, 0, OUTPUT)
                cases.append(dict(input=probe, result=native.cstr(OUTPUT)))
    return dict(**originals[number], unicorn=unicorn.__version__, cases=cases,
                boundary_model="Application ARM instructions are executed directly. Pinned Core and libc calls, StringUtils and C++ guard functions use controlled hooks in the native harness. Linux replay invokes actual pinned source providers.")


if __name__ == "__main__":
    print(json.dumps(generate(int(sys.argv[1])), indent=2))
