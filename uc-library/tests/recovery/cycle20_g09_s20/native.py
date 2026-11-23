"""Replay exact tagged app destructor and registration with typed ARM boundaries."""
import hashlib
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
from unicorn import (
    Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE,
    UC_HOOK_MEM_READ_UNMAPPED, UC_HOOK_MEM_WRITE_UNMAPPED,
)
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

CLASS_NAME = "PreDelayFormatterT3"
TAGGED = ("PreDelayFormatterT3", "EarlyRefFormatterT3", "PreDelayFormatterT4")
INITIALIZER = "_ZN8Presonus5Mixer24XmenFormatterInitializerC2Ev"
PROVIDERS = {
    "_ZN4Core17FormatterRegistry3addEPNS_9FormatterE": "register",
    "__cxa_guard_acquire@@CXXABI_1.3": "guard_acquire",
    "__cxa_guard_release@@CXXABI_1.3": "guard_release",
    "__aeabi_atexit@@GLIBC_2.4": "atexit",
}
TARGETS = [{'elf_path': '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11/packeting/actual07-authorized-wave01-capture02/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer', 'elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07', 'role': 'server', 'firmware': 'RM/RML mixer 13731', 'original_mangled': '_ZN8Presonus5Mixer19PreDelayFormatterT3D0Ev', 'range': {'address': 143580, 'section': 12, 'size': 44, 'file_offset': 110812, 'sha256': '02671d532af2ad98fbfada99226f166d3e9bbbcd1428f08042fb31fc938ff336'}}, {'elf_path': '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11/packeting/actual07-authorized-wave01-capture02/snapshot/rootfs/CS18_v13840/home/root/surface', 'elf_sha256': '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0', 'role': 'client', 'firmware': 'CS18AI surface 13840', 'original_mangled': '_ZN8Presonus5Mixer19PreDelayFormatterT3D0Ev', 'range': {'address': 66932, 'section': 12, 'size': 44, 'file_offset': 34164, 'sha256': '5eb47d249d2563f033192385b020c0fa26ec2042433e1879f749667abd177f1b'}}]
REFERENCE_PATH = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11/packeting/actual07-authorized-wave01-capture02/snapshot/temp/recovery-work/control10x20-after-4fed70d11/selection/third-tagged-formatters/PreDelayFormatterT3.guarded01.json")
REFERENCE_SHA256 = "bd9cbc705d963b249e32a8a275d8b7678bf4e2f5dec69d91978134d1e7b540ae"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def word(raw):
    return struct.unpack("<I", raw)[0]


def packed(value):
    return struct.pack("<I", value)


def qualification(cls):
    return f"N8Presonus5Mixer{len(cls)}{cls}"


def symbol(elf, name):
    [row] = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    section = elf.get_section(row["st_shndx"])
    addr, size = row["st_value"], row["st_size"]
    delta = addr - section["sh_addr"]
    assert 0 <= delta < delta + size <= section["sh_size"], name
    raw = bytes(size) if section["sh_type"] == "SHT_NOBITS" else section.data()[delta:delta + size]
    return addr, section["sh_offset"] + delta, row["st_shndx"], raw


def clear(symbol_tuple):
    address, offset, section, raw = symbol_tuple
    return dict(address=address, size=len(raw), section=section, file_offset=offset, sha256=sha(raw))


