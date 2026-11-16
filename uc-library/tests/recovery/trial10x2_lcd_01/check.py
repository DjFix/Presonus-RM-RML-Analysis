import argparse,hashlib,json,os,subprocess,datetime,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];os.chdir(ROOT)
BASE=Path('uc-library/tests/recovery/trial10x2_lcd_01');SCR=Path('temp/recovery-work/trial10x2-lcd-build');SCR.mkdir(parents=True,exist_ok=True)
SOURCES=['uc-library/src/Presonus/MainLCDComponent.cpp','uc-library/src/Presonus/PageComponent.cpp','uc-library/src/Presonus/MainLCDPageStack.cpp']
FLAGS=['-std=c++17','-O2','-DNDEBUG','-fno-lto','-frtti','-pthread','-Ulinux','-DCORE_USE_OPENSSL=1','-Iuc-library/include','-Ithird_party/ccl-framework']
EXECUTIONS=[]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(argv,**kw):
 argv=list(map(str,argv));print(json.dumps(argv),flush=True);start=time.monotonic();utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
 result=subprocess.run(argv,check=True,**kw)
 EXECUTIONS.append(dict(argv=argv,returncode=result.returncode,start_utc=utc,elapsed_seconds=time.monotonic()-start,stdout=result.stdout if isinstance(result.stdout,str) else None,stderr=result.stderr if isinstance(result.stderr,str) else None))
 return result

