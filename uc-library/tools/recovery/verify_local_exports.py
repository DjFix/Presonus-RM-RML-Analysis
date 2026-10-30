"""Verify the locally mirrored source-bound pseudocode and snapshot metadata."""
from pathlib import Path
import hashlib,json,sys
base=Path('uc-library')
e=Path(sys.argv[1]);manifest_name=sys.argv[2] if len(sys.argv)>2 else 'new-export-files.json'
snapshot=json.loads((e/manifest_name).read_text())
for f in snapshot['files']:
 assert hashlib.sha256((base/f['path']).read_bytes()).hexdigest()==f['sha256'],f['path']
counts={}
for role in ['client','server']:
 d=base/'recovered-all'/role
 index=json.loads((d/'trusted-exports.json').read_text())
 entries=json.loads((d/'decompilation.json').read_text())
 for addr,f in index['exports'].items():
  p=d/'pseudocode'/f'{int(addr):08x}.cpp.txt'
  assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'],p
 assert len(index['exports'])==sum(r['status']=='exported' for r in entries)
 counts[role]=dict(exports=len(index['exports']),failed=sum(r['status']=='failed' for r in entries),source_sha256=index['source_sha256'])
report={'counts':counts,'new_scope_checks':snapshot['new_exports_with_scope_checked'],
        'deferred_namespaces':snapshot.get('deferred_namespaces',[]),'all_snapshot_and_trusted_hashes_match':True}
name='local-export-verification-'+str(counts['client']['exports'])+'-'+str(counts['server']['exports'])+'.json'
(e/name).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
