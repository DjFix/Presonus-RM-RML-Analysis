"""Verify compiled base hook identity and replay typed portable observations."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCES = (
    "include/presonus/panel/PanelComponent.hpp",
    "src/Presonus/Panel/PanelComponent.cpp",
)
CORE_SOURCES = tuple("third_party/ccl-framework/core/" + name for name in (
    "portable/corecomponent.cpp",
    "portable/corecomponent.h",
    "portable/coreparams.cpp",
    "portable/coreparams.h",
))
ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
MANGLED = "_ZN8Presonus5Panel14PanelComponent10doActivateEv"
ROUTES = ("direct", "vtable", "start", "activateAll")
LIMITATIONS = [
    "The original return declaration and exact virtual layout remain unresolved.",
    "The portable route retains the existing borrowed activation service.",
    "Native observations use synthetic receiver memory and an offline ARM emulator.",
    "Derived firmware handlers, hardware and ARM interoperability are outside the replay.",
]
DOMAIN = (
    "Original ARM PanelComponent doActivate on three receiver seeds via direct call, "
    "vtable, start and activateAll. Portable base hook has no service events and "
    "preserves seeded timer, active, handler, mixer/registrar references and actual "
    "pinned CCL component feedback state. Portable start and activateAll independently "
    "retain one borrowed activation service call per invocation."
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(executable, fixture):
    assert fixture["elf"]["sha256"] == ELF_SHA
    assert fixture["target"]["mangled"] == MANGLED
    cases = fixture["cases"]
    assert {(item["route"], item["seed"]) for item in cases} == {
        (route, seed) for route in ROUTES for seed in (0, 79, 246)
    }
    assert len(cases) == len(ROUTES) * 3
    observations = []
    for case in cases:
        assert case["external_calls"] == 0 and not case["outside_stack_writes"]
        cmd = [str(executable.resolve()), case["route"], str(case["seed"])]
        result = subprocess.check_output(cmd, text=True).strip()
        state_unchanged, service_calls = (int(value) for value in result.split())
        assert state_unchanged == case["receiver_unchanged"]
        # Separately check the preserved portable adapter route.
        assert service_calls == int(case["route"] in ("start", "activateAll"))
        observations.append({
            "route": case["route"], "seed": case["seed"],
            "state_unchanged": bool(state_unchanged),
            "borrowed_activation_service_calls": service_calls,
        })
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", required=True, type=Path)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    symbols = subprocess.check_output(["nm", "--defined-only", str(args.object)], text=True)
    assert any(row.split()[-2:] == ["T", MANGLED] for row in symbols.splitlines())
    if args.exe is None:
        return

    fixture = json.loads(args.fixture.read_text())
    observations = replay(args.exe, fixture)
    receipt = {
        "success": True, "domain": DOMAIN, "validation_domain": DOMAIN,
        "cases": len(observations),
        "native_identity": fixture["target"],
        "portable_observations": observations,
        "fixture_sha256": sha(args.fixture),
        "object_sha256": sha(args.object),
        "executable_sha256": sha(args.exe),
        "replay_sha256": sha(Path(__file__)),
        "observed_symbol": MANGLED,
        "integration_sha256": (
            sha(args.integration)
            if args.integration and args.integration != Path("-") else None
        ),
        "proposed_readiness": {"ready": [], "pending": [{
            "original_elf_sha256": ELF_SHA,
            "mangled": MANGLED,
            "cpp_compiled": True,
            "mangling_namespace_checked": True,
            "cpp_differential_passed": True,
            "portable_ready": False,
            "declaration_uncertainties": LIMITATIONS[:1],
            "validation_domain": DOMAIN,
            "sources": {name: sha(ROOT / "uc-library" / name) for name in SOURCES},
            "repository_sources": {name: sha(ROOT / name) for name in CORE_SOURCES},
        }]},
    }
    if args.out and args.out != Path("-"):
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
