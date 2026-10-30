#!/usr/bin/env python3
"""Replay saved ARM fixtures and reseal sources without changing global ledgers."""
import argparse
import hashlib
import json
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(kind="subsystem"):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    args = parser.parse_args()
    library = (args.repository / "uc-library").resolve()
    packet = kind == "packet"
    group = "dice-packet" if packet else "dice-subsystem"
    base = library / "validation" / group
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid4().hex[:8]
    validation = base / "runs" / run_id
    validation.mkdir(parents=True, exist_ok=False)
    build = library / "build" / group / run_id
    build.mkdir(parents=True, exist_ok=False)
    oracle_path = library / ("tests/vectors/dice-arm-oracle.json" if packet else "validation/dice-subsystem/arm-oracle.json")
    vectors = library / ("tests/vectors/dice-arm-vectors.txt" if packet else "validation/dice-subsystem/arm-vectors.txt")
    oracle = json.loads(oracle_path.read_text())
    assert digest(vectors) == oracle["vectors_sha256"], "fixture hash mismatch"
    sources = (["src/Presonus/UC/DicePacketQueue.cpp"] if packet else
               ["src/Presonus/DICE/SysexPacket.cpp", "src/Presonus/DICE/Dice3Subsystem.cpp"])
    header = "include/presonus/uc/DicePacketQueue.hpp" if packet else "include/presonus/dice/sysex.hpp"
    test_source = "tests/dice_tests.cpp" if packet else "tests/dice_subsystem_tests.cpp"
    source_hashes = {name: digest(library / name) for name in sources + [header, test_source]}
    formatting_path = library / "validation/formatting.json"
    formatting = json.loads(formatting_path.read_text())
    assert formatting["format_check_passed"] is True
    for name, sha in source_hashes.items():
        assert formatting["files"][name] == sha, f"formatter binding stale: {name}"
    commands = []

    def run(argv, name):
        commands.append(argv)
        result = subprocess.run(argv, cwd=library, text=True, capture_output=True)
        (validation / name).write_text("$ " + shlex.join(argv) + "\n" + result.stdout + result.stderr)
        (validation / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(f"{validation / name}: exit {result.returncode}")
        return result.stdout

    objects = []
    for source in sources:
        output = str((build / (Path(source).stem + ".o")).relative_to(library))
        run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Iinclude", "-c", source, "-o", output], Path(source).stem + "-build.log")
        objects.append(output)
    executable = str((build / "tests").relative_to(library))
    run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Iinclude", test_source, *objects, "-o", executable], "test-build.log")
    test = run([executable, str(vectors.relative_to(library))], "differential-tests.log")
    if packet:
        assert test == f'PASS: {oracle["cases"]["encode"]} ARM encode fixtures, {oracle["cases"]["decode"]} ARM decode fixtures, 200 valid-length roundtrips\n'
    else:
        assert f'PASS: {oracle["filter_cases"]} original ARM filter cases, {oracle["command_string_cases"]} command-string cases;' in test
    nm = run(["nm", "--defined-only", *objects], "compiled-symbols.log")
    defined = {line.split()[-1] for line in nm.splitlines() if line.split()}
    symbols = oracle["functions" if packet else "symbols"]
    expected = {symbol["mangled"] for symbol in symbols.values()}
    assert expected <= defined, expected - defined
    assert source_hashes == {name: digest(library / name) for name in source_hashes}, "source changed during replay"
    proof = dict(run_id=run_id, original_elf_sha256=oracle["original_elf_sha256"],
                 namespace="Presonus::UC" if packet else "Presonus::DICE", mangled_names=sorted(expected),
                 cpp_differential_passed=True, compiled_mangled_names_matched=True,
                 test_output=test, sources=source_hashes, original_symbols=symbols,
                 domain=oracle["domain"], limitations=oracle.get("limitations", []),
                 original_arm_object_layout_compatible=False, hardware_verified=False,
                 compiler=run(["g++", "--version"], "compiler-version.log").splitlines()[0],
                 object_hashes={name: digest(library / name) for name in objects},
                 oracle={"path":str(oracle_path.relative_to(library)),"sha256":digest(oracle_path)},
                 fixtures={"path":str(vectors.relative_to(library)),"sha256":digest(vectors)},
                 formatting={"path":"validation/formatting.json", "sha256":digest(formatting_path),
                             "formatter":formatting["formatter"], "current_sources_match":True},
                 verifier_sources={"tools/dice_subsystem_verify.py":digest(library / "tools/dice_subsystem_verify.py")})
    if packet:
        proof.update(arm_reference_cases=oracle["cases"], roundtrip_cases=200)
        proof["verifier_sources"]["tools/dice_packet_verify.py"] = digest(library / "tools/dice_packet_verify.py")
    else:
        proof.update(filter_cases=oracle["filter_cases"], command_string_cases=oracle["command_string_cases"])
    proof_path = validation / "validation.json"
    proof_path.write_text(json.dumps(proof, indent=2) + "\n")
    fragment = {"functions":[dict(mangled=symbol["mangled"], original_elf_sha256=oracle["original_elf_sha256"],
                  validation=str(proof_path.relative_to(library)), validation_sha256=digest(proof_path),
                  sources=source_hashes, portable_ready=True, domain=oracle["domain"]) for symbol in symbols.values()]}
    fragment_text = json.dumps(fragment, indent=2) + "\n"
    (validation / "ready-functions.fragment.json").write_text(fragment_text)
    # Stable discovery copies; fragments refer to immutable run proofs.
    for name in ("validation.json", "ready-functions.fragment.json"):
        previous = base / name
        if previous.exists():
            archive = base / "history" / digest(previous)
            archive.mkdir(parents=True, exist_ok=True)
            saved = archive / name
            if not saved.exists():
                saved.write_bytes(previous.read_bytes())
    (base / "validation.json").write_bytes(proof_path.read_bytes())
    (base / "ready-functions.fragment.json").write_text(fragment_text)
    print(test, end="")
    print(f"PASS: original mangled names and formatter hashes match; proof {proof_path.relative_to(library)} sha256={digest(proof_path)}")


if __name__ == "__main__":
    main()