def _current_canonical_binding(root, obj, exe, integration, source, providers=()):
 from pathlib import Path
 if not integration or Path(integration).resolve() != (root/'uc-library/validation/integration.json').resolve():return None
 assert obj and exe, 'Canonical replay requires explicit actual object and executable'
 import importlib.util
 helper=root/'uc-library/tools/recovery/canonical_compile_bindings.py'
 spec=importlib.util.spec_from_file_location('actual_canonical_bindings',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 value=module.bind(root,Path(obj),source,exe_path=Path(exe),required_provider_sources=providers,required_archive_names=('libcorelib.a','libpresonus_core_allocator.a'))
 unexpected=[p for p in value['files'] if p.startswith('third_party/ccl-framework/') and not p.startswith('third_party/ccl-framework/core/')]
 assert not unexpected, ('Unexpected non-Core CCL inputs',unexpected)
 core={p:h for p,h in value['files'].items() if p.startswith('third_party/ccl-framework/core/')}
 library={p.removeprefix('uc-library/'):h for p,h in value['files'].items() if p.startswith('uc-library/')}
 assert core and source.removeprefix('uc-library/') in library, 'Actual canonical production/Core closure required'
 return {'binding':value,'sources':library,'repository_sources':core,'helper_sha256':hashlib.sha256(helper.read_bytes()).hexdigest()}

def _attach_current_canonical(proof, current):
 if current is None:return
 proof['actual_canonical_compile_binding']=current['binding']
 proof['canonical_producer_helper_sha256']=current['helper_sha256']
 proof['canonical_source_binding_scope']='Current actual Release object/depfile/link/archive inputs; historical frozen dependency expectations retained in original archived producer/proof, not refreshed or relabeled'
 proof['historical_provider_archives']=proof.get('provider_archives')
 proof['provider_archives']={v['path']:v['sha256'] for v in current['binding']['link']['archives']}
 proof['local_compile_defaults']=proof.get('compile_flags')
 proof['actual_canonical_compile_entries']=[x['compile_entry'] for x in current['binding']['objects']]
 proof['actual_canonical_sources']=current['sources']
 proof['actual_canonical_repository_sources']=current['repository_sources']
 for row in [*proof.get('proposed_readiness',{}).get('ready',[]),*proof.get('proposed_readiness',{}).get('pending',[])]:
  row.setdefault('sources',{}).update(current['sources'])
  repository=__import__('pathlib').Path(__file__).resolve().parents[4]
  for p,h in row['sources'].items():
   relative=__import__('pathlib').Path(p)
   assert not relative.is_absolute() and '..' not in relative.parts, ('Invalid library source binding',p)
   assert hashlib.sha256((repository/'uc-library'/relative).read_bytes()).hexdigest()==h, ('Retained library source binding changed outside actual closure',p)
  prior=row.setdefault('repository_sources',{})
  assert all(p.startswith('third_party/ccl-framework/core/') for p in prior), 'Unexpected prior non-Core repository dependency'
  repository=__import__('pathlib').Path(__file__).resolve().parents[4]
  for p,h in prior.items():assert hashlib.sha256((repository/p).read_bytes()).hexdigest()==h, ('Prior verified Core implementation changed',p)
  for p,h in current['repository_sources'].items():
   assert p not in prior or prior[p]==h, ('Conflicting verified Core source binding',p)
  prior.update(current['repository_sources'])

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','replay']);p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');p.add_argument('--providers');a=p.parse_args()
 exe=Path(a.exe or SCR/'replay');obj=Path(a.object or SCR/'MainLCDComponent.o')
 if a.mode=='format':
  run(['uc-library/.venv/bin/clang-format','--version']);run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES[:2],'uc-library/include/presonus/MainLCDComponent.hpp','uc-library/include/presonus/PageComponent.hpp',BASE/'Replay.cpp','uc-library/tests/recovery/trial10x2_lcd_02/Replay.cpp'])
 elif a.mode=='compile':
  objs=[]
  for src in [*SOURCES,str(BASE/'Replay.cpp')]:
   o=SCR/(Path(src).stem+'.o');run(['/usr/bin/c++',*FLAGS,'-MMD','-MF',str(o)+'.d','-c',src,'-o',o]);objs.append(o)
  provider=json.load(open(a.providers))
  for v in [*provider['archives'].values(),*provider['system_libraries']]:
   path=Path(v.get('frozen_read_path',v.get('path')));assert hashlib.sha256(path.read_bytes()).hexdigest()==v['sha256']
  run(['/usr/bin/c++',*objs,'-o',exe,*provider['default_link_order'][1:],'-pthread','-Wl,-rpath,/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu'])
 elif a.mode=='symbols':
  out=subprocess.check_output(['nm','--defined-only',obj],text=True)
  for s in ['_ZNK8Presonus16MainLCDComponent17getCurrentPageTagEv','_ZN8Presonus16MainLCDComponent13setupBackPageEv']:assert s in [x.split()[-1] for x in out.splitlines()]
  print('2 exact ELF mangled target symbols')
 else:
  d=json.loads((BASE/'fixtures.json').read_text());cases=d['cases'];inputs=''.join(' '.join(map(str,c['inputs']+[c['observed'][2]]))+'\n' for c in cases)
  r=run([exe.resolve()],input=inputs,text=True,capture_output=True);actual=[list(map(int,x.split())) for x in r.stdout.splitlines()];assert actual==[c['observed'] for c in cases]
  # Retain the worker's original native provenance, never relabel it as a
  # fresh native run. This invocation freshly checks the supplied product only.
  historical_path=Path('uc-library/candidates/trial10x2_lcd_01/worker-proof.json')
  historical=json.loads(historical_path.read_text())
  canonical_binding=_current_canonical_binding(ROOT,a.object,a.exe,a.integration,SOURCES[0],tuple(SOURCES[1:]))
  if canonical_binding is None:
   for path,digest in historical['source_hashes'].items():assert sha(path)==digest,path
  if canonical_binding is None:
   for path,digest in historical['repository_sources'].items():assert sha(path)==digest,path
  assert sha(BASE/'fixtures.json')==historical['fixture_sha256']
  assert sha(BASE/'native.py')==historical['oracle_producers'][str(BASE/'native.py')]
  provider_path=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/trial10x2-20261115/root-review/provider-supplement/PROVIDERS.json')
  assert sha(provider_path)=='0e4fc25d3383ae8609932b7e25c4d28bac3ee92b9435c11e8d63b61cd29f0c18'
  provider=json.loads(provider_path.read_text())
  for value in [*provider['archives'].values(),*provider['system_libraries']]:
   path=value.get('frozen_read_path',value.get('path'));assert sha(path)==value['sha256'],path
  format_paths=[*SOURCES[:2],'uc-library/include/presonus/MainLCDComponent.hpp','uc-library/include/presonus/PageComponent.hpp',str(BASE/'Replay.cpp'),'uc-library/tests/recovery/trial10x2_lcd_02/Replay.cpp']
  fmt=run(['uc-library/.venv/bin/clang-format','--version'],text=True,capture_output=True).stdout.strip()
  run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*format_paths],text=True,capture_output=True)
  symbols=run(['nm','--defined-only',obj],text=True,capture_output=True).stdout
  names=['_ZNK8Presonus16MainLCDComponent17getCurrentPageTagEv','_ZN8Presonus16MainLCDComponent13setupBackPageEv']
  for name in names:assert name in [x.split()[-1] for x in symbols.splitlines()]
  sources={x:sha('uc-library/'+x) for x in historical['proposed_readiness']['pending'][0]['sources']}
  for lane in ['trial10x2_lcd_01','trial10x2_lcd_02']:
   for name in ['Replay.cpp','check.py','native.py','fixtures.json']:
    path='tests/recovery/'+lane+'/'+name;sources[path]=sha('uc-library/'+path)
  pending=[]
  originals=[]
  for lane in ['trial10x2_lcd_01','trial10x2_lcd_02']:
   request=json.loads(Path('temp/recovery-work/trial10x2-20261115/prepared01/packets',lane,'request.json').read_text())
   target=request['targets'][0];originals.append(target)
   pending.append(dict(original_elf_sha256=target['original_elf_sha256'],mangled=target['mangled'],sources=sources,repository_sources=historical['repository_sources'],domain=historical['validation_domain'],portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,declaration_uncertainties=historical['limitations']))
  proof=dict(version=1,success=True,behavior_success=True,tests_passed=True,portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,compiled_original_mangled_names_matched=True,mangled_names=names,functions=[dict(original_elf_sha256=x['original_elf_sha256'],mangled=x['mangled']) for x in originals],originals=originals,cases=len(cases),domain=historical['validation_domain'],validation_domain=historical['validation_domain'],limitations=historical['limitations'],source_hashes={x:sha(x) for x in historical['source_hashes']},sources=sources,repository_sources=historical['repository_sources'],provider_supplement=historical['provider_supplement'],provider_archives=provider['archives'],compiled_transitive_snapshot_bindings=historical['compiled_transitive_snapshot_bindings'],formatter=fmt,format_check_passed=True,format_files={x:sha(x) for x in format_paths},native_ranges=d['ranges'],native_case_count=len(cases),native_observation_provenance=dict(fresh_native_execution=False,historical_worker_proof=dict(path=str(historical_path),sha256=sha(historical_path)),original_worker_end=historical['timing']['end'],oracle_producers=historical['oracle_producers'],fixture=dict(path=str(BASE/'fixtures.json'),sha256=sha(BASE/'fixtures.json')),scope='Recorded original ARM observations retained; fresh canonical product execution compared with those observations; pushBackPage remains intercepted original application boundary.'),oracle_producers=historical['oracle_producers'],fixture_sha256=sha(BASE/'fixtures.json'),executable=dict(path=str(exe.resolve()),sha256=sha(exe)),object=dict(path=str(obj.resolve()),sha256=sha(obj)),integration=dict(path=str(Path(a.integration).resolve()),sha256=sha(a.integration)) if a.integration else None,canonical_binding_pending=not bool(a.integration),proposed_readiness=dict(canonical_binding_pending=not bool(a.integration),ready=[],pending=pending),checks=EXECUTIONS,producer=dict(path=str(BASE/'check.py'),sha256=sha(BASE/'check.py')),executed_argv=[sys.executable,*sys.argv],fresh_product_execution=True,proof_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
  _attach_current_canonical(proof,canonical_binding)
  if a.out:
   Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
  print(json.dumps(proof))
if __name__=='__main__':main()
