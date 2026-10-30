#!/usr/bin/env python3
"""Verify portable embedded-DICE mixer semantics against a saved bounded oracle."""
import argparse
import hashlib
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("repository", type=Path)
    p.add_argument("oracle_run", help="library-relative oracle directory")
    a = p.parse_args()
    root = a.repository.resolve()
    lib = root / "uc-library"
    oracle_run = lib / a.oracle_run
    oracle_path = oracle_run / "arm-oracle.json"
    oracle = json.loads(oracle_path.read_text())
    fixtures = oracle_run / "arm-fixtures.txt"
    assert sha(fixtures) == oracle["fixture_sha256"]
    out = oracle_run / "verification" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True, exist_ok=False)
    commands = []

    def run(argv, name):
        commands.append(argv)
        result = subprocess.run(argv, cwd=lib, text=True, capture_output=True)
        (out / name).write_text("$ " + shlex.join(argv) + "\n" + result.stdout + result.stderr)
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(f"{out/name}: {result.stdout}{result.stderr}")
        return result.stdout

    sources = ["src/embedded_dice/mix.cpp", "include/presonus/embedded_dice/mix.hpp", "validation/dice-image/mix_differential.cpp"]
    formatter = str(lib / ".venv/bin/clang-format")
    version = run([formatter, "--version"], "formatter-version.log").strip()
    run([formatter, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *sources], "format-check.log")
    source_hashes = {path:sha(lib/path) for path in sources}
    formatting = dict(formatter=version, configuration_sha256=sha(root/".clang-format"), files=source_hashes, format_check_passed=True)
    (out / "formatting.json").write_text(json.dumps(formatting, indent=2)+"\n")
    obj = str((out / "mix.o").relative_to(lib))
    exe = str((out / "differential-tests").relative_to(lib))
    common = ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Iinclude"]
    run([*common, "-c", sources[0], "-o", obj], "build-source.log")
    run([*common, sources[2], obj, "-o", exe], "build-tests.log")
    output = run([sys.executable, "tools/dice_image_mix_replay.py", "--executable", exe,
                  "--oracle", str(oracle_path.relative_to(lib))], "differential-tests.log")
    assert output.startswith(f'PASS: {sum(oracle["counts"].values())} original ARM cases;')
    names = run(["nm", "-C", "--defined-only", obj], "compiled-portable-symbols.log")
    for name in oracle["callbacks"]:
        assert "presonus::embedded_dice::mix_" + name + "(" in names
    assert source_hashes == {path:sha(lib/path) for path in sources}
    proof = dict(image_sha256=oracle["image_sha256"], oracle_path=str(oracle_path.relative_to(lib)), oracle_sha256=sha(oracle_path),
        fixture_sha256=sha(fixtures), exact_trace_sha256=oracle["exact_trace_sha256"], sources=source_hashes, portable_namespace="presonus::embedded_dice",
        original_namespace=None, original_mangled_names=None, original_scope_unresolved=True,
        formatting={"path":str((out/"formatting.json").relative_to(lib)),"sha256":sha(out/"formatting.json")},
        cpp_differential_passed=True, exact_ordered_trace_comparison_passed=True, portable_compiled_names_checked=True, original_mangled_names_checked=False,
        callbacks=oracle["callbacks"], case_counts=oracle["counts"], test_output=output,
        original_arm_abi_compatible=False, hardware_verified=False, image_checksum_validated=False,
        domain="Pure portable callback semantics with RAM-backed register reads/writes, ordered diagnostics/printf-call output traces and normal-return external hooks; uint32 inputs. No device, scheduler, timing or MMIO side-effect equivalence.",
        limitations=[oracle["trace_comparison"], oracle["external_hook_contract"],
                    "Embedded image checksum remains unresolved; byte identity is checked against the extracted blob hash.",
                    "CLI labels are original descriptor strings; original C/C++ scopes, linker symbols, ABI and full function aliases remain unresolved."],
        compiler=run(["g++","--version"],"compiler-version.log").splitlines()[0], object_sha256=sha(lib/obj),
        tools={name:sha(lib/name) for name in ("tools/dice_image_mix_oracle.py", "tools/dice_image_mix_verify.py", "tools/dice_image_mix_replay.py")})
    proof_path = out / "validation.json"
    proof_path.write_text(json.dumps(proof, indent=2)+"\n")
    fragment = {"scope":"embedded_dice_cli_callbacks; separate from host ELF symbol denominator", "embedded_callbacks":[]}
    for name, metadata in oracle["callbacks"].items():
        fragment["embedded_callbacks"].append(dict(registration_label=metadata["registration_label"],
            runtime_entry=metadata["runtime_entry"], image_file_offset=metadata["image_file_offset"],
            image_sha256=oracle["image_sha256"], original_mangled_name=None, portable_name="presonus::embedded_dice::mix_"+name,
            sources=source_hashes, validation=str(proof_path.relative_to(lib)), validation_sha256=sha(proof_path),
            portable_semantics_verified=True, original_arm_abi_compatible=False, hardware_verified=False, domain=proof["domain"]))
    (out / "embedded-ready.fragment.json").write_text(json.dumps(fragment, indent=2)+"\n")
    print(output, end="")
    print("PROOF", proof_path, sha(proof_path))


if __name__ == "__main__":
    main()
