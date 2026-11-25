"""Compile and compare GUI MeterControl with five exact firmware identities."""

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import time

from native import ROOT, PACKETS, PREFIX, SEALED_PACKET, digest, generate, replay


TEST_ROOT = Path("uc-library/tests/recovery")
COMMON = TEST_ROOT / (PREFIX + "setattributes")
SOURCE = Path("uc-library/src/Presonus/MeterControl.cpp")
HEADER = Path("uc-library/include/presonus/MeterControl.hpp")
CONNECTION = Path("uc-library/src/Presonus/MeterControlConnection.cpp")
INTERP = Path("uc-library/src/DefaultMeterInterpolator.cpp")
DRIVER = COMMON / "Replay.cpp"
FORMATTED = [SOURCE, HEADER, DRIVER]
FORMATTER = "uc-library/.venv/bin/clang-format"
PYTHON = "uc-library/.venv/bin/python"
BUILD_ROOT = next(p for p in ROOT.parents if p.name == "ai-line-analysis") if ROOT.name != "ai-line-analysis" else ROOT
BUILD = BUILD_ROOT / "temp/core-upstream/root-integration-01"
CORE_LIB = BUILD / "upstream-core/sdk/lib"
ARCHIVES = [CORE_LIB / f"lib{name}.a" for name in
            ("corelib", "presonus_core_allocator", "presonus_png", "presonus_zlib")]
ARCHIVES.append(BUILD / "private-glibc29-provider/libpresonus_private_glibc29.a")
CORE_PROVENANCE = BUILD / "upstream-core/sdk/share/presonus-core-5/provenance.json"
WRAPS = ["-Wl,--wrap=_ZdlPv", "-Wl,--wrap=_ZdlPvm",
         "-Wl,--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE"]
FLAGS = ["/usr/bin/c++", "-std=c++20", "-DNDEBUG=1", "-DCORE_USE_OPENSSL=1",
         "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-Iuc-library/include",
         "-Ithird_party/ccl-framework", "-Ulinux", "-fno-rtti", "-fno-lto",
         "-fno-fast-math", "-ffp-contract=off", "-pthread"]
TASKS = tuple(PREFIX + suffix for suffix in
              ("isvertical", "setattributes", "destroy_base", "destroy_complete", "destroy_deleting"))


def hash_file(path):
    return digest((ROOT / path).read_bytes())


def binding(path, kind):
    return dict(path=str(path), sha256=hash_file(path), kind=kind)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


