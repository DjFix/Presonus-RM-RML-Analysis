import argparse,datetime,hashlib,importlib.util,json,os,pathlib,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[4]
TASK='rolling10_next100_scenes_c2'
SOURCE='uc-library/src/Presonus/Panel/ScenesComponent.cpp'
HEADER='uc-library/include/presonus/panel/ScenesComponent.hpp'
TEST='uc-library/tests/recovery/'+TASK
PACKET='temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/packets/'+TASK
OWNED=[SOURCE,HEADER,TEST+'/Replay.cpp',TEST+'/native.py',TEST+'/check.py',TEST+'/fixtures.json']
FLAGS=['c++','-std=c++17','-O2','-fno-access-control','-UNDEBUG','-fno-lto','-fno-rtti','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework','-Wno-multichar','-Ulinux']
CANON=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
ARCHIVES=[CANON/'upstream-core/sdk/lib/libcorelib.a',CANON/'upstream-core/sdk/lib/libpresonus_core_allocator.a']
CCL=['third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/coreparaminfo.h','third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/public/corevector.h']
SUPPLEMENT=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/root-review/provider-supplements/presets-ROOT_ADDENDUM.json')
APP_SOURCES=['uc-library/src/Presonus/Panel/FrontPanelLifecycle.cpp', 'uc-library/src/Presonus/Panel/PanelComponentLifecycle.cpp', 'uc-library/src/Presonus/Panel/PanelComponent.cpp', 'uc-library/src/Presonus/DelayTimer.cpp', 'uc-library/src/Presonus/DICE/PacketClockGateway.cpp', 'uc-library/src/Presonus/Panel/PresetComponent.cpp', 'uc-library/src/Presonus/Panel/PresetComponentSlotPaths.cpp', 'uc-library/src/Presonus/Panel/PresetNameManager.cpp', 'uc-library/src/Presonus/Panel/PresetNameCache.cpp', 'uc-library/src/Presonus/Panel/FxPresetComponent.cpp', 'uc-library/src/Presonus/Panel/FXPresetRecallComponent.cpp', 'uc-library/src/Presonus/Mixer/MixerComponentBase.cpp']
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

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
 proof.setdefault('historical_provider_archives',proof.get('provider_archives'))
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
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='all',choices=['all','format','compile','symbols','replay']);p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');p.add_argument('--provider-supplement');p.add_argument('--provider-supplement-sha256');a=p.parse_args()
 if bool(a.provider_supplement)!=bool(a.provider_supplement_sha256):p.error('--provider-supplement and --provider-supplement-sha256 must be supplied together')
 supplement_path=pathlib.Path(a.provider_supplement).resolve() if a.provider_supplement else SUPPLEMENT
 supplement_sha256=a.provider_supplement_sha256 if a.provider_supplement else '25456e6440fe7c82fde48b1e6bf10bc9b41bf234f122381800b6edc127c48b5c'
 work=ROOT/'temp/recovery-work'/TASK;work.mkdir(parents=True,exist_ok=True);exe=pathlib.Path(a.exe).resolve() if a.exe else work/'replay';obj=pathlib.Path(a.object).resolve() if a.object else work/'production.o';checks=[];start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 def run(argv,input=None):
  argv=list(map(str,argv));t=time.monotonic();r=subprocess.run(argv,cwd=ROOT,input=input,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(work)});checks.append(dict(argv=argv,returncode=r.returncode,seconds=time.monotonic()-t,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,(argv,r.stdout,r.stderr);return r.stdout
 import sys
 sys.path.insert(0,str(ROOT/'uc-library/tools/recovery'))
 from pinned_codec_replay_binding import validate_archives
 provider_binding=validate_archives(ROOT,a.exe,a.integration,{str(ARCHIVES[0]):'3c4f0825acb529fda135587b7ff5cb92ca0100bb417a20c034d3fdef80a93e0c',str(ARCHIVES[1]):'69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d'})
 supplement=json.loads(supplement_path.read_text());assert sha(supplement_path)==supplement_sha256
 canonical_binding=_current_canonical_binding(ROOT,a.object,a.exe,a.integration,SOURCE,APP_SOURCES)
 if canonical_binding is None:
  for path,info in supplement['read_inputs'].items():assert sha(ROOT/path)==info['sha256'],path
 if a.mode in ('all','format'):run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',SOURCE,HEADER,TEST+'/Replay.cpp'])
 if a.mode in ('all','compile') and not a.exe:
  run([*FLAGS,'-c',SOURCE,'-o',obj]);run([*FLAGS,TEST+'/Replay.cpp',*APP_SOURCES,obj,'-Wl,--gc-sections','-Wl,--start-group',*ARCHIVES,'-Wl,--end-group','-lpthread','-ldl','-lz','-o',exe])
 req=json.loads((ROOT/PACKET/'request.json').read_text());name=req['targets'][0]['mangled']
 if a.mode in ('all','symbols','replay'):
  symbols={x.split()[-1] for x in run(['nm','--defined-only',obj]).splitlines() if x.split()};assert name in symbols
 if a.mode in ('all','replay'):
  spec=importlib.util.spec_from_file_location('native_oracle',ROOT/TEST/'native.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native);fixture=json.loads((ROOT/TEST/'fixtures.json').read_text());assert native.generate(exe)==fixture
  for present in [0,1]:
   assert run([exe,'scenes',str(present)])==fixture['providers'][str(present)]
   assert run([exe,'legacy',str(present)])=='legacy:preserved\n'
  domain=f"{len(fixture['cases'])} exact original100B constructor executions with varied this/panel/mixer identities, base-before-panel ordering, exact3literal strings, derived writes and return-this observation. Separate actual provided PresetComponent and real CCL parameter factory/formatter observations compared with Scenes, formatter present/absent, old constructor association and zero-slot store branch preserved. Normal actual base cleanup separately observes real manager/cache lookup with EFL calls after construction."
  limits=[fixture['limitations'],'Existing store/destructor bodies retained; new bounded regression exercises default zero-slot early return and normal cleanup only, without claiming fresh nonzero store/native destructor validation.']
  sources={str(pathlib.Path(x).relative_to('uc-library')):sha(ROOT/x) for x in OWNED}
  sources.update({str(pathlib.Path(x).relative_to('uc-library')):sha(ROOT/x) for x in supplement['read_inputs'] if x.startswith('uc-library/')})
  repository={x:sha(ROOT/x) for x in CCL}
  repository.update({x:sha(ROOT/x) for x in supplement['read_inputs'] if x.startswith('third_party/')})
  target=req['targets'][0];pending=dict(original_elf_sha256=target['original_elf_sha256'],mangled=name,sources=sources,repository_sources=repository,domain=domain,portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,declaration_uncertainties=limits)
  proof=dict(version=1,provider_supplement=dict(path=str(supplement_path),sha256=sha(supplement_path)),task_id=TASK,originals=req['targets'],source_hashes=sources,repository_sources=repository,provider_archives=provider_binding["archives"],historical_provider_archives=provider_binding["historical"],pinned_codec_provider_binding=provider_binding,native_ranges=[fixture['range']],literal_arguments=fixture['literal_arguments'],native_case_count=len(fixture['cases']),validation_domain=domain,limitations=limits,checks=checks,formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler=run(['c++','--version']).splitlines()[0],unicorn=__import__('unicorn').__version__,object=dict(path=str(obj),sha256=sha(obj)),executable=dict(path=str(exe),sha256=sha(exe)),integration=dict(path=a.integration,sha256=sha(a.integration)) if a.integration else None,canonical_binding_pending=not bool(a.integration),proposed_readiness=dict(canonical_binding_pending=True,ready=[],pending=[pending]),session=dict(provider_thread_id=os.getenv('CODEX_THREAD_ID'),application_session_id=os.getenv('CODEX_SESSION_ID'),phase_start_utc=start,phase_end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
  _attach_current_canonical(proof,canonical_binding)
  out=pathlib.Path(a.out) if a.out else ROOT/'uc-library/candidates'/TASK/'worker-proof.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(proof,indent=2)+'\n');print(domain)
if __name__=='__main__':main()
