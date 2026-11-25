"""Execute the exact Celsius destructor and verify the real dispatch boundary."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, __version__
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

CELSIUS = "N8Presonus2UC6Format7CelsiusE"
BASE = "N4Core12IntFormatterE"
FORMATTER = "N4Core9FormatterE"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def contents(elf, image, name):
    sym, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    sid, address, size = sym["st_shndx"], sym["st_value"], sym["st_size"]
    section = elf.get_section(sid)
    relative = address - section["sh_addr"]
    assert section["sh_type"] == "SHT_PROGBITS" and 0 <= relative <= section["sh_size"] - size
    offset = section["sh_offset"] + relative
    body = image[offset:offset + size]
    return dict(mangled=name, section=sid, address=address, size=size, file_offset=offset,
                range_sha256=sha(body), range_hex=body.hex()), body


def execute(identity, body, initial_point, incoming_label, final_point, deallocator):
    receiver, stop, stack, label = 0x810000, 0x820000, 0x830800, 0x840000
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    pages = set()

    def put(address, data):
        for page in range(address & ~4095, ((address + len(data) - 1) & ~4095) + 4096, 4096):
            if page not in pages:
                uc.mem_map(page, 4096)
                pages.add(page)
        uc.mem_write(address, data)

    def read32(address):
        return struct.unpack("<I", uc.mem_read(address, 4))[0]

    address = identity["address"]
    put(address, body)
    put(receiver, struct.pack("<3I", initial_point, label, label if incoming_label else 0))
    put(receiver + 12, bytes(range(12, 32)))
    before = bytes(uc.mem_read(receiver, 32))
    text = incoming_label.encode("ascii") + b"\0" if incoming_label else b"untouched\0"
    put(label, text)
    put(stop, bytes(4))
    put(stack, bytes(4))
    if deallocator is not None:
        put(deallocator, bytes.fromhex("1eff2fe1"))
    for reg, value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_SP, stack), (UC_ARM_REG_LR, stop)):
        uc.reg_write(reg, value)
    release = []

    def hit(machine, pc, _size, _data):
        if pc == deallocator:
            assert machine.reg_read(UC_ARM_REG_R0) == receiver
            assert read32(receiver) == final_point
            assert bytes(machine.mem_read(receiver+4, 28)) == before[4:]
            machine.mem_unmap(receiver, 4096)
            try:
                machine.mem_read(receiver, 1)
            except UcError:
                release.append(pc)
            else:
                raise AssertionError("Released receiver remained accessible")
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))
        else:
            assert address <= pc < address + len(body) - 4

    writes = []

    def write(_machine, _kind, location, size, value, _data):
        if not stack - 24 <= location <= stack - size:
            assert location == receiver and size == 4
            writes.append([location - receiver, size, value])

    uc.hook_add(UC_HOOK_CODE, hit)
    uc.hook_add(UC_HOOK_MEM_WRITE, write)
    uc.emu_start(address, stop, count=30)
    assert uc.reg_read(UC_ARM_REG_PC) == stop and uc.reg_read(UC_ARM_REG_SP) == stack
    assert uc.reg_read(UC_ARM_REG_R0) == receiver
    assert writes == [[0, 4, final_point]]
    assert bytes(uc.mem_read(label, len(text))) == text
    if deallocator is None:
        assert not release and bytes(uc.mem_read(receiver+4, 28)) == before[4:]
    else:
        assert release == [deallocator]
    return dict(label=incoming_label, dispatch_writes=writes, receiver_released=bool(release),
                unrelated_label_preserved=True)


def observe(packet, rootfs, direct):
    ctx = json.loads(packet.read_text())
    mode = ctx["task"]["id"].removeprefix("sqlite02_celsius_")
    roles = json.loads(direct.read_text())["native"]
    entries = []
    for item in ctx["originals"]:
        original = item["original"]
        image = (rootfs / Path(original["elf_path"]).relative_to("rootfs")).read_bytes()
        assert sha(image) == original["elf"]
        elf = ELFFile(io.BytesIO(image))
        assert elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM"
        identity, body = contents(elf, image, original["mangled"])
        assert all(original[key] == value for key, value in identity.items())
        table, raw_table = contents(elf, image, "_ZTV" + CELSIUS)
        rtti, raw_rtti = contents(elf, image, "_ZTI" + CELSIUS)
        base, _ = contents(elf, image, "_ZTI" + BASE)
        formatter, _ = contents(elf, image, "_ZTV" + FORMATTER)
        assert struct.unpack_from("<I", raw_rtti, 8)[0] == base["address"]
        assert struct.unpack_from("<I", raw_table, 4)[0] == rtti["address"]
        assert struct.unpack_from("<I", raw_table, 12 if mode == "deleting_destroy" else 8)[0] == identity["address"]
        for offset, method in ((16, "5print"), (20, "4scan")):
            row, _ = contents(elf, image, "_ZNK4Core12IntFormatter" + method + "ERNS_9Formatter4DataE")
            assert struct.unpack_from("<I", raw_table, offset)[0] == row["address"]
        final_point = formatter["address"] + 8
        assert struct.unpack_from("<I", body, len(body) - 4)[0] == final_point
        deallocator = None
        if mode == "deleting_destroy":
            role = next(x for x in roles if x["original"]["elf"] == original["elf"])
            target, = [x for x in role["site_evidence"] if x["kind"] == "branch"]
            assert target["code_offset"] == 28 and "_ZdlPv@@GLIBCXX_3.4" in target["names"]
            branch, = Cs(CS_ARCH_ARM, CS_MODE_ARM).disasm(body[28:32], identity["address"]+28)
            assert branch.mnemonic == "bl" and int(branch.op_str[1:], 16) == target["destination"]
            deallocator = target["destination"]
        boundary = dict(derived_vtable=table, derived_rtti=rtti, intformatter_rtti=base,
                        final_vtable=formatter, operator_delete=deallocator)
        entries.append(dict(original=original, boundaries=boundary,
                            cases=[execute(identity, body, table["address"]+8, label, final_point, deallocator)
                                   for label in (None, "C", "degrees C")]))
    return dict(mode=mode, engine=f"Unicorn {__version__}", entries=entries)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("rootfs", type=Path)
    parser.add_argument("direct", type=Path)
    args = parser.parse_args()
    print(json.dumps(observe(args.packet, args.rootfs, args.direct), indent=2))
