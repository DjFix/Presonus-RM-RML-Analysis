"""Run the exact PanMeterControl ARM ranges and record independent observations."""
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

TEST = Path(__file__).parent
TASK = TEST.name
PACKET = Path("temp/recovery-work/sqlite-issued/packet") / TASK / "CONTEXT.json"
PAN = "_ZN8Presonus5Panel15PanMeterControl"
LEVEL = "_ZN8Presonus5Panel17MeterLevelControl"
CONTROL = "_ZN8Presonus5Panel7Control"
TAG_VALUES = [-2147483648, -4, 0, 3, 91, 2147483647]
DELETION_CASES = [(tag, mask, timer) for tag, mask, timer in
                  zip(TAG_VALUES, (0, 1, 2, 4, 7, 7), (0, 1, 0, 1, 0, 1), strict=True)]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def section_data(elf, raw, symbol):
    section = elf.get_section(symbol["st_shndx"])
    size = symbol["st_size"]
    displacement = symbol["st_value"] - section["sh_addr"]
    assert 0 <= displacement <= section["sh_size"] - size
    offset = section["sh_offset"] + displacement
    return raw[offset:offset + size], offset


def record(elf, raw, table, name):
    symbol, = table.get_symbol_by_name(name)
    body, offset = section_data(elf, raw, symbol)
    return dict(mangled=name, address=symbol["st_value"], size=symbol["st_size"],
                section=symbol["st_shndx"], file_offset=offset, data=body.hex(),
                sha256=digest(body))


def allocation_binding(elf, raw, address):
    plt = elf.get_section_by_name(".plt")
    displacement = address - plt["sh_addr"]
    index, remainder = divmod(displacement - 20, 12)
    assert index >= 0 and remainder == 0
    reloc = elf.get_section_by_name(".rel.plt")
    entry = reloc.get_relocation(index)
    name = elf.get_section(reloc["sh_link"]).get_symbol(entry["r_info_sym"]).name
    assert name == "_ZdlPv"
    offset = plt["sh_offset"] + displacement
    return dict(mangled=name, address=address, file_offset=offset,
                sha256=digest(raw[offset:offset + 12]), got=entry["r_offset"])


def word(emu, address):
    return struct.unpack("<I", emu.mem_read(address, 4))[0]


def signed(value):
    return struct.unpack("<i", struct.pack("<I", value))[0]


def execute(target, support, point, allocator, mode, inputs, exe):
    receiver, stack, stop = 0x1000100, 0x2000000, 0x3000000
    emu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    emu.mem_map(0x8000, 0x100000)
    emu.mem_map(0x1000000, 4096)
    emu.mem_map(stack, 4096)
    for entry in (target, *support.values()):
        emu.mem_write(entry["address"], bytes.fromhex(entry["data"]))
    emu.mem_write(receiver, b"\xa7" * 0x38)
    input_value = inputs[0]
    regs = ((UC_ARM_REG_LR, stop), (UC_ARM_REG_SP, stack + 0x800),
            (UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, input_value & 0xffffffff))
    trace, writes, calls = [], [], []
    released = False
    cleanup = []

    def start(entry):
        for register, value in regs:
            emu.reg_write(register, value)
        emu.emu_start(entry["address"], stop, count=128)
        assert emu.reg_read(UC_ARM_REG_PC) == stop
        assert emu.reg_read(UC_ARM_REG_SP) == stack + 0x800

    if mode in ("complete", "deleting", "cast"):
        start(support[PAN + "C1Ei"])
        assert word(emu, receiver) == point
    if mode in ("complete", "deleting"):
        _, mask, has_timer = inputs
        for index in range(3):
            if mask & (1 << index):
                emu.mem_write(receiver + 8 + index * 4, struct.pack("<I", receiver + 0x200 + index * 4))
        emu.mem_write(receiver + 0x200, struct.pack("<i", 17))
        emu.mem_write(receiver + 0x1c, struct.pack("<II", 1, receiver + 0x200))
    before = bytes(emu.mem_read(receiver, 0x38))

    def observe_code(uc, address, size, _):
        nonlocal released
        trace.append(address)
        for name, entry in support.items():
            if address == entry["address"]:
                calls.append([address, name, uc.reg_read(UC_ARM_REG_R0),
                              uc.reg_read(UC_ARM_REG_LR), word(uc, receiver)])
                assert calls[-1][2] == receiver
                if name == LEVEL + "C2Ei":
                    assert signed(uc.reg_read(UC_ARM_REG_R1)) == input_value
                elif name == CONTROL + "D2Ev":
                    payload = " ".join(map(str, inputs)) + "\n"
                    output = subprocess.run([str(exe.resolve()), "provider"], text=True,
                                            input=payload, capture_output=True, check=True).stdout
                    cleanup.extend(map(int, output.split()))
                    assert cleanup == [inputs[1], inputs[2], 0, 1]
                    assert word(uc, receiver + 0x200) == 17
                    uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
                return
        if allocator and address == allocator["address"]:
            assert len(calls) == 2 and not released and cleanup
            assert uc.reg_read(UC_ARM_REG_R0) == receiver
            assert uc.reg_read(UC_ARM_REG_LR) == target["address"] + 40
            assert word(uc, receiver + 0x200) == 17
            calls.append([address, allocator["mangled"], receiver,
                          uc.reg_read(UC_ARM_REG_LR), word(uc, receiver)])
            released = True
            uc.mem_unmap(0x1000000, 4096)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
            return
        assert any(entry["address"] <= address < entry["address"] + entry["size"]
                   for entry in (target, *support.values())), hex(address)

    def observe_write(uc, access, address, size, value, _):
        if stack <= address < stack + 4096:
            return
        assert receiver <= address < receiver + 0x38
        writes.append([address - receiver, size, value])

    emu.hook_add(UC_HOOK_CODE, observe_code)
    emu.hook_add(UC_HOOK_MEM_WRITE, observe_write)
    start(target)
    result = emu.reg_read(UC_ARM_REG_R0)
    if mode == "cast":
        assert result in (receiver, 0) and not writes and not calls
        assert bytes(emu.mem_read(receiver, 0x38)) == before
        expected = [int(result == receiver)]
    elif mode in ("c1", "c2"):
        assert [row[1] for row in calls] == [LEVEL + "C2Ei"]
        assert writes[-1] == [0, 4, point] and result == receiver
        assert [row[2] for row in writes if row[0] == 0][-2:] == [
            struct.unpack("<I", bytes.fromhex(support[LEVEL + "C2Ei"]["data"])[-4:])[0], point]
        expected = [signed(word(emu, receiver + 24)), signed(word(emu, receiver + 4)),
                    *(int(word(emu, receiver + offset) != 0) for offset in (8, 12, 16, 20)),
                    word(emu, receiver + 28), int(word(emu, receiver + 32) != 0),
                    word(emu, receiver + 52), emu.mem_read(receiver + 48, 1)[0],
                    int(word(emu, receiver) == point)]
    else:
        assert [row[1] for row in calls] == [LEVEL + "D2Ev", CONTROL + "D2Ev"] + (
            ["_ZdlPv"] if mode == "deleting" else [])
        assert calls[0][4] == point and writes[0] == [0, 4, point]
        assert result == receiver and released == (mode == "deleting")
        if not released:
            assert bytes(emu.mem_read(receiver + 4, 0x34)) == before[4:]
        expected = [*cleanup[:2], int(released), cleanup[3]]
    return dict(inputs=list(inputs), expected=expected, receiver=receiver,
                instructions=trace, calls=calls, receiver_writes=writes)


