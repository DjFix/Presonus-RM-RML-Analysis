"""Complete current registry/source/proof/format/Linux mirror audit after relocation."""
from pathlib import Path
import json,sys,time
R=Path.cwd();L=R/'uc-library';E=R/'evidence/recovery/2026-11-05/canonical-organization-bulk01';sys.path[:0]=[str(L/'tools'),str(L/'tools/registry')]
import adapter
from merge_readiness import ValidationCache,repository_sources_match
c=ValidationCache();start=time.monotonic();integration=c.read_json(L/'validation/integration.json');assert integration==c.read_json(L/'validation/integration-linux.json');assert integration['platform']=='linux' and integration['ctest_passed'] and integration['test_suites']==453
for p,h in integration['files'].items():assert c.sha(L/p)==h,p
for p,h in integration['logs'].items():assert c.sha(R/p)==h,p
assert c.sha(R/integration['test_log'])==integration['test_log_sha256'];fmt=c.read_json(L/'validation/formatting.json');seen=set();identities=set();found=set();count=0;counts={}
affected=c.read_json(E/'AFFECTED.json');targets={(x['entry']['original_elf_sha256'],x['entry']['mangled']) for x in affected['affected']}
with adapter.snapshot(L) as registry:
 for status in ['ready','pending']:
  rows=registry.load_registry(status)['functions'];counts[status]=len(rows)
  for row in rows:
   key=(row['original_elf_sha256'],row['mangled']);assert key not in identities;identities.add(key)
   assert c.sha(L/row['validation'])==row['validation_sha256'];assert repository_sources_match(L,row,c)
   if id(row['sources']) not in seen:
    for p,h in row['sources'].items():
     assert c.sha(L/p)==h,p
     if Path(p).suffix in ['.cpp','.hpp','.h']:assert fmt['files'].get(p)==h,p
    seen.add(id(row['sources']))
   if key in targets:
    expected_status=next(x['status'] for x in affected['affected'] if (x['entry']['original_elf_sha256'],x['entry']['mangled'])==key);assert status==expected_status;assert row['validation']=='validation/canonical-organization-bulk01/'+status+('.compat-proof.json' if status=='ready' else '.compat.fragment.json');assert not (set(row['sources'])&set(affected['mapping']));found.add(key)
   count+=1
 assert counts==affected['counts'] and found==targets
 guard=registry.guard
c.unchanged();(E/'MIRROR01.json').write_text(json.dumps({'passed':True,'counts':counts,'records':count,'rebound_existing_identities':len(found),'new_reconstruction':0,'promotions':0,'guard':guard,'seconds':time.monotonic()-start,'scope':'Full canonical current proof/source/Core/format and Linux compatibility mirror; no old entries silently dropped.'},indent=2)+'\n');print(counts,'all records and relocated identities verified')
