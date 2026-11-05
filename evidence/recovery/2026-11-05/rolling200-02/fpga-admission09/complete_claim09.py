from pathlib import Path
import json,sys,fcntl,hashlib,sqlite3,datetime
R=Path.cwd();L=R/'uc-library';E=R/'evidence/recovery/2026-11-05/rolling200-02/fpga-admission09';sys.path[:0]=[str(R/'dependency-graph'),str(L/'tools/registry')]
from dedup_index import connect,verify_inputs
from dedup_work import transition
from adapter import snapshot
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert read(E/'COMPLETED.json')['passed'] and read(E/'MIRROR01.json')['passed']
a=read(L/'candidates/rolling200_02_fpga_d0_audit/AUDIT.json');o=a['original'];claimid='9061a3f62f6e45c5bee0b3de397532cb';owner='rolling200_02_fpga_d0_audit_01'
proof=L/'validation/rolling200-fpga09/pending-proof.json'
q=read(R/'temp/recovery-work/rolling200-02/implementation-plan01/packets-current-fpga-d0-audit01/packets/rolling200_02_fpga_d0_audit_01/request.json');b=q['work_binding'];assert b['claim_id']==claimid and b['work_item_id']==a['unique_work_item']
with snapshot(L) as s:
 matches=[x for x in s.iter_records('pending') if x['original_elf_sha256']==o['elf_sha256'] and x['mangled']==o['original_mangled']];assert len(matches)==1 and matches[0]['behavior_validation_sha256']==sha(proof);guard=s.guard
checks={}
for x in b['covered_occurrences']:
 assert (x['elf_sha256'],x['original_mangled'])==(o['elf_sha256'],o['original_mangled'])
 checks[x['id']]={'elf_sha256':o['elf_sha256'],'original_mangled':o['original_mangled'],'range_sha256':o['range_sha256'],'compiled_mangling_checked':True,'behavioral_domain':a['validation_domain']}
manifest={'owner':owner,'reason':'Existing canonical FPGA D0 audited and admitted declaration-pending after exact native range/local acceptance/fullLinux508/role/install/compile-once/source bindings/guarded registry/tracker/mirror. No new implementation or ready promotion.','evidence_refs':[{'path':str(p.relative_to(R)),'sha256':sha(p)} for p in [proof,E/'MIRROR01.json',E/'RECONSTRUCTION_REMARKS01.json',E/'admission01.log']],'common_checks':{'compiled_mangling_checked':True,'canonical_linux_ctest':508,'local_acceptance':True,'portable_ready':False,'registry_guard':guard},'individual_checks':checks}
with (R/'dependency-graph/state/context.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 with snapshot(L) as s:assert s.guard==guard
 db=R/read(R/'dependency-graph/DEDUP_ACTIVE.json')['database']
 with connect(db) as c:
  verify_inputs(c);row=dict(c.execute('SELECT * FROM work_claims WHERE id=?',(claimid,)).fetchone());assert row['state']=='active' and row['owner']==owner
  other={x['id']:dict(x) for x in c.execute('SELECT * FROM work_claims WHERE state="active"') if x['id']!=claimid};O=E/'claim-completion09';O.mkdir(exist_ok=False)
  backup=O/'dedup-before.sqlite'
  with sqlite3.connect(backup) as dest:c.backup(dest)
  (O/'BACKUP.json').write_text(json.dumps({'path':str(backup.relative_to(R)),'sha256':sha(backup)},indent=2)+'\n');(O/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n');result=transition(c,claimid,'complete',manifest)
  for ident,value in other.items():assert dict(c.execute('SELECT * FROM work_claims WHERE id=?',(ident,)).fetchone())==value
  (O/'RECEIPT.json').write_text(json.dumps({'passed':True,'claim_id':claimid,'result':result,'unrelated_active_claims_preserved':len(other),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
print('Completed existing FPGA D0 audit claim; unrelated claims preserved')
