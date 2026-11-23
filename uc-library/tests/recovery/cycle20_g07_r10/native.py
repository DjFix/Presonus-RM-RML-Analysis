"""Offline ARM replay of the sealed Book and LCD query cases."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

ROOT_RECORDS = Path("temp/recovery-work/control10x20-after-4fed70d11/selection")
TASKS = ("s08", "s09", "r10", "r12", "r13", "r16", "r17", "r20")
RECORDS = {'r10': ('g07-tail-local-book/R10_NATIVE01.json',
         '2302844ec2f6674c54e9ae26852337cf37c4c0a1da9adb2a4b5d96a7782a1b59'),
 'r12': ('g07-tail-lcd/G07_R12_LCD_NATIVE01.json',
         'fbd0676a99dd094db937a83789292b2a270a7b2aea94dc5c69794a44eae354e5'),
 'r13': ('g07-tail-lcd/G07_R13_LCD_NATIVE01.json',
         '61722f1fbcb318171e6d101e1622f0747e0302a57db96809d38f32e49f3febd3'),
 'r16': ('g07-tail-lcd/G07_R16_LCD_NATIVE01.json',
         'a7f9b0155848187432fcd9159778a3b15d6ba65f4f3ea8cc084afb2a443f16c0'),
 'r17': ('g07-tail-lcd/G07_R17_LCD_NATIVE01.json',
         '90724e68bd260d69237f27d5d5e618f6501b724972d2ee6b13c8f6b2adad27ae'),
 'r20': ('g07-tail-lcd/G07_R20_LCD_NATIVE01.json',
         'e7dbddb544a42f28f0250bdea71b469ab816ac67e00cfa2aecb55821bfc42ba4'),
 's08': ('book-navigation/BOOK_NAVIGATION_NATIVE.json',
         '6cbfdea2f516e02a57acf8307c817b6b0369e74a79e22fe99ad0826204269009'),
 's09': ('book-navigation/BOOK_NAVIGATION_NATIVE.json',
         '6cbfdea2f516e02a57acf8307c817b6b0369e74a79e22fe99ad0826204269009')}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def u32(value):
    return struct.pack("<I", value & 0xffffffff)


def branch(address, blob, offset):
    word, = struct.unpack_from("<I", blob, offset)
    assert word & 0x0e000000 == 0x0a000000
    displacement = word & 0xffffff
    if displacement & 0x800000:
        displacement -= 1 << 24
    return address + offset + 8 + displacement * 4


class Role:
    def __init__(self, snapshot, digest):
        self.client = digest.startswith("304c")
        path = ("rootfs/CS18_v13840/home/root/surface" if self.client
                else "rootfs/RML16AI_Rack_13731/home/root/mixer")
        self.data = (snapshot / path).read_bytes()
        assert sha(self.data) == digest
        self.elf = ELFFile(io.BytesIO(self.data))
        assert self.elf.elfclass == 32 and self.elf.little_endian and self.elf["e_machine"] == "EM_ARM"
        self.symbols = self.elf.get_section_by_name(".symtab")

    def symbol(self, mangled):
        symbol, = self.symbols.get_symbol_by_name(mangled)
        return symbol

    def body(self, mangled):
        symbol = self.symbol(mangled)
        return self.range(symbol["st_shndx"], symbol["st_value"], symbol["st_size"])

    def range(self, index, address, size):
        section = self.elf.get_section(index)
        delta = address - section["sh_addr"]
        assert 0 <= delta <= delta + size <= section["sh_size"]
        offset = section["sh_offset"] + delta
        return offset, self.data[offset:offset + size]

    def named_plt(self, address, name):
        rel = self.elf.get_section_by_name(".rel.plt")
        symtab = self.elf.get_section(rel["sh_link"])
        plt = self.elf.get_section_by_name(".plt")
        index, = [n for n, entry in enumerate(rel.iter_relocations())
                  if symtab.get_symbol(entry["r_info_sym"]).name == name]
        assert address == plt["sh_addr"] + 20 + 12 * index


class Machine:
    root, first, second, allocated = 0x41000000, 0x41020000, 0x41030000, 0x41040000
    stack, stop, seq, query = 0x60000000, 0x70000000, 0x51000000, 0x52000000

    def __init__(self, entry, blob):
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.pages = set()
        self.events = []
        self.put(entry, blob)
        for address in (self.stack, self.stop, self.root, self.first, self.second, self.seq):
            self.put(address, b"\0")
        for register, value in ((UC_ARM_REG_R0, self.root), (UC_ARM_REG_LR, self.stop),
                                (UC_ARM_REG_SP, self.stack + 4080)):
            self.uc.reg_write(register, value)
        self.entry = entry

    def put(self, address, data):
        for page in range(address & ~4095, ((address + len(data) - 1) & ~4095) + 1, 4096):
            if page not in self.pages:
                self.uc.mem_map(page, 4096)
                self.pages.add(page)
        self.uc.mem_write(address, data)

    def string(self, address):
        data = bytearray()
        for advance in range(256):
            char = self.uc.mem_read(address + advance, 1)
            if char == b"\0":
                return bytes(data)
            data.extend(char)
        raise AssertionError("Unterminated native fixture")

    def run(self):
        self.uc.emu_start(self.entry, self.stop, count=1500)
        assert self.uc.reg_read(UC_ARM_REG_PC) == self.stop
        assert self.uc.reg_read(UC_ARM_REG_SP) == self.stack + 4080
        return self.uc.reg_read(UC_ARM_REG_R0)

    def hook(self, wrappers):
        def observe(uc, pc, _size, _user):
            if pc in wrappers:
                wrappers[pc]()
        self.uc.hook_add(UC_HOOK_CODE, observe)

    def boundary(self, pc):
        self.put(pc, bytes.fromhex("1eff2fe1"))

    def roster(self, offset, addresses):
        self.put(self.root + offset, u32(self.seq) + u32(len(addresses)))
        if addresses:
            self.put(self.seq, b"".join(map(u32, addresses)))


def navigation(m, case):
    slots = []
    for i, kind in enumerate(case["slots"]):
        address = m.first + 0x1000 * i
        if kind:
            m.put(address + 5, bytes([int(kind != 1)]))
        slots.append(address if kind else 0)
    m.roster(4, slots)
    m.put(m.root + 0x90, u32(case["index"]))
    return case | {"returned_index": m.run(), "calls": m.events}


def names(m, role, blob, case):
    addresses = [m.first + i * 0x1000 for i in range(len(case["arg"]))]
    for address, name in zip(addresses, case["arg"]):
        m.put(address + 0xd4, name.encode() + b"\0")
    m.roster(4, addresses)
    query = case["state"]
    if query is not None:
        m.put(m.query, query.encode() + b"\0")
    m.uc.reg_write(UC_ARM_REG_R1, m.query if query is not None else 0)
    literal, = struct.unpack_from("<I", blob, 180)
    segment, = [seg for seg in role.elf.iter_segments()
                if seg["p_type"] == "PT_LOAD" and seg["p_vaddr"] <= literal < seg["p_vaddr"] + seg["p_filesz"]]
    offset = segment["p_offset"] + literal - segment["p_vaddr"]
    assert role.data[offset] == 0
    m.put(literal, b"\0")
    handlers = {}
    for name, offset in (("strlen", 84), ("strncpy", 116), ("strcmp", 148)):
        pc = branch(m.entry, blob, offset)
        role.named_plt(pc, name)
        m.boundary(pc)
        def handler(name=name):
            m.events.append(name)
            a, b = (m.uc.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1))
            if name == "strlen":
                m.uc.reg_write(UC_ARM_REG_R0, len(m.string(a)))
            elif name == "strncpy":
                count = m.uc.reg_read(UC_ARM_REG_R2)
                m.put(a, m.string(b)[:count].ljust(count, b"\0"))
            else:
                m.uc.reg_write(UC_ARM_REG_R0, int(m.string(a) != m.string(b)))
        handlers[pc] = handler
    m.hook(handlers)
    return case | {"result": m.run(), "typed_runtime": m.events}


def lcd(task, m, role, blob, record, case):
    arg = case["arg"]
    m.uc.reg_write(UC_ARM_REG_R1, arg)
    handlers = {}
    if task == "r12":
        m.put(m.root + 0xdc, u32(m.first if arg else 0))
    elif task == "r13":
        tag = "_ZNK8Presonus5Panel4Book6getTagEv"
        address = role.symbol(tag)["st_value"]
        assert address == branch(m.entry, blob, 64)
        offset, body = role.body(tag)
        m.put(address, body)
        m.put(m.first + 0x8c, u32(1))
        m.put(m.second + 0x8c, u32(2))
        m.roster(0xe8, [m.first, m.second] if arg else [])
        handlers[address] = lambda: m.events.append("actual Book::getTag")
    elif task in ("r16", "r17"):
        base = "_ZN4Core8Portable9Component6onIdleEv"
        exact = role.symbol(base)["st_value"]
        if task == "r17":
            provider = record["provider"]
            idle = "_ZN8Presonus5Panel12LCDComponent6onIdleEv"
            target = role.symbol(idle)["st_value"]
            assert target == provider["actual_lcd_on_idle"]
            _, idle_code = role.body(idle)
            assert exact == branch(target, idle_code, 16) == provider["pinned_base_idle"]
            table = role.symbol("_ZTVN8Presonus5Panel12LCDComponentE")
            assert table["st_value"] == provider["vtable"]
            _, table_body = role.body(table.name)
            assert struct.unpack_from("<I", table_body, 48)[0] == target
            m.put(table["st_value"], table_body)
            m.put(m.root, u32(provider["vtable"] + 8))
            m.put(target, idle_code)
            handlers[target] = lambda: m.events.append("actual LCDComponent::onIdle")
        else:
            assert exact == branch(m.entry, blob, 16)
        m.boundary(exact)
        handlers[exact] = lambda: m.events.append("pinned actual Component::onIdle boundary")
    elif task == "r20":
        provider = record["provider"]
        allocator, constructor = branch(m.entry, blob, 20), branch(m.entry, blob, 32)
        assert allocator == provider["allocator"]
        role.named_plt(allocator, "_Znwj")
        assert constructor == provider["book_constructor"] == role.symbol("_ZN8Presonus5Panel4BookC1Ei")["st_value"]
        m.boundary(allocator)
        m.boundary(constructor)
        def allocate():
            count = m.uc.reg_read(UC_ARM_REG_R0)
            m.events.append(["real allocator boundary", count])
            m.put(m.allocated, b"\0" * count)
            m.uc.reg_write(UC_ARM_REG_R0, m.allocated)
        def construct():
            assert m.uc.reg_read(UC_ARM_REG_R0) == m.allocated
            mode = struct.unpack("<i", u32(m.uc.reg_read(UC_ARM_REG_R1)))[0]
            m.events.append(["actual typed Book C1 boundary", mode])
        handlers[allocator] = allocate
        handlers[constructor] = construct
    m.hook(handlers)
    return case | {"events": m.events, "returned": m.run()}


def harvest(snapshot, task):
    path, digest = RECORDS[task]
    source = (snapshot / ROOT_RECORDS / path).read_bytes()
    assert sha(source) == digest
    evidence = json.loads(source)
    if task.startswith("s"):
        key = "previousPage" if task == "s08" else "nextPage"
        sealed = []
        for record in evidence["originals"][key]:
            native = record["range"]
            sealed.append(native | {"elf_sha256": record["identity"]["elf_sha256"],
                                    "original_mangled": native["mangled"],
                                    "range_sha256": native["sha256"], "cases": record["cases"]})
    else:
        sealed = list(evidence["originals"].values())

    results = []
    for row in sealed:
        digest = row["elf_sha256"]
        role = Role(snapshot, digest)
        name = row["original_mangled"]
        offset, blob = role.body(name)
        entry = row["address"]
        symbol = role.symbol(name)
        assert entry == symbol["st_value"] and row["size"] == symbol["st_size"] == len(blob)
        assert symbol["st_shndx"] == 12 and role.elf.get_section(12).name == ".text"
        assert offset == row["file_offset"] and sha(blob) == row["range_sha256"]
        expected = row.get("cases", row.get("test"))
        observed = []
        for case in expected:
            machine = Machine(entry, blob)
            if task.startswith("s"):
                result = navigation(machine, case)
            elif task == "r10":
                result = names(machine, role, blob, case)
            else:
                result = lcd(task, machine, role, blob, row, case)
            assert result == case, (task, case, result)
            if task.startswith("s"):
                reachable = case | {"slots": [kind if kind != 1 else 0 for kind in case["slots"]]}
                typed = navigation(Machine(entry, blob), reachable)
                result |= {"typed_reachable_result": typed["returned_index"],
                           "typed_reachable_slots": typed["slots"]}
            observed.append(result)
        results.append(row | {"mangled": name, "section": 12, "cases": observed,
                              "firmware": "CS18AI surface 13840" if role.client else "RM/RML mixer 13731",
                              "role": "client" if role.client else "server"})
    assert len(results) == 2
    return {"originals": results, "sealed_prior_observation_sha256": sha(source)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(harvest(args.snapshot, args.task), indent=2) + "\n")


if __name__ == "__main__":
    main()
