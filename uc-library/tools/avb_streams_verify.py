#!/usr/bin/env python3
"""Original ARM listener/talker constructor, destructor and truth-value checks."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
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

L = "_ZN8Presonus3AVB11AvbListener"
T = "_ZN8Presonus3AVB9AvbTalker"
MANGLES = [L + "C1Ehyti", L + "C2Ehyti", L + "D1Ev", L + "D2Ev", L + "6updateEhhh",
           T + "C1Ehi", T + "C2Ehi", T + "D1Ev", T + "D2Ev", T + "6updateEhh"]
LABELS = ["LC1", "LC2", "LD1", "LD2", "LU", "TC1", "TC2", "TD1", "TD2", "TU"]


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


def generate(repository, library, output, role):
    directory = library / "recovered-all" / role
    manifest = json.loads((directory / "manifest.json").read_text())
    binary = repository / manifest["path"]
    raw = binary.read_bytes()
    assert sha(raw) == manifest["sha256"]
    rows = json.loads((directory / "symbols.json").read_text())
    by_mangle = {row["mangled"]: row for row in rows}
    functions = [by_mangle[mangled] for mangled in MANGLES]

    def checked(row):
        data = (directory / row["export_path"]).read_bytes()
        assert data == raw[row["file_offset"]:row["file_offset"] + row["size"]]
        assert sha(data) == row["sha256"]
        return data

    for row in functions:
        checked(row)
    if role == "client":
        caller = next(row for row in rows if row["demangled"] == "Presonus::AVB::AvbManagerBase::receive(Presonus::DICE::SysexPacket const&)")
        data = checked(caller)
        consumer = []
        for address, operation in ((0xcb660, 9), (0xcb6dc, 4)):
            branch, compare = struct.unpack_from("<II", data, address - caller["address"])
            assert branch & 0xff000000 == 0xeb000000 and compare == 0xe3500000
            displacement = (((branch & 0xffffff) ^ 0x800000) - 0x800000) << 2
            assert address + 8 + displacement == functions[operation]["address"]
            consumer.append(dict(call_address=address, compare_address=address + 4,
                                 target_mangled=functions[operation]["mangled"], compare="CMP R0,#0"))
        (output / "caller-receive.bin").write_bytes(data)
        (output / "caller-return-evidence.json").write_text(json.dumps(dict(caller=caller, consumers=consumer,
            conclusion="Both update return values are consumed as truth values before notice callbacks. Exact original return typedef spelling remains unencoded."), indent=2) + "\n")
    uc = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    pages = set()
    with binary.open("rb") as stream:
        for segment in ELFFile(stream).iter_segments():
            if segment["p_type"] != "PT_LOAD":
                continue
            start = int(segment["p_vaddr"])
            end = start + int(segment["p_memsz"])
            for page in range(start & ~4095, (end + 4095) & ~4095, 4096):
                if page not in pages:
                    uc.mem_map(page, 4096)
                    pages.add(page)
            uc.mem_write(start, segment.data())
    obj, stack, stop = 0x10000000, 0x20000000, 0x30000000
    uc.mem_map(obj, 4096)
    uc.mem_map(stack, 0x10000)
    uc.mem_map(stop, 4096)
    state = {}

    def code(machine, address, size, user):
        row = functions[state["operation"]]
        assert row["address"] <= address < row["address"] + row["size"], f"unapproved execution {address:#x}"

    def write(machine, access, address, size, value, user):
        if obj <= address and address + size <= obj + 64:
            state["writes"].append((address - obj, size))
        else:
            assert stack <= address and address + size <= stack + 0x10000, f"unexpected write {address:#x}"

    uc.hook_add(unicorn.UC_HOOK_CODE, code)
    uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, write)
    counts = Counter()
    rng = random.Random(0x53545245414d)
    fixture = output / f"{role}-vectors.bin.gz"
    with fixture.open("wb") as compressed:
        with gzip.GzipFile(filename="", fileobj=compressed, mode="wb", mtime=0) as stream:
            def emit(operation, identifier_byte=0, identifier=0, suffix=0, integer_word=0, first=0, second=0, third=0):
                initial = bytearray(((index * 37 + identifier_byte) ^ (integer_word >> ((index % 4) * 8))) & 255 for index in range(64))
                expected = bytearray(initial)

                def construct(target):
                    target[0] = identifier_byte
                    if operation < 5:
                        struct.pack_into("<QQH", target, 8, identifier, ((identifier << 16) | suffix) & 0xffffffffffffffff, suffix)
                        struct.pack_into("<I", target, 28, integer_word)
                    else:
                        struct.pack_into("<I", target, 8, integer_word)

                construct(expected)
                if operation not in (0, 1, 5, 6):
                    initial[:] = expected
                uc.mem_write(obj, bytes(initial))
                sp = stack + 0xff00
                uc.mem_write(sp, struct.pack("<II", suffix, integer_word))
                state.update(operation=operation, writes=[])
                uc.reg_write(arm.UC_ARM_REG_CPSR, 0x10)
                for register in range(13):
                    uc.reg_write(getattr(arm, f"UC_ARM_REG_R{register}"), 0)
                uc.reg_write(arm.UC_ARM_REG_R0, obj)
                if operation in (0, 1):
                    arguments = (identifier_byte, identifier & 0xffffffff, identifier >> 32)
                elif operation in (5, 6):
                    arguments = (identifier_byte, integer_word, 0)
                elif operation in (4, 9):
                    arguments = (first, second, third)
                else:
                    arguments = (0xa5a5a5a5, 0x5a5a5a5a, 0x12345678)
                for register, word in enumerate(arguments, 1):
                    uc.reg_write(getattr(arm, f"UC_ARM_REG_R{register}"), word)
                uc.reg_write(arm.UC_ARM_REG_SP, sp)
                uc.reg_write(arm.UC_ARM_REG_LR, stop)
                uc.emu_start(functions[operation]["address"], stop, count=100)
                assert uc.reg_read(arm.UC_ARM_REG_PC) == stop and uc.reg_read(arm.UC_ARM_REG_SP) == sp
                assert bytes(uc.mem_read(obj, 64)) == expected
                assert bytes(uc.mem_read(sp, 8)) == struct.pack("<II", suffix, integer_word)
                pattern = state["writes"]
                if operation in (0, 1):
                    assert pattern == [(16, 4), (20, 4), (0, 1), (8, 4), (28, 4), (12, 4), (24, 2)]
                elif operation in (5, 6):
                    assert pattern == [(0, 1), (8, 4)]
                else:
                    assert pattern == []
                result = uc.reg_read(arm.UC_ARM_REG_R0) if operation in (4, 9) else 0
                if operation in (4, 9):
                    assert result == 1
                stream.write(struct.pack("<BIQIIIIII32s", operation, identifier_byte, identifier, suffix,
                                         integer_word, first, second, third, result, bytes(expected[:32])))
                counts[LABELS[operation]] += 1

            identifiers = [0, 0xffffffffffffffff] + [value << (8 * byte) for byte in range(8) for value in range(256)]
            identifiers += [rng.getrandbits(64) for _ in range(1024)]
            for operation in (0, 1):
                for suffix in range(65536):
                    emit(operation, suffix & 255, 0xfedcba9876543210, suffix, (suffix << 16) | suffix)
                for identifier in identifiers:
                    emit(operation, identifier & 255, identifier, (identifier >> 48) & 65535, rng.getrandbits(32))
                print(role, LABELS[operation], counts[LABELS[operation]], flush=True)
            edges = [0, 1, 2, 0x7ffffffe, 0x7fffffff, 0x80000000, 0x80000001, 0xfffffffe, 0xffffffff]
            for operation in (5, 6):
                for identifier_byte in range(256):
                    for word in edges:
                        emit(operation, identifier_byte, integer_word=word)
                for _ in range(1024):
                    emit(operation, rng.randrange(256), integer_word=rng.getrandbits(32))
            for operation in (2, 3, 7, 8):
                for _ in range(1024):
                    emit(operation, rng.randrange(256), rng.getrandbits(64), rng.randrange(65536), rng.getrandbits(32))
            for operation in (4, 9):
                for first in range(256):
                    for second in range(256):
                        emit(operation, first, 0xabcdef0123456789, 0xfedc, 0x80000001, first, second, first ^ second)
                if operation == 4:
                    for first in (0, 1, 127, 128, 255):
                        for second in (0, 1, 127, 128, 255):
                            for third in range(256):
                                emit(operation, third, 0xffffffffffffffff, third, 0xffffffff, first, second, third)
                    for _ in range(1024):
                        emit(operation, rng.randrange(256), rng.getrandbits(64), rng.randrange(65536), rng.getrandbits(32),
                             rng.randrange(256), rng.randrange(256), rng.randrange(256))
                print(role, LABELS[operation], counts[LABELS[operation]], flush=True)
    report = dict(role=role, original_elf_sha256=manifest["sha256"], functions=functions, cases=dict(counts),
                  fixture_sha256=sha(fixture.read_bytes()), unicorn_version=unicorn.__version__,
                  original_listener_extent=32, original_talker_extent=12,
                  untouched_listener_bytes="1..7,26..27 and modeled32..63 tail", untouched_talker_bytes="1..7 and modeled12..63 tail",
                  listener_constructor_order=[16, 20, 0, 8, 28, 12, 24], talker_constructor_order=[0, 8],
                  update_behavior="Exact R0=1, no object writes, no argument reads beyond prologue. Consumer caller compares R0 with zero.",
                  execution="Only selected original state methods, no calls/Core/device/firmware programming. Whole64byte sentinel storage and caller stackargs checked; original stack restored.")
    (output / f"{role}-arm-oracle.json").write_text(json.dumps(report, indent=2) + "\n")
    return report, fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    args = parser.parse_args()
    repository = args.repository.resolve()
    library = repository / "uc-library"
    output = library / "validation/avb-streams/runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output.mkdir(parents=True, exist_ok=False)
    sources = [library / "include/presonus/avb/streams.hpp", library / "src/Presonus/AVB/Streams.cpp", library / "tests/avb_streams_tests.cpp"]
    formatter = library / ".venv/bin/clang-format"
    version = command([str(formatter), "--version"], output / "formatter-version.log").strip()
    command([str(formatter), "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *map(str, sources)], output / "formatter-check.log")
    reports, fixtures = [], []
    for role in ("client", "server"):
        report, fixture = generate(repository, library, output, role)
        reports.append(report)
        fixtures.append(fixture)
    for operation in (4, 9):
        assert reports[0]["functions"][operation]["sha256"] == reports[1]["functions"][operation]["sha256"]
    executable = output / "avb-streams-tests"
    command(["g++", "-std=c++17", "-O2", "-I" + str(library / "include"), str(sources[1]), str(sources[2]), "-lz", "-o", str(executable)], output / "compile.log")
    result = command([str(executable), *map(str, fixtures)], output / "replay.log").strip()
    nm = command(["nm", "--defined-only", str(executable)], output / "nm.log")
    compiled = {line.split()[-1] for line in nm.splitlines() if line.split()}
    assert set(MANGLES) <= compiled
    proof = dict(cpp_differential_passed=True, compiled_mangled_names_matched=True, mangled_names=sorted(MANGLES),
                 functions=[dict(row, operation=LABELS[index], role=report["role"], original_elf_sha256=report["original_elf_sha256"]) for report in reports for index, row in enumerate(report["functions"])],
                 sources={str(path.relative_to(library)): sha(path.read_bytes()) for path in sources}, formatter=version,
                 native_result=result, cases={report["role"]: report["cases"] for report in reports},
                 oracle_sha256={report["role"]: sha((output / f'{report["role"]}-arm-oracle.json').read_bytes()) for report in reports},
                 caller_evidence_sha256=sha((output / "caller-return-evidence.json").read_bytes()),
                 tool_sha256=sha(Path(__file__).read_bytes()), executable_sha256=sha(executable.read_bytes()),
                 domain="Both original ELF C1/C2,D1/D2/update entries independently bytechecked/executed. Listener ctor all65536suffixes plus everybytevalue in each64bitposition,0/allones and1024randomidentifiers withrandomsignedword; Talker all256IDs x9integeredges +1024randompairs. Destructors1024constructorinitializedstates each. Talker update all65536bytepairs; Listener all65536first/secondpairs withXORthird +5x5x256thirdaxis +1024randomtriples. Whole64byte original initializedsentinel storage unchangedexcept exactconstructorstores; originalholes/tail preserved. Native semanticfields matched while ARMholes/padding/layout excluded; fullnativeobject unchangedbyupdate/dtor. No originalABI, volatile/MMIO, ownership, completeclasslayout, concurrency or hardware claim.",
                 unresolved=["Update bool is an explicit portable truth-value choice; original return typedef spelling unencoded. ARM returns exact1, caller CMP consumesit, and no state updates are invented.",
                             "Field names are independent portable inspection names, not recovered original members. Constructor minimumextents do not prove sizeof or inherited layout.",
                             "Original listener constructor holes1..7/26..27 and Talkerholes1..7 remain untouched in initializedsentinel model; native padding is excluded from crossABIequivalence."])
    path = output / "validation.json"
    path.write_text(json.dumps(proof, indent=2) + "\n")
    ready = [dict(role=row["role"], mangled=row["mangled"], original_elf_sha256=row["original_elf_sha256"],
                  validation=str(path.relative_to(library)), validation_sha256=sha(path.read_bytes()), sources=proof["sources"],
                  cpp_compiled=True, mangling_namespace_checked=True, portable_ready=True, domain=proof["domain"]) for row in proof["functions"]]
    (output / "ready-functions.fragment.json").write_text(json.dumps(dict(functions=ready), indent=2) + "\n")
    print(result)
    print("COUNTS", proof["cases"])
    print("PROOF", sha(path.read_bytes()))
    print("OUTPUT", output)


if __name__ == "__main__":
    main()
