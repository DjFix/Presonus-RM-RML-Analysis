"""Fixed-batch read-only preflight; explicit --apply uses unchanged merger."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

p=argparse.ArgumentParser(description=__doc__);p.add_argument("--apply",action="store_true");a=p.parse_args()
assert sys.platform.startswith("linux")
repo=Path.cwd().resolve();lib=repo/"uc-library";phase=repo/"evidence/recovery/2026-10-27/spi-avb-helpers-root"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
key=lambda r:(r["original_elf_sha256"],r["mangled"])
snapshot=lambda:{str(p.relative_to(lib)):sha(p) for p in [lib/"validation/ready-functions.json",lib/"validation/compiled-functions.json",*sorted((lib/"validation/history").rglob("*"))] if p.is_file()}
inputs={"--fragment":["validation/noaa-spi-service/root-closure-01/ready-functions.fragment.json","validation/avb-rm-helpers/active-01/ready-functions.fragment.json"],"--pending":["validation/noaa-spi-service/root-closure-01/pending-functions.fragment.json"]}
command=[sys.executable,str(lib/"tools/merge_readiness.py"),"--library",str(lib)]
for flag,paths in inputs.items():
    for path in paths:command.extend([flag,path])
out=phase/"combined-preflight-01"
if not a.apply:
    out.mkdir(exist_ok=False);before=snapshot()
    result=subprocess.run([*command,"--dry-run"],capture_output=True,text=True,cwd=repo)
    (out/"stdout.log").write_text(result.stdout);(out/"stderr.log").write_text(result.stderr)
    assert result.returncode==0,result.stderr[-4000:]
    actual=json.loads(result.stdout)
    assert (actual["portable_ready_entries"],actual["unique_mangled_methods"],actual["compiled_declaration_pending_entries"])==(610,327,326)
    assert actual["validated_only"] and not actual["stale_previous_entries"] and not actual["demoted_entries"] and not actual["promoted_pending_entries"]
    assert before==snapshot()
    proof=dict(passed=True,result=actual,unchanged_ledgers_and_history=before,inputs={path:sha(lib/path) for paths in inputs.values() for path in paths},tool_sha256=sha(Path(__file__)))
    (out/"validation.json").write_text(json.dumps(proof,indent=2)+"\n")
    print(json.dumps(dict(preflight_passed=True,ready=610,mangles=327,pending=326)))
    raise SystemExit(0)
proof=read(out/"validation.json");assert proof["passed"] and proof["tool_sha256"]==sha(Path(__file__))
assert snapshot()==proof["unchanged_ledgers_and_history"]
for n,h in proof["inputs"].items():assert sha(lib/n)==h,n
assert read(phase/"raw-active-01/validation.json")["passed"]
oldready=read(lib/"validation/ready-functions.json")["functions"]
oldpending=read(lib/"validation/compiled-functions.json")["functions"]
assert (len(oldready),len(oldpending))==(603,320)
admission=phase/"admission-01";admission.mkdir(exist_ok=False)
result=subprocess.run(command,capture_output=True,text=True,cwd=repo)
(admission/"stdout.log").write_text(result.stdout);(admission/"stderr.log").write_text(result.stderr)
assert result.returncode==0,result.stderr[-4000:]
ready=read(lib/"validation/ready-functions.json")["functions"];pending=read(lib/"validation/compiled-functions.json")["functions"]
assert (len(ready),len({r["mangled"] for r in ready}),len(pending))==(610,327,326)
assert {key(r) for r in oldready}<={key(r) for r in ready}
assert {key(r) for r in oldpending}<={key(r) for r in pending}
assert not {key(r) for r in ready}&{key(r) for r in pending}
report=dict(passed=True,ready=610,mangles=327,pending=326,previous_ready_and_pending_preserved=True,preflight_sha256=sha(out/"validation.json"),tool_sha256=sha(Path(__file__)))
(admission/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
