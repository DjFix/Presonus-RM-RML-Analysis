"""Compile and compare the portable registrar with sealed ARM observations."""
import json
from pathlib import Path
import shlex
import subprocess
import sys


def run(argv, **options):
    print(shlex.join(map(str, argv)), flush=True)
    return subprocess.run(argv, check=True, **options)


def compile_replay(build, scratch):
    build, scratch = Path(build).resolve(), Path(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    sources = [
        Path("uc-library/src/Presonus/Panel/ControlRegistrarAccess.cpp"),
        Path("uc-library/src/surface_panel/ControlGroup.cpp"),
        Path(__file__).with_name("Replay.cpp"),
    ]
    objects = []
    for source in sources:
        output = scratch / (source.stem + ".o")
        run(["c++", "-std=c++20", "-O2", "-UNDEBUG", "-Ulinux", "-pthread",
             "-DCORE_USE_OPENSSL=1", "-DPRESONUS_HAS_UPSTREAM_CORE=1",
             "-Iuc-library/include", "-isystem", "third_party/ccl-framework",
             "-c", source, "-o", output])
        objects.append(output)
    core = build / "upstream-core/sdk/lib"
    dns = build.parent / "external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so"
    run(["c++", "-pthread", *objects, build / "libpresonus_uc.a",
         core / "libcorelib.a", core / "libpresonus_core_allocator.a",
         core / "libpresonus_png.a", core / "libpresonus_zlib.a",
         "-lssl", "-lcrypto", dns, "-ldl",
         build / "private-glibc29-provider/libpresonus_private_glibc29.a", "-lm",
         "-o", scratch / "findgroup-replay"])


def replay(binary, fixture):
    entries = json.loads(Path(fixture).read_bytes())["entries"]
    for entry in entries:
        cases = entry["cases"]
        request = "".join(f"{case['registrar']} {case['tag']}\n" for case in cases)
        actual = run([binary], text=True, input=request, capture_output=True).stdout
        expected = [case["outputs"] for case in cases]
        assert [list(map(int, line.split())) for line in actual.splitlines()] == expected
    print(f"{sum(len(row['cases']) for row in entries)} portable comparisons "
          f"against {len(entries)} verified ELF identities")


def native(producer, context, firmware, selected, fixture):
    actual = run([sys.executable, "-B", producer, context, firmware, selected],
                 capture_output=True).stdout
    assert json.loads(actual) == json.loads(Path(fixture).read_bytes())
    print("Independent ARM replay matches sealed fixture for both roles")


def symbols(object_path, binary, mangled):
    for path in (object_path, binary):
        lines = run(["nm", "--defined-only", path], text=True,
                    capture_output=True).stdout.splitlines()
        assert sum(1 for line in lines if line.split()[-2:] == ["T", mangled]) == 1
    print(mangled)


if __name__ == "__main__":
    operation, *arguments = sys.argv[1:]
    operations = {"compile": compile_replay, "symbols": symbols, "native": native,
                  "replay": replay}
    operations[operation](*arguments)
