"""Run original selected ARM panel entry and measure exact writes and returns."""
import hashlib
import json
from itertools import product
from pathlib import Path
from struct import pack, unpack

import elftools
import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP,
)

CONTROL = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11")
PACKETS = CONTROL / "packeting/actual03-separate-ui-audio-batch08/packets"
INPUT_MAP = CONTROL / "packeting/READ_INPUTS-actual03-separate-ui-audio-batch08-cycle20_g06-actual03-separate-ui-audio-batch08.json"
TASK = "cycle20_g06_s04"
MODE = "get"
PAGE = 4096
RECEIVER, STACK, STOP, DELEGATE, TABLE, STUB, NAME = range(0x40000000, 0x40007000, PAGE)
PARAMETERS = (0, 0x50000000, 0x50001000)
DELEGATES = (0, DELEGATE, DELEGATE + 0x100)
QUERIES = ("panel/fader", "fader", "other/panel/fader", "panel/missing")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(task, elf, stream, elf_sha):
    path = PACKETS / task
    req = json.loads((path / "request.json").read_text())
    ctx = json.loads((path / "native-context.json").read_text())
    target, = [row for row in req["targets"] if row["original_elf_sha256"] == elf_sha]
    roots = [ctx["bodies"][r] for r in ctx["roots"]]
    body, = [row for row in roots if row["address"] == target["address"]]
    section = elf.get_section(target["section"])
    displacement = target["address"] - section["sh_addr"]
    assert section.name == ".text" and 0 <= displacement <= section["sh_size"] - target["size"]
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(target["mangled"])
    assert (symbol["st_shndx"], symbol["st_value"], symbol["st_size"]) == (
        target["section"], target["address"], target["size"])
    offset = section["sh_offset"] + displacement
    stream.seek(offset)
    code = stream.read(target["size"])
    assert len(code) == target["size"] and offset == body["file_offset"]
    assert sha(code) == body["bytes_sha256"]
    return {**target, "file_offset": offset, "range_sha256": sha(code)}, code


