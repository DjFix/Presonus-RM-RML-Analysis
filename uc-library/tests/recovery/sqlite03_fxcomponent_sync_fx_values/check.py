"""Build and compare offline FX synchronization with native ARM observations."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from native import NAME, generate

HERE = Path(__file__).parent
WORK = Path("temp/recovery-work/sqlite03_fxcomponent_sync_fx_values")
OVERLAY = Path("temp/recovery-work/fx-sync-verified-peer-reverb01")
SOURCE = Path("uc-library/src/Presonus")
HEADER = Path("uc-library/include/presonus/mixer/FXComponent.hpp")
FX = SOURCE / "Mixer/FXComponent.cpp"
PROVIDER = Path("uc-library/src/Presonus/Dsp/SLReverbController.cpp")
REVERB_SET = "_ZN8Presonus3Dsp18SLReverbController8setValueEif"
PROVIDER_HEADER = Path("uc-library/include/presonus/dsp/SLReverbController.hpp")
PROVIDER_HEADER_SHA = "9221b08af9f00db28b6a54cf7a6765a59e2244e409bc0a294bd7fd3e77bd4b62"
DOMAIN = (
    "25 original RM ARM cases comparing type conversion, CCL order, signed tag and mapped-ID "
    "filtering, virtual value mapping, 64 ordered SLReverb calls and native controller input state "
    "stores. Reverb provider uses bounded preset-9 state; native calcParams is intercepted after "
    "entry and downstream calculated DSP output is outside this proof."
)
PROVIDER_SHA = "58c4ef71fff9f6697411a937a4e691a36fcd4419b2e609190e9432f93896dc8f"


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(argv, **kwargs):
    argv = list(map(str, argv))
    print(json.dumps(argv), flush=True)
    return subprocess.run(argv, check=True, text=True, **kwargs)


def verify_link_inputs():
    projection = json.loads((OVERLAY / "PEER_PROVIDER_RECEIPT.json").read_text())
    for entry in projection["files"]:
        assert digest(entry["consumer_overlay"]) == entry["sha256"]
    assert digest(OVERLAY / PROVIDER) == PROVIDER_SHA
    assert digest(OVERLAY / PROVIDER_HEADER) == PROVIDER_HEADER_SHA
    records = json.loads((OVERLAY / "role-archives/ARCHIVE_PROJECTION.json").read_text())["files"]
    archives = [Path(record["path"]) for record in records]
    for path, record in zip(archives, records):
        assert digest(path) == record["sha256"]

    return archives


def compile_replay(executable, production):
    archives = verify_link_inputs()
    flags = ["c++", "-std=c++20", "-O2", "-fno-rtti", "-Wno-multichar",
             "-ffunction-sections", "-fdata-sections", "-I" + str(OVERLAY / "uc-library/include"),
             "-Iuc-library/include", "-Ithird_party/ccl-framework"]
    sources = [
        (FX, production),
        (SOURCE / "DspComponent.cpp", WORK / "DspComponent.o"),
        (SOURCE / "Mixer/ReverbComponent.cpp", WORK / "ReverbComponent.o"),
        (OVERLAY / PROVIDER, WORK / "SLReverbController.o"),
        (HERE / "Replay.cpp", WORK / "Replay.o"),
    ]
    for source, obj in sources:
        run([*flags, "-MMD", "-MF", obj.with_suffix(".d"), "-c", source, "-o", obj])
    run(["c++", *(obj for _, obj in sources), "-Wl,--gc-sections", *archives,
         "-pthread", "-ldl", "-o", executable])
    verify_link_inputs()


def symbols(production, executable):
    for path, name in ((production, NAME), (executable, REVERB_SET)):
        output = run(["nm", "--defined-only", path], capture_output=True).stdout
        matches = [line for line in output.splitlines() if line.split()[-1:] == [name]]
        assert len(matches) == 1 and matches[0].split()[-2] == "T", (path, name)
        print(matches[0])


def native(fixture):
    assert generate() == fixture
    print(f'{len(fixture["cases"])} fresh native ARM cases matched')


def replay(executable, fixture):
    payload, expected = [], []
    for case in fixture["cases"]:
        payload.append(f'{case["mode"]} {case["type_bits"]} {len(case["entries"])}')
        payload.extend(" ".join(map(str, row)) for row in case["entries"])
        expected.extend(" ".join(map(str, event)) for event in case["trace"]
                        if event[0] not in ("valid", "calc"))
    output = run([executable.resolve()], input="\n".join(payload) + "\n",
                 capture_output=True).stdout.splitlines()
    if output != expected:
        from itertools import zip_longest

        for actual, wanted in zip_longest(output, expected):
            if actual != wanted:
                raise AssertionError(f"expected {wanted!r}, observed {actual!r}")
    print(f'{len(fixture["cases"])} ARM/native-to-Linux traces matched, '
          f'{sum(line.startswith("set ") for line in expected)} offline Reverb calls')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["format", "compile", "symbols", "native", "replay", "canonical"])
    parser.add_argument("--exe", type=Path, default=WORK / "Replay")
    parser.add_argument("--object", type=Path, default=WORK / "FXComponent.o")
    parser.add_argument("--fixture", type=Path, default=HERE / "fixtures.json")
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(WORK.resolve())
    if args.action == "format":
        run(["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
             "--dry-run", "--Werror", HEADER, FX, HERE / "Replay.cpp"])
    elif args.action == "compile":
        compile_replay(args.exe, args.object)
    elif args.action == "symbols":
        symbols(args.object, args.exe)
    else:
        fixture = json.loads(args.fixture.read_text())
        if args.action in ("native", "canonical"):
            native(fixture)
        if args.action == "replay":
            verify_link_inputs()
        if args.action in ("replay", "canonical"):
            replay(args.exe, fixture)
        if args.action == "replay":
            verify_link_inputs()
        if args.action == "canonical":
            if args.integration is None or args.out is None:
                parser.error("canonical mode requires --integration and --out")
            assert digest(PROVIDER) == PROVIDER_SHA
            assert digest(PROVIDER_HEADER) == PROVIDER_HEADER_SHA
            symbols(args.object, args.exe)
            receipt = {
                "behavior_validated": True,
                "portable_behavior_verified": True,
                "domain": DOMAIN,
                "cases": len(fixture["cases"]),
                "elf_sha256": fixture["elf_sha256"],
                "range": fixture["ranges"]["sync"],
                "fixtures_sha256": digest(args.fixture),
                "object_sha256": digest(args.object),
                "executable_sha256": digest(args.exe),
                "provider_source_sha256": digest(PROVIDER),
                "provider_header_sha256": digest(PROVIDER_HEADER),
                "integration_sha256": digest(args.integration),
            }
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
