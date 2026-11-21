"""Validate the active object and compare replay with original and provider observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

TASK = "cycle21_g05_s10"
SOURCES = ("src/ColorButton.cpp", "include/presonus/ColorButton.hpp")
CORE = tuple("third_party/ccl-framework/core/" + part for part in (
    "portable/gui/corecontrols.h", "portable/gui/corecontrols.cpp",
    "portable/gui/coreview.h", "portable/gui/coreview.cpp",
    "portable/gui/coreviewshared.h", "portable/coreparams.h"))
DOMAIN = (
    "Sixteen isolated callback deliveries using distinct and aliased primary/color "
    "parameters and BeginEdit, Edit, Changed and RangeChanged messages. Native ARM "
    "observations cover receiver/argument forwarding and ordered Core boundary entry; "
    "pinned Linux CCL observations cover enabled state and client-rectangle invalidations."
)
UNCERTAINTIES = [
    "Original ordinary return declaration and complete ColorButton base hierarchy, "
    "field ownership, constructors and ARM layout remain unresolved."
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capture(exe, *args):
    lines = subprocess.check_output([exe, *args], text=True).splitlines()
    cases = {}
    for line in lines:
        if line.startswith("case "):
            key = tuple(map(int, line.split()[1:]))
            assert key not in cases
            cases[key] = []
        elif cases:
            cases[key].append(line)
    return {key: [line for line in rows[:rows.index(next(
        row for row in rows if row.startswith("enabled ")) ) + 1]]
        for key, rows in cases.items()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("exe", "object", "fixtures", "integration", "out"):
        p.add_argument("--" + name, required=True)
    args = p.parse_args()
    native = json.loads(Path(args.fixtures).read_text())
    target = native["target"]
    symbols = subprocess.check_output(["nm", "--defined-only", args.object], text=True)
    assert any(line.split()[-1:] == [target["mangled"]] for line in symbols.splitlines())
    provider = capture(args.exe, "--provider")
    actual = capture(args.exe)
    observed = []
    for row in native["cases"]:
        key = (int(row["color_is_primary"]), row["message"], int(row["notify_primary"]))
        bound = provider[key]
        index = bound.index("direct")
        assert len(bound) == index + 3 and bound[index + 1].startswith("invalidate ")
        assert row["calls"][0] == "Control::paramChanged" and len(row["calls"]) in (1, 2)
        expected = bound[:index]
        if "View::invalidate" in row["calls"]:
            expected.append(bound[index + 1])
        expected.append(bound[-1])
        assert actual[key] == expected, (key, actual[key], expected)
        observed.append({"input": key, "provider": bound, "actual": actual[key]})
    assert len(observed) == len(provider) == len(actual) == 16
    integration = Path(args.integration)
    proof = {
        "passed": True, "task_id": TASK, "native": native,
        "case_count": len(observed), "observations": observed,
        "fixture_sha256": sha(args.fixtures), "object_sha256": sha(args.object),
        "executable_sha256": sha(args.exe),
        "integration_sha256": sha(integration) if integration.is_file() else None,
        "proposed_readiness": {"ready": [], "pending": [{
            **target, "cpp_compiled": True, "mangling_namespace_checked": True,
            "portable_ready": False, "domain": DOMAIN,
            "declaration_uncertainties": UNCERTAINTIES,
            "sources": {item: sha(Path("uc-library") / item) for item in SOURCES},
            "repository_sources": {item: sha(item) for item in CORE},
        }]},
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"PASSED {len(observed)} cases: {DOMAIN}")


if __name__ == "__main__":
    main()
