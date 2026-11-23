"""Execute exact channel-type routing and the original offline mixer lookup."""

import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

import unicorn as uc
from elftools.elf.elffile import ELFFile
from unicorn import arm_const as arm

THIS, MIXER, PARENT, STACK, STOP = 0x40000000, 0x40001000, 0x40002000, 0x50000800, 0x71000000
SUPPLEMENT_SHA = "00cff9a6d166cced4acf07c9b2fe841eae64e08ab8064512ddf51f5f08e6bc8b"
CASES = [[0, 0, "line"], [0, 1, "line"], [1, 0, "aux"]] + [
    [1, 1, name] for name in (
        "line", "return", "fxreturn", "talkback", "aux", "fxbus",
        "sub", "main", "mono", "signalgen", "unknown", "",
    )
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def elf_range(elf, name):
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    section = elf.get_section(symbol["st_shndx"])
    address, size = symbol["st_value"], symbol["st_size"]
    off = address - section["sh_addr"]
    assert 0 <= off <= off + size <= section["sh_size"]
    data = section.data()[off:off + size]
    return data, {"mangled": name, "address": address, "size": size, "section": symbol["st_shndx"],
                  "sha256": sha(data), "file_offset": section["sh_offset"] + off}


def authenticated_range(elf, expected):
    data, info = elf_range(elf, expected["mangled"])
    assert all(expected[k] == info[k] for k in ("sha256", "file_offset", "address", "size"))
    return data, info


def readonly_strings(elf, lookup):
    ptrs = struct.unpack("<10I", lookup[-40:])
    payloads = {}
    for pc in ptrs:
        section, = (s for s in elf.iter_sections() if s["sh_flags"] & 2
                    and s["sh_addr"] <= pc < s["sh_addr"] + s["sh_size"])
        off = pc - section["sh_addr"]
        string = section.data()[off:off + 32].split(b"\0", 1)[0]
        assert string and len(string) < 32
        payloads[pc] = string + b"\0"
    return payloads


def replay(body, getter, vtable, provider, payloads, strcmp, inputs):
    bound, attached, name = inputs
    code, get = body
    prov_code, prov = provider
    table, vt = vtable
    machine = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_ARM)
    memory = {get["address"]: code, prov["address"]: prov_code, vt["address"]: table, **payloads}
    pages = {THIS, MIXER, PARENT, STACK & ~4095, STOP, strcmp & ~4095}
    for address, data in memory.items():
        pages.update(range(address & ~4095, (address + len(data) + 4095) & ~4095, 4096))
    for page in sorted(pages):
        machine.mem_map(page, 4096)
    for address, data in memory.items():
        machine.mem_write(address, data)
    for address, value in (
        (THIS + 0x1D8, MIXER if bound else 0),
        (THIS + 0x50, PARENT if attached else 0),
        (MIXER, vt["address"] + 8),
    ):
        machine.mem_write(address, struct.pack("<I", value))
    machine.mem_write(PARENT + 8, name.encode() + b"\0")
    calls, compare_names, writes = [], [], []

    def cstring(address):
        return bytes(machine.mem_read(address, 32)).split(b"\0", 1)[0]

    def visit(emu, pc, _size, _data):
        r0, r1 = (emu.reg_read(r) for r in (arm.UC_ARM_REG_R0, arm.UC_ARM_REG_R1))
        if pc == strcmp:
            assert r0 == PARENT + 8 and r1 in payloads
            a, b = cstring(r0), cstring(r1)
            compare_names.append(b.decode())
            emu.reg_write(arm.UC_ARM_REG_R0, ((a > b) - (a < b)) & 0xFFFFFFFF)
            emu.reg_write(arm.UC_ARM_REG_PC, emu.reg_read(arm.UC_ARM_REG_LR))
        elif pc == prov["address"]:
            assert (r0, r1) == (MIXER, PARENT)
            calls.append("getChannelGroupType")
        else:
            assert (get["address"] <= pc < get["address"] + get["size"] or
                    prov["address"] <= pc < prov["address"] + prov["size"] - 40), hex(pc)

    def write(_machine, _kind, address, size, value, _data):
        if not (STACK & ~4095) <= address < STACK:
            writes.append([address, size, value])

    machine.hook_add(uc.UC_HOOK_CODE, visit)
    machine.hook_add(uc.UC_HOOK_MEM_WRITE, write)
    for reg, val in ((arm.UC_ARM_REG_R0, THIS), (arm.UC_ARM_REG_SP, STACK), (arm.UC_ARM_REG_LR, STOP)):
        machine.reg_write(reg, val)
    machine.emu_start(get["address"], STOP, count=200)
    assert machine.reg_read(arm.UC_ARM_REG_PC) == STOP
    assert not writes and bool(calls) == bool(bound and attached)
    result = machine.reg_read(arm.UC_ARM_REG_R0)
    if result >= 0x80000000:
        result -= 0x100000000
    return {"inputs": inputs, "output": result, "application_calls": calls,
            "modeled_strcmp_arguments": compare_names, "nonstack_writes": writes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("client", "server", "packet", "supplement"):
        parser.add_argument("--" + name, required=True, type=Path)
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--write", type=Path)
    options.add_argument("--check", type=Path)
    args = parser.parse_args()
    supplement = args.supplement.read_bytes()
    assert sha(supplement) == SUPPLEMENT_SHA
    roles = {s["elf_sha256"]: s for s in json.loads(supplement)["original_roles"]}
    request = json.loads((args.packet / "request.json").read_text())
    native = json.loads((args.packet / "native-context.json").read_text())
    result = []
    for target in request["targets"]:
        path = getattr(args, target["role"])
        elf_sha = sha(path.read_bytes())
        assert elf_sha == target["original_elf_sha256"]
        s = roles[elf_sha]
        with path.open("rb") as stream:
            elf = ELFFile(stream)
            assert elf["e_machine"] == "EM_ARM" and elf.little_endian
            body = elf_range(elf, target["mangled"])
            row = body[1]
            old, = (v for v in native["bodies"].values() if v["address"] == row["address"])
            assert (row["sha256"], row["file_offset"]) == (old["bytes_sha256"], old["file_offset"])
            lookup = authenticated_range(elf, s["slot_target"])
            table = authenticated_range(elf, s["vtable"])
            assert struct.unpack_from("<I", table[0], 8 + s["slot_from_address_point"])[0] == lookup[1]["address"]
            init, _ = authenticated_range(elf, s["exact_init"])
            assert struct.unpack_from("<I", init, s["init_owner_store"] - s["exact_init"]["address"])[0] == 0xE58011D8
            for constructor in s["constructor_zero_stores"]:
                authenticated_range(elf, constructor)
            payloads = readonly_strings(elf, lookup[0])
        relocs = subprocess.check_output(["readelf", "-rW", str(path)], text=True)
        relocation, = (line for line in relocs.splitlines()
                      if re.search(r"R_ARM_JUMP_SLOT\s+[0-9a-f]+\s+strcmp@GLIBC_", line))
        strcmp = int(relocation.split()[3], 16)
        result.append({
            "role": target["role"], "elf_sha256": elf_sha, "range": row,
            "provider_range": lookup[1], "vtable_range": table[1], "strcmp_plt": strcmp,
            "cases": [replay(body, row, table, lookup, payloads, strcmp, case) for case in CASES],
        })
    data = {"task": "15", "unicorn": uc.__version__, "originals": result}
    if args.write:
        args.write.write_text(json.dumps(data, indent=2) + "\n")
    else:
        assert data == json.loads(args.check.read_text())
    print(sum(len(row["cases"]) for row in result), "exact ARM observations")


if __name__ == "__main__":
    main()
