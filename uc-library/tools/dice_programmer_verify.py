#!/usr/bin/env python3
"""Validate only clock-free programmer construction/state/progress methods."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import subprocess

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import arm_const as arm

PREFIX = "_ZN8Presonus4DICE15Dice3Programmer"
MANGLES = {
    "C1": PREFIX + "C1EPNS_2UC23IFirmwareUpdateListenerEPKhj",
    "C2": PREFIX + "C2EPNS_2UC23IFirmwareUpdateListenerEPKhj",
    "D1": PREFIX + "D1Ev",
    "D2": PREFIX + "D2Ev",
    "V": PREFIX + "6verifyEv",
    "P": PREFIX + "13printProgressEPKcfb",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command(argv, log):
    scratch = log.parent / "temp"
    scratch.mkdir(exist_ok=True)
    result = subprocess.run(argv, capture_output=True, text=True, env=dict(os.environ, TMPDIR=str(scratch)))
    log.write_text("TMPDIR " + str(scratch) + "\nCOMMAND " + repr(argv) + "\n" + result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"command exit{result.returncode}: {log}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    args = parser.parse_args()
    repository = args.repository.resolve()
    library = repository / "uc-library"
    output = library / "validation/dice-programmer/runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output.mkdir(parents=True, exist_ok=False)
    directory = library / "recovered-all/client"
    manifest = json.loads((directory / "manifest.json").read_text())
    binary = repository / manifest["path"]
    raw = binary.read_bytes()
    assert sha(raw) == manifest["sha256"]
    rows = json.loads((directory / "symbols.json").read_text())
    by_mangle = {row["mangled"]: row for row in rows}
    functions = {op: by_mangle[name] for op, name in MANGLES.items()}

    def checked(row):
        data = (directory / row["export_path"]).read_bytes()
        assert data == raw[row["file_offset"]:row["file_offset"] + row["size"]]
        assert sha(data) == row["sha256"]
        return data

    for row in functions.values():
        checked(row)
    evidence_names = {"vtable for Presonus::UC::IFirmwareUpdateListener",
                      "typeinfo for Presonus::UC::IFirmwareUpdateListener",
                      "typeinfo for Presonus::Surface::PanelRegistrar",
                      "typeinfo for Presonus::Surface::SurfaceApplication",
                      "vtable for Presonus::Surface::PanelRegistrar",
                      "vtable for Presonus::Surface::SurfaceApplication"}
    by_address = {r["address"]: r for r in rows if r["kind"] == "STT_FUNC"}
    listener_evidence = []
    for row in rows:
        if row["demangled"] not in evidence_names:
            continue
        data = checked(row)
        name = f'{row["address"]:08x}-{row["size"]:x}.bin'
        (output / name).write_bytes(data)
        words = []
        for offset in range(0, len(data), 4):
            word = struct.unpack_from("<I", data, offset)[0]
            words.append(dict(offset=offset, value=word, function=by_address.get(word, {}).get("demangled")))
        listener_evidence.append(dict(symbol=row, words=words, evidence_file=name))
    (output / "listener-evidence.json").write_text(json.dumps(listener_evidence, indent=2) + "\n")
    # Independent RTTI/vtable relationships establish name/parameters, not return.
    info = next(r for r in rows if r["demangled"] == "typeinfo for Presonus::UC::IFirmwareUpdateListener")
    for owner, base_offset, table_offset, thunk in (
        ("PanelRegistrar", 0xac, 0x9c, "non-virtual thunk to Presonus::Surface::PanelRegistrar::onProgress(char const*, float)"),
        ("SurfaceApplication", 4, 0x34, "non-virtual thunk to Presonus::Surface::SurfaceApplication::onProgress(char const*, float)"),
    ):
        typeinfo = next(r for r in rows if r["demangled"] == f"typeinfo for Presonus::Surface::{owner}")
        data = checked(typeinfo)
        assert struct.unpack_from("<II", data, 0x18) == (info["address"], (base_offset << 8) | 2)
        table = next(r for r in rows if r["demangled"] == f"vtable for Presonus::Surface::{owner}")
        data = checked(table)
        assert struct.unpack_from("<I", data, table_offset - 8)[0] == (-base_offset & 0xffffffff)
        assert struct.unpack_from("<I", data, table_offset - 4)[0] == typeinfo["address"]
        assert by_address[struct.unpack_from("<I", data, table_offset)[0]]["demangled"] == thunk
    machine = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    pages = set()
    with binary.open("rb") as stream:
        for segment in ELFFile(stream).iter_segments():
            if segment["p_type"] != "PT_LOAD":
                continue
            start = int(segment["p_vaddr"])
            end = start + int(segment["p_memsz"])
            for page in range(start & ~4095, (end + 4095) & ~4095, 4096):
                if page not in pages:
                    machine.mem_map(page, 4096)
                    pages.add(page)
            machine.mem_write(start, segment.data())
    obj, listener, table, stack, stop, callback = 0x10000000, 0x10001000, 0x10002000, 0x20000000, 0x30000000, 0x30001000
    machine.mem_map(obj, 0x3000)
    machine.mem_map(stack, 0x10000)
    machine.mem_map(stop, 0x2000)
    machine.mem_write(listener, struct.pack("<I", table))
    machine.mem_write(table, struct.pack("<I", callback))
    state = {}
    callback_r3_values = set()

    def code(uc, address, size, user):
        if address == callback:
            assert uc.reg_read(arm.UC_ARM_REG_R0) == listener
            trace = tuple(uc.reg_read(getattr(arm, f"UC_ARM_REG_R{index}")) for index in (1, 2))
            state["calls"].append(trace)
            callback_r3_values.add(uc.reg_read(arm.UC_ARM_REG_R3))
            uc.reg_write(arm.UC_ARM_REG_R0, state["callback_return"])
            uc.reg_write(arm.UC_ARM_REG_PC, uc.reg_read(arm.UC_ARM_REG_LR))
        else:
            row = functions[state["operation"]]
            assert row["address"] <= address < row["address"] + row["size"], f"unapproved execution {address:#x}"

    def write(uc, access, address, size, value, user):
        if obj <= address < obj + 0x20:
            state["writes"].append((address - obj, size, value & ((1 << (size * 8)) - 1)))
        else:
            assert stack <= address and address + size <= stack + 0x10000, f"unexpected write {address:#x}"

    machine.hook_add(unicorn.UC_HOOK_CODE, code)
    machine.hook_add(unicorn.UC_HOOK_MEM_WRITE, write)
    counts = Counter()
    write_patterns = set()
    rng = random.Random(0x444943453350)
    fixture = output / "arm-vectors.txt"
    with fixture.open("w") as stream:
        def emit(operation, listener_word=0, image=0, length=0, text=0, value=0, force=0, callback_return=0):
            storage = bytearray(b"\xa5" * 0x20)
            struct.pack_into("<IIII", storage, 0, 0xffffffff, image, length, listener_word)
            if operation.startswith("C"):
                storage[:] = b"\xa5" * 0x20
            machine.mem_write(obj, bytes(storage))
            model_before = bytes(machine.mem_read(listener, 0x2000))
            state.update(operation=operation, calls=[], writes=[], callback_return=callback_return)
            machine.reg_write(arm.UC_ARM_REG_CPSR, 0x10)
            for index in range(13):
                machine.reg_write(getattr(arm, f"UC_ARM_REG_R{index}"), 0)
            machine.reg_write(arm.UC_ARM_REG_R0, obj)
            if operation.startswith("C"):
                arguments = (listener_word, image, length)
            elif operation == "P":
                arguments = (text, value, force)
            else:
                arguments = (0, 0, 0)
            for index, word in enumerate(arguments, 1):
                machine.reg_write(getattr(arm, f"UC_ARM_REG_R{index}"), word)
            machine.reg_write(arm.UC_ARM_REG_SP, stack + 0xff00)
            machine.reg_write(arm.UC_ARM_REG_LR, stop)
            machine.emu_start(functions[operation]["address"], stop, count=100)
            assert machine.reg_read(arm.UC_ARM_REG_PC) == stop
            assert machine.reg_read(arm.UC_ARM_REG_SP) == stack + 0xff00
            expected = bytearray(storage)
            if operation.startswith("C"):
                struct.pack_into("<IIII", expected, 0, 0xffffffff, image, length, listener_word)
                write_patterns.add(tuple(state["writes"]))
                assert [offset for offset, size, word in state["writes"]] == [12, 0, 4, 8]
            else:
                assert not state["writes"]
            assert bytes(machine.mem_read(obj, 0x20)) == expected
            assert bytes(machine.mem_read(listener, 0x2000)) == model_before
            calls = 1 if operation == "P" and listener_word else 0
            assert state["calls"] == ([(text, value)] if calls else [])
            result = machine.reg_read(arm.UC_ARM_REG_R0) if operation == "V" else 0
            if operation == "V":
                assert result == 0
            stream.write(f"{operation} {listener_word:08x} {image:08x} {length:08x} {text:08x} {value:08x} {force:x} {calls:x} {result:08x}\n")
            counts[operation] += 1

        lengths = [0, 1, 255, 256, 257, 0x7fffffff, 0x80000000, 0xffffffff] + [rng.getrandbits(32) for _ in range(512)]
        for operation in ("C1", "C2", "D1", "D2", "V"):
            for length in lengths:
                for receiver, image in ((0, 0), (listener, 0x10003000), (0xffffffff, 0xffffffff)):
                    emit(operation, receiver, image, length)
        floats = [0, 0x80000000, 1, 0x80000001, 0x7fffff, 0x807fffff, 0x800000, 0x80800000,
                  0x3f800000, 0xbf800000, 0x7f7fffff, 0xff7fffff, 0x7f800000, 0xff800000,
                  0x7fc00000, 0xffc00000, 0x7f800001, 0xff800001] + [rng.getrandbits(32) for _ in range(512)]
        for value in floats:
            for receiver in (0, listener):
                for force in (0, 1):
                    for return_word in (0, 0xffffffff, 0x7fc00000):
                        text = (0, 0x10003000, 0xffffffff)[return_word % 3]
                        emit("P", receiver, 0x10003000, 0xffffffff, text, value, force, return_word)
    oracle = dict(role="client", original_elf_sha256=manifest["sha256"], functions=functions, cases=dict(counts),
                  fixture_sha256=sha(fixture.read_bytes()), unicorn_version=unicorn.__version__,
                  constructor_write_offsets=[12, 0, 4, 8], callback_entry_r3_words=sorted(callback_r3_values),
                  callback_contract="Independent modeled slot-zero onProgress(char const*,float) records original listener this/text/exact float bits, arbitrary callback R0 ignored by portable candidate. Original force bool overwritten by vptr value, never forwarded.",
                  execution="Only six original Dice3Programmer entries and explicit callback gateway. No Core/library/device/firmware programming bodies executed.")
    (output / "arm-oracle.json").write_text(json.dumps(oracle, indent=2) + "\n")
    sources = [library / "include/presonus/dice/programmer.hpp", library / "src/Presonus/DICE/Dice3Programmer.cpp", library / "tests/dice_programmer_tests.cpp"]
    formatter = library / ".venv/bin/clang-format"
    version = command([str(formatter), "--version"], output / "formatter-version.log").strip()
    command([str(formatter), "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *map(str, sources)], output / "formatter-check.log")
    executable = output / "dice-programmer-tests"
    command(["g++", "-std=c++17", "-O2", "-fno-fast-math", "-I" + str(library / "include"), str(sources[1]), str(sources[2]), "-o", str(executable)], output / "compile.log")
    result = command([str(executable), str(fixture)], output / "replay.log").strip()
    nm = command(["nm", "--defined-only", str(executable)], output / "nm.log")
    compiled = {line.split()[-1] for line in nm.splitlines() if line.split()}
    assert set(MANGLES.values()) <= compiled
    proof = dict(cpp_differential_passed=True, compiled_mangled_names_matched=True, mangled_names=sorted(MANGLES.values()),
                 functions=[dict(symbol, role="client", original_elf_sha256=manifest["sha256"] , operation=op) for op, symbol in functions.items()],
                 sources={str(path.relative_to(library)): sha(path.read_bytes()) for path in sources}, formatter=version,
                 native_result=result, oracle_sha256=sha((output / "arm-oracle.json").read_bytes()),
                 listener_evidence_sha256=sha((output / "listener-evidence.json").read_bytes()),
                 tool_sha256=sha(Path(__file__).read_bytes()), inspector_sha256=sha((library / "tools/dice_programmer_inspect.py").read_bytes()),
                 executable_sha256=sha(executable.read_bytes()), cases=dict(counts),
                 domain="Only constructor-initialized programmer states; opaque pointer words copied without dereference, 32bit length boundaries/random words, exact min16byte constructor state and untouched tail. Both original C1/C2 and D1/D2 entries independently byte-audited/executed; compiled aliases acknowledged. Destructors have no side effects, including no descriptor close. verify alwaysreturns0 and does not inspect image. Progress null/non-null listeners, canonical forcefalse/true, 18 float boundaries+512random float words, arbitrary callback return words; exactcallbackthis/text/floatbits/count, unchangedstate. LP64 Linux pointer-word transport is test normalization, no hardware/ARMABI/layout/concurrency claim.",
                 unresolved=["verify() int is an explicit portable numeric choice; original return spelling unencoded and no caller-use evidence found.",
                             "printProgress return and listener return declaration remain unproved; callback adapter is independent, not an invented UC interface. Candidate void declaration is not original evidence.",
                             "Non-null listener requires bound portable ProgressSink. No actual listener Core/UI behavior recovered.",
                             "verify is an original constant-zero stub; no integrity verification or firmware programming implemented."])
    proof_path = output / "validation.json"
    proof_path.write_text(json.dumps(proof, indent=2) + "\n")
    ready, pending = [], []
    for function in proof["functions"]:
        operation = function["operation"]
        record = dict(role="client", mangled=function["mangled"], original_elf_sha256=manifest["sha256"],
                      sources=proof["sources"], cpp_compiled=True, mangling_namespace_checked=True,
                      portable_ready=operation.startswith(("C", "D")), domain=proof["domain"],
                      validation=str(proof_path.relative_to(library)), validation_sha256=sha(proof_path.read_bytes()))
        if record["portable_ready"]:
            ready.append(record)
        else:
            record["unresolved"] = proof["unresolved"][0 if operation == "V" else 1]
            pending.append(record)
    (output / "ready-functions.fragment.json").write_text(json.dumps(dict(functions=ready), indent=2) + "\n")
    (output / "compiled-functions.fragment.json").write_text(json.dumps(dict(functions=pending), indent=2) + "\n")
    print(result)
    print("COUNTS", dict(counts))
    print("PROOF", sha(proof_path.read_bytes()))
    print("OUTPUT", output)


if __name__ == "__main__":
    main()
