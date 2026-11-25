"""Execute the exact DAWFocusChannel ARM entries against called provider boundaries."""
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import __version__ as unicorn_version
from unicorn.arm_const import UC_ARM_REG_R0 as R0, UC_ARM_REG_R1 as R1
from unicorn.arm_const import UC_ARM_REG_SP as SP, UC_ARM_REG_LR as LR, UC_ARM_REG_PC as PC

FOCUS = "_ZN8Presonus15DAWFocusChannel"
CLIENT = "_ZN8Presonus2UC15ClientComponent"
COMPONENT_D2 = "_ZN4Core8Portable9ComponentD2Ev"
LOOKUP = "_ZNK4Core8Portable9ParamList5byTagEi"
FEEDBACK = "_ZN4Core8Portable9Parameter17setFeedbackNeededEb"
DELETE = "_ZdlPv"
METHODS = {
    "C1Ev": ("C1", [CLIENT + "C2EPKc"]),
    "C2Ev": ("C2", [CLIENT + "C2EPKc"]),
    "D0Ev": ("D0", [COMPONENT_D2, DELETE]),
    "D1Ev": ("D1", [COMPONENT_D2]),
    "6castToEi": ("cast", []),
    "4initEv": ("init", [LOOKUP, FEEDBACK]),
}
PAGE = 4096
RECEIVER = 0x1000000
PARAMETER = 0x1002000
STACK_PAGE = 0x1100000
STACK = STACK_PAGE + PAGE - 16
STOP = 0x1200000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def image_record(elf, raw, name):
    row, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    section = elf.get_section(row["st_shndx"])
    address, size = row["st_value"], row["st_size"]
    delta = address - section["sh_addr"]
    assert 0 <= delta <= section["sh_size"] - size
    offset = section["sh_offset"] + delta
    contents = raw[offset:offset + size]
    return dict(mangled=name, address=address, size=size, section=row["st_shndx"],
                file_offset=offset, section_name=section.name, range_hex=contents.hex(),
                range_sha256=digest(contents))


def delete_record(elf, raw, address):
    plt = elf.get_section_by_name(".plt")
    displacement = address - plt["sh_addr"]
    index, remainder = divmod(displacement - 20, 12)
    assert index >= 0 and remainder == 0
    rel = elf.get_section_by_name(".rel.plt")
    relocation = rel.get_relocation(index)
    dynamic = elf.get_section(rel["sh_link"])
    assert dynamic.get_symbol(relocation["r_info_sym"]).name == DELETE
    offset = plt["sh_offset"] + displacement
    return dict(mangled=DELETE, address=address, size=12, section=".plt",
                file_offset=offset, range_sha256=digest(raw[offset:offset + 12]),
                got_address=relocation["r_offset"])