def emulate(target, code, peer):
    arm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    pages = set()
    image = [(target, code)] + ([peer] if peer else [])

    def mapped(address, value):
        for page in range(address & -PAGE, ((address + len(value) - 1) & -PAGE) + PAGE, PAGE):
            if page not in pages:
                arm.mem_map(page, PAGE)
                pages.add(page)
        arm.mem_write(address, value)

    def put(address, value):
        mapped(address, pack("<I", value))

    def get(address):
        return unpack("<I", arm.mem_read(address, 4))[0]

    for item, body in image:
        mapped(item["address"], body)
    for page in (RECEIVER, STACK, STOP, DELEGATE, TABLE, STUB, NAME):
        mapped(page, bytes(PAGE))
    cell = unpack("<I", code[-4:])[0] if MODE in ("get", "set") else None
    if cell is not None:
        assert cell == unpack("<I", peer[1][-4:])[0]
        put(cell, 0)

    # Each typed delegate has an independent original slot-0 target.
    put(DELEGATE, TABLE)
    put(DELEGATE + 0x100, TABLE + 0x100)
    put(TABLE, STUB)
    put(TABLE + 0x100, STUB + 4)
    writes, calls = [], []
    active_range = None
    provider_value = 0

    def watch_write(_, _kind, address, size, value, __):
        if not STACK <= address < STACK + PAGE:
            writes.append([address, size, value])

    def watch_code(cpu, address, _, __):
        start, end = active_range
        if start <= address < end:
            return
        assert address in (STUB, STUB + 4)
        delegate = cpu.reg_read(UC_ARM_REG_R0)
        assert address == (STUB if delegate == DELEGATE else STUB + 4)
        assert cpu.reg_read(UC_ARM_REG_R1) == NAME
        calls.append(DELEGATES.index(delegate))
        cpu.reg_write(UC_ARM_REG_R0, provider_value)
        cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

    arm.hook_add(UC_HOOK_CODE, watch_code)
    arm.hook_add(UC_HOOK_MEM_WRITE, watch_write)

    def execute(entry, first, second=0):
        nonlocal active_range
        writes.clear()
        calls.clear()
        start = entry["address"]
        active_range = (start, start + entry["size"])
        arm.reg_write(UC_ARM_REG_R0, first)
        arm.reg_write(UC_ARM_REG_R1, second)
        arm.reg_write(UC_ARM_REG_SP, STACK + PAGE - 16)
        arm.reg_write(UC_ARM_REG_LR, STOP)
        arm.emu_start(start, STOP, count=64)
        assert arm.reg_read(UC_ARM_REG_PC) == STOP
        assert arm.reg_read(UC_ARM_REG_SP) == STACK + PAGE - 16
        return arm.reg_read(UC_ARM_REG_R0), list(writes), list(calls)

    observations = []
    if MODE in ("get", "set"):
        getter, setter = (target, peer[0]) if MODE == "get" else (peer[0], target)
        assert get(cell) == 0
        for index in (0, 1, 1, 2, 2, 0, 0, 1, 0):
            parameter = PARAMETERS[index]
            before = get(cell)
            _, stores, dispatch = execute(setter, parameter)
            assert not dispatch
            assert stores == ([[cell, 4, parameter]] if before != parameter else [])
            result, unexpected, dispatch = execute(getter, RECEIVER)
            assert result == parameter and not unexpected and not dispatch
            observations.append({"input": index, "before": PARAMETERS.index(before),
                                 "after": PARAMETERS.index(result), "stores": stores})
    elif MODE == "previous":
        for cursor, dirty in product(range(33), (0, 1)):
            put(RECEIVER + 0xa14, cursor)
            put(RECEIVER + 0x74, dirty)
            result, stores, dispatch = execute(target, RECEIVER)
            assert not dispatch
            assert stores == ([[RECEIVER + 0xa14, 4, cursor - 1], [RECEIVER + 0x74, 4, 1]]
                              if cursor else [])
            observations.append({"cursor": cursor, "dirty": dirty, "returns": result,
                                 "out_cursor": get(RECEIVER + 0xa14),
                                 "out_dirty": get(RECEIVER + 0x74), "stores": stores})
    else:
        setter, lookup = (target, peer[0]) if MODE == "delegate" else (peer[0], target)
        for index, query in [(0, QUERIES[0]), (1, QUERIES[0]), (1, QUERIES[1]),
                             (2, QUERIES[2]), (2, QUERIES[3]), (0, QUERIES[1]),
                             (1, QUERIES[2]), (0, QUERIES[3])]:
            arguments = query.encode() + b"\0"
            mapped(NAME, arguments)
            delegate = DELEGATES[index]
            prior = get(RECEIVER + 4)
            _, stores, dispatch = execute(setter, RECEIVER, delegate)
            assert not dispatch and stores == [[RECEIVER + 4, 4, delegate]]
            assert get(RECEIVER + 4) == delegate
            provider_index = QUERIES.index(query) + 1 if query != "panel/missing" and index else 0
            provider_value = 0x50000000 + (provider_index << 12) if provider_index else 0
            result, unexpected, calls = execute(lookup, RECEIVER, NAME)
            assert calls == ([index] if index else [])
            assert not unexpected and result == provider_value
            assert bytes(arm.mem_read(NAME, len(arguments))) == arguments
            observations.append({"binding": index, "query": query, "after": result,
                                 "opaque_provider_case": provider_index, "calls": calls,
                                 "before": DELEGATES.index(prior), "stores": stores})
    return observations


def generate():
    request = json.loads((PACKETS / TASK / "request.json").read_text())
    inputs = json.loads(INPUT_MAP.read_text())
    peer_task = {"get": "05", "set": "04", "delegate": "10", "lookup": "09"}.get(MODE)
    originals = []
    for release in request["work_binding"]["binary_releases"]:
        elf_sha = release["elf_sha256"]
        frozen = inputs[release["original_path"]]
        path = Path(frozen["frozen_read_path"])
        assert sha(path.read_bytes()) == frozen["sha256"] == elf_sha
        with path.open("rb") as stream:
            elf = ELFFile(stream)
            assert elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM"
            target, code = verify(TASK, elf, stream, elf_sha)
            peer = verify("cycle20_g06_s" + peer_task, elf, stream, elf_sha) if peer_task else None
        observed = emulate(target, code, peer)
        originals.append({**target, "elf_path": str(path), "cases": observed,
                          "peer_observer": peer[0] if peer else None})
    return {"task_id": TASK, "originals": originals, "unicorn_version": unicorn.__version__,
            "pyelftools_version": elftools.__version__,
            "scope": "Exact original application instructions. LCD slot-0 call targets are receiver/query capture shims with controlled opaque results. Encoder pointer tokens are never dereferenced. Core and hardware are excluded from native execution."}


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2, sort_keys=True))
