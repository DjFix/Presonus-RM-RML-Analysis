"""Execute original IconManager::loadIcons and the independently verified parser."""
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, __version__
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP,
    UC_ARM_REG_LR, UC_ARM_REG_PC,
)

PACKETS = Path("temp/recovery-work/reconstruction10x10-20261121/packeting")
BASE = PACKETS / "post39-tail-batch02/packets/cycle21_g05_s09"
READMAP = PACKETS / "READ_INPUTS-post39-tail-batch02-cycle21_g05-post39-tail-scoped02-dispatch02.json"
PRIOR = Path("uc-library/validation/reconstruction10x10-20261121-scoped29-01/cycle21_g05_s02.canonical.json")
ELF_NAME = "rootfs/CS18_v13840/home/root/surface"
LOAD_HASH = "ccf4c26eecc73693c87f7b38b21c431e892e0849a0dfc8603789a78b578017a3"
PARSE_HASH = "57090260f5da8ff1d08c04b8983d0b7dc102ec035fb24683e3fa26a7eea1c575"
MANAGER = 0x400000
HEAP = 0x410000
ENTRIES = 0x430000
VECTORS = 0x450000
STACK = 0x4f0000
STOP = 0x4ff000

CONFIGS = {
    "missing": ("missing", 1, {}),
    "empty": ("empty", 1, {"empty": []}),
    "hidden": ("hidden", 1, {"hidden": [(".ignore", False), (".cache", True)],
                             "hidden/.cache": [("Never.PNG", False)]}),
    "orphans": ("orphans", 1, {"orphans": [("Loose.PNG", False)]}),
    "percent-name": ("percent", 1, {"percent": [("100%.PNG", False)]}),
    "mixed": ("icons", 1, {
        "icons": [("Drums", True), ("Empty", True), (".Secret", True),
                  ("Orphan.PNG", False), ("Keys", True)],
        "icons/Drums": [("Snare.PNG", False), ("Nested", True), (".skip", False)],
        "icons/Drums/Nested": [("Deeper", True), ("Tom.PNG", False)],
        "icons/Drums/Nested/Deeper": [("Level", True), ("Hat.PNG", False)],
        "icons/Drums/Nested/Deeper/Level": [("Kick.PNG", False)],
        "icons/Empty": [], "icons/.Secret": [("Never.PNG", False)],
        "icons/Keys": [("Synth.PNG", False)]}),
    "growth-repeat": ("growth", 2, {
        "growth": [(f"Cat{i}", True) for i in range(7)],
        **{f"growth/Cat{i}": [(f"Icon{i}.PNG", False)] for i in range(7)},
    }),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inputs():
    bindings = json.loads(READMAP.read_text())
    original = Path(bindings[ELF_NAME]["frozen_read_path"])
    prior = json.loads(Path(bindings[str(PRIOR)]["frozen_read_path"]).read_text())
    target = json.loads((BASE / "request.json").read_text())["targets"][0]
    parse = prior["original"]
    assert prior["passed"] and parse["address"] == 0x9c0c8
    assert parse["elf_sha256"] == target["original_elf_sha256"]
    assert digest(original.read_bytes()) == target["original_elf_sha256"]
    records = []
    with original.open("rb") as stream:
        elf = ELFFile(stream)
        segments = [(s["p_vaddr"], s.data()) for s in elf.iter_segments()
                    if s["p_type"] == "PT_LOAD"]
        for row, expected in ((target, LOAD_HASH), (parse, PARSE_HASH)):
            section = elf.get_section(row["section"])
            delta = row["address"] - section["sh_addr"]
            assert section.name == ".text" and 0 <= delta <= section["sh_size"] - row["size"]
            offset = section["sh_offset"] + delta
            stream.seek(offset)
            actual = digest(stream.read(row["size"]))
            assert actual == expected
            records.append(dict(target=row, section=section.name, file_offset=offset,
                                range_sha256=actual))
    return segments, records


class Machine:
    def __init__(self, segments, records, tree, fail_resize=False):
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.uc.mem_map(0x8000, 0x300000)
        self.uc.mem_map(MANAGER, 0x100000)
        for address, data in segments:
            self.uc.mem_write(address, data)
        self.bodies = [(row["target"]["address"], row["target"]["size"]) for row in records]
        self.tree = tree
        self.fail_resize = fail_resize
        self.iterators = {}
        self.objects = []
        self.freed = []
        self.trace = []
        self.uc.hook_add(UC_HOOK_CODE, self.hook)

    def put(self, address, value):
        self.uc.mem_write(address, struct.pack("<I", value))

    def word(self, address):
        return struct.unpack("<I", self.uc.mem_read(address, 4))[0]

    def cstr(self, address):
        if not address:
            return ""
        return bytes(self.uc.mem_read(address, 256)).split(b"\0", 1)[0].decode("ascii")

    def write_string(self, address, string):
        self.uc.mem_write(address, string.encode("ascii")[:255].ljust(256, b"\0"))

    def resize(self, receiver, request, items):
        capacity = self.word(receiver + 12)
        if capacity == request:
            return 1
        if receiver == MANAGER:
            self.trace.append(["grow_categories", request])
            if self.fail_resize:
                return 0
            data = VECTORS
        else:
            category = self.objects.index(receiver - 0x100)
            data = VECTORS + 0x1000 * (category + 1)
        self.put(receiver + 4, data)
        self.put(receiver + 12, ((request + 4) // 5) * 5)
        return 1

    def hook(self, uc, pc, size, _):
        if any(start <= pc < start + extent for start, extent in self.bodies):
            return
        a, b, c = (uc.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        result = a
        if pc == 0xa90c:
            assert a == 0x114
            result = HEAP + 0x200 * len(self.objects)
            self.objects.append(result)
            self.trace.append(["allocate", len(self.objects) - 1])
        elif pc == 0xad5c:
            assert a in self.objects and a not in self.freed
            self.freed.append(a)
            self.trace.append(["delete", self.objects.index(a)])
        elif pc == 0x72480:
            self.trace.append(["destroy_icon_vector", self.objects.index(a - 0x100)])
        elif pc == 0x722c8:
            result = self.resize(a, b, 256)
        elif pc == 0x9b340:
            assert a == MANAGER
            result = self.resize(a, b, 4)
        elif pc == 0x12bb14:
            self.write_string(a, self.cstr(b))
        elif pc == 0x129a3c:
            self.write_string(b, self.cstr(a).rsplit("/", 1)[-1])
        elif pc == 0x9b55c:
            self.write_string(a, self.cstr(a).lower())
        elif pc == 0x12bcbc:
            path = self.cstr(b)
            slot = next(i for i in range(32)
                        if i not in {active[2] for active in self.iterators.values()})
            self.iterators[a] = (path, iter(self.tree.get(path, [])), slot)
            self.trace.append(["open", path])
        elif pc == 0x12bb6c:
            path, entries, slot = self.iterators[a]
            item = next(entries, None)
            if item is None:
                result = 0
            else:
                name, directory = item
                result = ENTRIES + 0x200 * slot
                self.write_string(result, path + "/" + name)
                uc.mem_write(result + 256, bytes([directory, name.startswith(".")]))
        elif pc == 0x129994:
            self.trace.append(["close", self.iterators.pop(a)[0]])
        elif pc == 0xaffc:
            uc.mem_write(a, bytes(uc.mem_read(b, c)))
        elif pc == 0x1179d4:
            assert self.cstr(a) == "Track icon with no category!?%s\n"
            self.trace.append(["orphan", self.cstr(b)])
        else:
            raise AssertionError(f"unexpected branch {pc:#x}")
        uc.reg_write(UC_ARM_REG_R0, result)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    def run(self, path):
        self.write_string(MANAGER + 0x14, path)
        for reg, value in ((UC_ARM_REG_R0, MANAGER), (UC_ARM_REG_SP, STACK),
                           (UC_ARM_REG_LR, STOP)):
            self.uc.reg_write(reg, value)
        self.uc.emu_start(self.bodies[0][0], STOP, count=150000)
        assert self.uc.reg_read(UC_ARM_REG_PC) == STOP
        assert self.uc.reg_read(UC_ARM_REG_SP) == STACK and not self.iterators
        attached = [self.word(VECTORS + 4 * i) for i in range(self.word(MANAGER + 8))]
        assert set(attached) <= set(self.objects) and not set(attached) & set(self.freed)
        return {
            "categories": [
                {"name": self.cstr(obj), "icons": [
                    self.cstr(self.word(obj + 0x104) + 256 * i)
                    for i in range(self.word(obj + 0x108))]} for obj in attached],
            "addresses": [self.objects.index(obj) for obj in attached],
            "unattached_unfreed": [index for index, obj in enumerate(self.objects)
                                   if obj not in attached and obj not in self.freed],
        }


def generate(trees=None):
    segments, records = inputs()
    cases = []
    for name, (path, repeat, default_tree) in CONFIGS.items():
        tree = default_tree if trees is None else trees[name]
        native = Machine(segments, records, tree)
        states = [native.run(path) for _ in range(repeat)]
        cases.append(dict(name=name, path=path, repeat=repeat, states=states,
                          trace=native.trace))
    path, _, tree = CONFIGS["orphans"]
    failure = Machine(segments, records, tree, fail_resize=True)
    state = failure.run(path)
    assert not state["categories"] and state["unattached_unfreed"] == [0]
    return dict(original=records[0], parser_dependency=records[1], unicorn=__version__,
                cases=cases, failed_manager_growth=dict(state=state, trace=failure.trace),
                boundaries="Native loader and parser instructions execute directly. CCL, libc, logging and allocation transitions use explicit controlled hooks.")


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
