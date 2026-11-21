"""Verify exact original branches and replay current CCL-bound production code."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import generate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TASK = HERE.name[-2:]
SOURCES = [
    "include/presonus/mixer/AutoFilterGroupManager.hpp",
    "src/Presonus/Mixer/AutoFilterGroupManager.cpp",
    "include/presonus/mixer/ChannelComponent.hpp",
    "include/presonus/uc/ServerComponent.hpp",
]
CORE = [
    "portable/corecomponent.h", "portable/corecomponent.cpp",
    "portable/coreparams.h", "portable/coreparams.cpp",
    "portable/coretypeinfo.h", "public/corevector.h",
    "public/corestringbuffer.h", "system/coredebug.h", "system/coredebug.cpp",
]
DOMAINS = {
    "02": "Nine bounded original cases with the nine exact RM13731 category entries, explicit channel ordinal 2, real Controller-independent channel and filter-group CCL parameters, matched and unmatched trusted ASCII icon strings, wrong source/destination subtype, group-reset and retained-peer branches. Compare original ordered set/reset/string edits, final flags, labels and pinned Core logging. Native libc uses actual Linux routines against exact ARM boundary buffers; native compiler comparison runs original emitted ARM instructions.",
    "03": "Seven native queues including empty, null-head, live singleton, multiple ordered entries and duplicates. Observe original Core base call before queue inspection and at most one original FIFO removal before exact updateAutoGroup tail call. Portable replay invokes actual pinned Core::Portable::Component::onIdle with a real CCL child and runs the co-owned grouping method using real CCL parameters, confirming the remaining queue, channel identity and updated queue size.",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(exe, cases):
    for case in cases:
        if TASK == "02":
            arguments = [case["icon"], case["current"], int(case["other"]),
                         int(case["is_string"]), int(case["label_string"])]
            observed = subprocess.check_output(
                [str(exe), *map(str, arguments)], text=True).splitlines()
            events = [e for e in case["events"] if e[0] in ("set", "reset", "label")]
            expected = [" ".join(map(str, event)) for event in events]
            assert [x for x in observed if x.startswith(("set ", "reset ", "label "))] == expected, (case, observed)
            final = [f"group {i} {m} {o} {label}" for i, (m, o, label) in enumerate(
                zip(case["member"], case["other_members"], case["labels"]))]
            assert [x for x in observed if x.startswith("group ")] == final, (case, observed)
            formats = [event for event in case["events"] if event[0] == "format"]
            logs = "".join(fmt % ((argument, ordinal) if "%d" in fmt else argument)
                           for _, fmt, argument, ordinal in formats).splitlines()
            assert [x for x in observed if x.startswith(("resetting ", "updating ", "found ", "creating "))] == logs, (case, observed)
        else:
            observed = subprocess.check_output(
                [str(exe), *map(str, case["entries"])], text=True).splitlines()
            events = [" ".join(map(str, event)) for event in case["events"]]
            events.append(" ".join(["remaining", *map(str, case["remaining"])]))
            assert [x for x in observed if x.startswith(("base ", "update ", "remaining"))] == events, (case, observed)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--object", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    p.add_argument("--exe", type=Path)
    p.add_argument("--integration", type=Path, default=Path("-"))
    p.add_argument("--out", type=Path, default=Path("-"))
    a = p.parse_args()
    fixture = json.loads(a.fixture.read_text())
    original = fixture["original"]
    mangled = original["mangled"]
    symbols = subprocess.check_output(["nm", "--defined-only", a.object], text=True)
    assert any(row.split()[-2:] == ["T", mangled] for row in symbols.splitlines() if row)
    if a.exe is None:
        return
    assert generate() == fixture
    replay(a.exe.resolve(), fixture["cases"])
    domain = DOMAINS[TASK]
    core = ["third_party/ccl-framework/core/" + name for name in CORE]
    row = {
        "original_elf_sha256": original["original_elf_sha256"], "mangled": mangled,
        "cpp_compiled": True, "mangling_namespace_checked": True,
        "cpp_differential_passed": True, "portable_ready": False,
        "validation_domain": domain,
        "declaration_uncertainties": ["Original ordinary return declaration and complete class layout remain unverified."],
        "sources": {name: digest(ROOT / "uc-library" / name) for name in SOURCES},
        "repository_sources": {name: digest(ROOT / name) for name in core},
    }
    proof = {
        "success": True, "validation_domain": domain, "cases": len(fixture["cases"]),
        "proposed_readiness": {"ready": [], "pending": [row]},
        "observed_symbol": mangled, "object_sha256": digest(a.object),
        "fixture_sha256": digest(a.fixture), "executable_sha256": digest(a.exe),
        "integration_sha256": None if a.integration == Path("-") else digest(a.integration),
    }
    if a.out != Path("-"):
        a.out.parent.mkdir(exist_ok=True, parents=True)
        a.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof))


if __name__ == "__main__":
    main()
