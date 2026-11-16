"""Exact worker and canonical object/executable lifecycle replay entry point."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,time,sys
ROOT=pathlib.Path(__file__).resolve().parents[4];BASE=pathlib.Path(__file__).parent;TASK=BASE.name
SCRATCH=ROOT/'temp/recovery-work'/TASK;SCRATCH.mkdir(parents=True,exist_ok=True)
CANON=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis')
SUP=CANON/'temp/recovery-work/trial10x2-20261115/root-review/provider-supplement/PROVIDERS.json'
APP=SUP.with_name('ROOT_APPROVAL.json')
PROVIDER=json.loads(SUP.read_text());PACKET=ROOT/'temp/recovery-work/trial10x2-20261115/prepared01/packets'/TASK
REQ=json.loads((PACKET/'request.json').read_text());HDR='uc-library/include/presonus/mixer/BeastMixerComponent.hpp';SRC='uc-library/src/Presonus/Mixer/BeastMixerComponent.cpp';TEST=str(BASE.relative_to(ROOT)/'Replay.cpp')
FLAGS=['/usr/bin/c++','-std=c++17','-O0','-fno-rtti','-fno-lto','-fno-sized-deallocation','-ffunction-sections','-fdata-sections','-Wno-multichar','-UNDEBUG','-Iuc-library/include','-Ithird_party/ccl-framework']
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def run(argv,**kw):
 argv=list(map(str,argv));start=time.monotonic();p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(SCRATCH)},**kw);print(json.dumps(argv),flush=True)
 with (SCRATCH/'commands.jsonl').open('a') as f:f.write(json.dumps(dict(argv=argv,elapsed_seconds=time.monotonic()-start,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))+'\n')
 if p.returncode:print(p.stdout,p.stderr);p.check_returncode()
 return p.stdout

def providers():
 assert sha(SUP)=='0e4fc25d3383ae8609932b7e25c4d28bac3ee92b9435c11e8d63b61cd29f0c18'
 approval=json.loads(APP.read_text());assert approval['approved'] and approval['provider_manifest_sha256']==sha(SUP)
 for v in PROVIDER['archives'].values():assert sha(v['frozen_read_path'])==v['sha256']
 for name,v in PROVIDER['read_inputs'].items():
  assert sha(v['frozen_read_path'])==v['sha256']
 return {name:v['frozen_read_path'] for name,v in PROVIDER['archives'].items()}
def symbols(obj):
 out=run(['/usr/bin/nm','--defined-only',obj]);syms={s.split()[-1]:s.split()[0] for s in out.splitlines() if s.split()}
 for variant in ['D0','D1','D2']:assert '_ZN8Presonus5Mixer19BeastMixerComponent'+variant+'Ev' in syms
 assert syms['_ZN8Presonus5Mixer19BeastMixerComponentD1Ev']==syms['_ZN8Presonus5Mixer19BeastMixerComponentD2Ev']
 dis=run(['/usr/bin/objdump','-dr',obj]);d0=dis.split('<_ZN8Presonus5Mixer19BeastMixerComponentD0Ev>:')[1].split('\n\n')[0];assert '_ZdlPv' in d0 and '_ZdlPvm' not in d0
 return dict(symbols={k:v for k,v in syms.items() if 'BeastMixerComponentD' in k},d0_disassembly=d0)

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
 ap=argparse.ArgumentParser();ap.add_argument('mode',nargs='?',default='replay')
 for n in ['exe','object','integration','out','dependency-proof']:ap.add_argument('--'+n,type=pathlib.Path)
 ap.add_argument('--dependency-proof-sha256')
 a=ap.parse_args();exe=(a.exe or SCRATCH/'replay').resolve();obj=(a.object or SCRATCH/'production.o').resolve();libs=providers();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 if a.mode=='format':
  run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',HDR,SRC,TEST]);return
 if a.mode=='compile':
  run([*FLAGS,'-MMD','-MF',SCRATCH/'production.d','-c',SRC,'-o',obj]);run([*FLAGS,'-MMD','-MF',SCRATCH/'replay.d',TEST,obj,libs['libpresonus_rm_components.a'],libs['libpresonus_private_glibc29.a'],libs['libcorelib.a'],libs['libpresonus_core_allocator.a'],'-Wl,--gc-sections','-Wl,--wrap=_ZdlPv','-lz','-lpthread','-ldl','-lm','-o',exe]);return
 if a.mode=='symbols':print(json.dumps(symbols(obj),indent=2));return
 import native
 fresh=native.generate(exe)
 if a.mode=='fixture':(BASE/'fixtures.json').write_text(json.dumps(fresh,indent=2)+'\n');return
 fixture=json.loads((BASE/'fixtures.json').read_text());assert fresh==fixture
 if a.mode=='native':print(len(fixture['cases']),'original ARM range executions with actual canonical base/free RPC');return
 assert a.mode=='replay'
 for c in fixture['cases']:
  result=run([exe],input=f'{c["count"]}\n{c["variant"]}\nREPORT\nCLEAN\n').splitlines();assert result==['1',c['product_report'],c['cleanup']],(c,result)
 sym=symbols(obj)
 run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',HDR,SRC,TEST])
 deps={};closure_provenance={}
 canonical_binding=_current_canonical_binding(ROOT,a.object,a.exe,a.integration,SRC,('uc-library/src/Presonus/Mixer/ChannelComponent.cpp',))
 canonical=bool(a.exe or a.object or a.integration)
 if canonical_binding is not None:
  # Validate the supplied historical proof identity without claiming old hashes built current objects.
  assert a.dependency_proof and a.dependency_proof_sha256
  dp=a.dependency_proof.resolve();assert sha(dp)==a.dependency_proof_sha256
  historical=json.loads(dp.read_text());assert historical['task_id']==TASK and historical['functions'][0]['mangled']==REQ['targets'][0]['mangled'] and historical['original_elf_sha256']==REQ['targets'][0]['original_elf_sha256']
  deps=canonical_binding['binding']['files']
  closure_provenance={'kind':'actual_canonical_compile_dependencies','binding':canonical_binding['binding'],'historical_dependency_proof':{'path':str(dp),'sha256':sha(dp),'scope':'Retained original identity/history only, not current compile evidence'}}
 elif canonical or a.dependency_proof:
  assert a.dependency_proof and a.dependency_proof_sha256,'Explicit hash-bound --dependency-proof and --dependency-proof-sha256 required for canonical supplied binaries'
  dp=a.dependency_proof.resolve();assert sha(dp)==a.dependency_proof_sha256,'Historical dependency proof hash mismatch'
  historical=json.loads(dp.read_text());assert historical['task_id']==TASK
  assert historical['functions'][0]['mangled']==REQ['targets'][0]['mangled']
  assert historical['original_elf_sha256']==REQ['targets'][0]['original_elf_sha256']
  for name,digest in historical['source_hashes'].items():assert sha(ROOT/name)==digest,(name,'changed production source from original compile')
  deps=historical['captured_transitive_inputs'];assert isinstance(deps,dict) and deps,'Original compile dependency closure unavailable'
  for name,digest in deps.items():assert sha(ROOT/name)==digest,(name,'current dependency differs from original compile')
  closure_provenance=dict(kind='historical_worker_compile_dependencies_verified_against_current_and_frozen_sources',path=str(dp),sha256=sha(dp),historical_producer_inputs=historical['producer_inputs'],historical_executable=historical['executable'],historical_object=historical['object'],historical_compile_commands='Bound original proof preserves original producer identity; this replay does not claim recompilation of supplied canonical binaries.')
 else:
  for depfile in ['production.d','replay.d']:
   p=SCRATCH/depfile;assert p.is_file(),('Required compile dependency file unavailable; provide explicit hash-bound --dependency-proof',str(p))
   for name in p.read_text().replace('\\\n',' ').split(':',1)[1].split():
    f=pathlib.Path(name)
    if not f.is_absolute():f=ROOT/f
    f=f.resolve();assert f.is_file(),('Missing compiled dependency',str(f))
    deps[str(f.relative_to(ROOT)) if f.is_relative_to(ROOT) else str(f)]=sha(f)
  closure_provenance=dict(kind='fresh_local_compile_depfiles',depfiles=[dict(path=str(SCRATCH/f),sha256=sha(SCRATCH/f)) for f in ['production.d','replay.d']])
 required={'third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/public/corevector.h','uc-library/include/presonus/mixer/MixerComponent.hpp','uc-library/include/presonus/mixer/ChannelComponent.hpp',HDR,SRC}
 assert required <= deps.keys(),('Incomplete dependency closure',sorted(required-deps.keys()))
 snap=native.SNAP;captured=json.loads((snap.parent/'SNAPSHOT.json').read_text())['files'];bound=[]
 if canonical_binding is None:
  for name,digest in deps.items():
   if name in [HDR,SRC,TEST,'uc-library/tests/recovery/trial10x2_beast_d2/Replay.cpp']:continue
   assert name in captured,(name,'missing frozen transitive input')
   assert digest==captured[name]==sha(snap/name),(name,'changed frozen transitive input')
   bound.append(dict(path=name,sha256=digest,frozen_read_path=str(snap/name)))
 sources={p.removeprefix('uc-library/'):sha(ROOT/p) for p in [HDR,SRC]}
 providersources={p:sha(ROOT/p) for p in deps if p.startswith('third_party/')}
 limits=['Partial portable source lifecycle: original constructor, complete fields, inheritance/vptr layout, exception cleanup, ARM ABI and hardware remain unresolved. Tagged constructor is independent and receives live borrowed state/services.','Actual MixerComponent inline destructor owns only references and preserves state/services. It has no Core resource cleanup. Real borrowed Channel/Core parameter survives mixer destruction; harness separately destroys Channel and observes actual parameter kDestroyed, never credited as mixer cleanup.','Exact original ARM app instructions execute; original base body is an explicit real canonical host provider boundary and original delete boundary executes actual host unsized deallocation, not original ARM base/Core instructions. Native vptr stores and object-return identity are recorded, not reproduced as portable fields/ordinary return declaration.','App-service fixture methods abort if unexpectedly invoked; no app service method is invoked by the actual inline base destructor. Native object storage fill only 0/165/255, counts 1/2/7/32, valid lifetime, no allocation failure/concurrency/EH/hardware coverage.','Generated host D1/D2 alias separately identified but only assigned original D2/D0 receive credit. Canonical full integration and guarded readiness are Root owned.']
 t=REQ['targets'][0];entry=dict(original_elf_sha256=t['original_elf_sha256'],mangled=t['mangled'],sources=sources,repository_sources=providersources,domain=fixture['scope'],portable_ready=False,declaration_uncertainties=limits[:1],cpp_compiled=True,mangling_namespace_checked=True)
 proof=dict(version=1,task_id=TASK,functions=[entry],validation_domain=fixture['scope'],limitations=limits,original_elf_sha256=fixture['elf_sha256'],native_ranges=fixture['ranges'],case_count=len(fixture['cases']),arm_differential_passed=True,compiled_mangled_names_matched=True,behavior_comparison_passed=True,formatter_version=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler_version=run(['/usr/bin/c++','--version']).splitlines()[0],compiled_symbols=sym,producer_inputs={str(BASE.relative_to(ROOT)/x):sha(BASE/x) for x in ['Replay.cpp','native.py','check.py','fixtures.json']},source_hashes={p:sha(ROOT/p) for p in [HDR,SRC]},captured_transitive_inputs=deps,dependency_closure_provenance=closure_provenance,fresh_replay_argv=[sys.executable,*sys.argv],canonical_supplied_binaries=canonical,verified_frozen_transitive_inputs=bound,provider_sources=providersources,provider_archives={str(v['frozen_read_path']):v['sha256'] for v in PROVIDER['archives'].values()},provider_supplement={'path':str(SUP),'sha256':sha(SUP),'approval_path':str(APP),'approval_sha256':sha(APP)},fixture={'path':str(BASE.relative_to(ROOT)/'fixtures.json'),'sha256':sha(BASE/'fixtures.json')},executable={'path':str(exe),'sha256':sha(exe)},object={'path':str(obj),'sha256':sha(obj)},proposed_readiness=dict(canonical_binding_pending=True,ready=[],pending=[entry]),phase_timestamps=dict(replay_start=start,replay_end=datetime.datetime.now(datetime.timezone.utc).isoformat()),producer_session_id=os.environ.get('CODEX_THREAD_ID'))
 _attach_current_canonical(proof,canonical_binding)
 if a.integration:assert a.integration.is_file();proof['integration']={'path':str(a.integration),'sha256':sha(a.integration)};proof['proposed_readiness']['canonical_binding_pending']=False
 out=a.out or ROOT/'uc-library/candidates'/TASK/'worker-proof.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(proof,indent=2)+'\n');print(len(fixture['cases']),'exact native/provider/product lifecycle comparisons passed; proof',out)
if __name__=='__main__':main()
