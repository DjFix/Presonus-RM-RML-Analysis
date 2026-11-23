"""Execute the sealed original application ranges in an offline ARM harness."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

import elftools
import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import arm_const as regs

R0, R1, R2, R3 = (regs.UC_ARM_REG_R0, regs.UC_ARM_REG_R1,
                  regs.UC_ARM_REG_R2, regs.UC_ARM_REG_R3)
SP, LR, PC = regs.UC_ARM_REG_SP, regs.UC_ARM_REG_LR, regs.UC_ARM_REG_PC
RECEIVER, ARG, BUFFER, STACK, END = 0x40000000, 0x40100000, 0x40200000, 0x40301000, 0x40400000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_elf(path, expected):
    data = path.read_bytes()
    assert sha(data) == expected
    elf = ELFFile(io.BytesIO(data))
    assert elf["e_machine"] == "EM_ARM" and elf.little_endian
    return elf


def section_range(elf, name):
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    sec = elf.get_section(symbol["st_shndx"])
    start = symbol["st_value"] - sec["sh_addr"]
    size = symbol["st_size"]
    assert 0 <= start <= sec["sh_size"] - size
    code = bytes(size) if sec["sh_type"] == "SHT_NOBITS" else sec.data()[start:start+size]
    return dict(mangled=name, address=symbol["st_value"], size=size,
                section=sec.name, section_index=symbol["st_shndx"],
                section_type=sec["sh_type"], kind=symbol["st_info"]["type"],
                file_offset=sec["sh_offset"] + start, range_sha256=sha(code)), code


def app(elf):
    uc = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    uc.mem_map(0x8000, 0x600000 - 0x8000)
    for segment in elf.iter_segments():
        if segment["p_type"] == "PT_LOAD":
            uc.mem_write(segment["p_vaddr"], segment.data())
    for address in (RECEIVER, ARG, BUFFER, STACK - 0x1000):
        uc.mem_map(address, 0x1000)
    return uc


def put(uc, address, *words):
    uc.mem_write(address, struct.pack(f"<{len(words)}I", *words))


def get(uc, address):
    return struct.unpack("<I", uc.mem_read(address, 4))[0]


def call(uc, identity, second=0, third=0, allowed=(), hook=None):
    trace = []
    def execute(cpu, pc, size, _):
        if identity["address"] <= pc < identity["address"] + identity["size"]:
            trace.append(pc)
        elif not any(start <= pc < start + size for start, size in allowed):
            assert hook is not None, hex(pc)
            hook(cpu, pc)
    uc.hook_add(unicorn.UC_HOOK_CODE, execute)
    for reg, value in ((SP, STACK), (LR, END), (R0, RECEIVER), (R1, second), (R2, third)):
        uc.reg_write(reg, value & 0xFFFFFFFF)
    uc.emu_start(identity["address"], END, count=700)
    assert (uc.reg_read(PC), uc.reg_read(SP)) == (END, STACK)
    return uc.reg_read(R0), trace


def ret(uc, value):
    uc.reg_write(R0, value & 0xFFFFFFFF)
    uc.reg_write(PC, uc.reg_read(LR))


def row(elf, spec):
    sha256, firmware, role, mangled, address, size, body = spec
    identity, code = section_range(elf, mangled)
    assert (identity["address"], identity["size"], identity["range_sha256"]) == (
        address, size, body)
    assert identity["section"] == ".text" and identity["kind"] == "STT_FUNC"
    return {**identity, "elf_sha256": sha256, "firmware": firmware, "role": role}, code

TASK = "cycle20_g04_s07"
ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
FIRMWARE = "RM/RML mixer 13731"
PREFIX = "_ZN8Presonus5Mixer22AutoFilterGroupManager"
SIGNATURE = "EPKcRNS0_18MixerComponentBaseE"
SPECS = [
    (ELF_SHA, FIRMWARE, "server", PREFIX + "C2" + SIGNATURE, 0x5B138, 424,
     "1b975896f89594a1075029e392e5dc9ebe59ced51c7495ff0fc762bdb2fe55c5"),
    (ELF_SHA, FIRMWARE, "server", PREFIX + "C1" + SIGNATURE, 0x5AF90, 424,
     "d61c4631a62b8d3cca1a5caf48e7e2cefa9d11bfca21e594153a2fe332589ca9"),
]
CASE_CALLS = {
    24: (0xF6160, "local_server"),
    92: (0x3928C, "empty_update_vector"),
    140: (0x3874C, "empty_owners_vector"),
    204: (0xA7E4, "allocate_observer"),
    220: (0x5ACEC, "construct_observer"),
    236: (0x5C6D0, "register_owner"),
    288: (0x1CF90, "category_name"),
    300: (0x5CA34, "register_category"),
    336: (0x1CFE8, "unwind_server"),
    344: (0xACD0, "unwind_end"),
    356: (0xAC10, "unwind_delete"),
    364: (0x3884C, "unwind_owners"),
    372: (0x3938C, "unwind_updates"),
}
MODELED_CCL = 0x119E8C
CATEGORY_CACHE = 0x494708
CATEGORY_TABLE = 0x31C468
ROSTER = BUFFER + 0x100
OWNERS = 0x40500000
CHANNELS = [0x40600000 + 0x100 * i for i in range(3)]
NAME = b"Offline group roster"
SERVER_NAME = "_ZN8Presonus2UC15ServerComponentC2EPKc"
CCL_NAME = "_ZN4Core8Portable9ComponentC2EPKc"
OBSERVER_NAME = "_ZN8Presonus5Mixer19GroupChangeObserverC1EPNS0_16ChannelComponentERNS0_22AutoFilterGroupManagerE"


def branch_target(address, instruction):
    assert instruction >> 24 == 0xEB
    displacement = (instruction & 0xFFFFFF) << 2
    return address + 8 + displacement - (displacement & 0x2000000) * 2


def observe(elf, identity, body):
    original = identity["address"]
    for offset, (target, _) in CASE_CALLS.items():
        operation, = struct.unpack_from("<I", body, offset)
        assert branch_target(original + offset, operation) == target
    server, server_code = section_range(elf, SERVER_NAME)
    assert (server["address"], server["range_sha256"]) == (
        0xF6160, "c123fddeb3533c847abbe9e4182e839c48195f0c74b9b0cde92928db6327d56b")
    ccl, _ = section_range(elf, CCL_NAME)
    assert ccl["address"] == MODELED_CCL
    assert branch_target(server["address"] + 20, struct.unpack_from("<I", server_code, 20)[0]) == MODELED_CCL
    observer, _ = section_range(elf, OBSERVER_NAME)
    assert observer["address"] == CASE_CALLS[220][0]
    assert struct.unpack_from("<III", body, 0x19C) == (CATEGORY_CACHE, CATEGORY_TABLE, CATEGORY_CACHE + 4)
    initial = app(elf)
    category_bytes = bytes(initial.mem_read(CATEGORY_TABLE, 36))
    category_sha = sha(category_bytes)
    assert category_sha == "b84cb98c2ec6e7330defdf668feaac81f98f79faea593f3dd63285fb71abb976"
    category_pointers = struct.unpack("<9I", category_bytes)
    case_targets = {address: name for address, name in CASE_CALLS.values()}
    cases = []
    for count in (0, 3):
        for warm in (0, 9):
            uc = app(elf)
            uc.mem_write(RECEIVER, b"\xA6" * 0x180)
            uc.mem_write(ARG, NAME + b"\0")
            put(uc, BUFFER + 0x134, ROSTER, count)
            put(uc, ROSTER, *CHANNELS)
            put(uc, CATEGORY_CACHE + 8, warm)
            roster_before = bytes(uc.mem_read(ROSTER, 12))
            calls = []
            allocated = []
            roster_indices = []
            category_names = []

            def boundary(cpu, pc):
                r0, r1, r2 = (cpu.reg_read(reg) for reg in (R0, R1, R2))
                if server["address"] <= pc < server["address"] + server["size"]:
                    if pc == server["address"]:
                        assert (r0, r1) == (RECEIVER, ARG)
                        calls.append("local_server")
                    return
                name = case_targets.get(pc, "pinned_component" if pc == MODELED_CCL else None)
                assert name and not name.startswith("unwind"), hex(pc)
                result = r0
                if name == "pinned_component":
                    assert (r0, r1) == (RECEIVER, ARG)
                elif name == "empty_update_vector":
                    assert (r0, r1) == (RECEIVER + 0x8C, 0)
                elif name == "empty_owners_vector":
                    assert (r0, r1) == (RECEIVER + 0xA0, 0)
                elif name == "allocate_observer":
                    assert r0 == 0x8C
                    result = OWNERS + 0x100 * len(allocated)
                    allocated.append(result)
                elif name == "construct_observer":
                    index = len(allocated) - 1
                    assert (r0, r1, r2) == (allocated[index], CHANNELS[index], RECEIVER)
                    roster_indices.append(index)
                elif name == "register_owner":
                    assert r0 == RECEIVER + 0xA4 and get(cpu, r1) == allocated[-1]
                elif name == "category_name":
                    assert r1 == category_pointers[len(category_names)]
                    name_bytes = bytes(cpu.mem_read(r1, 64)).split(b"\0", 1)[0]
                    category_names.append(name_bytes.decode("ascii"))
                elif name == "register_category":
                    assert r0 == CATEGORY_CACHE + 4
                calls.append(name)
                ret(cpu, result)

            result, trace = call(uc, identity, ARG, BUFFER, hook=boundary)
            assert result == RECEIVER and get(uc, RECEIVER + 0x88) == BUFFER
            assert bytes(uc.mem_read(ROSTER, 12)) == roster_before
            expected = ["local_server", "pinned_component", "empty_update_vector", "empty_owners_vector"]
            expected += ["allocate_observer", "construct_observer", "register_owner"] * count
            expected += [] if warm else ["category_name", "register_category"] * 9
            assert calls == expected
            output = " ".join([str(len(allocated)), *(str(index) for index in roster_indices)])
            cases.append(dict(input=f"{count} {warm}", output=output,
                              executed=trace, provider_calls=calls, category_names=category_names))
    return cases, [server, ccl, observer, dict(address=CATEGORY_TABLE, sha256=category_sha)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--out", type=Path)
    output.add_argument("--verify", type=Path)
    args = parser.parse_args()
    elf = load_elf(args.elf, ELF_SHA)
    results = []
    for spec in SPECS:
        identity, code = row(elf, spec)
        cases, dependencies = observe(elf, identity, code)
        results.append(dict(original=identity, cases=cases, dependencies=dependencies))
    fixture = dict(task=TASK, originals=results, unicorn_version=unicorn.__version__,
                   pyelftools_version=elftools.__version__)
    if args.out:
        with args.out.open("x") as stream:
            json.dump(fixture, stream, indent=2)
            stream.write("\n")
    else:
        assert fixture == json.loads(args.verify.read_text())
        print(sum(len(item["cases"]) for item in results), "exact original cases reproduced")


if __name__ == "__main__":
    main()
