#!/usr/bin/env python3
"""Format-check, build, replay and seal eight original interpolator entries."""
import argparse
import hashlib
import json
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("repository", type=Path)
    p.add_argument("oracle_run", help="library-relative directory containing client/server oracle files")
    a = p.parse_args()
    root = a.repository.resolve()
    lib = root / "uc-library"
    oracle_run = lib / a.oracle_run
    out = oracle_run / "verification" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True, exist_ok=False)
    commands = []

    def run(argv, name):
        commands.append(argv)
        result = subprocess.run(argv,cwd=lib,text=True,capture_output=True)
        (out/name).write_text("$ "+shlex.join(argv)+"\n"+result.stdout+result.stderr)
        (out/"commands.json").write_text(json.dumps(commands,indent=2)+"\n")
        if result.returncode:
            raise RuntimeError(f"{out/name}: {result.stdout}{result.stderr}")
        return result.stdout

    sources = ["src/Core/interpolator.cpp","include/presonus/core/interpolator.hpp","tests/core_interpolator_tests.cpp"]
    formatter = str(lib/".venv/bin/clang-format")
    version = run([formatter,"--version"],"formatter-version.log").strip()
    run([formatter,"--style=file","--fallback-style=LLVM","--dry-run","--Werror",*sources],"formatter-check.log")
    source_hashes = {name:sha(lib/name) for name in sources}
    formatting = dict(formatter=version,configuration_sha256=sha(root/".clang-format"),files=source_hashes,format_check_passed=True)
    (out/"formatting.json").write_text(json.dumps(formatting,indent=2)+"\n")
    flags = ["-std=c++17","-O2","-Wall","-Wextra","-Wpedantic","-fno-fast-math","-ffp-contract=off","-Iinclude"]
    obj = str((out/"interpolator.o").relative_to(lib))
    exe = str((out/"tests").relative_to(lib))
    run(["g++",*flags,"-c",sources[0],"-o",obj],"build-source.log")
    run(["g++",*flags,sources[2],obj,"-o",exe],"build-tests.log")
    nm = run(["nm","--defined-only",obj],"compiled-symbols.log")
    defined = {line.split()[-1] for line in nm.splitlines() if line.split()}
    domain = ("Bounded fixtures: 24 edge binary32 words cubed over minimum, maximum and input, plus4096 seeded random bit-pattern triples for each of4methods in eachELF. "
              "FE_TONEAREST, gradual underflow, FTZ/DAZ disabled; -fno-fast-math -ffp-contract=off; separate binary32 operations and explicit original libgcc NaN sign/payload behavior. "
              "Exact return bits and unchanged state compared. Floating exception flags, original leading-word/inheritance/vtable layout, ARM binary ABI and hardware are unproven.")
    reports = []
    logs = {}
    for role in ("client","server"):
        oracle_path = oracle_run/role/"arm-oracle.json"
        oracle = json.loads(oracle_path.read_text())
        vectors = oracle_run/role/"arm-vectors.txt"
        assert sha(vectors) == oracle["fixture_sha256"]
        for symbol in oracle["functions"].values():
            assert symbol["mangled"] in defined, symbol["mangled"]
        logs[role] = run([exe,str(vectors.relative_to(lib))],role+"-differential-tests.log")
        expected = "PASS:" + "".join(f' {op}={oracle["cases"][op]}' for op in sorted(oracle["cases"]))
        assert logs[role].startswith(expected)
        reports.append(dict(role=role,oracle=str(oracle_path.relative_to(lib)),oracle_sha256=sha(oracle_path),
                            fixture=str(vectors.relative_to(lib)),fixture_sha256=sha(vectors),
                            original_elf_sha256=oracle["original_elf_sha256"],cases=oracle["cases"],symbols=oracle["functions"]))
    assert source_hashes == {name:sha(lib/name) for name in sources}
    proof = dict(sources=source_hashes,namespace="Core",classes=["LinearInterpolator","LinearReverseInterpolator"],
        records=reports,domain=domain,cpp_differential_passed=True,compiled_original_mangled_names_matched=True,
        return_signature_evidence="Original methods return results of original ARM __aeabi float arithmetic, with+0.0 early returns. Originalfloat parameter/const/member/class identity is encoded by mangling; modernpublicheader corroborates float return but is not the firmware layout authority.",
        portable_state="two float fields corresponding to originalARMthis+4 andthis+8; original leadingword/inheritance/vtable not modeled",
        compiler=run(["g++","--version"],"compiler-version.log").splitlines()[0],compiler_flags=flags,
        formatting={"path":str((out/"formatting.json").relative_to(lib)),"sha256":sha(out/"formatting.json")},
        tools={name:sha(lib/name) for name in ("tools/core_interpolator_oracle.py","tools/core_interpolator_verify.py","tools/mixer_dsp_oracle.py")},
        object_sha256=sha(lib/obj),test_output=logs,original_arm_abi_compatible=False,hardware_verified=False)
    path = out/"validation.json"
    path.write_text(json.dumps(proof,indent=2)+"\n")
    fragment = {"functions":[]}
    for report in reports:
        for symbol in report["symbols"].values():
            fragment["functions"].append(dict(role=report["role"],mangled=symbol["mangled"],
                original_elf_sha256=report["original_elf_sha256"],validation=str(path.relative_to(lib)),
                validation_sha256=sha(path),sources=source_hashes,portable_ready=True,domain=domain))
    (out/"ready-functions.fragment.json").write_text(json.dumps(fragment,indent=2)+"\n")
    print("".join(role+": "+text for role,text in logs.items()),end="")
    print("PROOF",path,sha(path))


if __name__ == "__main__":
    main()
