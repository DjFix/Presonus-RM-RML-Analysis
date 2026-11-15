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
  for path,digest in historical['source_hashes'].items():assert sha(path)==digest,path
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
  if a.out:
   Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
  print(json.dumps(proof))
if __name__=='__main__':main()
