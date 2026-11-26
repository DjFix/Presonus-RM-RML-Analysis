"""Format, build and replay the GEQ store with pinned Linux providers."""
import argparse
import json
import os
import pathlib
import subprocess
import tempfile
import time

from native import ROOT, PACKET, generate, sha

TASK = "sqlite03_geq_preset_store"
TEST = pathlib.Path("uc-library/tests/recovery") / TASK
CANDIDATE = pathlib.Path("uc-library/candidates") / TASK
HEADER = pathlib.Path("uc-library/include/presonus/panel/GeqPresetComponent.hpp")
SOURCE = pathlib.Path("uc-library/src/Presonus/Panel/GeqPresetComponent.cpp")
WORK = ROOT / "temp/recovery-work" / TASK
CANON = pathlib.Path(__file__).resolve()
CANON = next(p for p in CANON.parents if p.name == "ai-line-analysis") / "temp/core-upstream/root-integration-01"
ARCHIVES = [
    CANON / "libpresonus_uc.a",
    CANON / "upstream-core/sdk/lib/libcorelib.a",
    CANON / "upstream-core/sdk/lib/libpresonus_core_allocator.a",
    CANON / "upstream-core/sdk/lib/libpresonus_png.a",
    CANON / "upstream-core/sdk/lib/libpresonus_zlib.a",
    CANON / "private-glibc29-provider/libpresonus_private_glibc29.a",
]
FORMATTED = [HEADER, SOURCE, TEST / "Replay.cpp"]
FORMATTER = "uc-library/.venv/bin/clang-format"
DOMAIN = (
    "Absent or finite signed-int-representable selector, initialized CCL roster, "
    "invalid and null entries, distinct equalizer identities, ignored save return, "
    "tag-2 name and empty category. Genuine CCL output, asynchronous file and "
    "archive providers, local preset cache and delegate notifications in isolated directories."
)
LIMITATIONS = [
    "Original declared return spelling, ARM object layout and binary interoperability remain unresolved.",
    "Native oracle intercepts typed CCL and app boundaries, including the selected equalizer's save. "
    "Portable replay uses a synthetic instrumented equalizer as the application input with genuine "
    "CCL storage, file, and archive providers and current reconstructed PresetComponent.",
    "Bounds failures assume the original zero-initialized ConstVector error entry stays null. "
    "No hardware, concurrent saves, storage failure, or nonfinite or oversized conversion was tested.",
]


def run(argv, checks):
    argv = list(map(str, argv))
    began = time.monotonic()
    child = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True,
                           env={**os.environ, "TMPDIR": str(WORK)})
    checks.append(dict(argv=argv, stdout=child.stdout, stderr=child.stderr,
                       returncode=child.returncode, seconds=time.monotonic() - began))
    if child.returncode:
        raise RuntimeError(f"{argv}: {child.returncode}\n{child.stdout}\n{child.stderr}")
    return child.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["all", "format", "compile", "symbols", "replay"])
    parser.add_argument("--exe", type=pathlib.Path)
    parser.add_argument("--fixture", type=pathlib.Path, default=ROOT / TEST / "fixtures.json")
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    checks = []
    obj, exe = WORK / "geq.o", args.exe or WORK / "replay"
    flags = ["c++", "-std=c++17", "-O2", "-g0", "-DNDEBUG", "-Ulinux",
             "-Wno-multichar", "-fno-rtti", "-fno-lto", "-pthread", "-DCORE_USE_OPENSSL=1",
             "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-Iuc-library/include",
             "-Ithird_party/ccl-framework"]
    if args.mode in ("all", "format"):
        run([FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run",
             "--Werror", *FORMATTED], checks)
    if args.mode in ("all", "compile"):
        run([*flags, "-c", SOURCE, "-o", obj], checks)
        run([*flags, TEST / "Replay.cpp", obj, "-Wl,--start-group", *ARCHIVES,
             "-Wl,--end-group", "-lssl", "-lcrypto", "-ldl", "-lm", "-o", exe], checks)
    fixture = json.loads(args.fixture.read_text())
    if args.mode in ("all", "symbols"):
        symbols = run(["nm", "--defined-only", obj], checks).splitlines()
        assert any(row.split()[-1] == fixture["original"]["mangled"] for row in symbols)
    if args.mode not in ("all", "replay"):
        return
    assert fixture == generate(), "The fresh native traces differ"
    for case in fixture["cases"]:
        test = case["input"]
        roster = "".join("x" if slot is None else str(slot) for slot in test["roster"])
        selector = "~" if test["selection"] is None else str(test["selection"])
        trace = case["trace"]
        expected = ["|".join(map(str, row)) for row in trace if row[0] == "save"]
        expected.append(f'result|{case["result"]}')
        for row in trace:
            if row[0] == "persist":
                parts = list(row)
                if not parts[1]:
                    # The real cache exposes its empty-slot marker for an empty name.
                    parts[1] = "* Empty Location *"
                expected.append("|".join(map(str, parts)))
        with tempfile.TemporaryDirectory(dir=WORK) as folder:
            observed = run([exe, selector, roster, int(test["save_result"]),
                            test["name"], folder], checks).splitlines()
        assert observed == expected, (case, observed, expected)
    print(f'{len(fixture["cases"])} original and portable GEQ store cases matched')
    if args.mode == "all":
        packet = json.loads((ROOT / PACKET).read_text())
        inputs = [
            *FORMATTED, TEST / "native.py", TEST / "check.py",
            args.fixture, ROOT / PACKET, *map(pathlib.Path, packet["read_files"])
        ]
        bound = {str((ROOT / p).relative_to(ROOT)): sha((ROOT / p).read_bytes()) for p in inputs}
        original = fixture["original"]
        proof = dict(
            version=1, task_id=TASK, original=original, source_hashes=bound,
            fixture_sha256=sha(args.fixture.read_bytes()), case_count=len(fixture["cases"]),
            validation_domain=DOMAIN, limitations=LIMITATIONS,
            formatter=run([FORMATTER, "--version"], checks).strip(),
            compiler=run(["c++", "--version"], checks).splitlines()[0],
            unicorn=__import__("unicorn").__version__,
            archives={str(p): sha(p.read_bytes()) for p in ARCHIVES},
            object_sha256=sha(obj.read_bytes()), executable_sha256=sha(exe.read_bytes()),
            checks=checks, original_execution="Unicorn ARM with typed intercepted boundaries",
            portable_execution="Linux C++ with real cache and filesystem archive providers",
            proposed_classification="compiled declaration-pending",
        )
        (ROOT / CANDIDATE / "worker-proof.json").write_text(json.dumps(proof, indent=2) + "\n")


if __name__ == "__main__":
    main()
