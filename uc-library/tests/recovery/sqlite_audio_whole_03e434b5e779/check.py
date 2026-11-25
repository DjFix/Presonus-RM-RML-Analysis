"""Build and replay the HP/LP filter component lifecycle evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

BASE = Path("uc-library/tests/recovery") / Path(__file__).parent.name
PACKETS = Path("temp/recovery-work/sqlite-issued/packet")
WORK = Path("temp/recovery-work/filter-validation")
ROOT = Path("/home/rs/projects/opencs/ai-line-analysis")
BUILD = ROOT / "temp/core-upstream/root-integration-01"
SDK = BUILD / "upstream-core/sdk/lib"
FORMATTER = "uc-library/.venv/bin/clang-format"
SOURCES = [
    Path("uc-library/src/Presonus/Mixer/HPFilterComponent.cpp"),
    Path("uc-library/src/Presonus/Mixer/LPFilterComponent.cpp"),
    Path("uc-library/src/mixer_dsp/FilterControllers.cpp"),
]
HEADERS = [
    Path("uc-library/include/presonus/mixer/HPFilterComponent.hpp"),
    Path("uc-library/include/presonus/mixer/LPFilterComponent.hpp"),
    Path("uc-library/include/presonus/mixer_dsp/FilterControllers.hpp"),
]
REPLAY = BASE / "Replay.cpp"
NATIVE = BASE / "native.py"
CHECK = BASE / "check.py"
PROVIDERS = [
    Path("uc-library/include/presonus/dsp/ControllerInfo.hpp"),
    Path("uc-library/include/presonus/mixer_dsp/Dsp.hpp"),
    Path("uc-library/include/presonus/mixer_dsp/EqSourceProviders.hpp"),
    Path("uc-library/src/Presonus/Dsp/ControllerInfo.cpp"),
    Path("uc-library/src/Presonus/Dsp/EqSourceProviders.cpp"),
    Path("uc-library/src/Presonus/Dsp/FilterParameterLists.cpp"),
    Path("third_party/ccl-framework/core/portable/corecomponent.cpp"),
    Path("third_party/ccl-framework/core/portable/corecomponent.h"),
    Path("third_party/ccl-framework/core/portable/coreparaminfo.h"),
    Path("third_party/ccl-framework/core/public/coreformatter.cpp"),
    Path("third_party/ccl-framework/core/public/coreinterpolator.cpp"),
]
DOMAIN = (
    "RM/RML mixer 13731 original ARM function ranges independently replayed "
    "over three distinct signed controller/channel ID pairs, each with a real "
    "nonempty HP or LP descriptor and initial EQ value. Exact native filter, "
    "AudioComponent, DspComponent and controller application instructions drive "
    "the observed initialization, sync/readout exclusion and destructor cleanup. "
    "Portable replay uses CCL Component/ParamList/Parameter and the actual "
    "EQ/filter provider with a live property target, then varies values to verify "
    "registry binding, readout exclusion, resync and exactly-once cleanup."
)
LIMITATIONS = [
    "Portable source layout, vtables and allocator ABI differ from the firmware. "
    "Only the normal lifecycle and bounded provider behavior are validated; "
    "ARM binary interoperability, unwinding and hardware are outside scope.",
    "Native lower LinkableComponent construction and the EQ base constructor "
    "are intercepted, with initialized descriptor/processor memory modeled from "
    "the native list/table evidence and previously accepted provider behavior. "
    "Native CCL adds, value writes and destruction are boundaries; their real "
    "implementations execute only through upstream CCL in the portable replay.",
    "The native property-handler release boundary models the external caller's "
    "handler. Native controller D0 and Controller release execute and reach the "
    "operator-delete boundary. Portable operator delete wraps and calls through "
    "to the real allocator, and CCL itself reports parameter destruction.",
    "No additional original symbols are proposed for admission. Existing "
    "deleting-destructor source APIs are preserved.",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, capture=False):
    args = [str(x) for x in argv]
    print("+", shlex.join(args), file=sys.stderr)
    return subprocess.run(args, check=True, text=True, capture_output=capture).stdout


def format_check():
    run([FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run",
         "--Werror", *HEADERS, *SOURCES, REPLAY])
    version = run([FORMATTER, "--version"], capture=True).strip()
    print(version)
    return version


def obj(source):
    return WORK / (source.name + ".o")


def compile_local():
    WORK.mkdir(parents=True, exist_ok=True)
    flags = [
        "-std=c++20", "-O2", "-pthread", "-Ulinux", "-DNDEBUG=1",
        "-DCORE_USE_OPENSSL=1", "-DPRESONUS_HAS_UPSTREAM_CORE=1",
        "-fno-fast-math", "-ffp-contract=off", "-Wall", "-Wextra", "-Wpedantic",
        "-Iuc-library/include", "-isystem", "third_party/ccl-framework",
    ]
    libraries = [
        BUILD / "libpresonus_rm_components.a", SDK / "libcorelib.a",
        SDK / "libpresonus_core_allocator.a", SDK / "libpresonus_png.a",
        SDK / "libpresonus_zlib.a",
        Path("/usr/lib/x86_64-linux-gnu/libssl.so"),
        Path("/usr/lib/x86_64-linux-gnu/libcrypto.so"),
        BUILD.parent / "external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so",
        BUILD / "private-glibc29-provider-history/20261125T141810793209Z/libpresonus_private_glibc29.a",
    ]
    providers = {str(p): digest(p) for p in libraries}
    commands = []
    for source in [*SOURCES, REPLAY]:
        special = ["-fno-sized-deallocation"] if source in SOURCES[:2] else []
        commands.append(["/usr/bin/c++", *flags, *special, "-c", source, "-o", obj(source)])
    commands.append([
        "/usr/bin/c++", "-pthread", "-Wl,--wrap=_ZdlPv,--wrap=_ZdlPvm",
        *map(obj, [*SOURCES, REPLAY]), *libraries, "-ldl", "-lm", "-o", WORK / "Replay",
    ])
    for argv in commands:
        run(argv)
    assert providers == {str(p): digest(p) for p in libraries}
    receipt = {
        "compiler_version": run(["/usr/bin/c++", "--version"], capture=True).strip(),
        "commands": [[str(x) for x in cmd] for cmd in commands],
        "providers": providers,
        "outputs": {str(p): digest(p) for p in [*map(obj, [*SOURCES, REPLAY]), WORK / "Replay"]},
    }
    (WORK / "compile.json").write_text(json.dumps(receipt, indent=2) + "\n")


def symbol_check(original):
    source = SOURCES[0 if "HPFilterComponent" in original["mangled"] else 1]
    output = run(["nm", "--defined-only", obj(source)], capture=True)
    mangled = original["mangled"]
    lines = [line for line in output.splitlines() if line.split()[-1] == mangled]
    assert len(lines) == 1 and lines[0].split()[-2] == "T", (source, mangled)
    print(lines[0])
    return lines[0]


def replay(args, manifest, original):
    fixture = args.fixture
    if args.native or args.proof:
        run([sys.executable, "-B", NATIVE, args.task, fixture])
    kind = "HP" if "HPFilterComponent" in original["mangled"] else "LP"
    variant = next(v for v in ("C1", "C2", "D1") if f"Component{v}E" in original["mangled"])
    rows = json.loads(fixture.read_text())
    assert len(rows) == 1 and rows[0]["original"] == original
    results = []
    for case in rows[0]["cases"]:
        expected = case["observed"]
        table = expected["table"]
        argv = [
            args.exe, kind, variant, expected["controller_id"],
            expected["channel_id"], table["unit"], table["curve"], table["delta"],
        ]
        actual, cleanup = run(argv, capture=True).strip().splitlines()
        fields = shlex.split(actual)
        numeric = [
            expected[k] for k in ("controller_id", "channel_id", "count", "readouts",
                                  "descriptor_flags", "band_type", "band_enabled", "band_dirty",
                                  "band_active", "provider_pending", "value")
        ]
        numeric.extend(table[k] for k in ("type", "tag", "minimum", "maximum",
                                          "midpoint", "default", "flags"))
        names = [table["name"], table["title"], table["short_title"] or table["title"]]
        assert [str(x) for x in numeric] + names == fields, (expected, actual)
        assert cleanup == "handler-release controller-deallocation ccl-parameter-destruction"
        results.append({"argv": [str(x) for x in argv], "observation": actual, "cleanup": cleanup})
    if args.proof:
        sources = {str(p.relative_to("uc-library")): digest(p) for p in [*SOURCES, *HEADERS]}
        dependencies = set(PROVIDERS)
        dependencies.update(Path(x["path"]) for x in manifest["task"]["review"]["providers"])
        dependencies.difference_update([*SOURCES, *HEADERS])
        repo_sources = {str(p): digest(p) for p in sorted(dependencies)}
        formatter = format_check()
        original_observation = {
            "original_elf_sha256": original["elf"],
            "mangled": original["mangled"],
            "original_address": original["address"],
            "sources": sources,
            "repository_sources": repo_sources,
            "domain": DOMAIN,
            "portable_ready": True,
            "cpp_compiled": True,
            "mangling_namespace_checked": True,
            "behavior_validation_passed": True,
            "success": True,
        }
        import elftools
        import unicorn
        proof = {
            "version": 1, "task_id": args.task, "success": True, "domain": DOMAIN,
            "limitations": LIMITATIONS, "native": rows, "observations": results,
            "native_replayed": True, "cpp_differential_passed": True,
            "cpp_compiled": True, "mangling_namespace_checked": True,
            "format_check_passed": True, "behavior_validation_passed": True,
            "portable_ready": True, "functions": [original_observation],
            "proposed_readiness": {"ready": [original_observation], "pending": []},
            "formatter_version": formatter, "compiled_symbol": symbol_check(original),
            "oracle_versions": {"pyelftools": elftools.__version__, "unicorn": unicorn.__version__},
            "oracle_sha256": digest(NATIVE), "producer_sha256": digest(CHECK),
            "portable_replay_sha256": digest(REPLAY), "binary_sha256": digest(args.exe),
            "fixture": {"path": str(fixture), "sha256": digest(fixture)},
            "actual_argv": sys.argv,
            "local_build_receipt": json.loads((WORK / "compile.json").read_text()),
        }
        args.proof.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{args.task} {len(results)} portable comparisons passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["format", "compile", "symbols", "replay"])
    parser.add_argument("task")
    parser.add_argument("--exe", type=Path, default=WORK / "Replay")
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--proof", type=Path)
    args = parser.parse_args()
    args.fixture = args.fixture or Path("uc-library/tests/recovery") / args.task / "fixtures.json"
    manifest = None
    original = None
    if args.action == "symbols" or args.proof or args.native:
        manifest = json.loads((PACKETS / args.task / "CONTEXT.json").read_text())
        original, = [row["original"] for row in manifest["originals"]]
    elif args.action == "replay":
        row, = json.loads(args.fixture.read_text())
        original = row["original"]
    if args.action == "format":
        format_check()
    elif args.action == "compile":
        compile_local()
    elif args.action == "symbols":
        symbol_check(original)
    else:
        args.exe = args.exe.resolve()
        replay(args, manifest, original)


if __name__ == "__main__":
    main()
