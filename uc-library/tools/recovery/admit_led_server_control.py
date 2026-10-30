"""Guarded admission of this one reviewed batch through the existing merger."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

assert sys.platform.startswith("linux")
repo=Path.cwd().resolve();lib=repo/"uc-library"
phase=repo/"evidence/recovery/2026-10-27/led-server-control-root"
gate=lib/"candidates/uc-file-server-service/validation/active-01/preflight-combined-01"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
proof=read(gate/"validation.json")
assert proof["passed"] and proof["global_ledgers_and_history_unchanged"]
actual=proof["actual"]
assert (actual["portable_ready_entries"],actual["unique_mangled_methods"],actual["compiled_declaration_pending_entries"])==(603,322,320)
assert actual["validated_only"] and not actual["stale_previous_entries"] and not actual["demoted_entries"] and not actual["promoted_pending_entries"]
for name,digest in read(gate/"before.json").items():assert sha(lib/name)==digest,name
for name,digest in proof["inputs"].items():assert sha(lib/name)==digest,name
assert read(phase/"raw-active-01/validation.json")["passed"]
assert read(lib/"validation/integration.json")["ctest_passed"]
keys=lambda rows:{(r["original_elf_sha256"],r["mangled"]) for r in rows}
oldready=read(lib/"validation/ready-functions.json")["functions"]
oldpending=read(lib/"validation/compiled-functions.json")["functions"]
assert (len(oldready),len(oldpending))==(595,298)
argv=read(gate/"command.json")
assert argv[-1]=="--dry-run" and argv[1]==str(lib/"tools/merge_readiness.py")
argv=argv[:-1]
output=phase/"admission-01";output.mkdir(exist_ok=False)
(output/"command.json").write_text(json.dumps(argv,indent=2)+"\n")
completed=subprocess.run(argv,cwd=repo,capture_output=True,text=True)
(output/"stdout.log").write_text(completed.stdout)
(output/"stderr.log").write_text(completed.stderr)
assert completed.returncode==0,completed.stderr[-4000:]
ready=read(lib/"validation/ready-functions.json")["functions"]
pending=read(lib/"validation/compiled-functions.json")["functions"]
assert (len(ready),len({r["mangled"] for r in ready}),len(pending))==(603,322,320)
assert keys(oldready)<=keys(ready) and keys(oldpending)<=keys(pending)
assert not keys(ready)&keys(pending)
report=dict(passed=True,ready=603,unique_ready_names=322,pending=320,previous_ready_preserved=True,previous_pending_preserved=True,combined_preflight_sha256=sha(gate/"validation.json"),ledgers={name:sha(lib/"validation"/name) for name in ("ready-functions.json","compiled-functions.json")},tool_sha256=sha(Path(__file__)))
(output/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
