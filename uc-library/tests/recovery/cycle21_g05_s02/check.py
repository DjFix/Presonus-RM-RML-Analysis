"""Compare isolated IconManager replays to original ARM observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import native

ROOT = Path.cwd()
SCRATCH = ROOT / "temp/recovery-work"
SOURCES = ("src/IconManager.cpp", "include/presonus/IconManager.hpp")
LIB_DEPS = ("include/presonus/utilities/string_utils.hpp",
            "src/utilities/StringUtils.cpp", "include/presonus/SLChannel.hpp",
            "src/Presonus/SLChannel.cpp")
CORE = tuple("third_party/ccl-framework/core/" + part for part in (
    "portable/corefile.h", "portable/corefilename.h", "portable/corefilename.cpp",
    "public/corevector.h", "public/corestringbuffer.h",
    "platform/shared/coreplatformfilesystem.h",
    "platform/shared/posix/corefilesystem.posix.h",
    "platform/shared/posix/corefilesystem.posix.cpp"))
DOMAINS = {
    1: "Original complete-object D1 entry and vector cleanup receiver for empty and nonempty categories. The host runs actual pinned Vector destruction and observes one real backing-array deletion.",
    2: "Original append behavior of existing category state with recursion enabled and disabled. Directory order is obtained from the actual pinned Linux iterator, with visible/hidden files and directories, three nested levels, and empty and missing directories.",
    3: "Original C1 constructor variant with false and true recursive parsing over existing, empty and missing directories. Native initialization and parser call execute in concert, with real host pinned filename, iterator and vector behavior.",
    4: "Negative, valid and beyond-end indices over four ordered filename forms, including embedded dots and differing extensions. Native scratch bytes are observed immediately at return and compared with owning portable output.",
    5: "Null, empty, exact normalized match, case mismatch, duplicate and absent names in a fixed four-entry order. Native returned indices are compared with real host pinned Filename and canonical StringUtils.",
    6: "Empty and populated manager categories, negative and valid indices and repeated out-of-range indices. Native static guards and D1 registration are observed at boundaries and host fallback identity, name and count are checked.",
    7: "Empty, slash-free, matching, missing and case-mismatched icon paths over two categories. The original by-value ARM parameter is split across registers and stack and exact category alias results are checked against host pinned FileName ascend behavior.",
    8: "Null, empty, matching, missing and differently cased icon references and the 255-byte output boundary. Compare original caller-owned output with real host pinned Core filename and canonical StringUtils, using a real unused SLChannelBase fixture.",
}
UNCERTAINTIES = {
    1: "Complete C++ class definition and original ARM destructor ABI remain unresolved; native test covers only D1.",
    2: "The original unencoded ordinary return declaration, allocation failure, and ARM object layout remain unresolved.",
    3: "Original complete class definition and ARM C1 ABI remain unresolved; this receipt does not cover C2.",
    4: "Original return declaration is unresolved. The original r0 points into its local scratch; this port returns an owning buffer with a different return ABI.",
    5: "Original unencoded return declaration and complete native object layout are unresolved; portable uses a signed int index.",
    6: "Original unencoded pointee/return qualifiers and complete manager layout remain unresolved; portable uses a borrowed const pointer.",
    7: "Original unencoded pointee/return qualifiers and complete manager layout remain unresolved; portable uses a borrowed const pointer.",
    8: "Original ordinary return declaration and full native class/layout remain unresolved; this port exposes the observed output reference.",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_files(cwd):
    for folder, entries in native.DEFAULT_TREE.items():
        path = cwd / folder
        path.mkdir(parents=True, exist_ok=True)
        for name, directory in entries:
            child = path / name
            if directory:
                child.mkdir(exist_ok=True)
            else:
                child.touch()
    paths = {
        "v/existing": "existing.PNG",
        "v/ordered/0": "Snare Drum.PNG",
        "v/ordered/1": "SnareDrum.PNG",
        "v/ordered/2": "Kick.wav",
        "v/ordered/3": "one.two.PNG",
        "v/MANAGER/DRUMS": None,
        "v/MANAGER/keys": None,
    }
    for folder, name in paths.items():
        path = cwd / folder
        path.mkdir(parents=True)
        if name is not None:
            (path / name).touch()


def run(exe, cwd, *arguments):
    return subprocess.check_output([exe, *map(str, arguments)], cwd=cwd,
                                   text=True).splitlines()


def provider_tree(exe, cwd):
    result = {}
    for folder in native.DEFAULT_TREE:
        entries = []
        for line in run(exe, cwd, "list", folder):
            kind, name = line.split(" ", 1)
            entries.append((name, bool(int(kind))))
        assert set(entries) == set(native.DEFAULT_TREE[folder]), (folder, entries)
        result[folder] = entries
    return result


def compare(exe, cwd, number, fixture):
    observations = []
    for row in fixture["cases"]:
        if number in (2, 3):
            args = [row["path"], int(row["recurse"])]
            expected = [row["category"], *row["names"]]
        elif number == 1:
            args = [len(row["input"]), 0]
            assert row["trace"] == [["destroy_vector", 0x100, len(row["input"])]]
            assert row["post_count"] == 0
            expected = [f"before {len(row['input'])}", "array deletions 1"]
        else:
            probe = "<null>" if row["input"] is None else row["input"]
            args = [probe, int(bool(row.get("available")))]
            if number in (6, 7):
                result = row["result"] or "null"
            else:
                result = row["result"]
            expected = [str(result)]
        actual = run(exe, cwd, number, *args)
        assert actual == expected, (number, args, actual, expected)
        observations.append(dict(argv=args, actual=actual))
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("exe", "object", "fixtures", "integration", "out"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--task", type=int, required=True)
    args = parser.parse_args()
    number = args.task
    fixture = json.loads(Path(args.fixtures).read_text())
    assert native.generate(number) == fixture
    target = fixture["target"]
    symbols = subprocess.check_output(["nm", "--defined-only", args.object], text=True).splitlines()
    assert any(line.split()[-1:] == [target["mangled"]] for line in symbols)
    exe = str(Path(args.exe).resolve())
    with tempfile.TemporaryDirectory(prefix="icon-replay-", dir=SCRATCH) as directory:
        cwd = Path(directory)
        make_files(cwd)
        actual_tree = provider_tree(exe, cwd) if number in (2, 3) else None
        # Reexecute native instructions when the provider's actual enumeration
        # order differs from the fixed synthetic boundary fixture.
        native_case = native.generate(number, actual_tree) if actual_tree is not None else fixture
        observations = compare(exe, cwd, number, native_case)
    integration = Path(args.integration)
    proof = {
        "passed": True, "task_id": f"cycle21_g05_s{number:02}", "native": native_case,
        "case_count": len(observations), "observations": observations,
        "provider_order": actual_tree, "fixture_sha256": sha(args.fixtures),
        "object_sha256": sha(args.object), "executable_sha256": sha(args.exe),
        "integration_sha256": sha(integration) if integration.is_file() else None,
        "proposed_readiness": {"ready": [], "pending": [{
            **target, "cpp_compiled": True, "mangling_namespace_checked": True,
            "portable_ready": False, "domain": DOMAINS[number],
            "declaration_uncertainties": [UNCERTAINTIES[number]],
            "sources": {item: sha(Path("uc-library") / item) for item in SOURCES},
            "repository_sources": {item: sha(item) for item in CORE},
        }]},
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"PASSED {len(observations)} cases: {DOMAINS[number]}")


if __name__ == "__main__":
    main()
