#!/usr/bin/env python3
"""Isolated real-CCL AVB binding, original app-only ARM lookup oracle."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import struct

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import arm_const as arm

from avb_protocol_reseal import command, sha, verify_originals, PROOFS, HELPER, LISTENER, TALKER

MANGLES = ["_ZN8Presonus3AVB14AvbManagerBase12findListenerEh",
           "_ZN8Presonus3AVB14AvbManagerBase10findTalkerEh",
           "_ZN8Presonus3AVB14AvbManagerBase21lookupNextTalkerIndexEv"]
PIN = "e8cbdea4a4a20e15111f5a690798a259c0374b31"


def generate(repository, library, output, role):
    directory = library / "recovered-all" / role
    manifest = json.loads((directory / "manifest.json").read_text())
    binary = repository / manifest["path"]
    assert sha(binary) == manifest["sha256"]
    rows = {r["mangled"]:r for r in json.loads((directory / "symbols.json").read_text())}
    functions = [dict(rows[n], role=role, original_elf_sha256=manifest["sha256"]) for n in MANGLES]
    verify_originals(repository, library, [functions])
    uc = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    pages = set()
    with binary.open("rb") as stream:
        for segment in ELFFile(stream).iter_segments():
            if segment["p_type"] != "PT_LOAD":
                continue
            start, end = segment["p_vaddr"], segment["p_vaddr"] + segment["p_memsz"]
            for page in range(start & ~4095, (end + 4095) & ~4095, 4096):
                if page not in pages:
                    uc.mem_map(page, 4096)
                    pages.add(page)
            uc.mem_write(start, segment.data())
    obj, stack, stop = 0x10000000, 0x20000000, 0x30000000
    uc.mem_map(obj, 16384)
    uc.mem_map(stack, 65536)
    uc.mem_map(stop, 4096)
    state = {}

    def code(machine, address, size, user):
        row = functions[state["operation"]]
        assert row["address"] <= address < row["address"] + row["size"], f"non-app execution {address:#x}"

    def write(machine, access, address, size, value, user):
        assert stack <= address and address + size <= stack + 65536, f"state write {address:#x}"

    uc.hook_add(unicorn.UC_HOOK_CODE, code)
    uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, write)
    counts = Counter()
    rng = random.Random(0x4156424c495354)
    fixture = output / f"{role}-lookup-vectors.txt"
    with fixture.open("w") as stream:
        def emit(operation, query, items):
            initial = bytearray([0xa5] * 16384)
            for index, (identifier, word) in enumerate(items):
                node, item = 0x100 + index * 16, 0x1000 + index * 64
                next_node = obj + node + 16 if index + 1 < len(items) else 0
                struct.pack_into("<III", initial, node, obj + item, next_node, obj + node - 16 if index else 0)
                initial[item] = identifier
                struct.pack_into("<I", initial, item + 8, word)
            head = obj + 0x100 if items else 0
            struct.pack_into("<I", initial, 0x74, head)
            struct.pack_into("<I", initial, 0x80, head)
            uc.mem_write(obj, bytes(initial))
            for register in range(13):
                uc.reg_write(getattr(arm, f"UC_ARM_REG_R{register}"), 0x55555555)
            uc.reg_write(arm.UC_ARM_REG_CPSR, 0x10)
            uc.reg_write(arm.UC_ARM_REG_R0, obj)
            uc.reg_write(arm.UC_ARM_REG_R1, query)
            uc.reg_write(arm.UC_ARM_REG_SP, stack + 0xff00)
            uc.reg_write(arm.UC_ARM_REG_LR, stop)
            state["operation"] = operation
            uc.emu_start(functions[operation]["address"], stop, count=10000)
            assert uc.reg_read(arm.UC_ARM_REG_PC) == stop
            assert uc.reg_read(arm.UC_ARM_REG_SP) == stack + 0xff00
            assert bytes(uc.mem_read(obj, 16384)) == initial
            actual = uc.reg_read(arm.UC_ARM_REG_R0)
            if operation < 2:
                result = next((i + 1 for i, (identifier, _) in enumerate(items) if identifier == query), 0)
                expected = obj + 0x1000 + (result - 1) * 64 if result else 0
            else:
                result = sum(word for _, word in items) & 255
                expected = result
            assert actual == expected, (operation, query, items, actual, expected)
            stream.write(" ".join(map(str, [operation, query, len(items), result, *[v for item in items for v in item]])) + "\n")
            counts[str(operation)] += 1

        for query in range(256):
            for operation in (0, 1):
                for ids in ([], [query], [(query + 1) & 255], [query, query], [(query + 1) & 255, query], [query] * 64):
                    emit(operation, query, [(identifier, rng.getrandbits(32)) for identifier in ids])
        for operation in (0, 1, 2):
            for _ in range(4096):
                count = rng.randrange(65)
                emit(operation, rng.randrange(256), [(rng.randrange(256), rng.getrandbits(32)) for _ in range(count)])
        edges = [0, 1, 127, 128, 255, 256, 257, 0x7fffffff, 0x80000000, 0xffffff00, 0xffffffff]
        for word in edges:
            for count in (0, 1, 2, 3, 16, 64):
                emit(2, 0, [(i, word) for i in range(count)])
        for word in range(65536):
            emit(2, 0, [(0, word)])
    result = dict(role=role, functions=functions, counts=dict(counts), fixture_sha256=sha(fixture),
                  execution="Only three original Presonus app bodies; no Core, constructor, device or firmware execution.",
                  domain="Acyclic ordered lists 0..64 borrowed non-null objects; duplicate IDs first-match; all256queries; all16bit single words, uint32 edges/random; no writes to manager/nodes/objects; full R0 checked.")
    (output / f"{role}-arm-oracle.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    args = parser.parse_args()
    assert platform.system() == "Linux"
    repository = args.repository.resolve()
    library = repository / "uc-library"
    candidate = library / "validation/avb-lookup-candidate"
    output = candidate / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output.mkdir(parents=True, exist_ok=False)
    vendor = repository / "third_party/ccl-framework"
    assert command(["git", "-C", str(vendor), "rev-parse", "HEAD"], output / "vendor-commit.log").strip() == PIN
    sdk = repository / "temp/core-upstream/provider-integration-02/build/upstream-core/sdk"
    archives = [sdk / "lib/libcorelib.a", sdk / "lib/libpresonus_core_allocator.a"]
    provider_hashes = {str(p.relative_to(repository)):sha(p) for p in archives}
    owned = sorted([*candidate.glob("include/presonus/avb/*.hpp"), *candidate.glob("src/*.cpp"), *candidate.glob("tests/*.cpp")])
    formatter = library / ".venv/bin/clang-format"
    version = command([str(formatter), "--version"], output / "formatter-version.log").strip()
    command([str(formatter), "--style=file", "--fallback-style=LLVM", "-i", *map(str, owned)], output / "formatter-apply.log")
    command([str(formatter), "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *map(str, owned)], output / "formatter-check.log")
    old = {group:json.loads((library / path).read_text()) for group,(path,_) in PROOFS.items()}
    for group,(path,expected) in PROOFS.items():
        assert sha(library / path) == expected
    compatibility = {
        "protocol": [library / Path(PROOFS["protocol"][0]).parent / p for p in ("accept-vectors.txt", "reverse-vectors.txt", "memory-vectors.bin.gz")],
        "streams": [library / Path(PROOFS["streams"][0]).parent / f"{role}-vectors.bin.gz" for role in ("client", "server")],
        "receive": [library / Path(PROOFS["receive"][0]).parent / "receive-vectors.txt.gz"],
    }
    # Assert every reused fixture against its frozen proof.
    for group, paths in compatibility.items():
        if group == "streams":
            for role, path in zip(("client", "server"), paths):
                oracle_path = path.parent / f"{role}-arm-oracle.json"
                assert sha(oracle_path) == old[group]["oracle_sha256"][role]
                assert sha(path) == json.loads(oracle_path.read_text())["fixture_sha256"]
        else:
            oracle_path = paths[0].parent / "arm-oracle.json"
            assert sha(oracle_path) == old[group]["oracle_sha256"]
            oracle = json.loads(oracle_path.read_text())
            for path in paths:
                expected = oracle["fixture_sha256"] if group == "receive" else oracle["fixtures"][path.name]
                assert sha(path) == expected
    oracles = {role:generate(repository, library, output, role) for role in ("client", "server")}
    source_files = [library / "src/Presonus/AVB" / n for n in ("AvbManagerReceive.cpp", "Protocol.cpp", "Streams.cpp")]
    closure = owned + source_files + [library / "include/presonus/avb/streams.hpp", library / "include/presonus/dice/sysex.hpp"]
    vendor_files = [vendor / p for p in ("core/public/corelinkedlist.h", "core/public/corecontainer.h", "core/public/coremacros.h", "core/public/coretypes.h")]
    before = {str(p.relative_to(library)):sha(p) for p in closure}
    build = ["g++", "-std=c++17", "-O2", "-Ulinux", "-DNDEBUG=1", "-DCORE_USE_OPENSSL=1", "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-I" + str(candidate / "include"), "-I" + str(library / "include"), "-I" + str(sdk / "include/presonus-core-5"), *map(str, source_files), str(candidate / "src/AvbManagerLookup.cpp")]
    tests = {"protocol":library / "tests/avb_protocol_tests.cpp", "streams":library / "tests/avb_streams_tests.cpp", "receive":candidate / "tests/receive_ccl_tests.cpp", "lookup":candidate / "tests/lookup_tests.cpp"}
    results = {}
    for group,test in tests.items():
        executable = output / f"{group}-tests"
        wraps = ["-Wl,--wrap=" + n for n in (HELPER, LISTENER, TALKER)] if group == "receive" else []
        command([*build, str(test), *wraps, *map(str, archives), "-lz", "-pthread", "-ldl", "-lm", "-o", str(executable)], output / f"{group}-compile.log")
        fixtures = compatibility[group] if group != "lookup" else [output / f"{role}-lookup-vectors.txt" for role in ("client", "server")]
        results[group] = [command([str(executable), *map(str, fixtures)], output / f"{group}-replay.log").strip()] if group != "lookup" else [command([str(executable), str(p)], output / f"lookup-{p.stem}-replay.log").strip() for p in fixtures]
        nm = command(["nm", "--defined-only", str(executable)], output / f"{group}-nm.log")
        names = {line.split()[-1] for line in nm.splitlines() if line.split()}
        assert set(MANGLES) <= names
    assert before == {str(p.relative_to(library)):sha(p) for p in closure}
    proof = dict(status="isolated CCL binding candidate; no active apply", cpp_differential_passed=True, compiled_mangled_names_matched=True, mangled_names=MANGLES,
                 functions=[dict(row, portable_ready=row["mangled"] == MANGLES[2]) for oracle in oracles.values() for row in oracle["functions"]],
                 sources=before, upstream_commit=PIN, upstream_sources={str(p.relative_to(repository)):sha(p) for p in vendor_files},
                 provider_archives=provider_hashes, formatter=version, native_results=results, oracle_sha256={role:sha(output / f"{role}-arm-oracle.json") for role in oracles},
                 receive_cpp_unchanged_sha256=sha(source_files[0]), existing_fixture_sha256={str(p.relative_to(library)):sha(p) for ps in compatibility.values() for p in ps},
                 tool_sha256=sha(Path(__file__)),
                 domain="Actual CCL5.0 LinkedList pointer collections, default consumer RTTI, app findIf and modulo sum. Original app-only ARM bothELFs; acyclic non-null lists <=64. Full existing800070 protocol/stream/receive fixtures replayed, including collection-clearing notices.",
                 unresolved=["Pointer return spelling/const/typedef unencoded: find methods compiled/declaration-pending; typed list metadata supports portable pointer choice only.", "unsigned char sum return is portable numeric choice; original typedef/spelling unproven, all observed R0 0..255.", "No old complete manager/layout, Core ABI, concurrent mutation, cycles/null stream pointer or hardware claim.", "ReceiveContext lists own CCL link nodes only and context copying explicitly disabled; streams remain borrowed. Production app source receive byte unchanged; test vector captures independently adapted.", "CCL source behavior is preferred where framework differs; it is not original Core binary recovery."])
    path = output / "candidate-validation.json"
    path.write_text(json.dumps(proof, indent=2) + "\n")
    for ready, name in ((True,"candidate-ready-functions.fragment.json"),(False,"candidate-compiled-functions.fragment.json")):
        records = [dict(role=r["role"], mangled=r["mangled"], original_elf_sha256=r["original_elf_sha256"], validation=str(path.relative_to(library)), validation_sha256=sha(path), sources=before, cpp_compiled=True, mangling_namespace_checked=True, portable_ready=ready, unresolved=proof["unresolved"] if not ready else []) for r in proof["functions"] if r["portable_ready"] == ready]
        (output / name).write_text(json.dumps(dict(functions=records), indent=2) + "\n")
    print("RESULTS", results, flush=True)
    print("PROOF", path, sha(path), flush=True)


if __name__ == "__main__":
    main()
