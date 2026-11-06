from pathlib import Path
import datetime,fcntl,hashlib,json,sqlite3,sys,collections
R=Path.cwd();L=R/'uc-library';E=R/'evidence/recovery/2026-11-06/rolling200-02/integration115';O=E/'claim-completion01';sys.path[:0]=[str(R/'dependency-graph'),str(L/'tools/registry')]
from adapter import snapshot
from dedup_index import connect,verify_inputs,meta
from dedup_work import transition
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();proofpath=L/'validation/rolling200-integrated115-r1/new.pending-proof.json';proof=read(proofpath);config=read(E/'FINAL_CONFIG01.json');assert read(E/'MIRROR01.json')['passed'] and len(proof['functions'])==27
with snapshot(L) as s:
 guard=s.guard;pending={(x['original_elf_sha256'],x['mangled']):x for x in s.iter_records('pending')}
 for f in proof['functions']:assert pending[(f['original_elf_sha256'],f['mangled'])]['behavior_validation_sha256']==sha(proofpath)
groups={}
for f in proof['functions']:
 h=read(R/f['handoff']['path']);q=read((R/h['packet_manifest']).parent/'request.json');b=q['work_binding'];g=groups.setdefault(b['claim_id'],{'binding':b,'task':h['task_id'],'functions':{}});assert g['binding']==b;key=(f['original_elf_sha256'],f['mangled']);assert key not in g['functions'];g['functions'][key]=f
assert len(groups)==21
O.mkdir(exist_ok=False);refs=[{'path':str(p.relative_to(R)),'sha256':sha(p)} for p in [proofpath,E/'MIRROR01.json',E/'RECONSTRUCTION_REMARKS01.json',E/'admission01.log']];items=[]
for claim,g in groups.items():
 b=g['binding'];checks={};covered=set()
 for original in b['covered_occurrences']:
  key=(original['elf_sha256'],original['original_mangled']);f=g['functions'][key];covered.add(key);checks[original['id']]={'elf_sha256':key[0],'original_mangled':key[1],'range_sha256':f['native_range']['bytes_sha256'],'compiled_mangling_checked':True,'behavioral_domain':f['validation_domain']}
 assert covered==set(g['functions'])
 manifest={'owner':b['claim_owner'],'reason':'Exact covered identities admitted compiled-declaration-pending with separate original ranges, local native/provider replay, Linux532, role/compile-once, guarded admission and mirror. No original return/layout/ARM ABI/hardware claim.','evidence_refs':refs,'common_checks':{'compiled_mangling_checked':True,'canonical_linux_ctest':532,'local_acceptance':True,'portable_ready':False,'registry_guard':guard},'individual_checks':checks};p=O/(g['task']+'.json');p.write_text(json.dumps(manifest,indent=2)+'\n');items.append({'task':g['task'],'claim_id':claim,'manifest':str(p.relative_to(R))})
with (R/'dependency-graph/state/context.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 with snapshot(L) as s:assert s.guard==guard
 pointer=read(R/'dependency-graph/DEDUP_ACTIVE.json');db=R/pointer['database']
 with connect(db) as c:
  verify_inputs(c);assert meta(c,'generation')==pointer['generation'];untouched={r['id']:dict(r) for r in c.execute('SELECT * FROM work_claims WHERE state="active"') if r['id'] not in groups}
  for item in items:
   row=c.execute('SELECT * FROM work_claims WHERE id=?',(item['claim_id'],)).fetchone();assert row and row['state']=='active' and row['owner']==read(R/item['manifest'])['owner']
  backup=O/'dedup-before.sqlite'
  with sqlite3.connect(backup) as target:c.backup(target)
  (O/'BACKUP.json').write_text(json.dumps({'path':str(backup.relative_to(R)),'sha256':sha(backup),'database':str(db.relative_to(R))},indent=2)+'\n');receipts=[]
  for item in items:
   result=transition(c,item['claim_id'],'complete',read(R/item['manifest']));receipts.append(dict(item,result=result,manifest_sha256=sha(R/item['manifest'])));(O/'RECEIPTS.partial.json').write_text(json.dumps(receipts,indent=2)+'\n')
  for ident,before in untouched.items():assert dict(c.execute('SELECT * FROM work_claims WHERE id=?',(ident,)).fetchone())==before
  (O/'RECEIPTS.json').write_text(json.dumps({'passed':True,'completed_claims':len(items),'covered_identities':27,'other_active_claims_preserved':sorted(untouched),'receipts':receipts,'readiness_changed':False,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
print('Completed21 admitted claims covering27 exact identities; other claims preserved')
