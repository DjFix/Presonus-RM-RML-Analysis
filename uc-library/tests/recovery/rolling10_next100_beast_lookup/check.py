"""Fresh original-ELF execution, actual CCL consumers, full metadata comparison."""
import argparse,datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
import native
ROOT=Path(__file__).resolve().parents[4]
TASK='rolling10_next100_beast_lookup'
KEY='beast'
TEST=Path('uc-library/tests/recovery')/TASK
SCRATCH=Path('temp/recovery-work')/TASK
PROD=['uc-library/src/Presonus/Panel/'+s+'.cpp' for s in ['WolverinePanelRegistrar','BeastPanelRegistrar','PanelParameterTables']]
HEAD=['uc-library/include/presonus/panel/'+s+'.hpp' for s in ['WolverinePanelRegistrar','BeastPanelRegistrar','PanelParameterTables']]
SRC=HEAD+PROD+[str(TEST/'Replay.cpp')]
FLAGS=['-std=c++17','-O2','-fno-lto','-UNDEBUG','-Ulinux','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Iuc-library/include','-Ithird_party/ccl-framework']
SDK=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib')
LIBS=[SDK/'libcorelib.a',SDK/'libpresonus_core_allocator.a']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv):
 r=subprocess.run(list(map(str,argv)),cwd=ROOT,env={**os.environ,'TMPDIR':str(ROOT/SCRATCH)},text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 if r.returncode: print(r.stdout);raise RuntimeError((argv,r.returncode))
 return r.stdout
def encoded(s):return '-' if s is None else 'x'+s.encode('ascii').hex()
def expected(table,count):
 return ''.join(' '.join(map(str,[r['type'],r['tag'],r['name32'],*r['float_bits'],r['flags'],*[encoded(s) for s in r['strings']]]))+'\n' for r in table['records'][:count])
COMPAT_BINDINGS={'uc-library/validation/generation06-first5-reproof01/beast-existing-reproof.json': 'f87ec4da85072d27b9fad2eeaaeae034f618db840f9fd9384f7f55c806c96824', 'uc-library/candidates/native-live-trial-02-beast/fixture.json': 'a0a492aca8ea5f477c7e0507860102fc8bb712d695a69b529fc0e9bf1110cd38', 'uc-library/candidates/native-live-trial-02-beast/validate.py': 'e0b9bc41a59d0c9980792bb613b4874fabb9f3f063631983d7263f206ca8084c', 'uc-library/tests/recovery/rolling10_next100_wolverine_counts/fixtures.json': '608732ed70bfbbe4a829168da620eedf61d7d5dcb9a4316de3ba42860f147ecc', 'uc-library/tests/recovery/rolling10_next100_wolverine_counts/native.py': '08c0d8a3f1fddb5169a731fdefcfb9de7c82668c434f792fbc4d56b23017230b', 'uc-library/tests/recovery/rolling10_next100_wolverine_counts/check.py': '20fe6b0108dd1c3fc1f6c9ec5f33232d15547c3cbed83e83d06951f89d281c21', 'uc-library/tests/recovery/rolling10_next100_wolverine_counts/Replay.cpp': 'b8df6db7b825934cffcdf36b343cb2cca88c10c30e40aec75f5fdb4b3265cd39', 'uc-library/validation/rolling10x10-cohort03-new-r2/rolling10_next100_wolverine_counts-canonical-worker-proof.json': 'afee963641decb90fc7e5c4c06da3dd57929d38314be0466d782406ef16d3ed8', 'uc-library/tests/recovery/rolling10_next100_beast_counts/fixtures.json': 'e1b766eba310c59c139a4c8e68bfbf8e33ebfe337acd382f4ebcec3e315d48c9', 'uc-library/tests/recovery/rolling10_next100_beast_counts/native.py': '939650ca089168aec17bb2658f9a24b5be51bee2aaa6284cc4e62553ed266196', 'uc-library/tests/recovery/rolling10_next100_beast_counts/check.py': 'e8a22ff220c9440fb325bb850e4b756966d6182225c4b7ba3c4da131cc09c755', 'uc-library/tests/recovery/rolling10_next100_beast_counts/Replay.cpp': 'aa3c5e1383113e75f4146ad11b8d85a0d015646734cf9bcceac4e76d4610f054', 'uc-library/validation/rolling10x10-cohort03-new-r2/rolling10_next100_beast_counts-canonical-worker-proof.json': '196dad7c8c0b0f314025be5b568b1078ac64eace4943e954063e45942244a830'}
def compatibility(exe):
 canonical=Path('/home/rs/projects/opencs/ai-line-analysis')
 for path,digest in COMPAT_BINDINGS.items():assert sha(canonical/path)==digest
 prior=json.loads((canonical/'uc-library/validation/generation06-first5-reproof01/beast-existing-reproof.json').read_text())
 assert prior['historical_fixture']['sha256']==COMPAT_BINDINGS[prior['historical_fixture']['path']]
 cases=json.loads((canonical/prior['historical_fixture']['path']).read_text())['cases']
 for c in cases:
  observed=run([exe,'tags',c['group'],c['initial_count']]).split()
  assert list(map(int,observed))==[int(c['native_r0']!=0),c['count'],*c['tag_words_u32']]
 counts={}
 for key in ['wolverine','beast']:
  base='uc-library/tests/recovery/rolling10_next100_'+key+'_counts/'
  proof=json.loads((canonical/('uc-library/validation/rolling10x10-cohort03-new-r2/rolling10_next100_'+key+'_counts-canonical-worker-proof.json')).read_text())
  if key=='beast':
   assert proof['fixture']['sha256']==COMPAT_BINDINGS[base+'fixtures.json']
   assert proof['oracle_producer_sha256']==COMPAT_BINDINGS[base+'native.py']
  else:
   assert proof['source_sha256'][base+'fixtures.json']==COMPAT_BINDINGS[base+'fixtures.json']
   assert proof['source_sha256'][base+'native.py']==COMPAT_BINDINGS[base+'native.py']
  fixture=json.loads((canonical/(base+'fixtures.json')).read_text())
  groups=[int(c['stdin']) if key=='wolverine' else c['group'] for c in fixture['cases']]
  want=[int(c['stdout']) if key=='wolverine' else c['result'] for c in fixture['cases']]
  result=subprocess.run([str(exe),'counts',key],input=''.join(str(g)+'\n' for g in groups),text=True,capture_output=True,check=True)
  assert list(map(int,result.stdout.split()))==want
  counts[key]=len(groups)
 return {'historical_getTags_cases':len(cases),'historical_count_cases':counts,'bindings':COMPAT_BINDINGS,'scope':'Read-only original fixtures/producers bound to prior canonical proof; current source executable replay, no historical producer rewritten or relabeled.'}
def main():
 p=argparse.ArgumentParser();p.add_argument('kind',nargs='?',choices=['format','compile','symbols','replay'],default='replay');p.add_argument('--exe',type=Path);p.add_argument('--object',type=Path);p.add_argument('--integration',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();os.chdir(ROOT);(ROOT/SCRATCH).mkdir(parents=True,exist_ok=True)
 obj=a.object or SCRATCH/(KEY+'.o'); exe=(a.exe or SCRATCH/'replay').resolve()
 if a.kind=='compile':
  objects=[]
  for source in PROD:
   o=obj if KEY.capitalize()+'PanelRegistrar.cpp' in source else SCRATCH/(Path(source).stem+'.o');run(['/usr/bin/c++',*FLAGS,'-c',source,'-o',o]);objects.append(o)
  run(['/usr/bin/c++',*FLAGS,TEST/'Replay.cpp',*objects,*LIBS,'/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto','-ldl','-lm','-o',exe]);print('compiled actual source + SDK providers');return
 fmt=['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SRC]
 if a.kind=='format':run(fmt);print('format passed');return
 mangled='_ZN8Presonus5Panel'+('23Wolverine' if KEY=='wolverine' else '19Beast')+'PanelRegistrar25getParamInfoListFromGroupEi'
 symbols=run(['nm','--defined-only',obj]);assert mangled in [r.split()[-1] for r in symbols.splitlines() if r.split()]
 if a.kind=='symbols':print(symbols);return
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();run(fmt)
 fresh=json.loads(json.dumps(native.collect())); fixture=json.loads((ROOT/TEST/'fixtures.json').read_text());assert fresh==fixture
 byaddr={t['address']:t for t in fresh['tables']};observations=[];seen=set()
 for l,c in zip(fresh['observations'][KEY+'_lookup'],fresh['observations'][KEY+'_counts']):
  assert l['group']==c['group'];addr=l['result'];count=c['result'];assert bool(addr)==bool(count)
  if addr:assert count<=len(byaddr[addr]['records']);seen.add(addr)
  result=run([exe,KEY,l['group'],addr,count]);want=expected(byaddr[addr],count) if addr else '';assert result==want,(KEY,l['group'],result[:100],want[:100]);observations.append({'group':l['group'],'original_pointer':addr,'original_count':count,'typed_metadata_stdout_sha256':hashlib.sha256(result.encode()).hexdigest(),'consumer_lifecycle_repetitions':2})
 compat=compatibility(exe)
 sources={str(Path(s).relative_to('uc-library')):sha(s) for s in SRC}
 deps={str(Path('third_party/ccl-framework/core/portable')/s):sha(Path('third_party/ccl-framework/core/portable')/s) for s in ['coreparaminfo.h','coreparams.h','coreparams.cpp','corecomponent.h']}
 domain=fresh['domain']+' All selected original tables fully decoded independently; actual typed metadata compared field-for-field (name32, five float bitpatterns, strings/nulls/type/tag/flags). Actual pinned ParamList.add(infos,nativecount,false), two construction/destruction/reuse cycles per group; NumericParam identity/default/range/flags/set(min,max)/reset, borrowed static name pointer. No original Core instructions executed.'
 limits=['Original ordinary return type and pointee const qualification unresolved; provisional const Core::Portable::ParamInfo* source port only.','Original class inheritance/layout/static membership/ARM ABI and hardware behavior unresolved.','84-byte original records converted field-by-field to actual pinned host declarations; no reinterpretation or original layout equivalence.','onoff unit preserved exactly; original formatter equivalence unresolved (no fake formatter).','CCL source-provider numeric/factory/lifecycle behavior is intentional source port, not original Core binary equivalence.']
 entry={'original_elf_sha256':native.ELF_SHA,'mangled':mangled,'original_address':fresh['ranges'][KEY+'_lookup']['target']['address'],'portable_ready':False,'cpp_compiled':True,'mangling_namespace_checked':True,'original_function_verified':False,'hardware_verified':False,'canonical_binding_pending':not bool(a.integration),'sources':sources,'repository_sources':deps,'domain':domain,'declaration_uncertainties':limits[:2]}
 proof={'version':1,'task_id':TASK,'session_id':'/root/rolling10_panel','started_utc':started,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'canonical_binding_pending':not bool(a.integration),'portable_ready':False,'cpp_compiled':True,'mangling_namespace_checked':True,'format_check_passed':True,'behavior_validation_passed':True,'sources':sources,'repository_sources':deps,'domain':domain,'proposed_readiness':{'ready':[],'pending':[entry]},'original_native':{'elf_sha256':fresh['elf_sha256'],'elf_path':str(native.ELF),'ranges':fresh['ranges'],'executions':sum(len(v) for v in fresh['observations'].values()),'fixture_sha256':sha(TEST/'fixtures.json'),'observations':fresh['observations']},'selected_table_ranges':[t for t in fresh['tables'] if t['address'] in seen],'cases':observations,'prior_compatibility':compat,'limitations':limits,'producers':{str(TEST/s):sha(TEST/s) for s in ['native.py','check.py']},'sdk_archives':{str(s):sha(s) for s in LIBS},'executable':{'path':str(exe),'sha256':sha(exe)},'object':{'path':str(obj),'sha256':sha(obj)},'symbols':symbols,'versions':{'compiler':run(['/usr/bin/c++','--version']).splitlines()[0],'formatter':run(['uc-library/.venv/bin/clang-format','--version']).strip()}}
 if a.integration:proof['integration']={'path':str(a.integration),'sha256':sha(a.integration)}
 if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(proof,indent=2)+'\n')
 print('PASS',TASK,len(observations),'group cases',len(seen),'original table identities, fresh native/real CCL lifecycles/metadata')
if __name__=='__main__':main()
