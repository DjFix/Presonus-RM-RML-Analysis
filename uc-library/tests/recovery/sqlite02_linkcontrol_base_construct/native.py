"""Execute the sealed LinkControl ARM range and record app-side lifecycle effects."""
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
    UC_ARM_REG_SP,
)

TASK = Path(__file__).resolve().parent.name
PACKET = Path("temp/recovery-work/sqlite-issued/packet") / TASK / "CONTEXT.json"
ARENA, STACK, STOP = 0x1000000, 0x2000000, 0x3000000
OBJECT = ARENA + 0x100
PROVIDERS = ARENA + 0x1000
RECT, PRIMARY, SIDE, LEFT, RIGHT = (PROVIDERS + i * 0x100 for i in range(5))
CASES = (
    (0, 0, 0, 0, 0, 0, 0),
    (1, 0, 1, -8, -4, 11, 20),
    (0, 2, 2, 13, 9, 26, 38),
    (1, 1, 3, 20, 30, 55, 60),
    (1, 2, 3, -86, -4, 1, 15),
    (1, 3, 3, 0, 0, 50, 32),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def u32(cpu, address):
    return struct.unpack("<I", cpu.mem_read(address, 4))[0]


def put32(cpu, address, value):
    cpu.mem_write(address, struct.pack("<I", value))


def symbol_range(elf, image, symtab, name):
    symbol, = symtab.get_symbol_by_name(name)
    section_number = symbol["st_shndx"]
    section = elf.get_section(section_number)
    address = symbol["st_value"]
    size = symbol["st_size"]
    relative = address - section["sh_addr"]
    assert 0 <= relative <= relative + size <= section["sh_size"]
    offset = section["sh_offset"] + relative
    body = image[offset:offset + size]
    return body, dict(mangled=name, address=address, size=size,
                      file_offset=offset, section=section_number,
                      section_name=section.name, range_sha256=digest(body))


def bindings(original, sites):
    image = Path(original["elf_path"]).read_bytes()
    assert digest(image) == original["elf"]
    elf = ELFFile(io.BytesIO(image))
    assert elf["e_machine"] == "EM_ARM" and elf.little_endian
    symtab = elf.get_section_by_name(".symtab")
    body, target = symbol_range(elf, image, symtab, original["mangled"])
    assert all(original[key] == value for key, value in target.items())
    assert original["range_hex"] == body.hex()
    table, table_range = symbol_range(elf, image, symtab, "_ZTVN8Presonus11LinkControlE")
    address_point = struct.unpack("<I", body[-4:])[0]
    assert address_point == table_range["address"] + 8
    assert address_point == next(site["value"] for site in sites if site["kind"] == "literal")
    variant = original["mangled"].split("LinkControl")[1][:2]
    slots = [i for i in range(0, len(table), 4)
             if struct.unpack_from("<I", table, i)[0] == target["address"]]
    assert bool(slots) == (variant in ("D0", "D1"))
    provider_ranges = {}
    for site in sites:
        if site["kind"] != "branch" or not site["names"]:
            continue
        name = site["names"][0]
        if name.startswith("_ZN4Core"):
            _, record = symbol_range(elf, image, symtab, name)
            assert record["address"] == site["destination"]
            provider_ranges[name] = record
        elif name.startswith("_ZdlPv"):
            plt = elf.get_section_by_name(".plt")
            address = site["destination"]
            index, remainder = divmod(address - plt["sh_addr"] - 20, 12)
            assert index >= 0 and remainder == 0
            relocations = elf.get_section_by_name(".rel.plt")
            entry = relocations.get_relocation(index)
            symbol = elf.get_section(relocations["sh_link"]).get_symbol(entry["r_info_sym"])
            assert symbol.name == "_ZdlPv"
            offset = plt["sh_offset"] + address - plt["sh_addr"]
            provider_ranges["_ZdlPv"] = dict(mangled=symbol.name, address=address,
                file_offset=offset, got=entry["r_offset"],
                range_sha256=digest(image[offset:offset + 12]))
    return body, address_point, variant, slots, table_range, provider_ranges


def execute(original, body, point, variant, providers, row, exe):
    has_primary, side, images, *rect = row
    primary = PRIMARY if has_primary else 0
    side_param = PRIMARY if side == 1 else SIDE if side else 0
    entry = original["address"]
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for address, size in ((0x8000, 0x140000), (ARENA, 8192), (STACK, 4096)):
        cpu.mem_map(address, size)
    cpu.mem_write(entry, body)
    cpu.mem_write(OBJECT, b"\xa7" * 104)
    cpu.mem_write(RECT, struct.pack("<4i", *rect))
    ctor = variant.startswith("C")
    if not ctor:
        for offset, value in ((0x58, LEFT if images & 1 else 0),
                              (0x5c, RIGHT if images & 2 else 0),
                              (0x60, 0), (0x64, side_param)):
            put32(cpu, OBJECT + offset, value)
        put32(cpu, LEFT + 0x34, int(bool(images & 1)))
        put32(cpu, RIGHT + 0x34, int(bool(images & 2)))

    for reg, val in ((UC_ARM_REG_R0, OBJECT), (UC_ARM_REG_R1, RECT),
                     (UC_ARM_REG_R2, primary), (UC_ARM_REG_LR, STOP),
                     (UC_ARM_REG_SP, STACK + 0x800)):
        cpu.reg_write(reg, val)
    calls, writes, trace, detachments = [], [], [], []
    released = False
    control_result = []
    stack = STACK + 0x800
    targets = {record["address"]: name for name, record in providers.items()}

    def refs():
        return [u32(cpu, LEFT + 0x34), u32(cpu, RIGHT + 0x34)]

    def observe(address, lr):
        nonlocal released
        name = targets[address]
        calls.append(dict(mangled=name, address=address, call_site=lr - 4,
                          r0=cpu.reg_read(UC_ARM_REG_R0),
                          r1=cpu.reg_read(UC_ARM_REG_R1),
                          r2=cpu.reg_read(UC_ARM_REG_R2)))
        call = calls[-1]
        if "ControlC2" in name:
            assert (call["r0"], call["r1"], call["r2"]) == (OBJECT, RECT, primary)
            args = [int(bool(call["r2"])), 0, 0, *struct.unpack("<4i", cpu.mem_read(RECT, 16))]
            result = subprocess.run([str(exe.resolve()), "provider"],
                input=" ".join(map(str, args)) + "\n", check=True,
                capture_output=True, text=True)
            control_result.extend(map(int, result.stdout.split()))
        elif "removeObserver" in name:
            assert call["r0"] == side_param and call["r1"] == OBJECT + 0x44
            detachments.append([1 if side_param == primary else 2, *refs()])
        elif "ControlD2" in name:
            assert call["r0"] == OBJECT and refs() == [0, 0]
            if primary:
                detachments.append([1, *refs()])
        else:
            assert name == "_ZdlPv" and call["r0"] == OBJECT
            assert calls[-2]["mangled"].endswith("ControlD2Ev") and refs() == [0, 0]
            cpu.mem_unmap(ARENA, 4096)
            released = True
        cpu.reg_write(UC_ARM_REG_PC, lr)

    def code_hook(uc, address, size, _):
        if address in targets:
            observe(address, uc.reg_read(UC_ARM_REG_LR))
        else:
            assert entry <= address < entry + len(body) - 4
            trace.append(address)

    def write_hook(uc, access, address, size, value, _):
        if not STACK <= address < STACK + 4096:
            assert ARENA <= address < ARENA + 8192 and size == 4
            writes.append([address, value])

    cpu.hook_add(UC_HOOK_CODE, code_hook)
    cpu.hook_add(UC_HOOK_MEM_WRITE, write_hook)
    cpu.emu_start(entry, STOP, count=150)
    assert cpu.reg_read(UC_ARM_REG_PC) == STOP and cpu.reg_read(UC_ARM_REG_SP) == stack
    if ctor:
        assert cpu.reg_read(UC_ARM_REG_R0) == OBJECT
        assert dict(writes) == {OBJECT: point, OBJECT + 4: point + 0x6c,
                               OBJECT + 0x44: point + 0x88, OBJECT + 0x58: 0,
                               OBJECT + 0x5c: 0, OBJECT + 0x60: 0, OBJECT + 0x64: 0}
        assert control_result == [has_primary, *rect]
        normalized = control_result
    else:
        assert released == (variant == "D0")
        expected_writes = [[OBJECT, point], [OBJECT + 4, point + 0x6c],
                           [OBJECT + 0x44, point + 0x88]]
        if images & 2:
            expected_writes.extend(([RIGHT + 0x34, 0], [OBJECT + 0x5c, 0]))
        if images & 1:
            expected_writes.extend(([LEFT + 0x34, 0], [OBJECT + 0x58, 0]))
        assert dict(writes) == dict(expected_writes)
        assert [w for w in writes if w[0] in (RIGHT + 0x34, OBJECT + 0x5c, LEFT + 0x34, OBJECT + 0x58)] == expected_writes[3:]
        normalized = [int(released), len(detachments), *(x for d in detachments for x in d)]
    return dict(inputs=list(row), calls=calls, writes=writes, instructions=trace,
                receiver_released=released, normalized=normalized)


def generate(exe):
    packet = json.loads(PACKET.read_text())
    binding, = packet["task"]["review"]["evidence"]
    evidence_raw = Path(binding["path"]).read_bytes()
    assert digest(evidence_raw) == binding["sha256"]
    entry, = packet["originals"]
    original = entry["original"]
    evidence, = [item for item in json.loads(evidence_raw)["items"]
                 if item["original"]["mangled"] == original["mangled"]]
    assert all(original[key] == value for key, value in evidence["original"].items())
    body, point, variant, slots, table, providers = bindings(original, evidence["native_sites"])
    return dict(original=original, variant=variant, native_vtable_slots=slots,
                vtable=table, provider_ranges=providers, cases=[
                    execute(original, body, point, variant, providers, row, exe)
                    for row in CASES])