def observe_registration(elf):
    address, offset, section, code = symbol(elf, INITIALIZER)
    symbols = elf.get_section_by_name(".symtab")
    boundaries = {symbols.get_symbol_by_name(name)[0]["st_value"]: provider
                  for name, provider in PROVIDERS.items()}
    tables = {}
    for cls in TAGGED:
        prefix = qualification(cls)
        table, _, _, raw = symbol(elf, "_ZTV" + prefix + "E")
        parent = qualification(cls[:-2])
        delete0 = symbol(elf, "_Z" + prefix + "D0Ev")[0]
        complete = symbol(elf, "_Z" + prefix + "D1Ev")[0]
        expected_print = symbol(elf, "_ZNK" + parent[1:] + "5printERN4Core9Formatter4DataE")[0]
        expected_scan = symbol(elf, "_ZNK" + parent[1:] + "4scanERN4Core9Formatter4DataE")[0]
        assert struct.unpack("<6I", raw)[2:] == (complete, delete0, expected_print, expected_scan)
        tables[table + 8] = (cls, complete, sha(raw))
    data = [
        (section["sh_addr"], section["sh_addr"] + section["sh_size"],
         None if section["sh_type"] == "SHT_NOBITS" else section.data())
        for section in elf.iter_sections()
        if section["sh_flags"] & 2 and section.name in
        (".rodata", ".bss", ".data", ".data.rel.ro", ".data.rel.ro.local", ".got")
    ]
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    receiver, stack, stop = 0x50000000, 0x51000000, 0x52000000
    virtual = set()

    def map_page(value):
        page = value & ~4095
        if page not in virtual:
            machine.mem_map(page, 4096)
            virtual.add(page)
        return page

    for value in (receiver, stack, stop, *boundaries):
        map_page(value)
    for page in range(address & ~4095, (address + len(code) + 4095) & ~4095, 4096):
        map_page(page)
    machine.mem_write(address, code)

    def supply(addr, size):
        for low, high, raw in data:
            if low <= addr < addr + size <= high:
                page = map_page(addr)
                first, end = max(low, page), min(high, page + 4096)
                if raw is not None:
                    machine.mem_write(first, raw[first - low:end - low])
                return True
        return False

    def missing(_cpu, _access, addr, size, _value, _ctx):
        return supply(addr, size)

    def load(addr, count):
        assert addr and (addr & ~4095 in virtual or supply(addr, 1)), hex(addr)
        return bytes(machine.mem_read(addr, min(count, 4096 - (addr & 4095))))

    recorded, teardown = [], []

    def call(cpu, site, _size, _ctx):
        if address <= site < address + len(code):
            return
        provider = boundaries[site]
        r0, r1, r2 = (cpu.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        result = 0
        if provider == "guard_acquire":
            result = int(not (load(r0, 1)[0] & 1))
        elif provider == "guard_release":
            cpu.mem_write(r0, b"\1")
        elif provider == "atexit":
            teardown.append((r0, r1, r2))
        elif provider == "register":
            table = word(load(r0, 4))
            if table in tables:
                cls, complete, table_sha = tables[table]
                label = load(word(load(r0 + 4, 4)), 128).split(b"\0")[0].decode()
                recorded.append(dict(cls=cls, label=label, receiver=r0,
                                     table_sha256=table_sha, complete_dtor=complete))
            result = 1
        cpu.reg_write(UC_ARM_REG_R0, result)
        cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

    machine.hook_add(UC_HOOK_MEM_READ_UNMAPPED | UC_HOOK_MEM_WRITE_UNMAPPED, missing)
    machine.hook_add(UC_HOOK_CODE, call)
    for run in range(2):
        for reg, value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_SP, stack + 2048),
                           (UC_ARM_REG_LR, stop)):
            machine.reg_write(reg, value)
        machine.emu_start(address, stop, count=5000)
        assert machine.reg_read(UC_ARM_REG_PC) == stop
        assert len(recorded) == (run + 1) * len(TAGGED)
    assert recorded[:3] == recorded[3:]
    for row in recorded[:3]:
        assert len([item for item in teardown if item[:2] == (
            row["receiver"], row["complete_dtor"])]) == 1
    return dict(initializer=dict(mangled=INITIALIZER, **clear((address, offset, section, code))),
                order=recorded[:3])


