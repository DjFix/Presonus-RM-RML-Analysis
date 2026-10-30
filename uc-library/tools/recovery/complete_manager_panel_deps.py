"""Complete same-run Panel dependency receipts; original native proof untouched."""
import hashlib
import json
import os
import shlex
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PHASE = REPO / "evidence/recovery/2026-10-28/manager-discovery-batch"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    original_path = PHASE / "panel-uart-active-01/validation.json"
    original = json.loads(original_path.read_text())
    assert original["passed"] and original["source_mode"] == "active"
    for name, digest in original["source_hashes"].items():
        assert sha(REPO / name) == digest
    out = PHASE / "panel-system-deps-01"
    out.mkdir(exist_ok=False)
    scratch = REPO / "temp/recovery-work/manager-panel-system-deps-01"
    scratch.mkdir(exist_ok=False)
    env = dict(os.environ, TMPDIR=str(scratch), TMP=str(scratch), TEMP=str(scratch))
    commands = json.loads((original_path.parent / "commands.json").read_text())
    records = []
    dependencies = dict(original["compiler_dependencies"])
    for command in commands:
        if "-compile-" not in command["label"]:
            continue
        args = list(command["command"])
        index = args.index("-o")
        del args[index:index + 2]
        args.remove("-c")
        args.remove("-MMD")
        args.append("-M")
        result = subprocess.run(args, cwd=REPO, env=env, capture_output=True, text=True)
        label = command["label"]
        (out / (label + ".stdout.log")).write_text(result.stdout)
        (out / (label + ".stderr.log")).write_text(result.stderr)
        assert result.returncode == 0, (label, result.stderr[-3000:])
        records.append({"label": label, "command": args, "returncode": result.returncode, "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest()})
        for token in shlex.split(result.stdout.replace("\\\n", " ").split(":", 1)[1]):
            path = Path(token).resolve()
            if path.is_relative_to(REPO) and path.is_file():
                dependencies[str(path.relative_to(REPO))] = sha(path)
    assert len(records) == 12
    core_prefix = "temp/core-upstream/root-integration-01/upstream-core/sdk/include/presonus-core-5/core/"
    core = {name: digest for name, digest in dependencies.items() if name.startswith(core_prefix)}
    assert core
    for name, digest in core.items():
        source = REPO / "third_party/ccl-framework/core" / name.removeprefix(core_prefix)
        assert sha(source) == digest, name
    for name, digest in original["source_hashes"].items():
        assert sha(REPO / name) == digest
    for name, digest in dependencies.items():
        assert sha(REPO / name) == digest
    original["compiler_dependencies"] = dependencies
    original["source_hashes"][str(Path(__file__).relative_to(REPO))] = sha(Path(__file__))
    original["dependency_completion"] = {"original_replay": str(original_path.relative_to(REPO)), "original_replay_sha256": sha(original_path), "commands": records, "current_core_header_count": len(core), "native_receipts_unchanged": True, "reason": "Original -MMD omitted -isystem SDK declarations; same current sources/flags/includes reprocessed with -M. Original native outputs/objects/proof preserved, not rerun or rewritten."}
    destination = original_path.with_name("validation-system-deps.json")
    with destination.open("x") as stream:
        stream.write(json.dumps(original, indent=2) + "\n")
    (out / "commands.json").write_text(json.dumps(records, indent=2) + "\n")
    print(json.dumps({"passed": True, "compiler_dependency_queries": len(records), "actual_core_headers": len(core), "proof": str(destination.relative_to(REPO))}))


if __name__ == "__main__":
    main()
