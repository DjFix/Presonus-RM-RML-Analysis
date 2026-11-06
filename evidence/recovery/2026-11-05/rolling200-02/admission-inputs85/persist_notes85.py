"""Append exact-original admission resolutions, retaining existing research history."""
from pathlib import Path
import datetime,hashlib,json,sqlite3,sys
R=Path.cwd();L=R/'uc-library';E=R/'evidence/recovery/2026-11-05/rolling200-02/admission-inputs85';O=E/'admitted-notes02';sys.path.insert(0,str(L/'tools/registry'))
from adapter import snapshot,resolve_db
from catalog import operate
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
proof=L/'validation/rolling200-integrated85-r1/new.pending-proof.json';remarks=E/'RECONSTRUCTION_REMARKS01.json'
assert read(E/'MIRROR01.json')['passed'];notes=read(remarks)['functions'];assert len(notes)==read(E/'FINAL_CONFIG01.json')['new_count']
O.mkdir(exist_ok=False);ops=[];at=datetime.datetime.now(datetime.timezone.utc).isoformat()
refs=[{'path':str(p.relative_to(R)),'sha256':sha(p)} for p in [proof,remarks,E/'MIRROR01.json',E/'admission01.log']]
with snapshot(L) as s:
 guard=s.guard;pending={(r['original_elf_sha256'],r['mangled']):r for r in s.iter_records('pending')}
 for note in notes:
  key=(note['original_elf_sha256'],note['mangled']);assert pending[key]['behavior_validation_sha256']==sha(proof)
  matches=s.c.execute('SELECT t.* FROM catalog_tasks t JOIN catalog_symbols s ON s.anchor=t.anchor WHERE s.elf=? AND s.mangled=?',key).fetchall();assert len(matches)==1
  row=matches[0];new=dict(note,date=at,evidence=refs,resolution='Implementation accepted into current canonical Linux source port with bounded local native/provider and combined Linux integration proof. Declaration pending; previous research remarks retained. No whole-original ARM ABI or hardware claim.',resolution_or_retry_condition=note['retry_condition'])
  ops.append({'anchor':row['anchor'],'expected_revision':row['revision'],'notes':row['notes']+('\n' if row['notes'] else '')+json.dumps(new,sort_keys=True),'reason':'Append admitted implementation resolution and remaining exact-original declaration/domain requirements; preserve prior history and task state.'})
request={'request_id':'rolling200-02-integrated85-notes-20261106-01','actor':'Root','operations':ops};(O/'REQUEST.json').write_text(json.dumps(request,indent=2)+'\n');db=resolve_db(L)
(O/'DRY_RUN.json').write_text(json.dumps(operate(db,request,dry_run=True),indent=2)+'\n');backup=O/'registry-before-notes.sqlite'
with sqlite3.connect(Path(db).as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(backup) as target:source.backup(target)
(O/'BACKUP.json').write_text(json.dumps({'path':str(backup.relative_to(R)),'sha256':sha(backup),'database':str(db)},indent=2)+'\n')
result=operate(db,request,dry_run=False)
with snapshot(L) as s:assert s.guard==guard
result['readiness_guard_unchanged']=guard;(O/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print('Appended',len(notes),'exact-original admission resolutions; prior history retained.')