def observe_destruction(elf, target, reference):
    prefix = qualification(CLASS_NAME)
    d0 = symbol(elf, "_Z" + prefix + "D0Ev")
    d1 = symbol(elf, "_Z" + prefix + "D1Ev")
    base_vtable = symbol(elf, "_ZTVN4Core9FormatterE")[0] + 8
    table = symbol(elf, "_ZTV" + prefix + "E")[0] + 8
    assert elf.get_section_by_name(".symtab").get_symbol_by_name("_Z" + prefix + "D2Ev") is None
    assert clear(d0) == target["range"]
    addr, _, _, code = d0
    instruction = word(code[28:32])
    assert instruction >> 24 == 0xEB
    displacement = (instruction & 0xFFFFFF) << 2
    deallocator = addr + 28 + 8 + displacement - ((displacement & 0x2000000) << 1)
    native_delete = elf.get_section_by_name(".symtab").get_symbol_by_name("_ZdlPv@@GLIBCXX_3.4")[0]["st_value"]
    assert deallocator == native_delete == reference["actual_deallocator"]
    variants = {}
    for kind, item in (("D0", d0), ("D1", d1)):
        addr, offset, section, code = item
        assert word(code[-4:]) == base_vtable
        rows = []
        for seed in (1, 99, 255):
            machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
            receiver, data, stack, stop = 0x22000000, 0x23000000, 0x24000000, 0x25000000
            for page in {value & ~4095 for value in
                         (addr, addr + len(code) - 1, deallocator, receiver, data, stack, stop)}:
                machine.mem_map(page, 4096)
            machine.mem_write(addr, code)
            machine.mem_write(receiver, packed(table) + bytes([seed]) * 28)
            other = bytes([seed]) * 32
            machine.mem_write(data, other)
            sp = stack + 2048
            for reg,value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, data),
                              (UC_ARM_REG_LR, stop), (UC_ARM_REG_SP, sp)):
                machine.reg_write(reg,value)
            events = []

            def visit(cpu, site, _size, _ctx):
                if addr <= site < addr + len(code):
                    return
                assert kind == "D0" and site == deallocator
                assert cpu.reg_read(UC_ARM_REG_R0) == receiver
                assert bytes(cpu.mem_read(receiver, 32)) == packed(base_vtable) + bytes([seed]) * 28
                cpu.mem_unmap(receiver, 4096)
                events.append("same_receiver_unmapped")
                cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

            machine.hook_add(UC_HOOK_CODE, visit)
            machine.emu_start(addr, stop, count=40)
            assert machine.reg_read(UC_ARM_REG_PC) == stop and machine.reg_read(UC_ARM_REG_SP) == sp
            try:
                value = bytes(machine.mem_read(receiver, 32))
            except UcError:
                accessible = False
            else:
                accessible = True
                assert value == packed(base_vtable) + bytes([seed]) * 28
            assert accessible == (kind == "D1")
            assert events == (["same_receiver_unmapped"] if kind == "D0" else [])
            assert bytes(machine.mem_read(data, 32)) == other
            rows.append(dict(seed=seed, receiver_mapped_at_end=accessible,
                             data_unchanged=True, observed=events))
        variants[kind] = dict(range=clear(item), cases=rows)
    assert variants["D0"]["cases"] == reference["native_cases"]
    return dict(variants=variants, actual_deallocator=deallocator, native_D2_present=False)


def generate():
    source = REFERENCE_PATH.read_bytes()
    assert sha(source) == REFERENCE_SHA256
    previous = {item["elf_sha256"]: item for item in json.loads(source)["per_occurrence_checks"].values()}
    originals = []
    for target in TARGETS:
        path = Path(target["elf_path"])
        assert sha(path.read_bytes()) == target["elf_sha256"]
        with path.open("rb") as stream:
            elf = ELFFile(stream)
            result = observe_destruction(elf, target, previous[target["elf_sha256"]])
            registration = observe_registration(elf)
        item, = [row for row in registration["order"] if row["cls"] == CLASS_NAME]
        originals.append(dict(result, registration=registration, name=item["label"], **target))
    assert [row["label"] for row in originals[0]["registration"]["order"]] == [
        row["label"] for row in originals[1]["registration"]["order"]]
    return {"originals": originals, "sealed_reference_sha256": REFERENCE_SHA256}


if __name__ == "__main__":
    Path(sys.argv[1]).write_text(json.dumps(generate(), indent=2) + "\n")
