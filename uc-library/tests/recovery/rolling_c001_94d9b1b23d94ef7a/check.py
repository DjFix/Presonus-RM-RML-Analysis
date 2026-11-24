"""Compare scoped Page calls against verified original no-effect observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from canonical_source_transition import current_source_digest, load_transition

HERE = Path(__file__).parent
DOMAIN = (
    "Exact RM/RML 13731 ARM entry with two mapped, a zero and an unmapped "
    "receiver register, varied argument registers, stack and pointed-to sentinels. "
    "Observe frame restoration, instruction and memory traces, and no application "
    "writes or callbacks. Portable calls use constructed Pages with active or "
    "unselected owned recording Elements and compare receiver state, element "
    "state and callback counts."
)
LIMITATIONS = [
    "Portable declaration is a virtual void member; original unencoded return "
    "type and definitive member/virtual declaration traits remain unresolved.",
    "Four original calls at the entry and 14 static table word observations "
    "do not exercise original dispatch, receiver construction or layout.",
    "Original r0 was preserved; no result is asserted for the portable void call. "
    "Original ARM ABI and hardware behavior remain unresolved.",
]
SOURCE_PATHS = (
    "include/presonus/panel/Page.hpp", "src/Presonus/Panel/Page.cpp",
    "include/presonus/panel/Element.hpp", "include/presonus/panel/TextEntryElement.hpp",
)
ELEMENT_SOURCE = "src/Presonus/Panel/Element.cpp"
ELEMENT_HASH = "723669c42b99b51cc15ab450ee910e7da0b7ceae325f305e503295a39da3d432"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--object", required=True)
    parser.add_argument("--exe")
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--integration", default="none")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--symbols-only", action="store_true")
    parser.add_argument("--element-source", default=f"uc-library/{ELEMENT_SOURCE}")
    parser.add_argument("--source-transition", type=Path)
    parser.add_argument("--source-transition-sha256")
    args = parser.parse_args()
    transition = load_transition(args.source_transition, args.source_transition_sha256)
    fixture = json.loads(args.fixtures.read_text())
    symbol = fixture["mangled"]
    symbols = subprocess.check_output(["nm", "--defined-only", args.object], text=True)
    matches = [line for line in symbols.splitlines()
               if line.split()[-2:] == ["T", symbol]]
    assert len(matches) == 1, matches
    if args.symbols_only:
        print(matches[0])
        return

    traces = []
    for case in fixture["cases"]:
        actual = subprocess.check_output([args.exe, str(case["seed"])], text=True)
        observed = list(map(int, actual.split()))
        expected = [int(case["application_memory_unchanged"]), case["callback_count"]]
        assert observed == expected, (case["seed"], observed, expected)
        traces.append({"scenario": case["seed"], "application_memory_unchanged": bool(observed[0]),
                       "callback_count": observed[1]})
    assert len(traces) == 4
    sources = {path: sha(Path("uc-library") / path) for path in SOURCE_PATHS}
    logical_element = f"uc-library/{ELEMENT_SOURCE}"
    assert not transition or args.element_source == logical_element
    expected_element = current_source_digest(logical_element, ELEMENT_HASH, transition)
    assert sha(args.element_source) == expected_element
    if args.element_source == logical_element:
        sources[ELEMENT_SOURCE] = expected_element
    row = {
        "original_elf_sha256": fixture["elf_sha256"], "mangled": symbol,
        "original_address": fixture["address"], "cpp_compiled": True,
        "mangling_namespace_checked": True, "portable_ready": False, "domain": DOMAIN,
        "declaration_uncertainties": LIMITATIONS, "sources": sources,
        "repository_sources": {},
    }
    version = subprocess.check_output(["uc-library/.venv/bin/clang-format", "--version"], text=True)
    proof = {
        "cpp_differential_passed": True, "compiled_mangled_names_matched": True,
        "portable_ready": False, "case_count": len(traces), "domain": DOMAIN,
        "limitations": LIMITATIONS, "functions": [row], "mangled_names": [symbol],
        "verified_symbols": matches, "observations": traces, "originals": [fixture],
        "fixture_sha256": sha(args.fixtures), "checker_sha256": sha(__file__),
        "native_producer_sha256": sha(HERE / "native.py"),
        "replay_source_sha256": sha(HERE / "Replay.cpp"),
        "object_sha256": sha(args.object), "executable_sha256": sha(args.exe),
        "element_provider": {"path": args.element_source, "sha256": expected_element},
        "source_transition": {"path": str(args.source_transition),
                              "sha256": args.source_transition_sha256} if transition else None,
        "integration_sha256": sha(args.integration) if args.integration != "none" else None,
        "format_version": version.strip(),
        "proposed_readiness": {"ready": [], "pending": [row]},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{len(traces)} portable Page calls matched the original no-effect domain")


if __name__ == "__main__":
    main()
