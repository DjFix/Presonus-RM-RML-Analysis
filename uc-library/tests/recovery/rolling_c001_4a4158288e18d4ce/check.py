import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from native import observe

SOURCE = 'uc-library/src/Presonus/Panel/SharedMemoryComm.cpp'
HEADER = 'uc-library/include/presonus/panel/SharedMemoryComm.hpp'
REPLAY = 'uc-library/tests/recovery/rolling_c001_4a4158288e18d4ce/Replay.cpp'
DOMAIN = 'False and true inputs across distinct ARM receiver sentinels. Original ARM returns word 1, restores the frame and accesses only its stack. Portable execution compares the return word for each case.'
LIMITS = 'Portable nonvirtual, nonstatic int member. Original return declaration, virtual dispatch, inheritance, object layout, ARM ABI and hardware behavior remain unresolved. Original table references are recorded without claiming dispatch.'
FORMATTER = "uc-library/.venv/bin/clang-format"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv):
    print(argv, flush=True)
    return subprocess.check_output(argv, text=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    start = datetime.now(timezone.utc).isoformat()
    fixture = json.loads(args.fixtures.read_text())
    scratch = Path("temp/recovery-work/rolling_c001_4a4158288e18d4ce")
    obj = args.object or scratch / "SharedMemoryComm.o"
    exe = args.exe or scratch / "replay"
    paths = [SOURCE, HEADER, REPLAY]
    formatter = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *paths]
    compile_obj = ["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-Iuc-library/include",
                   "-c", SOURCE, "-o", str(obj)]
    compile_exe = ["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-Iuc-library/include",
                   REPLAY, str(obj), "-o", str(exe)]
    symbol_cmd = ["nm", "--defined-only", str(obj)]
    if args.mode == "format":
        run(formatter)
    if args.mode == "compile":
        scratch.mkdir(parents=True, exist_ok=True)
        run(compile_obj)
        run(compile_exe)
    if args.mode in ("symbols", "replay"):
        symbol = fixture["original"]["mangled"]
        assert any(line.split()[-1] == symbol for line in run(symbol_cmd).splitlines() if line.split())
    if args.mode == "replay":
        run(formatter)
        native = observe(Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/packeting/next59/snapshot/rootfs/CS18_v13840/home/root/surface'))
        assert native == fixture
        words = [int(value) for value in run([str(exe)]).splitlines()]
        assert words == [case["return_word"] for case in native["cases"]]
        row = dict(native["original"], sources={p.removeprefix("uc-library/"): digest(p)
                                                 for p in [SOURCE, HEADER]},
                   cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
                   declaration_uncertainties=[LIMITS], domain=DOMAIN)
        row["original_elf_sha256"] = row.pop("elf_sha256")
        proof = dict(verified=True, domain=DOMAIN, proposed_readiness=dict(ready=[],pending=[row]),
                     native=native, portable_words=words, fixtures_sha256=digest(args.fixtures),
                     object_sha256=digest(obj), executable_sha256=digest(exe),
                     integration_sha256=digest(args.integration) if args.integration else None,
                     producers={str(p):digest(p) for p in [Path(__file__), Path(__file__).with_name("native.py"), REPLAY]},
                     formatter=run([FORMATTER,"--version"]).strip(),
                     compiler=run(["c++","--version"]).splitlines()[0],
                     commands=dict(format=formatter, symbols=symbol_cmd, local_compile=[compile_obj,compile_exe]),
                     start_utc=start, end_utc=datetime.now(timezone.utc).isoformat())
        if args.out:
            args.out.write_text(json.dumps(proof,indent=2)+"\n")
        print(DOMAIN)


if __name__ == "__main__":
    main()
