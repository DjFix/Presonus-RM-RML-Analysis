"""Read-only unchanged-merger gate for the three fixed candidate packets."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

repo = Path.cwd().resolve()
lib = repo / "uc-library"
out = repo / "evidence/recovery/2026-10-28/queue-gate-geq-batch/candidate-preflight-01"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
mapping_path = lib / "candidates/uc-event-queue-lifecycle/CONTROLLED-APPLY-02.json"
mapping = read(mapping_path)
assert sha(mapping_path) == "0cbb0e9267b7ecd4ed8b83f8b817841a14667d31bb5b317bba305817493bf762"
manifest_path = lib / mapping["candidate_fragment_manifest"]
assert sha(manifest_path) == mapping["fragment_manifest_sha256"]
manifest = read(manifest_path)
ready, pending = list(manifest["ready"]), list(manifest["pending"])
for name, attempt in (("dsp-gate-parameter-list", "gate-candidate-preflight-01"),
                      ("dsp-geq-parameter-list", "candidate-preflight-01")):
    own = lib / "candidates" / name
    assert read(own / "validation" / attempt / "audit.json")["passed"]
    ready.append(f"candidates/{name}/validation/{attempt}/ready.fragment.json")
    pending.append(f"candidates/{name}/validation/{attempt}/pending.fragment.json")
assert len(ready) == len(pending) == 27
inputs = {str(mapping_path.relative_to(lib)): sha(mapping_path), str(manifest_path.relative_to(lib)): sha(manifest_path)}
for path in ("candidates/dsp-gate-parameter-list/CONTROLLED-APPLY.json", "candidates/dsp-geq-parameter-list/CONTROLLED-APPLY.json"):
    inputs[path] = sha(lib / path)
key_groups = []
for names, count in ((ready, 401), (pending, 305)):
    keys = []
    for name in names:
        inputs[name] = sha(lib / name)
        for row in read(lib / name)["functions"]:
            keys.append((row["original_elf_sha256"], row["mangled"]))
            proof = row["validation"]
            assert sha(lib / proof) == row["validation_sha256"]
            inputs[proof] = sha(lib / proof)
    assert len(keys) == len(set(keys)) == count
    key_groups.append(set(keys))
assert key_groups[0].isdisjoint(key_groups[1])
paths = [lib / "validation" / name for name in ("ready-functions.json", "compiled-functions.json", "formatting.json", "integration.json")]
paths += [p for p in (lib / "validation/history").rglob("*") if p.is_file()]
state = lambda: {str(p.relative_to(lib)): sha(p) for p in paths}
before = state()
out.mkdir(parents=True, exist_ok=False)
command = [sys.executable, str(lib / "tools/merge_readiness.py"), "--library", str(lib)]
for names, flag in ((ready, "--fragment"), (pending, "--pending")):
    for name in names:
        command += [flag, name]
command += ["--dry-run"]
result = subprocess.run(command, cwd=repo, capture_output=True, text=True)
(out / "stdout.log").write_text(result.stdout)
(out / "stderr.log").write_text(result.stderr)
assert result.returncode == 0, result.stderr[-5000:]
data = json.loads(result.stdout)
assert (data["portable_ready_entries"], data["unique_mangled_methods"], data["compiled_declaration_pending_entries"]) == (832, 464, 809), data
assert not any(data[n] for n in ("stale_previous_entries", "demoted_entries", "promoted_pending_entries"))
assert before == state()
assert all(sha(lib / name) == digest for name, digest in inputs.items())
proof = dict(passed=True, result=data, command=command, unchanged_state=before, inputs=inputs,
             ready_fragments=ready, pending_fragments=pending, tool_sha256=sha(Path(__file__)))
(out / "validation.json").write_text(json.dumps(proof, indent=2) + "\n")
print(json.dumps(dict(passed=True, ready=832, ready_unique=464, pending=809, admitted=False)))
