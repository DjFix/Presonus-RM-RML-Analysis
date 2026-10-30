"""Snapshot immutable source-bound exports and coherent metadata for local mirroring."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys
import time

root=Path.cwd()
state=json.loads((root/'temp/recovery-work/batch-supervisor-state.json').read_text())
since=datetime.fromisoformat(state['started_utc']).timestamp()
library=root/'uc-library'
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+f'-{os.getpid()}'
snapshot=root/'temp/recovery-work/export-sync-snapshots'/stamp/'uc-library'
snapshot.mkdir(parents=True)
files=[];export_count=0;new_scope_checks={};counts={}
spec=importlib.util.spec_from_file_location('scope_classifier',library/'tools/extraction_verify_bounded.py')
classifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(classifier)
for role in ['client','server']:
 d=library/'recovered-all'/role
 source=json.loads((d/'manifest.json').read_text())['sha256']
 names=['decompilation.json','trusted-exports.json','analysis-input.json','run-state.json','deferred-scope.json']
 for attempt in range(100):
  metadata={name:(d/name).read_bytes() for name in names if (d/name).exists()}
  index=json.loads(metadata['trusted-exports.json']);entries=json.loads(metadata['decompilation.json']);run=json.loads(metadata['run-state.json'])
  recorded={str(e['address']) for e in entries if e['status']=='exported'}
  if recorded==set(index['exports']) and run['exports']==len(recorded) and run['processed']==len(entries):break
  time.sleep(.02)
 else:raise RuntimeError(f'{role}: could not obtain a coherent metadata snapshot')
 assert index['source_sha256']==source
 owners={}
 for symbol in json.loads((d/'symbols.json').read_text()):
  if symbol['kind']=='STT_FUNC':owners.setdefault(symbol['address'],set()).add(classifier.owning_namespace(symbol['mangled']))
 checked=0
 for addr,item in index['exports'].items():
  p=d/'pseudocode'/f'{int(addr):08x}.cpp.txt'
  mtime=p.stat().st_mtime
  if '--all-trusted' not in sys.argv and mtime<since:continue
  relative=p.relative_to(library);destination=snapshot/relative
  destination.parent.mkdir(parents=True,exist_ok=True)
  os.link(p,destination)
  data=destination.read_bytes();sha=hashlib.sha256(data).hexdigest()
  assert sha==item['sha256']
  if mtime>=since:
   assert not owners[int(addr)].intersection(state.get('deferred_namespaces',[])),f'deferred owner in new export: {p}'
   checked+=1
  files.append(dict(path=relative.as_posix(),sha256=sha,bytes=len(data),source_sha256=source))
  export_count+=1
 for name,data in metadata.items():
  relative=(d/name).relative_to(library);p=snapshot/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  files.append(dict(path=relative.as_posix(),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
 new_scope_checks[role]=checked
 counts[role]=dict(exports=len(recorded),failed=sum(e['status']=='failed' for e in entries),source_sha256=source)
selection='all-trusted' if '--all-trusted' in sys.argv else 'new-session-exports'
manifest=dict(captured_utc=datetime.now(timezone.utc).isoformat(),session=state['session'],selection=selection,
              snapshot_source=str(snapshot),counts=counts,
              deferred_namespaces=state.get('deferred_namespaces',[]),new_exports_with_scope_checked=new_scope_checks,
              supervisor_state=state['state'],live_snapshot=state['state'] not in ['complete','scope-complete','planned','aborted','stopped','partial'],
              disclaimer='Pseudocode is unvalidated analysis evidence. Metadata snapshot is coherent and immutable.',files=files)
e=Path(state['evidence'])
(e/('trusted-export-files.json' if '--all-trusted' in sys.argv else 'new-export-files.json')).write_text(json.dumps(manifest,indent=2)+'\n')
(root/'temp/recovery-work/export-sync.list').write_text(''.join(x['path']+'\n' for x in files))
(root/'temp/recovery-work/export-sync-session.json').write_text(json.dumps(dict(session=state['session'],selection=selection,evidence=state['evidence']),indent=2)+'\n')
pointer=root/'temp/recovery-work/export-sync-current'
temporary=pointer.with_name(pointer.name+f'.{os.getpid()}.new');temporary.symlink_to(snapshot.parent);temporary.replace(pointer)
print(json.dumps(dict(session=state['session'],state=state['state'],selection=selection,exports=export_count,counts=counts,
                     checked_new_owner_counts=new_scope_checks,bytes=sum(x['bytes'] for x in files))))
