"""Offline instruction replay of the original registrar and bounded call exits."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, __version__
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_PC

PREFIX = "_ZN8Presonus2UC15ServerRegistrar"
REMOTE_REMOVE = PREFIX + "6removeEPNS0_12RemoteServerE"
DELETE_REMOTE = "_ZN8Presonus2UC12RemoteServerD0Ev"
REMOTE_TABLE = "_ZTVN8Presonus2UC12RemoteServerE"
METADATA = {1: ("desk", 123, True), 2: ("desk", 123, False), 3: ("desk", 123, True),
            4: ("desk", 124, True), 5: ("other", 123, True), 6: ("", 65535, True)}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def symbol(elf, name):
    row, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    return row


def function(elf, image, name):
    row = symbol(elf, name)
    section = elf.get_section(row["st_shndx"])
    address, size = row["st_value"], row["st_size"]
    relative = address - section["sh_addr"]
    assert row["st_info"]["type"] == "STT_FUNC"
    assert section.name == ".text" and section["sh_type"] == "SHT_PROGBITS"
    assert 0 <= relative <= section["sh_size"] - size
    offset = section["sh_offset"] + relative
    code = image[offset:offset + size]
    identity = dict(mangled=name, address=address, size=size, section=row["st_shndx"],
                    file_offset=offset, range_sha256=sha(code), range_hex=code.hex())
    return identity, code


def read_at(elf, image, address, size):
    for segment in elf.iter_segments():
        delta = address - segment["p_vaddr"]
        if segment["p_type"] == "PT_LOAD" and 0 <= delta <= segment["p_memsz"] - size:
            offset = segment["p_offset"] + delta
            count = min(size, max(0, segment["p_filesz"] - delta))
            return image[offset:offset + count] + b"\0" * (size - count)
    raise ValueError(f"No ELF mapping for {address:#x}")


def instruction_destination(identity, code, at, mnemonic):
    begin = identity["address"] + at
    insn, = Cs(CS_ARCH_ARM, CS_MODE_ARM).disasm(code[at:at+4], begin)
    assert insn.mnemonic == mnemonic
    return int(insn.op_str.removeprefix("#"), 16)


def execute(elf, image, original, code, mode, case, evidence):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    pages = set()
    prefix = 0x800000
    registrar, local_data, remote_data, enlarged = (prefix + i * 4096 for i in range(1, 5))
    arg_text, stack, stop = 0x890080, 0x8a0800, 0x8b0000
    identities = {i: 0x810000 + i * 4096 for i in METADATA}
    labels = {address: label for label, address in identities.items()}
    initial, other = case["initial"], [5]
    is_local = mode.endswith("local")
    targets, body_ranges = {}, []

    def put(address, data):
        for page in range(address & ~4095, ((address + len(data) - 1) & ~4095) + 4096, 4096):
            if page not in pages:
                uc.mem_map(page, 4096)
                pages.add(page)
        uc.mem_write(address, data)

    def put32(address, value):
        put(address, struct.pack("<I", value))

    def u32(address):
        return struct.unpack("<I", uc.mem_read(address, 4))[0]

    def cstr(address):
        result = bytearray()
        for at in range(address, address + 256):
            value = uc.mem_read(at, 1)[0]
            if value == 0:
                return result.decode("ascii")
            result.append(value)
        raise ValueError("synthetic fixture name exceeds bound")

    def bind_target(name, action):
        address = symbol(elf, name)["st_value"]
        targets[address] = action
        put32(address, 0xe12fff1e)
        return address

    def bind_body(identity, body):
        address = identity["address"]
        put(address, body)
        body_ranges.append(range(address, address + len(body)))

    bind_body(original, code)
    notified = None
    format_name = "Local" if is_local else "Remote"
    array_offset, used_offset, max_offset = (4, 8, 12) if is_local else (24, 28, 32)
    if mode.startswith("add"):
        resize = f"_ZN4Core6VectorIPN8Presonus2UC{len(format_name)+6}{format_name}ServerEE6resizeEi"
        resize_address = bind_target(resize, "resize")
        assert instruction_destination(original, code, 60 if is_local else 76, "bl") == resize_address
        if not is_local:
            notified = bind_target(PREFIX + "17notifyServerAddedEPNS0_6ServerE", "added")
    elif mode == "remove_manual":
        remote, remote_code = function(elf, image, REMOTE_REMOVE)
        assert instruction_destination(original, code, 152, "bl") == remote["address"]
        bind_body(remote, remote_code)
        delete_address = bind_target(DELETE_REMOTE, "delete")
        table = symbol(elf, REMOTE_TABLE)["st_value"] + 8
        assert struct.unpack("<I", read_at(elf, image, table + 4, 4))[0] == delete_address
        put(table, read_at(elf, image, table, 8))
        for label, (address, port, manual) in METADATA.items():
            obj = identities[label]
            put32(obj, table)
            put(obj + 0x124, address.encode("ascii") + b"\0")
            put(obj + 0x324, struct.pack("<H", port))
            put(obj + 0x32c, bytes([manual]))
        strcmp = instruction_destination(original, code, 116, "bl")
        assert any(x["destination"] == strcmp and "strcmp@@GLIBC_2.4" in x["names"]
                   for x in evidence["site_evidence"] if x["kind"] == "branch")
        targets[strcmp] = "strcmp"
        put32(strcmp, 0xe12fff1e)
        empty, = struct.unpack_from("<I", code, len(code)-8)
        put(empty, read_at(elf, image, empty, 1))
        assert cstr(empty) == ""
        default, = struct.unpack_from("<I", remote_code, len(remote_code)-4)
        put(default, read_at(elf, image, default, 4))
        notified = bind_target(PREFIX + "19notifyServerRemovedEPNS0_6ServerE", "removed")
        assert instruction_destination(remote, remote_code, 96, "b") == notified
    else:
        default, = struct.unpack_from("<I", code, len(code)-4)
        put(default, read_at(elf, image, default, 4))
        notified = bind_target(PREFIX + "19notifyServerRemovedEPNS0_6ServerE", "removed")
        assert instruction_destination(original, code, 96, "b") == notified
    if mode == "add_remote":
        assert instruction_destination(original, code, 68, "b") == notified

    for address, rows in ((local_data, initial if is_local else other),
                          (remote_data, other if is_local else initial)):
        put(address, struct.pack("<8I", *(identities[i] for i in rows), *([0] * (8-len(rows)))))
    put(registrar, bytes(80))
    for address, rows, begin in ((local_data, initial if is_local else other, 4),
                                 (remote_data, other if is_local else initial, 24)):
        capacity = len(rows) if case.get("full") and begin == array_offset else 8
        put(registrar+begin, struct.pack("<III", address, len(rows), capacity))
    put(enlarged, bytes(32))
    put32(stack, 0)
    put32(stop, 0)
    if mode == "remove_manual":
        needle = case["argument"]
        if needle is not None:
            put(arg_text, needle.encode("ascii") + b"\0")
        argument = arg_text if needle is not None else 0
    else:
        argument = identities[case["argument"]]
    for reg, val in ((UC_ARM_REG_R0, registrar), (UC_ARM_REG_R1, argument),
                     (UC_ARM_REG_R2, case.get("port", 0)), (UC_ARM_REG_SP, stack),
                     (UC_ARM_REG_LR, stop)):
        uc.reg_write(reg, val)

    def roster(offset):
        array, used = u32(registrar + offset), u32(registrar + offset + 4)
        return [labels[u32(array + 4*i)] for i in range(used)]

    events, calls = [], []

    def on_instruction(machine, pc, _size, _):
        action = targets.get(pc)
        if action is None:
            assert any(pc in addresses for addresses in body_ranges), hex(pc)
            return
        r0, r1 = machine.reg_read(UC_ARM_REG_R0), machine.reg_read(UC_ARM_REG_R1)
        result = r0
        if action == "resize":
            assert r0 == registrar + array_offset - 4 and r1 == len(initial) + 1
            put(enlarged, bytes(machine.mem_read(u32(registrar + array_offset), 32)))
            put32(registrar + array_offset, enlarged)
            put32(registrar + max_offset, 8)
            result = 1
            calls.append([action, r1])
        elif action == "strcmp":
            left, right = cstr(r0), cstr(r1)
            calls.append([action, left, right])
            result = int(left != right)
        elif action == "delete":
            events.append([action, labels[r0], roster(array_offset)])
        else:
            assert r0 == registrar
            events.append([action, labels[r1], roster(array_offset)])
        machine.reg_write(UC_ARM_REG_R0, result)
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    uc.hook_add(UC_HOOK_CODE, on_instruction)
    uc.emu_start(original["address"], stop, count=1200)
    assert uc.reg_read(UC_ARM_REG_PC) == stop and uc.reg_read(UC_ARM_REG_SP) == stack
    assert roster(24 if is_local else 4) == other
    return dict(case, final=roster(array_offset), events=events, calls=calls)


CASES = {
    "add_local": [dict(initial=[], argument=1, full=True), dict(initial=[1, 2], argument=1),
                  dict(initial=[2], argument=3, full=True)],
    "add_remote": [dict(initial=[], argument=1, full=True, listeners=0),
                   dict(initial=[1, 2], argument=3, listeners=2),
                   dict(initial=[2], argument=3, full=True, listeners=2)],
    "remove_local": [dict(initial=[1, 2, 3], argument=2, listeners=2),
                     dict(initial=[1, 2], argument=3, listeners=2),
                     dict(initial=[1, 1, 2], argument=1, listeners=0)],
    "remove_remote": [dict(initial=[1, 2, 3], argument=2, listeners=2),
                      dict(initial=[1, 2], argument=3, listeners=2),
                      dict(initial=[], argument=2, listeners=0)],
    "remove_manual": [dict(initial=[1, 2, 3, 4, 5], argument="desk", port=123, listeners=2),
                      dict(initial=[1, 2, 3, 4, 5], argument="desk", port=44, listeners=2),
                      dict(initial=[2, 6], argument=None, port=65535, listeners=0)],
}


def observe(packet, rootfs, direct):
    context = json.loads(packet.read_text())
    mode = context["task"]["id"].removeprefix("sqlite02_serverregistrar_")
    evidence = json.loads(direct.read_text())["native"]
    entries = []
    for item in context["originals"]:
        original = item["original"]
        image = (rootfs / Path(original["elf_path"]).relative_to("rootfs")).read_bytes()
        assert sha(image) == original["elf"]
        elf = ELFFile(io.BytesIO(image))
        assert elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM"
        identity, code = function(elf, image, original["mangled"])
        assert all(original[key] == value for key, value in identity.items())
        role = next(x for x in evidence if x["original"]["elf"] == original["elf"])
        dependent = function(elf, image, REMOTE_REMOVE)[0] if mode == "remove_manual" else None
        entries.append(dict(original=original, remote_remove=dependent,
                            cases=[execute(elf, image, identity, code, mode, case, role)
                                   for case in CASES[mode]]))
    return dict(mode=mode, engine=f"Unicorn {__version__}", entries=entries)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("rootfs", type=Path)
    parser.add_argument("direct", type=Path)
    args = parser.parse_args()
    print(json.dumps(observe(args.packet, args.rootfs, args.direct), indent=2))
