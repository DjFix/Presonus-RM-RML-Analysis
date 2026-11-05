from pathlib import Path
import json,subprocess,sys,time,hashlib
R=Path.cwd();L=R/'uc-library';E=R/'evidence/recovery/2026-11-05/rolling200-02/fpga-admission09';P=str(L/'.venv/bin/python')
sys.path.insert(0,str(L/'tools/registry'))
from adapter import snapshot
read=lambda p:json.loads(p.read_text())
receipt=R/'evidence/recovery/2026-11-05/rolling200-02/admission-inputs08b/claim-completion08/RECEIPTS.json'
process=Path('/proc/2516652');expected=b'complete_claims08.py'
print('Waiting for live25claimcompletion before registry mutation',flush=True)
while process.exists() and expected in (process/'cmdline').read_bytes():time.sleep(15)
assert receipt.exists(),'Claim completion exited without receipt; inspect existing job, no admission'
r=read(receipt);assert r['passed'] and r['completed']==25
with snapshot(L) as s:assert s.guard==read(E/'SEAL01.json')['registry_guard'],'Registry changed; review before admission'
assert read(E/'admission-dry-run01.log')['validated_only']
for argv,log in [
 ([P,str(L/'tools/merge_readiness.py'),'--library','uc-library','--pending','validation/rolling200-fpga09/pending.fragment.json'],'admission01.log'),
 ([P,str(L/'tools/generate_symbol_tracking.py'),'--library','uc-library','--repository','.', '--timing',str(E/'tracker-timing.json')],'tracker01.log'),
 ([P,str(L/'tools/recovery/audit_recovery_checkpoint.py'),'--repository','.', '--ready','1063','--pending','1999','--mangles','589','--suites','508','--phase','FPGA D0 existing canonical audit admission','--output',str(E/'MIRROR01.json')],'mirror01.log')]:
 print('Running',argv[1],flush=True)
 with (E/log).open('x') as f:subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,check=True)
assert read(E/'MIRROR01.json')['passed']
(E/'COMPLETED.json').write_text(json.dumps({'passed':True,'admitted_existing_audit_identities':1,'new_cpp_reconstructions':0,'ready':1063,'pending':1999,'claims_dependency_receipt':str(receipt.relative_to(R))},indent=2)+'\n')
print('FPGA D0 admitted pending; tracker and mirror passed',flush=True)
