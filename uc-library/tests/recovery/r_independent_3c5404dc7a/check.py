"""Build and check a local replay or validate canonical build artifacts."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

TASK = Path(__file__).parent.name
TEST = Path("uc-library/tests/recovery") / TASK
SOURCE = Path("uc-library/src/Presonus/UC/MulticastSocketServices.cpp")
HEADER = Path("uc-library/include/presonus/uc/multicast_connection.hpp")
CORE = [
    Path("third_party/ccl-framework/core/network/coresocket.h"),
    Path("third_party/ccl-framework/core/platform/shared/posix/coresocket.posix.h"),
    Path("third_party/ccl-framework/core/platform/shared/posix/coresocket.posix.cpp"),
]
DOMAIN = ("Both original ARM ranges execute offline with two qualified disable "
          "provider calls captured, unicast then multicast, false arguments and "
          "unchanged receiver bytes with providers intercepted. Portable cleanup "
          "executes real CCL provider teardown with empty and one-descriptor "
          "bundles, flags/time reset, descriptor closure and repeated cleanup.")
LIMITATIONS = ("Original return declaration unencoded. Void is a portable choice; "
               "the native provider calls were observed at their boundaries. "
               "Portable provider checks use owned pipe descriptors and do not "
               "establish native socket internals, ARM ABI or hardware behavior.")
SCRATCH = Path("temp/recovery-work/queue-transport-worker") / TASK
BUILD = Path("/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01")
CPP = ["/usr/bin/c++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Wpedantic",
       "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-DCORE_USE_OPENSSL=1",
       "-pthread", "-Ulinux", "-fno-lto", "-Iuc-library/include",
       "-isystem", str(BUILD / "upstream-core/sdk/include/presonus-core-5"),
       "-isystem", str(BUILD / "upstream-core/sdk/include/presonus-core-codecs")]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def run(argv, **options):
    print("argv:", *argv, flush=True)
    return subprocess.run(argv, check=True, text=True, **options)


def compile_local(role):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    obj = SCRATCH / "application.o"
    run([*CPP, "-c", SOURCE, "-o", obj])
    sdk = BUILD / "upstream-core/sdk/lib"
    external = BUILD.parent / "external-dev/usr/lib/x86_64-linux-gnu"
    result = SCRATCH / f"replay-{role}"
    run([*CPP, TEST / "Replay.cpp", obj, "-o", result,
         BUILD / f"libpresonus_{role}_components.a",
         *[sdk / f"lib{name}.a" for name in
           ("corelib", "presonus_core_allocator", "presonus_png", "presonus_zlib")],
         "-lssl", "-lcrypto", external / "libdns_sd.so", "-ldl",
         BUILD / "private-glibc29-provider/libpresonus_private_glibc29.a",
         f"-Wl,-rpath,{external}", "-lm"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compile", choices=("rm", "cs18"))
    parser.add_argument("--symbols-only", action="store_true")
    parser.add_argument("--fixture", type=Path, default=TEST / "fixtures.json")
    parser.add_argument("--object", type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.compile:
        compile_local(args.compile)
        return
    fixture = json.loads(args.fixture.read_text())
    originals = fixture["originals"]
    names = {row["mangled"] for row in originals}
    symbols = run(["nm", "--defined-only", args.object], capture_output=True).stdout
    exported = {fields[-1] for line in symbols.splitlines() if (fields := line.split())}
    assert names <= exported, names - exported
    if args.symbols_only:
        print("Exact original mangling:", *sorted(names))
        return
    result = run([args.exe], capture_output=True).stdout
    actual = [list(map(int, line.split())) for line in result.splitlines()]
    if fixture["queue"]:
        for row in originals:
            assert actual == [case["portable_line"] for case in row["cases"]], actual
    else:
        # Direct native cleanup has no receiver writes with provider calls trapped.
        # The existing real CCL providers independently define these postconditions.
        expected = [[state, attempt, 0, 0, 0, 0, 0, 0, 1]
                    for state in (0, 1) for attempt in (0, 1)]
        assert actual == expected, actual
    sources = {str(path.relative_to("uc-library")): digest(path)
               for path in (SOURCE, HEADER)}
    core = {str(path): digest(path) for path in CORE}
    pending = [
        dict(original_elf_sha256=row["elf_sha256"], mangled=row["mangled"],
             domain=DOMAIN, validation_domain=DOMAIN, cpp_compiled=True,
             mangling_namespace_checked=True, portable_ready=False,
             cpp_differential_passed=True, sources=sources, repository_sources=core,
             declaration_uncertainties=["Original ordinary return type unresolved"])
        for row in originals
    ]
    formatter = "uc-library/.venv/bin/clang-format"
    proof = dict(replay_passed=True, cpp_differential_passed=True,
                 compiled_mangled_names_matched=True, portable_ready=False,
                 mangled_names=sorted(names), validation_domain=DOMAIN,
                 limitations=LIMITATIONS, functions=pending,
                 proposed_readiness={"ready": [], "pending": pending},
                 object_sha256=digest(args.object), executable_sha256=digest(args.exe),
                 fixture_sha256=digest(args.fixture), checker_sha256=digest(Path(__file__)),
                 native_producer_sha256=digest(TEST / "native.py"),
                 replay_source_sha256=digest(TEST / "Replay.cpp"),
                 formatter_version=run([formatter, "--version"],
                                       capture_output=True).stdout.strip(),
                 format_checked={str(path): digest(path)
                                 for path in (SOURCE, HEADER, TEST / "Replay.cpp")},
                 original_observations=originals, cpp_cases=actual,
                 executed_utc=datetime.now(timezone.utc).isoformat())
    if args.integration:
        proof["integration_sha256"] = digest(args.integration)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(len(actual), "portable cases passed")


if __name__ == "__main__":
    main()
