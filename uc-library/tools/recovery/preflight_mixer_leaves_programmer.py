"""Read-only unchanged-merger preflight for three frozen candidate packets."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

repo = Path.cwd().resolve()
lib = repo / "uc-library"
out = repo / "evidence/recovery/2026-10-28/mixer-leaves-programmer-batch/candidate-preflight-01"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text())
manifest = read(repo / "evidence/recovery/2026-10-28/mixer-leaves-programmer-batch/CANDIDATES.json")
assert manifest["all_candidate_guards_released"]
ready, pending = manifest["ready"], manifest["pending"]
assert len(ready) == len(pending) == 2
assert all((lib / name).is_file() for name in ready + pending)
paths = [lib / "validation" / name for name in ("ready-functions.json", "compiled-functions.json", "formatting.json", "integration.json")]
paths += [path for path in (lib / "validation/history").rglob("*") if path.is_file()]
state = lambda: {str(path.relative_to(lib)): sha(path) for path in paths}
before = state()
inputs = {name: sha(lib / name) for name in ready + pending}
for name in ready + pending:
    for row in read(lib / name)["functions"]:
        proof = row.get("behavior_validation", row["validation"])
        inputs[proof] = sha(lib / proof)
out.mkdir()
cmd = [sys.executable, str(lib / "tools/merge_readiness.py"), "--library", str(lib)]
for name in ready:
    cmd += ["--fragment", name]
for name in pending:
    cmd += ["--pending", name]
cmd += ["--dry-run"]
result = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
(out / "stdout.log").write_text(result.stdout)
(out / "stderr.log").write_text(result.stderr)
assert result.returncode == 0, result.stderr[-5000:]
data = json.loads(result.stdout)
assert (data["portable_ready_entries"], data["unique_mangled_methods"], data["compiled_declaration_pending_entries"]) == (917, 511, 857), data
assert not any(data[name] for name in ("stale_previous_entries", "demoted_entries", "promoted_pending_entries"))
assert before == state()
assert all(sha(lib / name) == digest for name, digest in inputs.items())
proof = dict(passed=True, result=data, command=cmd, unchanged_state=before, inputs=inputs, tool_sha256=sha(Path(__file__)))
(out / "validation.json").write_text(json.dumps(proof, indent=2) + "\n")
print(json.dumps(dict(passed=True, ready=917, unique_ready=511, pending=857, admitted=False)))
