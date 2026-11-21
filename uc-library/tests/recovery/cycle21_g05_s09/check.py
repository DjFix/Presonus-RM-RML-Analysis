"""Verify loadIcons against fresh native execution and actual pinned Linux CCL."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import native

SOURCES = ("src/IconManager.cpp", "include/presonus/IconManager.hpp")
CORE = tuple("third_party/ccl-framework/core/" + name for name in (
    "portable/corefile.h", "portable/corefilename.h", "portable/corefilename.cpp",
    "public/corevector.h", "public/corestringbuffer.h",
    "platform/shared/coreplatformfilesystem.h",
    "platform/shared/posix/corefilesystem.posix.h",
    "platform/shared/posix/corefilesystem.posix.cpp",
    "platform/shared/posix/coredebug.posix.h", "system/coredebug.h",
    "system/coredebug.cpp"))
DOMAIN = (
    "Offline missing, empty, hidden-only, orphan-only, mixed nested and repeated "
    "growth directory cases. Observe provider enumeration order, aggregate and "
    "direct category names and content, orphan diagnostics, append order, "
    "literal percent-name diagnostics and actual portable allocation and deallocation. Also observe "
    "the original false-growth branch separately from thrown host allocation failure."
)
LIMITS = [
    "Original ordinary return declaration, manager construction and full object layout remain unresolved.",
    "The port owns retained categories and frees temporary categories on empty aggregate or failed append. "
    "In the bounded native empty aggregate and injected false-growth branches the allocated object is neither attached nor freed before return.",
    "Actual Linux Vector allocation throws, so the portable bad_alloc case verifies cleanup during unwinding. "
    "The native false-growth fixture is a controlled provider-boundary result and follows different continuation behavior.",
    "ARM ABI, original Core binary behavior, firmware runtime, hardware and concurrency are outside the validated domain.",
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(exe, directory, *arguments):
    return subprocess.check_output([exe, *map(str, arguments)], cwd=directory,
                                   text=True).splitlines()


def fixture_tree(tree, directory, exe):
    for relative, entries in tree.items():
        path = directory / relative
        path.mkdir(parents=True, exist_ok=True)
        for name, child_is_directory in entries:
            if child_is_directory:
                (path / name).mkdir(exist_ok=True)
            else:
                (path / name).touch()
    result = {}
    for folder, expected in tree.items():
        observed = []
        for line in run(exe, directory, "list", folder):
            kind, name = line.split(" ", 1)
            observed.append((name, bool(int(kind))))
        assert set(observed) == set(expected), (folder, expected, observed)
        result[folder] = observed
    return result


def expected_rows(case):
    allocated = sum(event[0] == "allocate" for event in case["trace"])
    orphans = [event[1] for event in case["trace"] if event[0] == "orphan"]
    assert not orphans or case["repeat"] == 1
    lines = []
    for index, state in enumerate(case["states"]):
        lines.append(f"begin {index}")
        lines.extend(f"Track icon with no category!?{name}" for name in orphans)
        for category in state["categories"]:
            lines.append(f"category {category['name']}")
            lines.extend(f"icon {icon}" for icon in category["icons"])
        lines.append(f"live {len(state['categories'])}")
    return lines + [f"allocated {allocated}", f"deleted {allocated}"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("exe", "object", "fixtures", "integration", "out"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    fixture = json.loads(Path(args.fixtures).read_text())
    assert native.generate() == fixture
    target = fixture["original"]["target"]
    symbols = subprocess.check_output(["nm", "--defined-only", args.object], text=True)
    assert any(line.split()[-1:] == [target["mangled"]] for line in symbols.splitlines())

    exe = str(Path(args.exe).resolve())
    with tempfile.TemporaryDirectory(prefix="icons-load-", dir="temp/recovery-work") as scratch:
        root = Path(scratch).resolve()
        provider_order = {name: fixture_tree(tree, root, exe)
                          for name, (_, _, tree) in native.CONFIGS.items()}
        oracle = native.generate(provider_order)
        observed = []
        for case in oracle["cases"]:
            actual = run(exe, root, "run", case["path"], case["repeat"])
            wanted = expected_rows(case)
            assert actual == wanted, (case["name"], actual, wanted)
            observed.append(dict(name=case["name"], output=actual))
        failure = run(exe, root, "failure", "orphans", 1)
        assert failure == ["begin 0", "allocation failure", "live 0",
                           "allocated 1", "deleted 1"], failure
        observed.append(dict(name="throwing-allocation-cleanup", output=failure))

    integration = Path(args.integration)
    proof = {
        "passed": True, "task_id": "cycle21_g05_s09", "native": oracle,
        "provider_order": provider_order, "observations": observed,
        "case_count": len(observed),
        "fixture_sha256": sha(args.fixtures), "object_sha256": sha(args.object),
        "executable_sha256": sha(args.exe),
        "integration_sha256": sha(integration) if integration.is_file() else None,
        "proposed_readiness": {"ready": [], "pending": [{
            **target, "cpp_compiled": True, "mangling_namespace_checked": True,
            "portable_ready": False, "domain": DOMAIN,
            "declaration_uncertainties": [LIMITS[0]],
            "sources": {name: sha(Path("uc-library") / name) for name in SOURCES},
            "repository_sources": {name: sha(name) for name in CORE},
        }]},
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"PASSED {len(observed)} cases: {DOMAIN}")


if __name__ == "__main__":
    main()
