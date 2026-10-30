"""Fixed Fader/SPI guards around unchanged merger."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path.cwd().resolve()
LIB = REPO / "uc-library"
OUT = REPO / "evidence/recovery/2026-10-28/interpolator-programmer-batch"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def keys(rows):
    return {(row["original_elf_sha256"], row["mangled"]) for row in rows}


def state():
    paths = [LIB / "validation" / name for name in ("ready-functions.json", "compiled-functions.json", "formatting.json", "integration.json")]
    paths += [path for path in (LIB / "validation/history").rglob("*") if path.is_file()]
    return {str(path.relative_to(LIB)): sha(path) for path in paths}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    raw = read(OUT / "raw-active-01/validation.json")
    assert raw["passed"] and raw["canonical_ctest_count"] == 255 and raw["cases"] == 115933
    assert read(OUT / "raw-active-mirror-01/validation.json")["passed"]
    headers = read(OUT / "public-headers-01.log")
    assert headers["headers"] == 146 and headers["returncode"] == 0
    role = read(OUT / "role-audit-01.log")
    assert role["passed"] and role["units"] == 211 and role["groups"] == {"common": 109, "cs18": 46, "rm": 56}
    assert sha(LIB / role["proof"]) == role["sha256"]
    assert read(LIB / "validation/integration.json")["test_suites"] == 255
    assert read(OUT / "assertions.json")["passed"]
    assert len(read(OUT / "assertions.json")["tests"]) == 3
    manifest = read(OUT / "FINAL-FRAGMENTS.json")
    assert manifest["passed"]
    for name, digest in manifest["fragment_hashes"].items():
        assert sha(LIB / name) == digest, name
    incoming = {kind: [row for name in manifest[kind] for row in read(LIB / name)["functions"]] for kind in ("ready", "pending")}
    assert (len(incoming["ready"]), len(incoming["pending"])) == (151, 102)
    assert all(len(rows) == len(keys(rows)) for rows in incoming.values())
    assert not keys(incoming["ready"]) & keys(incoming["pending"])
    command = [sys.executable, str(LIB / "tools/merge_readiness.py"), "--library", str(LIB)]
    for kind, flag in (("ready", "--fragment"), ("pending", "--pending")):
        for name in manifest[kind]:
            command.extend([flag, name])
    pre = OUT / "combined-preflight-01"
    if not args.apply:
        pre.mkdir(exist_ok=False)
        before = state()
        result = subprocess.run(command + ["--dry-run"], cwd=REPO, text=True, capture_output=True)
        (pre / "stdout.log").write_text(result.stdout)
        (pre / "stderr.log").write_text(result.stderr)
        assert result.returncode == 0, result.stderr[-5000:]
        data = json.loads(result.stdout)
        assert (data["portable_ready_entries"], data["unique_mangled_methods"], data["compiled_declaration_pending_entries"]) == (893, 497, 822), data
        assert not any(data[name] for name in ("stale_previous_entries", "demoted_entries", "promoted_pending_entries"))
        assert state() == before
        proof = {"passed": True, "result": data, "command": command, "unchanged_state": before, "inputs": manifest["fragment_hashes"], "tool_sha256": sha(Path(__file__))}
        (pre / "validation.json").write_text(json.dumps(proof, indent=2) + "\n")
        print(json.dumps({"passed": True, "dry_run": True, "ready": 893, "ready_unique": 497, "pending": 822}))
        return
    proof = read(pre / "validation.json")
    assert proof["passed"] and proof["tool_sha256"] == sha(Path(__file__)) and proof["command"] == command
    assert state() == proof["unchanged_state"]
    for name, digest in proof["inputs"].items():
        assert sha(LIB / name) == digest
    old_ready = read(LIB / "validation/ready-functions.json")["functions"]
    old_pending = read(LIB / "validation/compiled-functions.json")["functions"]
    assert (len(old_ready), len(old_pending)) == (856, 816)
    admit = OUT / "admission-01"
    admit.mkdir(exist_ok=False)
    result = subprocess.run(command, cwd=REPO, capture_output=True, text=True)
    (admit / "stdout.log").write_text(result.stdout)
    (admit / "stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stderr[-5000:]
    ready = read(LIB / "validation/ready-functions.json")["functions"]
    pending = read(LIB / "validation/compiled-functions.json")["functions"]
    assert (len(ready), len({row["mangled"] for row in ready}), len(pending)) == (893, 497, 822)
    assert keys(old_ready) <= keys(ready) and keys(old_pending) <= keys(pending)
    assert not keys(ready) & keys(pending)
    added_ready = keys(ready) - keys(old_ready)
    added_pending = keys(pending) - keys(old_pending)
    assert len(added_ready) == 37 and len({name for _, name in added_ready}) == 21
    assert len(added_pending) == 6 and len({name for _, name in added_pending}) == 6
    report = {"passed": True, "ready": 893, "ready_unique": 497, "pending": 822, "new_ready_records": 37, "new_ready_unique_names": 21, "new_pending_records": 6, "new_pending_unique_names": 6, "no_removals": True, "demotions": 0, "promotions": 0, "preflight_sha256": sha(pre / "validation.json"), "tool_sha256": sha(Path(__file__))}
    (admit / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
