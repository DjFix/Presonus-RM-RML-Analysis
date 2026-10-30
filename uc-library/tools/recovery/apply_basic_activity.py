"""Guarded BasicConnection/Activity integration; no readiness admission."""
import argparse
import hashlib
import json
from pathlib import Path
from apply_queue_gate_geq import once, counts

r=Path.cwd(); lib=r/'uc-library'; out=r/'evidence/recovery/2026-10-28/basic-activity-batch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
own=lib/'candidates/uc-basic-connection-lifecycle'
assert sha(own/'CONTROLLED-APPLY.json')=='bac5eb858bc1ec3ad0d59b21f0a6dec26298813a96d2e6153cfb8d64e1ba2fe1'
assert sha(own/'CMAKE-RECIPE.json')=='4e681bf6a51e4571b58b44c1293146bc33ab5d2a1ee36063b867d6bb981a6a49'
m=read(own/'CONTROLLED-APPLY.json'); recipe=read(own/'CMAKE-RECIPE.json')
proof=r/m['schema_proof']; assert sha(proof)==m['schema_proof_sha256'] and read(proof)['passed']
for n,h in read(proof)['guard_after'].items(): assert sha(lib/n)==h,n
products={}; previous={}; origins={}
for row in m['products']:
 s=lib/row['source']; t=lib/row['target']; old=row['previous_sha256']
 assert s.resolve().is_relative_to(lib.resolve()) and t.resolve().is_relative_to(lib.resolve()) and not t.is_symlink()
 assert sha(s)==row['sha256']; assert (not t.exists()) if old is None else sha(t)==old
 products[row['target']]=s.read_bytes();previous[row['target']]=old;origins[row['target']]=row['source']
groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text(); assert counts(groups)==[114,46,63]
for n in recipe['production_new_common_cpp']:
 assert n not in groups; groups=once(groups,'set(PRESONUS_common_SOURCES\n','set(PRESONUS_common_SOURCES\n  '+n+'\n')
assert counts(groups)==[117,46,63]
cmake=(lib/'CMakeLists.txt').read_text()
for n in recipe['new_public_headers']:
 h=n.removeprefix('include/'); assert h not in groups and h not in cmake
 groups=once(groups,'set(PRESONUS_PUBLIC_HEADERS\n','set(PRESONUS_PUBLIC_HEADERS\n  '+h+'\n')
 cmake=once(cmake,'set(PRESONUS_UC_PUBLIC_HEADERS\n','set(PRESONUS_UC_PUBLIC_HEADERS\n  '+h+'\n')
tests=[]
for t,cmd in zip(recipe['test_targets'],recipe['CTest_commands']):
 n=t['target']; assert 'add_executable('+n not in cmake
 tests += [f"  add_executable({n} {t['source']})",f'  target_link_libraries({n} PRIVATE presonus::uc)',f'  target_compile_options({n} PRIVATE -UNDEBUG)',f"  target_link_options({n} PRIVATE "+' '.join('-Wl,--wrap='+x for x in t['link_wraps'])+')',f"  add_test(NAME {n} COMMAND "+' '.join(cmd)+')']
marker='  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)'; cmake=once(cmake,marker,'\n'.join(tests)+'\n'+marker)
for n,s in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:
 products[n]=s.encode();previous[n]=sha(lib/n);origins[n]='fixed Basic/Activity recipe'
changed={n for n,h in previous.items() if h and hashlib.sha256(products[n]).hexdigest()!=h}
impact={k:[x for x in read(lib/'validation'/f)['functions'] if changed.intersection(x['sources'])] for k,f in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
plan={'products':len(products),'partitions':counts(groups),'expected_suites':270,'expected_headers':154,'affected_ready':len(impact['ready']),'affected_pending':len(impact['pending']),'previous':previous,'result_hashes':{n:hashlib.sha256(b).hexdigest() for n,b in products.items()},'origins':origins}
out.mkdir(parents=True,exist_ok=True)
if not a.apply:
 (out/'application-plan.json').write_text(json.dumps(plan,indent=2)+'\n');(out/'planned-source-impact.json').write_text(json.dumps(impact,indent=2)+'\n')
else:
 assert not (out/'application.json').exists() and read(out/'application-plan.json')==plan
 for n,b in products.items():
  target=lib/n
  if target.exists():
   backup=out/'before'/n;backup.parent.mkdir(parents=True,exist_ok=True)
   if backup.exists(): assert backup.read_bytes()==target.read_bytes()
   else: backup.write_bytes(target.read_bytes())
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
 (out/'application.json').write_text(json.dumps(plan,indent=2)+'\n');(out/'affected-source-closure.json').write_text(json.dumps(impact,indent=2)+'\n')
 paths=sorted(n for n in products if Path(n).suffix in ('.cpp','.h','.hpp'))
 (lib/'validation/format-basic-activity-paths.json').write_text(json.dumps(paths,indent=2)+'\n')
 additions=sorted(set(products)|{'tools/recovery/apply_basic_activity.py','candidates/uc-basic-connection-lifecycle/CONTROLLED-APPLY.json','candidates/uc-basic-connection-lifecycle/CMAKE-RECIPE.json'})
 (lib/'validation/integration-basic-activity-additions.json').write_text(json.dumps(additions,indent=2)+'\n')
print(json.dumps({k:v for k,v in plan.items() if k not in ('previous','result_hashes','origins')}))
