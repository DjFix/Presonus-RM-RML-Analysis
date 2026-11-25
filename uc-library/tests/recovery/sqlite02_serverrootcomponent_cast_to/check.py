"""Compile the portable component and compare it to both native executions."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
TEST = Path(__file__).resolve().parent
TASK = TEST.name
SOURCE = "uc-library/src/Presonus/UC/ServerRootComponent.cpp"
HEADER = "uc-library/include/presonus/uc/ServerRootComponent.hpp"
BASE_SOURCE = "uc-library/src/Presonus/UC/ServerComponent.cpp"
BASE_HEADER = "uc-library/include/presonus/uc/ServerComponent.hpp"
FORMATTER = "uc-library/.venv/bin/clang-format"
CORE = [
    "portable/corecomponent.h", "portable/corecomponent.cpp",
    "portable/coretypeinfo.h", "system/coretime.h",
    "platform/shared/posix/coretime.posix.h", "platform/shared/coreplatformtime.h",
    "platform/shared/coreplatformtime.cpp",
]
DOMAINS = {
    "cast_to": "Both original ARM roles and the typed portable dispatcher were exercised for each of the three native literal IDs and four unmatched IDs. Compare primary receiver identity or null, with no receiver writes.",
    "get_root": "Both original ARM roles returned the initialized opaque receiver address. Compare the portable borrowed pointer with its live receiver and verify that the native receiver was unchanged.",
    "get_system_time": "Both original ARM roles executed with injected signed nanosecond ticks and real native division. Compare portable results under the same injection and bracket live calls on the real pinned CCL monotonic provider. Also observe pinned CCL floating-point conversion separately.",
}
LIMITS = [
    "The portable subset uses the pinned CCL primary component. No native secondary composition, full native construction or destruction, transport, callbacks, ARM layout, or hardware was verified.",
]
UNCERTAINTY = {
    "cast_to": "The portable virtual signature follows the actual CCL TypedObject provider. The firmware return type and any alternate pointer interpretation remain unencoded.",
    "get_root": "The native return value is the receiver address, which does not establish whether the original declaration used a derived or base pointer or reference.",
    "get_system_time": "The native result has signed 64-bit integer millisecond semantics. The spelling of the original return type and its source typedef remain unencoded.",
}
METHOD = TASK.split("serverrootcomponent_", 1)[1]
CLOCK = METHOD == "get_system_time"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(argv, **kwargs):
    return subprocess.check_output(argv, cwd=ROOT, text=True, **kwargs)


def format_check():
    argv = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run",
            "--Werror", SOURCE, HEADER, str((TEST / "Replay.cpp").relative_to(ROOT))]
    run(argv)
    return argv


def build(args):
    sdk = args.build / "upstream-core/sdk"
    args.object.parent.mkdir(parents=True, exist_ok=True)
    common = ["c++", "-std=gnu++20", "-Ulinux", "-DCORE_USE_OPENSSL=1",
              "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-Iuc-library/include",
              "-isystem", str(sdk / "include/presonus-core-5"),
              "-isystem", str(sdk / "include/presonus-core-codecs"),
              "-ffunction-sections", "-fdata-sections", "-fno-rtti", "-O3",
              "-fno-lto", "-fno-fast-math", "-ffp-contract=off"]
    base_object = str(args.object.with_name("ServerComponent.o"))
    commands = [
        common + ["-c", SOURCE, "-o", str(args.object)],
        common + ["-c", BASE_SOURCE, "-o", base_object],
    ]
    link = common + [str(TEST / "Replay.cpp"), str(args.object), base_object,
                     "-Wl,--gc-sections"]
    if CLOCK:
        link.append("-Wl,--wrap=clock_gettime")
    libraries = [sdk / "lib" / f"lib{name}.a" for name in
                 ("corelib", "presonus_core_allocator", "presonus_png", "presonus_zlib")]
    link += [str(path) for path in libraries] + [
        "-lssl", "-lcrypto", str(args.dns), "-ldl",
        str(args.build / "private-glibc29-provider/libpresonus_private_glibc29.a"),
        "-lm", "-pthread", "-o", str(args.exe),
    ]
    commands.append(link)
    for argv in commands:
        run(argv)
    print(json.dumps({"commands": commands, "compiler": run(["c++", "--version"])}))


def symbol(path, expected):
    rows = run(["nm", "--defined-only", "--format=posix", str(path)]).splitlines()
    matches = [row for row in rows if len(row.split()) >= 2
               and row.split()[0] == expected and row.split()[1] in ("T", "W")]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one definition of {expected} in {path}")
    return matches[0]


def replay(args, executions):
    observations = []
    for execution in executions:
        cases = execution["cases"]
        argv = [str(args.exe)]
        stdout = run(argv, input="".join(f"{c['argument']}\n" for c in cases))
        results = [list(map(int, line.split())) for line in stdout.splitlines()]
        if len(results) != len(cases):
            raise ValueError(f"Portable result count differs for {execution['original']['firmware']}")
        for case, values in zip(cases, results):
            if len(values) != (2 if CLOCK else 1) or values[0] != case["result"]:
                raise ValueError(f"Portable observation {values} differs from {case}")
            observation = dict(firmware=execution["original"]["firmware"],
                               argument=case["argument"], result=values[0])
            if CLOCK:
                observation["ccl_getMilliseconds"] = values[1]
            observations.append(observation)
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--integration", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--build", type=Path)
    parser.add_argument("--dns", type=Path)
    parser.add_argument("--symbols", action="store_true")
    args = parser.parse_args()
    if args.build:
        build(args)
        return
    fixture = json.loads(args.fixture.read_text())
    executions = fixture["executions"]
    expected, = {entry["original"]["mangled"] for entry in executions}
    assert {entry["original"]["role"] for entry in executions} == {"client", "server"}
    matches = {str(path): symbol(path, expected) for path in (args.object, args.exe)}
    if args.symbols:
        print(json.dumps(matches))
        return
    observations = replay(args, executions)
    integration = {}
    if args.integration != "-":
        path = Path(args.integration)
        if json.loads(path.read_text()).get("ctest_passed") is not True:
            raise ValueError("Canonical integration must record passing CTest")
        integration = {"path": str(path), "sha256": sha(path)}
    sources = {str(Path(path).relative_to("uc-library")): sha(path)
               for path in (SOURCE, HEADER, BASE_SOURCE, BASE_HEADER)}
    repository_sources = {f"third_party/ccl-framework/core/{path}":
                          sha(f"third_party/ccl-framework/core/{path}") for path in CORE}
    rows = [dict(original_elf_sha256=e["original"]["elf"], mangled=expected,
                 cpp_compiled=True, mangling_namespace_checked=True,
                 portable_ready=False, domain=DOMAINS[METHOD], sources=sources,
                 repository_sources=repository_sources,
                 declaration_uncertainties=[UNCERTAINTY[METHOD]]) for e in executions]
    proof = dict(
        cpp_differential_passed=True, compiled_mangled_names_matched=True,
        domain=DOMAINS[METHOD], limitations=LIMITS, functions=rows,
        integration=integration, proposed_readiness={"ready": [], "pending": rows},
        native_evidence=fixture, portable_observations=observations,
        portable_case_count=len(observations), symbols=matches,
        formatted_sources={name: sources[name] for name in sources
                           if "ServerRootComponent" in name},
        format_argv=format_check(), formatter=run([FORMATTER, "--version"]).strip(),
        fixture_sha256=sha(args.fixture), oracle_sha256=sha(TEST / "native.py"),
        checker_sha256=sha(__file__), test_sha256=sha(TEST / "Replay.cpp"),
        executable_sha256=sha(args.exe), object_sha256=sha(args.object),
    )
    if CLOCK:
        proof["clock_observation"] = (
            "Pinned CCL time retrieval is used directly. Its getMilliseconds uses floating-point "
            "conversion, whereas the original app uses integer division. Negative synthetic fixtures "
            "supply signed seconds and remainder before CCL combines them. Real monotonic time is "
            "also exercised with no injection."
        )
    if args.out != "-":
        Path(args.out).write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: {len(observations)} portable cases match sealed original ARM observations")


if __name__ == "__main__":
    main()
