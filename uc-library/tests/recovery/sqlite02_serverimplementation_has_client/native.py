"""Replay the verified app-owned ARM roster query or destructor offline."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, __version__
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

PREFIX = "_ZN8Presonus2UC20ServerImplementation"
TABLE = "_ZTVN8Presonus2UC20ServerImplementationE"
VECTOR_D1 = "_ZN4Core6VectorIPN8Presonus2UC18ClientSubscriptionEED1Ev"
DELETE = "_ZdlPv@@GLIBCXX_3.4"
IDS = [-2147483648, 7, 7, -9, 2147483647]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def row(elf, name):
    sym, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    return sym


def contents(elf, image, sym):
    sid, address, size = sym["st_shndx"], sym["st_value"], sym["st_size"]
    section = elf.get_section(sid)
    relative = address - section["sh_addr"]
    assert section["sh_type"] == "SHT_PROGBITS" and 0 <= relative <= section["sh_size"] - size
    offset = section["sh_offset"] + relative
    body = image[offset:offset+size]
    return dict(mangled=sym.name, section=sid, address=address, size=size,
                file_offset=offset, range_sha256=sha(body), range_hex=body.hex()), body


def execute(original, body, mode, identifiers, query, boundaries):
    receiver, vector, stack, stop, unrelated = 0x810000, 0x820000, 0x890800, 0x8a0000, 0x8b0000
    children = {0x830000 + 0x1000 * i: i + 1 for i in range(len(identifiers))}
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    pages = set()

    def put(address, data):
        for page in range(address & ~4095, ((address + len(data) - 1) & ~4095) + 4096, 4096):
            if page not in pages:
                uc.mem_map(page, 4096)
                pages.add(page)
        uc.mem_write(address, data)

    def put32(address, value):
        put(address, struct.pack("<I", value))

    def is_readable(address):
        return any(begin <= address <= end for begin, end, _ in uc.mem_regions())

    def release(address):
        assert is_readable(address)
        uc.mem_unmap(address, 4096)
        assert not is_readable(address)
        try:
            uc.mem_read(address, 1)
        except UcError:
            return
        raise AssertionError("Released fixture page is still readable")

    address = original["address"]
    put(address, body)
    put(receiver, bytes(256))
    put32(stack, 0)
    put32(stop, 0)
    sentinel = bytes((7 * i + 29) % 256 for i in range(256))
    put(unrelated, sentinel)
    put(receiver + 0x14, struct.pack("<2I", unrelated, unrelated))
    if children:
        put(vector, struct.pack("<" + "I" * len(children), *children))
        put32(receiver + 0x20, vector)
    put32(receiver + 0x24, len(children))
    for child, identifier in zip(children, identifiers, strict=True):
        put32(child, identifier & 0xffffffff)
    for reg, val in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, query & 0xffffffff),
                     (UC_ARM_REG_SP, stack), (UC_ARM_REG_LR, stop)):
        uc.reg_write(reg, val)

    writes, events = [], []
    for target in boundaries.get("call_addresses", {}).values():
        put32(target, 0xe12fff1e)

    def hit(machine, pc, _size, _data):
        if address <= pc < address + len(body):
            return
        argument = machine.reg_read(UC_ARM_REG_R0)
        calls = boundaries["call_addresses"]
        if pc == calls["delete"]:
            if argument == receiver:
                assert mode == "deleting_destroy"
                release(receiver)
                events.append(["receiver", 0])
            else:
                label = children[argument]
                release(argument)
                events.append(["child", label])
        elif pc == calls["vector_destructor"]:
            assert argument == receiver + 0x1c and all(not is_readable(child) for child in children)
            pointer, = struct.unpack("<I", uc.mem_read(argument + 4, 4))
            if pointer:
                assert pointer == vector
                release(pointer)
                events.append(["vector", 0])
        else:
            raise AssertionError(f"Unexpected branch to {pc:#x}")
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    def write(_machine, _kind, location, size, value, _data):
        if not stack - 32 <= location <= stack - size:
            assert location == receiver and size == 4
            writes.append([location - receiver, size, value])

    uc.hook_add(UC_HOOK_CODE, hit)
    uc.hook_add(UC_HOOK_MEM_WRITE, write)
    uc.emu_start(address, stop, count=250)
    assert uc.reg_read(UC_ARM_REG_PC) == stop and uc.reg_read(UC_ARM_REG_SP) == stack
    assert bytes(uc.mem_read(unrelated, 256)) == sentinel
    r0 = uc.reg_read(UC_ARM_REG_R0)
    if mode.endswith("destroy"):
        assert writes == [[0, 4, boundaries["vtable_address_point"]]]
        assert all(not is_readable(child) for child in children)
        assert not is_readable(vector)
        assert is_readable(receiver) == (mode != "deleting_destroy")
        assert r0 == receiver
        result = 0
    else:
        assert not writes and not events and is_readable(receiver)
        if children:
            assert struct.unpack("<" + "I" * len(children), uc.mem_read(vector, len(children)*4)) == tuple(children)
        result = children.get(r0, 0) if mode == "find_client" else r0
        assert (r0 == 0 or r0 in children) if mode == "find_client" else result in (0, 1)
    return dict(identifiers=identifiers, query=query, result=result, writes=writes,
                releases=events, unrelated_provider_preserved=True)


def observe(packet, rootfs, direct):
    ctx = json.loads(packet.read_text())
    mode = ctx["task"]["id"].removeprefix("sqlite02_serverimplementation_")
    native = json.loads(direct.read_text())["native"]
    entries = []
    for item in ctx["originals"]:
        original = item["original"]
        image = (rootfs / Path(original["elf_path"]).relative_to("rootfs")).read_bytes()
        assert sha(image) == original["elf"]
        elf = ELFFile(io.BytesIO(image))
        assert elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM"
        sym = row(elf, original["mangled"])
        assert sym["st_info"]["type"] == "STT_FUNC"
        assert elf.get_section(sym["st_shndx"]).name == ".text"
        actual, body = contents(elf, image, sym)
        assert all(original[key] == value for key, value in actual.items())
        boundaries = {}
        if mode.endswith("destroy"):
            table, data = contents(elf, image, row(elf, TABLE))
            point = table["address"] + 8
            assert struct.unpack_from("<I", body, 124 if mode == "deleting_destroy" else 116)[0] == point
            if mode != "base_destroy":
                slot = 16 if mode == "deleting_destroy" else 12
                assert struct.unpack_from("<I", data, slot)[0] == original["address"]
            else:
                complete, complete_body = contents(elf, image, row(elf, PREFIX + "D1Ev"))
                assert original["address"] != complete["address"] and body != b""
                # Separate verified ranges differ only at the relocated external
                # branch displacements. Require all other bytes to agree and
                # independently verify both instructions resolve to one target.
                call_sites = (88, 104)
                assert len(body) == len(complete_body)
                normalized = []
                destinations = []
                for identity, code in ((actual, body), (complete, complete_body)):
                    compare = bytearray(code)
                    targets = []
                    for site in call_sites:
                        start = identity["address"] + site
                        branch, = Cs(CS_ARCH_ARM, CS_MODE_ARM).disasm(code[site:site+4], start)
                        assert branch.mnemonic == "bl"
                        targets.append(int(branch.op_str.removeprefix("#"), 16))
                        compare[site:site+4] = b"BL  "
                    normalized.append(bytes(compare))
                    destinations.append(targets)
                assert normalized[0] == normalized[1]
                assert destinations[0] == destinations[1]
                boundaries["relocated_sibling_branches"] = dict(offsets=list(call_sites), targets=destinations[0])
                boundaries["ordinary_complete_sibling"] = complete
            role = next(x for x in native if x["original"]["elf"] == original["elf"])
            branches = {x["code_offset"]: x for x in role["site_evidence"] if x["kind"] == "branch"}
            vector_d1 = row(elf, VECTOR_D1)["st_value"]
            assert branches[104]["destination"] == vector_d1
            assert VECTOR_D1 in branches[104]["names"] and DELETE in branches[88]["names"]
            deleting = branches[88]["destination"]
            if mode == "deleting_destroy":
                assert branches[112]["destination"] == deleting and DELETE in branches[112]["names"]
            boundaries.update(vtable=table, vtable_address_point=point,
                              call_addresses=dict(vector_destructor=vector_d1, delete=deleting))
            cases = [([], 0), ([7], 0), (IDS, 0)]
        elif mode == "has_clients":
            cases = [([], 0), ([7], 0), (IDS, 0)]
        else:
            cases = [([], 0), (IDS, 0), (IDS, -2147483648), (IDS, 7),
                     (IDS, -9), (IDS, 2147483647), (IDS, -2147483647)]
        entries.append(dict(original=original, boundaries=boundaries,
                            cases=[execute(actual, body, mode, ids, arg, boundaries) for ids, arg in cases]))
    return dict(mode=mode, engine=f"Unicorn {__version__}", entries=entries)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("rootfs", type=Path)
    parser.add_argument("direct", type=Path)
    args = parser.parse_args()
    print(json.dumps(observe(args.packet, args.rootfs, args.direct), indent=2))
