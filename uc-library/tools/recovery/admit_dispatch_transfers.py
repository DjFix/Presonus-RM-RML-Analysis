"""Fixed batch source gate and explicit admission through the existing merger."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

p=argparse.ArgumentParser(description=__doc__);p.add_argument("--apply",action="store_true");a=p.parse_args()
assert sys.platform.startswith("linux")
repo=Path.cwd().resolve();lib=repo/"uc-library";phase=repo/"evidence/recovery/2026-10-27/dispatch-transfers-root"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
keys=lambda rows:{(r["original_elf_sha256"],r["mangled"]) for r in rows}
state=lambda:{str(p.relative_to(lib)):sha(p) for p in [lib/"validation/ready-functions.json",lib/"validation/compiled-functions.json",*sorted((lib/"validation/history").rglob("*"))] if p.is_file()}
audits=list((lib/"candidates/panel-switch-dispatch/validation").glob("active-*/audit.json"));assert len(audits)==1
switch=audits[0].parent;assert read(audits[0])["native_source_gate_passed"]
m="candidates/uc-transfer-manager-transfers/validation/active-01/"
assert read(lib/m/"component-validation.json")["passed"]
raw=read(phase/"raw-active-01/validation.json");assert raw["passed"] and raw["canonical_ctest_count"]==124
headers=read(phase/"public-headers.log");assert headers["headers"]==83 and headers["returncode"]==0
s=str(switch.relative_to(lib))+"/";spi="validation/noaa-spi-service-dispatch-transfers/root-closure-01/"
inputs={"--fragment":[s+"ready.fragment.json",m+"ft-ready-fragment.json",spi+"ready-functions.fragment.json"],"--pending":[s+"pending.fragment.json",m+"ft-pending-fragment.json",m+"manager-pending-fragment.json",m+"transfers-pending-fragment.json",spi+"pending-functions.fragment.json"]}
command=[sys.executable,str(lib/"tools/merge_readiness.py"),"--library",str(lib)]
for flag,paths in inputs.items():
    for name in paths:command.extend([flag,name])
out=phase/"combined-preflight-01"
if not a.apply:
    out.mkdir(exist_ok=False);before=state()
    result=subprocess.run([*command,"--dry-run"],capture_output=True,text=True,cwd=repo)
    (out/"stdout.log").write_text(result.stdout);(out/"stderr.log").write_text(result.stderr)
    assert result.returncode==0,result.stderr[-5000:]
    actual=json.loads(result.stdout)
    assert (actual["portable_ready_entries"],actual["unique_mangled_methods"],actual["compiled_declaration_pending_entries"])==(622,334,378)
    assert actual["validated_only"] and not any(actual[n] for n in ("stale_previous_entries","demoted_entries","promoted_pending_entries"))
    assert before==state()
    proof=dict(passed=True,result=actual,unchanged_ledgers_and_history=before,inputs={n:sha(lib/n) for paths in inputs.values() for n in paths},command=command,tool_sha256=sha(Path(__file__)))
    (out/"validation.json").write_text(json.dumps(proof,indent=2)+"\n")
    print(json.dumps(dict(preflight_passed=True,ready=622,mangles=334,pending=378,switch_active=str(switch.relative_to(lib)))))
    raise SystemExit(0)
proof=read(out/"validation.json");assert proof["passed"] and proof["tool_sha256"]==sha(Path(__file__))
assert state()==proof["unchanged_ledgers_and_history"] and command==proof["command"]
for n,h in proof["inputs"].items():assert sha(lib/n)==h,n
oldready=read(lib/"validation/ready-functions.json")["functions"];oldpending=read(lib/"validation/compiled-functions.json")["functions"]
assert (len(oldready),len(oldpending))==(622,358)
admission=phase/"admission-01";admission.mkdir(exist_ok=False)
result=subprocess.run(command,capture_output=True,text=True,cwd=repo)
(admission/"stdout.log").write_text(result.stdout);(admission/"stderr.log").write_text(result.stderr)
assert result.returncode==0,result.stderr[-4000:]
ready=read(lib/"validation/ready-functions.json")["functions"];pending=read(lib/"validation/compiled-functions.json")["functions"]
assert (len(ready),len({r["mangled"] for r in ready}),len(pending))==(622,334,378)
assert keys(oldready)==keys(ready) and keys(oldpending)<=keys(pending) and not keys(ready)&keys(pending)
report=dict(passed=True,ready=622,mangles=334,pending=378,previous_ready_and_pending_preserved=True,preflight_sha256=sha(out/"validation.json"),tool_sha256=sha(Path(__file__)))
(admission/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
