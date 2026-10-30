#!/usr/bin/env python3
"""Linux fixture-only active-path AVB protocol/receive controlled reseal."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess

from elftools.elf.elffile import ELFFile

RECEIVE = "_ZN8Presonus3AVB14AvbManagerBase7receiveERKNS_4DICE11SysexPacketE"
HELPER = "_ZN8Presonus3AVB14AvbManagerBase15unpackAvbSpiMsgEPhPKhi"
LISTENER = "_ZN8Presonus3AVB11AvbListener6updateEhhh"
TALKER = "_ZN8Presonus3AVB9AvbTalker6updateEhh"
PROOFS = {
    "protocol": ("validation/avb-protocol/runs/20261026T235518.530958Z/validation.json", "e0176c38263305a67b67d9631af9ae93267d39876ecbe9ec84df9f0c22b05db8"),
    "streams": ("validation/avb-streams/runs/20261027T000739.509106Z/validation.json", "f54b3d21818192568d215aa9d46aea10cd68e96c2a66c1bf773f5e7432f044ee"),
    "receive": ("validation/avb-receive-candidate/runs/20261027T003044.766641Z/candidate-validation.json", "6a0f2f7e066fe4cc9bbcaecc05394ee60f5f740a22c627a66fdaaf1c4a48e068"),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(argv, log):
    scratch = log.parent / "temp"
    scratch.mkdir(exist_ok=True)
    result = subprocess.run(argv, capture_output=True, text=True, env=dict(os.environ, TMPDIR=str(scratch)))
    log.write_text("TMPDIR " + str(scratch) + "\nCOMMAND " + repr(argv) + "\n" + result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"command exit{result.returncode}: {log}")
    return result.stdout


def verify_originals(repository, library, groups):
    by_role = {}
    for rows in groups:
        for row in rows:
            by_role.setdefault(row["role"], {})[row["mangled"]] = row
    checked = []
    for role, functions in by_role.items():
        directory = library / "recovered-all" / role
        manifest = json.loads((directory / "manifest.json").read_text())
        binary = repository / manifest["path"]
        assert sha(binary) == manifest["sha256"]
        raw = binary.read_bytes()
        with binary.open("rb") as stream:
            elf = ELFFile(stream)
            for row in functions.values():
                assert row["original_elf_sha256"] == manifest["sha256"]
                section = elf.get_section(row["section"])
                assert section["sh_type"] != "SHT_NOBITS"
                offset = section["sh_offset"] + row["address"] - section["sh_addr"]
                assert offset == row["file_offset"]
                assert section["sh_addr"] <= row["address"] and row["address"] + row["size"] <= section["sh_addr"] + section["sh_size"]
                code = raw[offset:offset + row["size"]]
                assert code == (directory / row["export_path"]).read_bytes()
                assert hashlib.sha256(code).hexdigest() == row["sha256"]
                checked.append(dict(role=role, mangled=row["mangled"], original_elf_sha256=manifest["sha256"], byte_sha256=row["sha256"]))
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("--mode", choices=("active", "candidate"), default="active")
    args = parser.parse_args()
    if platform.system() != "Linux":
        raise RuntimeError("Linux-only validation; macOS validation was explicitly skipped")
    repository = args.repository.resolve()
    library = repository / "uc-library"
    candidate = library / "validation/avb-receive-candidate"
    output = library / "validation/avb-protocol-reseal/runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output.mkdir(parents=True, exist_ok=False)
    old = {}
    locations = {}
    for group, (name, expected) in PROOFS.items():
        path = library / name
        assert sha(path) == expected, name
        old[group] = json.loads(path.read_text())
        locations[group] = path.parent
    # Frozen candidate inputs stay unchanged; header migration is a new proof.
    for name, expected in {**old["receive"]["sources"], **old["receive"]["sealed_dependencies"]}.items():
        assert sha(library / name) == expected, name
    manifest = json.loads((candidate / "apply-manifest.json").read_text())
    selected = {}
    for entry in manifest["files"]:
        path = candidate / entry["candidate"] if args.mode == "candidate" else library / entry["target"]
        if not path.exists():
            raise RuntimeError(f"controlled apply not complete: {path}")
        assert sha(path) == entry["sha256"], f"source differs from reviewed candidate: {path}"
        selected[entry["candidate"]] = path
    header = selected["include/presonus/avb/protocol.hpp"]
    services = selected["include/presonus/avb/receive_services.hpp"]
    receive_cpp = selected["src/AvbManagerReceive.cpp"]
    receive_test = selected["tests/receive_tests.cpp"]
    # Bind original oracle metadata and existing fixtures; do not regenerate ARM.
    oracle_paths = {
        "protocol": locations["protocol"] / "arm-oracle.json",
        "receive": locations["receive"] / "arm-oracle.json",
        "client_streams": locations["streams"] / "client-arm-oracle.json",
        "server_streams": locations["streams"] / "server-arm-oracle.json",
    }
    assert sha(oracle_paths["protocol"]) == old["protocol"]["oracle_sha256"]
    assert sha(oracle_paths["receive"]) == old["receive"]["oracle_sha256"]
    for role in ("client", "server"):
        assert sha(oracle_paths[f"{role}_streams"]) == old["streams"]["oracle_sha256"][role]
    oracles = {name: json.loads(path.read_text()) for name, path in oracle_paths.items()}
    vectors = {
        "protocol": [locations["protocol"] / name for name in ("accept-vectors.txt", "reverse-vectors.txt", "memory-vectors.bin.gz")],
        "receive": [locations["receive"] / "receive-vectors.txt.gz"],
        "streams": [locations["streams"] / f"{role}-vectors.bin.gz" for role in ("client", "server")],
    }
    for path in vectors["protocol"]:
        assert sha(path) == oracles["protocol"]["fixtures"][path.name]
    assert sha(vectors["receive"][0]) == oracles["receive"]["fixture_sha256"]
    for index, role in enumerate(("client", "server")):
        assert sha(vectors["streams"][index]) == oracles[f"{role}_streams"]["fixture_sha256"]
    original_checks = verify_originals(repository, library, [old[group]["functions"] for group in ("protocol", "receive", "streams")])
    protocol_cpp = library / "src/Presonus/AVB/Protocol.cpp"
    streams_cpp = library / "src/Presonus/AVB/Streams.cpp"
    protocol_test = library / "tests/avb_protocol_tests.cpp"
    streams_test = library / "tests/avb_streams_tests.cpp"
    closure = [header, services, receive_cpp, receive_test, protocol_cpp, streams_cpp,
               library / "include/presonus/avb/streams.hpp", library / "include/presonus/dice/sysex.hpp", protocol_test, streams_test]
    formatter = library / ".venv/bin/clang-format"
    version = command([str(formatter), "--version"], output / "formatter-version.log").strip()
    command([str(formatter), "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *map(str, closure)], output / "formatter-check.log")
    sources = {str(path.relative_to(library)): sha(path) for path in closure}
    include = candidate / "include" if args.mode == "candidate" else library / "include"
    build = ["g++", "-std=c++17", "-O2", "-I" + str(include), "-I" + str(library / "include"),
             str(receive_cpp), str(protocol_cpp), str(streams_cpp)]
    results, executable_hashes, symbol_sets = {}, {}, {}
    for group, test in (("protocol", protocol_test), ("streams", streams_test), ("receive", receive_test)):
        executable = output / f"{group}-tests"
        wraps = ["-Wl,--wrap=" + name for name in (HELPER, LISTENER, TALKER)] if group == "receive" else []
        command([*build, str(test), *wraps, "-lz", "-o", str(executable)], output / f"{group}-compile.log")
        results[group] = command([str(executable), *map(str, vectors[group])], output / f"{group}-replay.log").strip()
        nm = command(["nm", "--defined-only", str(executable)], output / f"{group}-nm.log")
        symbol_sets[group] = {line.split()[-1] for line in nm.splitlines() if line.split()}
        executable_hashes[group] = sha(executable)
    expected_names = {row["mangled"] for group in ("protocol", "receive", "streams") for row in old[group]["functions"]}
    assert expected_names <= symbol_sets["receive"]
    compiler = command(["g++", "--version"], output / "compiler-version.log").splitlines()[0]
    checked_after = {str(path.relative_to(library)):sha(path) for path in closure}
    assert checked_after == sources, "source changed during validation"
    rows = []
    for original in old["protocol"]["functions"]:
        rows.append(dict(original, portable_ready=original["operation"] not in ("C", "N"), group="protocol"))
    rows.append(dict(old["receive"]["functions"][0], portable_ready=False, group="receive", operation="receive"))
    proof = dict(status="active-path reseal" if args.mode == "active" else "isolated reseal candidate; not active admission",
                 mode=args.mode, cpp_differential_passed=True, compiled_mangled_names_matched=True,
                 mangled_names=sorted(expected_names), functions=rows, sources=sources,
                 formatter=version, compiler=compiler, platform=platform.platform(), native_results=results,
                 executable_sha256=executable_hashes, input_proofs={key:dict(path=value[0],sha256=value[1]) for key,value in PROOFS.items()},
                 input_oracle_sha256={key:sha(path) for key,path in oracle_paths.items()},
                 fixtures={str(path.relative_to(library)):sha(path) for paths in vectors.values() for path in paths},
                 original_bytes_checked=original_checks, original_arm_regenerated=False,
                 tool_sha256=sha(Path(__file__)), base_header_sha256=old["receive"]["base_header_sha256"],
                 current_protocol_header_sha256=sha(header),
                 domain=old["protocol"]["domain"] + " Receive: " + old["receive"]["domain"],
                 original_semantic_limits=old["receive"]["unresolved"] + old["protocol"]["unresolved"],
                 readiness="Only protocol A/R/U may be ready; C/N and receive original returns remain declaration-pending. Streams are unchanged compatibility inputs, not new admissions.")
    path = output / "validation.json"
    path.write_text(json.dumps(proof, indent=2) + "\n")
    ready, pending = [], []
    for row in rows:
        record = dict(role=row["role"], mangled=row["mangled"], original_elf_sha256=row["original_elf_sha256"],
                      validation=str(path.relative_to(library)), validation_sha256=sha(path), sources=sources,
                      cpp_compiled=True, mangling_namespace_checked=True, portable_ready=row["portable_ready"],
                      domain=old[row["group"]]["domain"])
        if row["portable_ready"]:
            ready.append(record)
        else:
            record["unresolved"] = "Original receive return unproved; candidate void is a portable choice only. Known scratch/prefix and independent collection/notice contracts remain bounded." if row["group"] == "receive" else "Original nibble method return declaration unproved; void port covers exact memory side effects, not incidental R0."
            pending.append(record)
    prefix = "candidate-" if args.mode == "candidate" else ""
    (output / (prefix + "ready-functions.fragment.json")).write_text(json.dumps(dict(functions=ready),indent=2) + "\n")
    (output / (prefix + "compiled-functions.fragment.json")).write_text(json.dumps(dict(functions=pending),indent=2) + "\n")
    print("MODE", args.mode)
    print("RESULTS", results)
    print("ORIGINAL MANGLES", len(expected_names))
    print("READY", len(ready), "PENDING", len(pending))
    print("PROOF", sha(path))
    print("OUTPUT", output)


if __name__ == "__main__":
    main()