class Provider:
    def __init__(self, path, mode):
        self.proc = subprocess.Popen([path, "provider-" + mode], text=True,
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.trace = []

    def write(self, text):
        self.proc.stdin.write(text + "\n")
        self.proc.stdin.flush()

    def call(self, command):
        self.write(command)
        response = self.proc.stdout.readline().strip()
        assert response, (command, self.proc.poll())
        self.trace.append([command, response])
        return list(map(int, response.split()))

    def close(self):
        self.proc.stdin.close()
        assert self.proc.wait(timeout=10) == 0
        assert not self.proc.stdout.read()
        self.proc.stdout.close()


def run_case(original, mode, case, code, records, address_points, name_pointer,
             provider, literals_size):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    mapped = set()

    def put(address, data):
        for page in range(address & -PAGE, (address + len(data) + PAGE - 1) & -PAGE, PAGE):
            if page not in mapped:
                machine.mem_map(page, PAGE)
                mapped.add(page)
        machine.mem_write(address, data)

    target = original["address"]
    prefill = case if mode in ("C1", "C2") else 165
    put(target, code)
    put(RECEIVER, bytes([prefill]) * PAGE)
    put(STACK_PAGE, bytes(PAGE))
    put(STOP, bytes(4))
    branches = {record["address"]: record["mangled"] for record in records}
    for boundary in branches:
        put(boundary, bytes.fromhex("1eff2fe1"))  # bx lr after the modeled call

    calls, writes = [], []
    host = Provider(provider, "init" if mode == "init" else "dtor") if mode in (
        "init", "D0", "D1"
    ) else None
    if mode in ("D0", "D1"):
        host.write(" ".join(map(str, case)))

    def on_code(uc, pc, _size, _):
        called = branches.get(pc)
        if called is None:
            assert target <= pc < target + len(code) - literals_size, hex(pc)
            return
        one, two = uc.reg_read(R0), uc.reg_read(R1)
        detail = dict(address=pc, symbol=called)
        if called.startswith(CLIENT):
            assert one == RECEIVER and two == name_pointer
            output = subprocess.check_output([provider, "provider-ctor"], text=True)
            detail.update(empty_provider=int(output), name="")
        elif called == COMPONENT_D2:
            assert one == RECEIVER
            assert list(struct.unpack("<II", uc.mem_read(RECEIVER, 8))) == address_points
            assert host.call("base") == [1]
        elif called == DELETE:
            assert one == RECEIVER and host.call("free") == [1]
            uc.mem_unmap(RECEIVER, PAGE)
            detail["released_guest_page"] = True
        elif called == LOOKUP:
            assert one == RECEIVER + 0x28 and two == 0
            found, = host.call("lookup " + str(two))
            detail.update(tag=two, found=found)
            uc.reg_write(R0, PARAMETER if found else 0)
        elif called == FEEDBACK:
            assert one == PARAMETER and two == 1
            assert host.call("feedback " + str(two)) == [1]
            detail.update(enabled=two)
        else:
            raise AssertionError(called)
        calls.append(detail)

    def on_write(_uc, _access, address, size, value, _):
        if RECEIVER <= address < RECEIVER + PAGE:
            writes.append([address - RECEIVER, size, value])
        else:
            assert STACK_PAGE <= address < STACK

    machine.hook_add(UC_HOOK_CODE, on_code)
    machine.hook_add(UC_HOOK_MEM_WRITE, on_write)

    def invoke(argument=0):
        for reg, value in ((R0, RECEIVER), (R1, argument & 0xffffffff), (SP, STACK), (LR, STOP)):
            machine.reg_write(reg, value)
        machine.emu_start(target, STOP, count=128)
        assert machine.reg_read(PC) == STOP and machine.reg_read(SP) == STACK
        return machine.reg_read(R0)

    if mode == "init":
        expected, steps = [], []
        for zero, other in case:
            assert host.call(f"configure {zero} {other}") == [1]
            write_index, call_index = len(writes), len(calls)
            invoke()
            cached, = struct.unpack("<I", machine.mem_read(RECEIVER + 0x84, 4))
            assert cached in (0, PARAMETER)
            assert writes[write_index:] == [[0x84, 4, cached]]
            assert [b["symbol"] for b in calls[call_index:]] == ([LOOKUP, FEEDBACK] if cached else [LOOKUP])
            result = [int(bool(cached)), *host.call("report")]
            expected.append(result)
            steps.append(dict(cache_address=cached, feedback=result[1:]))
    else:
        result = invoke(case if mode == "cast" else 0)
        steps = []
        if mode == "cast":
            assert result in (0, RECEIVER) and not calls and not writes
            assert bytes(machine.mem_read(RECEIVER, PAGE)) == bytes([prefill]) * PAGE
            expected = [[int(result == RECEIVER)]]
        elif mode in ("C1", "C2"):
            assert result == RECEIVER and len(calls) == 1
            points = list(struct.unpack("<II", machine.mem_read(RECEIVER, 8)))
            cache, = struct.unpack("<I", machine.mem_read(RECEIVER + 0x84, 4))
            assert points == address_points and cache == 0
            assert writes == [[4, 4, points[1]], [0x84, 4, 0], [0, 4, points[0]]]
            expected = [[calls[0]["empty_provider"], int(points == address_points), int(cache == 0)]]
        else:
            assert result == RECEIVER
            assert writes == [[0, 4, address_points[0]], [4, 4, address_points[1]]]
            assert [b["symbol"] for b in calls] == ([COMPONENT_D2, DELETE] if mode == "D0"
                                                    else [COMPONENT_D2])
            assert any(base <= RECEIVER <= end for base, end, _ in machine.mem_regions()) == (mode == "D1")
            expected = [host.call("report")]
    if host:
        host.close()
    return dict(input=case, expected=expected, writes=writes, calls=calls, init_steps=steps,
                provider_trace=host.trace if host else [])


def observe(packet, provider):
    entries = []
    for item in json.loads(Path(packet).read_text())["originals"]:
        original = item["original"]
        raw = Path(original["elf_path"]).read_bytes()
        assert digest(raw) == original["elf"]
        elf = ELFFile(io.BytesIO(raw))
        assert elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM"
        record = image_record(elf, raw, original["mangled"])
        assert record["section_name"] == ".text" and all(original[k] == v for k, v in record.items())
        mode, symbols = METHODS[original["mangled"].removeprefix(FOCUS)]
        body = bytes.fromhex(record["range_hex"])
        literals = {"cast": 12, "init": 0, "C1": 8, "C2": 8, "D0": 4, "D1": 4}[mode]
        code_end = len(body) - literals
        branches = [int(i.op_str.removeprefix("#"), 0) for i in
                    Cs(CS_ARCH_ARM, CS_MODE_ARM).disasm(body[:code_end], record["address"])
                    if i.mnemonic in ("b", "bl")]
        boundaries = [delete_record(elf, raw, pc) if symbol == DELETE else image_record(elf, raw, symbol)
                      for symbol, pc in zip(symbols, branches, strict=True)]
        assert branches == [entry["address"] for entry in boundaries]
        points, table, name_address, sibling = [], None, None, None
        if mode == "cast":
            ids = struct.unpack("<iii", body[-12:])
            cases = [*ids, *(value + delta for value in ids for delta in (-1, 1)),
                     -2147483648, -1, 0, 2147483647]
        elif mode == "init":
            cases = [[[0, 0]], [[0, 1]], [[1, 0], [1, 0], [0, 0]],
                     [[0, 1], [1, 1], [1, 1], [0, 1]]]
        else:
            constructor = mode in ("C1", "C2")
            table = image_record(elf, raw, ("_ZTVN" + FOCUS[3:] if constructor else
                                           "_ZTVN" + CLIENT[3:]) + "E")
            points = [table["address"] + 8, table["address"] + 0x44]
            assert struct.unpack_from("<I", body, len(body) - 4)[0] == points[0]
            if constructor:
                name_address, = struct.unpack_from("<I", body, len(body) - 8)
                region, = [s for s in elf.iter_segments() if s["p_type"] == "PT_LOAD" and
                           s["p_vaddr"] <= name_address < s["p_vaddr"] + s["p_filesz"]]
                assert raw[region["p_offset"] + name_address - region["p_vaddr"]] == 0
                sibling = image_record(elf, raw, FOCUS + ("C2Ev" if mode == "C1" else "C1Ev"))
                assert sibling["address"] != record["address"]
                cases = [60, 165]
            else:
                cases = [[0, 0], [1, 1], [2, 2]]
        if table:
            table.pop("range_hex")
        entries.append(dict(original=original, mode=mode, boundaries=boundaries, vtable=table,
                            sibling_constructor=sibling, name_literal_address=name_address,
                            cases=[run_case(original, mode, case, body, boundaries, points,
                                            name_address, provider, literals) for case in cases]))
    return dict(oracle="original ARM instructions with separate source-provider executable",
                unicorn=unicorn_version, entries=entries)


if __name__ == "__main__":
    print(json.dumps(observe(*sys.argv[1:]), indent=2))
