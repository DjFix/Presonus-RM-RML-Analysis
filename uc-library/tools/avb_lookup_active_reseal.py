#!/usr/bin/env python3
"""Fixture-only Linux reseal after root-controlled CCL AVB candidate apply."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform

from avb_lookup_verify import MANGLES
from avb_protocol_reseal import command, sha, verify_originals, PROOFS, HELPER, LISTENER, TALKER

SEALED = "validation/avb-lookup-candidate/seals/20261027T020810.539263Z/candidate-validation.json"
SEALED_SHA = "2a4fb303dab19d29273bf5e470b459019d658b881768f100faa696dd7f907d51"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("--sdk", type=Path)
    parser.add_argument("--provider-proof", type=Path)
    args = parser.parse_args()
    assert platform.system() == "Linux"
    repository = args.repository.resolve()
    library = repository / "uc-library"
    assert sha(library / SEALED) == SEALED_SHA
    sealed = json.loads((library / SEALED).read_text())
    candidate = library / "validation/avb-lookup-candidate"
    manifest = json.loads((candidate / "apply-manifest.json").read_text())
    for entry in manifest["files"]:
        assert sha(library / entry["target"]) == entry["sha256"], "root apply incomplete: " + entry["target"]
    replacements = {str((candidate / row["candidate"]).relative_to(library)):row["target"] for row in manifest["files"]}
    sources = {}
    for name, expected in sealed["sources"].items():
        if name == "validation/avb-lookup-candidate/tests/lookup_tests.cpp":
            selected = name
        else:
            selected = replacements.get(name, name)
        assert sha(library / selected) == expected, selected
        sources[selected] = expected
    for name, expected in sealed["provider_archives"].items():
        assert sha(repository / name) == expected
    for name, entry in sealed["actual_sdk_dependencies"].items():
        assert sha(repository / name) == entry["sha256"]
    provider = sealed["provider_proof"]
    assert sha(library / provider["path"]) == provider["sha256"]
    old = {group:json.loads((library / path).read_text()) for group,(path,_) in PROOFS.items()}
    output = library / "validation/avb-lookup-active/runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output.mkdir(parents=True, exist_ok=False)
    original_checks = verify_originals(repository, library, [sealed["functions"], *[d["functions"] for d in old.values()]])
    formatter = library / ".venv/bin/clang-format"
    command([str(formatter), "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *[str(library / n) for n in sources]], output / "formatter-check.log")
    sdk = (repository / args.sdk).resolve() if args.sdk else repository / "temp/core-upstream/provider-integration-02/build/upstream-core/sdk"
    assert sdk.is_relative_to(repository) and sdk.is_dir()
    current_provider = None
    if args.provider_proof:
        current_path = (repository / args.provider_proof).resolve()
        assert current_path.is_relative_to(repository)
        current_provider = json.loads(current_path.read_text())
        assert current_provider['passed'] and current_provider['source_commit'] == 'e8cbdea4a4a20e15111f5a690798a259c0374b31'
        for name, digest in current_provider['provider_sdk_hashes'].items():
            assert sha(sdk / name) == digest, name
        current_provider = dict(path=str(current_path.relative_to(repository)), sha256=sha(current_path),
            sdk=str(sdk.relative_to(repository)),
            sdk_files={str(p.relative_to(sdk)):sha(p) for p in sdk.rglob('*') if p.is_file()})
    production = [library / "src/Presonus/AVB" / n for n in ("AvbManagerReceive.cpp", "Protocol.cpp", "Streams.cpp", "AvbManagerLookup.cpp")]
    build = ["g++", "-std=c++17", "-O2", "-Ulinux", "-DNDEBUG=1", "-DCORE_USE_OPENSSL=1", "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-I" + str(library / "include"), "-I" + str(sdk / "include/presonus-core-5"), *map(str, production)]
    fixtures = {}
    for name, expected in sealed["existing_fixture_sha256"].items():
        assert sha(library / name) == expected
        group = "receive" if "receive-" in name else "streams" if "avb-streams" in name else "protocol"
        fixtures.setdefault(group, []).append(library / name)
    # Keep the protocol executable's required argument order independent of JSON ordering.
    fixtures["protocol"].sort(key=lambda p:("accept" not in p.name, "reverse" not in p.name))
    replay = library / sealed["input_replay"]["path"]
    assert sha(replay) == sealed["input_replay"]["sha256"]
    fixtures["lookup"] = [replay.parent / f"{role}-lookup-vectors.txt" for role in ("client", "server")]
    for role, fixture in zip(("client", "server"), fixtures["lookup"]):
        oracle_path = replay.parent / f"{role}-arm-oracle.json"
        assert sha(oracle_path) == sealed["oracle_sha256"][role]
        assert sha(fixture) == json.loads(oracle_path.read_text())["fixture_sha256"]
    tests = {"protocol":library / "tests/avb_protocol_tests.cpp", "streams":library / "tests/avb_streams_tests.cpp", "receive":library / "tests/avb_receive_tests.cpp", "lookup":candidate / "tests/lookup_tests.cpp"}
    results = {}
    expected_names = set(MANGLES) | {r["mangled"] for d in old.values() for r in d["functions"]}
    for group,test in tests.items():
        executable = output / f"{group}-tests"
        wraps = ["-Wl,--wrap=" + n for n in (HELPER, LISTENER, TALKER)] if group == "receive" else []
        command([*build, str(test), *wraps, str(sdk / "lib/libcorelib.a"), str(sdk / "lib/libpresonus_core_allocator.a"), "-lz", "-pthread", "-ldl", "-lm", "-o", str(executable)], output / f"{group}-compile.log")
        results[group] = [command([str(executable), str(p)], output / f"lookup-{p.stem}-replay.log").strip() for p in fixtures[group]] if group == "lookup" else [command([str(executable), *map(str, fixtures[group])], output / f"{group}-replay.log").strip()]
        names = {line.split()[-1] for line in command(["nm", "--defined-only", str(executable)], output / f"{group}-nm.log").splitlines() if line.split()}
        assert expected_names <= names
    assert all(sha(library / n) == h for n,h in sources.items())
    rows = [dict(r, group="lookup") for r in sealed["functions"]]
    rows += [dict(r, group="protocol", portable_ready=r["operation"] not in ("C", "N")) for r in old["protocol"]["functions"]]
    rows += [dict(r, group="receive", portable_ready=False) for r in old["receive"]["functions"]]
    domains = {"lookup":sealed["domain"],
               "protocol":old["protocol"]["domain"],
               "receive":old["receive"]["domain"]}
    assert all(isinstance(value,str) and value.strip() for value in domains.values())
    proof = dict(sealed, status="active-path CCL list binding reseal", sources=sources, functions=rows, native_results=results,
                 mangled_names=sorted(expected_names), original_bytes_checked=original_checks, original_arm_regenerated=False,
                 input_candidate=dict(path=SEALED, sha256=SEALED_SHA), active_tool_sha256=sha(Path(__file__)), validation_replayed=True)
    proof['current_source_provider'] = current_provider
    proof['validation_domains'] = domains
    proof['provider_archives'] = {str((sdk / 'lib' / n).relative_to(repository)):sha(sdk / 'lib' / n)
                                 for n in ('libcorelib.a', 'libpresonus_core_allocator.a')}
    path = output / "validation.json"
    path.write_text(json.dumps(proof,indent=2) + "\n")
    for ready,name in ((True,"ready-functions.fragment.json"),(False,"compiled-functions.fragment.json")):
        records = [dict(role=r["role"], mangled=r["mangled"], original_elf_sha256=r["original_elf_sha256"], validation=str(path.relative_to(library)), validation_sha256=sha(path), sources=sources, domain=domains[r['group']], cpp_compiled=True, mangling_namespace_checked=True, portable_ready=ready, unresolved=[] if ready else "Original return declaration unresolved; portable behavior only. See detailed proof.") for r in rows if r["portable_ready"] == ready]
        (output / name).write_text(json.dumps(dict(functions=records),indent=2) + "\n")
    print("ACTIVE RESULTS", results)
    print("PROOF", path, sha(path))


if __name__ == "__main__":
    main()
