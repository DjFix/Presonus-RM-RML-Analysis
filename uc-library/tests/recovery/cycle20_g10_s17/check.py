"""Compare the exact commissioned palette updates through real typed providers."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

UP = True
TASK = "17" if UP else "18"
METHOD = "updateColorIndex" if UP else "updateColorFromIndex"
MANGLED = f"_ZN8Presonus13SLChannelBase{len(METHOD)}{METHOD}Ev"
ROOT = Path(__file__).resolve().parents[4]
SOURCES = (
    "include/presonus/SLChannel.hpp", "src/Presonus/SLChannel.cpp",
    "include/presonus/MappableMixer.hpp", "src/Presonus/MappableMixer.cpp",
    "include/presonus/color/IColorConverter.hpp",
    "include/presonus/color/MixerColorConverter.hpp",
    "src/Presonus/Color/MixerColorConverter.cpp",
    "include/presonus/ColorMapping.hpp", "src/Presonus/ColorMapping.cpp",
    "src/Presonus/Color/ColorMappingName.cpp",
)
CORE = tuple("third_party/ccl-framework/core/" + name for name in (
    "portable/corecomponent.h", "portable/corecomponent.cpp", "portable/coreparams.h",
    "portable/coreparams.cpp", "public/gui/corecolor.h",
))
DOMAIN = (
    f"{METHOD}: eight finite independent palette cases per CS18/RM original. "
    "Exercises missing mixer, index, converter and color bindings, finite fractional "
    "indices, packed RGBA, change/no-change edits, and pinned CCL controller notification. "
    "Native executes exact app body and MappableMixer getter with identified virtual "
    "and Core/runtime boundaries. Host executes current MappableMixer, concrete "
    "MixerColorConverter/ColorMapping and real pinned CCL NumericParam/ColorParam."
)
UNCERTAINTIES = ["Original ordinary return declaration, class state layout and ARM ABI remain unresolved."]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def output(exe, mode, inputs):
    return subprocess.check_output(
        [str(exe.resolve()), mode, *map(str, inputs)], text=True,
    ).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--object", required=True, type=Path)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    symbols = subprocess.check_output(["nm", "--defined-only", str(args.object)], text=True)
    assert any(line.split()[-2:] == ["T", MANGLED] for line in symbols.splitlines())
    if args.exe is None:
        return
    fixture = json.loads(args.fixture.read_text())
    assert fixture["task"] == TASK and {r["role"] for r in fixture["originals"]} == {"client", "server"}
    cases, pending = [], []
    for original in fixture["originals"]:
        elf, target = original["elf_sha256"], original["range"]
        assert target["mangled"] == MANGLED and len(original["cases"]) == 8
        for native in original["cases"]:
            inputs = native["inputs"]
            assert int(output(args.exe, "provider", inputs)) == native["independent_palette_output"]
            fields = output(args.exe, "replay", inputs).split()
            result = [float(fields[0]), *map(int, fields[1:])]
            assert result == native["output"], (inputs, result, native["output"])
            cases.append({"elf_sha256": elf, "inputs": inputs, "output": result})
        pending.append({
            "original_elf_sha256": elf, "mangled": MANGLED, "cpp_compiled": True,
            "mangling_namespace_checked": True, "cpp_differential_passed": True,
            "portable_ready": False, "validation_domain": DOMAIN,
            "declaration_uncertainties": UNCERTAINTIES,
            "sources": {name: sha(ROOT / "uc-library" / name) for name in SOURCES},
            "repository_sources": {name: sha(ROOT / name) for name in CORE},
        })
    result = {
        "success": True, "validation_domain": DOMAIN, "cases": len(cases),
        "portable_observations": cases, "observed_symbol": MANGLED,
        "native_ranges": [{k: v for k, v in entry.items() if k != "cases"} for entry in fixture["originals"]],
        "fixture_sha256": sha(args.fixture), "executable_sha256": sha(args.exe),
        "object_sha256": sha(args.object), "replay_sha256": sha(__file__),
        "integration_sha256": sha(args.integration) if args.integration and args.integration != Path("-") else None,
        "proposed_readiness": {"ready": [], "pending": pending},
    }
    if args.out and args.out != Path("-"):
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
