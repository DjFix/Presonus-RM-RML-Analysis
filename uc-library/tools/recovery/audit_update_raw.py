"""Read-only local hash audit of this batch's Linux raw-source seal."""
import hashlib
import json
from pathlib import Path

repo=Path('/home/rs/projects/opencs/ai-line-analysis');lib=repo/"uc-library"
phase=repo/"evidence/recovery/2026-10-28/update-interp-batch"
raw=phase/"raw-active-01";proof=json.loads((raw/"validation.json").read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def resolve(name):
    return lib/name.removeprefix("uc-library/") if name.startswith("uc-library/") else repo/name
assert proof["passed"] and proof["cases"]==115933 and len(proof["suites"])==8
checked={}
def check(path,digest):
    assert path.is_file() and sha(path)==digest,str(path)
    checked[str(path.relative_to(repo))]=digest
for group in ("source_hashes","fixture_hashes","replay_tools"):
    for name,digest in proof[group].items():check(lib/name,digest)
for name,row in proof["original_receipts"].items():check(resolve(name),row["sha256"])
for name,digest in proof["original_artifacts"].items():check(resolve(name),digest)
for row in proof["input_images"]:check(resolve(row["path"]),row["sha256"])
for name,digest in json.loads((raw/"artifact-hashes.json").read_text()).items():check(raw/name,digest)
check(raw/"seal_raw_root.py",proof["tool_sha256"])
report=dict(passed=True,linux_seal_sha256=sha(raw/"validation.json"),checked_files=len(checked),cases=proof["cases"],source_bindings=len(proof["source_hashes"]),scope="Local mirrored raw receipts, source, fixtures and Linux proof artifacts only; no Mac C++ execution",tool_sha256=sha(Path(__file__)),files=checked)
out=phase/"raw-active-mirror-01";out.mkdir(exist_ok=False)
(out/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({k:v for k,v in report.items() if k!="files"}))