def generate(exe):
    packet = json.loads(PACKET.read_text())
    evidence = next(item for item in packet["task"]["review"]["evidence"]
                    if item["path"].endswith("_DIRECT_EVIDENCE.json"))
    raw_evidence = Path(evidence["path"]).read_bytes()
    assert digest(raw_evidence) == evidence["sha256"]
    sites = {item["original"]["elf"]: item for item in json.loads(raw_evidence)["native"]}
    observations = []
    for item in packet["originals"]:
        original = item["original"]
        raw = Path(original["elf_path"]).read_bytes()
        assert digest(raw) == original["elf"]
        elf = ELFFile(io.BytesIO(raw))
        table = elf.get_section_by_name(".symtab")
        assert elf.little_endian and elf["e_machine"] == "EM_ARM"
        target = record(elf, raw, table, original["mangled"])
        for field in ("mangled", "address", "size", "section", "file_offset"):
            assert target[field] == original[field]
        assert target["data"] == original["range_hex"] and target["sha256"] == original["range_sha256"]
        assert elf.get_section(target["section"]).name == original["section_name"]
        direct = sites[original["elf"]]
        assert direct["original"] == original
        site = direct["site_evidence"]
        vtable = record(elf, raw, table, PAN.replace("_ZN", "_ZTVN") + "E")
        point = vtable["address"] + 8
        support = {LEVEL + "C2Ei": record(elf, raw, table, LEVEL + "C2Ei")}
        allocator = None
        if "construct" in TASK:
            mode = "c2" if "base" in TASK else "c1"
            cases = [(tag,) for tag in TAG_VALUES]
            assert site[0]["destination"] == support[LEVEL + "C2Ei"]["address"]
            assert struct.unpack("<I", bytes.fromhex(target["data"])[-4:])[0] == point
        else:
            support[PAN + "C1Ei"] = record(elf, raw, table, PAN + "C1Ei")
            if "cast_type" in TASK:
                mode = "cast"
                ids = struct.unpack("<4i", bytes.fromhex(target["data"])[-16:])
                assert list(ids) == [observation["value"] for observation in site]
                cases = [(value,) for value in sorted({0, *TAG_VALUES, *(i + n for i in ids for n in (-1, 0, 1))})]
            else:
                mode = "deleting" if "deleting" in TASK else "complete"
                cases = DELETION_CASES
                for name in (LEVEL, CONTROL):
                    support[name + "D2Ev"] = record(elf, raw, table, name + "D2Ev")
                assert site[0]["value"] == point and site[1]["destination"] == support[LEVEL + "D2Ev"]["address"]
                slot = 20 if mode == "deleting" else 16
                assert struct.unpack_from("<I", bytes.fromhex(vtable["data"]), slot)[0] == target["address"]
                if mode == "deleting":
                    allocator = allocation_binding(elf, raw, site[2]["destination"])
        observations.append(dict(original=original, support=support, vtable=vtable,
                                 mode=mode, allocator=allocator,
                                 cases=[execute(target, support, point, allocator, mode, case, exe)
                                        for case in cases]))
    return observations


if __name__ == "__main__":
    print(json.dumps(generate(Path(sys.argv[1])), indent=2))
