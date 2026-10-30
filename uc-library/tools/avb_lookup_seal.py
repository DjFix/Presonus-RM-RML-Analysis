#!/usr/bin/env python3
"""Add immutable actual-provider/dependency closure to an existing AVB replay."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex

from avb_protocol_reseal import command, sha, PROOFS

PROVIDER_SHA = "cf13e63b689bcf3ef1b8a63f6dfb5e2bbecd4fa3c41b45b7725c44b27e52b408"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("replay", type=Path)
    args = parser.parse_args()
    repository = args.repository.resolve()
    library = repository / "uc-library"
    replay_path = library / args.replay
    replay = json.loads(replay_path.read_text())
    output = library / "validation/avb-lookup-candidate/seals" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output.mkdir(parents=True, exist_ok=False)
    for name, expected in replay["sources"].items():
        assert sha(library / name) == expected, name
    sources = dict(replay["sources"])
    for group, test in (("protocol", "tests/avb_protocol_tests.cpp"), ("streams", "tests/avb_streams_tests.cpp")):
        old = json.loads((library / PROOFS[group][0]).read_text())
        assert sha(library / test) == old["sources"][test]
        sources[test] = sha(library / test)
    # The tested receive body must still be the reviewed original active body.
    frozen_receive = library / "validation/avb-receive-candidate/src/AvbManagerReceive.cpp"
    assert sha(frozen_receive) == replay["receive_cpp_unchanged_sha256"]
    provider_path = library / "validation/core-upstream/provider-integration-02-validation.json"
    assert sha(provider_path) == PROVIDER_SHA
    provider = json.loads(provider_path.read_text())
    assert provider["source_commit"] == replay["upstream_commit"]
    for name, expected in provider["files"].items():
        assert sha(repository / name) == expected["sha256"], name
        assert (repository / name).stat().st_size == expected["size"], name
    for name, expected in replay["provider_archives"].items():
        assert sha(repository / name) == expected, name
    candidate = library / "validation/avb-lookup-candidate"
    sdk = repository / "temp/core-upstream/provider-integration-02/build/upstream-core/sdk/include/presonus-core-5"
    vendor = repository / "third_party/ccl-framework"
    dependencies = {}
    for index, source in enumerate((candidate / "src/AvbManagerLookup.cpp", library / "src/Presonus/AVB/AvbManagerReceive.cpp", candidate / "tests/receive_ccl_tests.cpp")):
        text = command(["g++", "-std=c++17", "-Ulinux", "-DNDEBUG=1", "-DCORE_USE_OPENSSL=1", "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-I" + str(candidate / "include"), "-I" + str(library / "include"), "-I" + str(sdk), "-M", "-MT", "closure", str(source)], output / f"dependencies-{index}.log")
        for name in shlex.split(text.replace("\\\n", " ").split(":", 1)[1]):
            path = Path(name)
            if not path.is_relative_to(sdk):
                continue
            relative = path.relative_to(sdk)
            assert sha(path) == sha(vendor / relative), str(relative)
            blob = command(["git", "-C", str(vendor), "rev-parse", replay["upstream_commit"] + ":" + str(relative)], output / ("blob-" + str(relative).replace("/", "-") + ".log")).strip()
            actual = command(["git", "-C", str(vendor), "hash-object", str(vendor / relative)], output / ("hash-" + str(relative).replace("/", "-") + ".log")).strip()
            assert blob == actual
            dependencies[str(path.relative_to(repository))] = dict(sha256=sha(path), upstream_path=str(relative), pinned_git_blob=blob)
    assert dependencies
    formatter = library / ".venv/bin/clang-format"
    command([str(formatter), "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *map(str, [library / n for n in sources])], output / "formatter-check.log")
    assert all(sha(library / name) == expected for name,expected in sources.items())
    proof = dict(replay, sources=sources, input_replay=dict(path=str(replay_path.relative_to(library)), sha256=sha(replay_path)),
                 provider_proof=dict(path=str(provider_path.relative_to(library)), sha256=PROVIDER_SHA, files_checked=len(provider["files"])),
                 actual_sdk_dependencies=dependencies, source_provider_headers_git_checked=True, seal_tool_sha256=sha(Path(__file__)),
                 validation_replayed=False, sealing_note="No input source/fixture changed after successful replay; added actual provider277file audit, unchanged historical test sources, and transitive compiler SDK-header/pinned-Git identity closure.")
    path = output / "candidate-validation.json"
    path.write_text(json.dumps(proof, indent=2) + "\n")
    for ready, name in ((True,"candidate-ready-functions.fragment.json"),(False,"candidate-compiled-functions.fragment.json")):
        records = [dict(role=r["role"], mangled=r["mangled"], original_elf_sha256=r["original_elf_sha256"], validation=str(path.relative_to(library)), validation_sha256=sha(path), sources=sources, cpp_compiled=True, mangling_namespace_checked=True, portable_ready=ready, unresolved=proof["unresolved"] if not ready else []) for r in proof["functions"] if r["portable_ready"] == ready]
        (output / name).write_text(json.dumps(dict(functions=records), indent=2) + "\n")
    print("SEALED", path, sha(path), "SDK HEADERS", len(dependencies), "PROVIDER FILES", len(provider["files"]))


if __name__ == "__main__":
    main()