class Check:
    def __init__(self, task):
        self.task = task
        self.scratch = Path("temp/recovery-work/gui-meter-build") / task
        self.scratch.mkdir(parents=True, exist_ok=True)
        self.obj = self.scratch / "meter.o"
        self.exe = self.scratch / "replay"
        self.driver_obj = self.scratch / "replay.o"
        self.records = []

    def run(self, argv):
        argv = list(map(str, argv))
        print(json.dumps(argv), flush=True)
        before = time.monotonic()
        result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True,
                                env={**os.environ, "TMPDIR": str(ROOT / self.scratch)})
        self.records.append(dict(argv=argv, returncode=result.returncode,
                                 seconds=time.monotonic() - before,
                                 stdout=result.stdout, stderr=result.stderr))
        if result.returncode:
            raise RuntimeError(f"{argv}: {result.returncode}\n{result.stdout}\n{result.stderr}")
        return result.stdout

    def format(self):
        self.run([FORMATTER, "--style=file", "--fallback-style=LLVM",
                  "--dry-run", "--Werror", *FORMATTED])

    def compile(self):
        objects, records = [], []
        for source, obj in ((SOURCE, self.obj), (CONNECTION, self.scratch / "connection.o"),
                            (INTERP, self.scratch / "interp.o"), (DRIVER, self.driver_obj)):
            depfile = obj.with_suffix(".d")
            argv = [*FLAGS, "-MMD", "-MF", depfile, "-c", source, "-o", obj]
            self.run(argv)
            dependencies = shlex.split(depfile.read_text().replace("\\\n", "").split(":", 1)[1])
            records.append(dict(argv=list(map(str, argv)), source=str(source),
                                object=binding(obj, "object"), depfile=binding(depfile, "depfile"),
                                dependencies=[binding(Path(dep), "dependency") for dep in dependencies]))
            objects.append(obj)
        link_map = self.scratch / "link.map"
        self.run([FLAGS[0], *objects, *ARCHIVES, *WRAPS, "-Wl,-Map," + str(link_map),
                  "-pthread", "-ldl", "-lm", "-o", self.exe])
        return dict(compiles=records, link=binding(link_map, "link-map"),
                    core_provenance=binding(CORE_PROVENANCE, "provider"))

    def symbols(self, original, obj):
        rows = self.run(["/usr/bin/nm", "--defined-only", obj]).splitlines()
        matches = [row for row in rows if row.split()[-1] == original["mangled"]]
        assert len(matches) == 1 and matches[0].split()[-2] == "T"
        if self.driver_obj.exists() and "destroy" in self.task:
            needed = self.run(["/usr/bin/nm", "--undefined-only", self.driver_obj])
            assert all(f"_ZN8Presonus12MeterControlD{n}Ev" in needed for n in (1, 2))
        return matches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("format", "compile", "symbols", "native", "replay", "all"))
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()
    check = Check(args.task)
    exe, obj = args.exe or check.exe, args.object or check.obj
    fixture_path = args.fixture or TEST_ROOT / args.task / "fixtures.json"
    packet_path = PACKETS / args.task / "CONTEXT.json"
    if not packet_path.exists():
        packet_path = SEALED_PACKET / args.task / "CONTEXT.json"
    packet = json.loads(packet_path.read_text())
    original = packet["originals"][0]["original"]
    if args.mode in ("format", "all"):
        check.format()
    if args.mode in ("compile", "all"):
        build = check.compile()
    if args.mode in ("symbols", "all") or args.object:
        symbols = check.symbols(original, obj)
    if args.mode == "native":
        write_json(fixture_path, generate(args.task, exe))
        return
    if args.mode not in ("replay", "all"):
        return
    fixture = json.loads(fixture_path.read_text())
    assert fixture == generate(args.task, exe), "Fresh bound ARM observations differ"
    count = replay(args.task, exe, fixture)
    print(f"{args.task}: {count} fresh native/provider and Linux replay cases matched")
    if args.mode != "all":
        return

    review = packet["task"]["review"]
    limitations = [
        "ARM object layout and binary interoperability remain unresolved.",
        "Portable ownership covers factory allocations and leaves compatibility pointers borrowed.",
    ]
    if "destroy" in args.task:
        limitations += [
            "Native execution starts with seeded application fields and uses a guest virtual "
            "interpolator deletion boundary plus independent pinned CCL peak/base cleanup.",
            "D0 executes the exact firmware _ZdlPv PLT entry to an instrumented guest heap provider "
            "which unmaps the receiver. Allocator internals remain outside the domain.",
            "Native D1 and D2 have distinct verified ranges. The Linux compiler may alias their "
            "definitions, with complete and base-subobject call sites independently exercised.",
        ]
    elif args.task.endswith("setattributes"):
        limitations.append(
            "The ARM CCL configuration boundaries are substituted by real pinned source "
            "observations. The builder singleton starts initialized, and ARM observer storage, "
            "builder initialization/error edges and allocation failure are outside the domain.")
    else:
        limitations.append(
            "The original unencoded return declaration remains unresolved. The portable return is bool.")
    classification = ("compiled declaration-pending" if args.task.endswith("isvertical")
                      else "compiled portable-validated")
    inputs = {*FORMATTED, COMMON / "native.py", COMMON / "check.py", fixture_path,
              packet_path, *[Path(p) for p in packet["read_files"]]}
    sha = {str(path): hash_file(path) for path in sorted(inputs)}
    proof = dict(
        version=1, task_id=args.task, original=original, case_count=count,
        validation_domain=review["domain"], limitations=limitations,
        fixture_sha256=hash_file(fixture_path), source_hashes=sha,
        formatter=check.run([FORMATTER, "--version"]).strip(),
        compiler=check.run([FLAGS[0], "--version"]).splitlines()[0],
        unicorn=__import__("unicorn").__version__,
        archives={str(path): hash_file(path) for path in ARCHIVES},
        executable_sha256=hash_file(exe), object_sha256=hash_file(obj),
        checks=check.records, symbols=symbols, build=build,
        original_execution="Verified CS18AI ARM symbols with exact boundary identities",
        portable_execution="Linux C++ against pinned CCL 5.0.0 and current app providers",
        proposed_classification=classification,
    )
    write_json(Path("uc-library/candidates") / args.task / "worker-proof.json", proof)


if __name__ == "__main__":
    main()
