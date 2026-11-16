import argparse,datetime,hashlib,json,os,subprocess,sys,time,importlib.util
from pathlib import Path
import native
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent;TASK=T.name;O=R/'temp/recovery-work'/TASK
CLASSES={'01':('surface/PreampsPageComponent','Surface/PreampsPageComponent'),'02':('surface/CapturePageComponent','Surface/CapturePageComponent'),'06':('TargetedComponent','TargetedComponent'),'08':('surface/ScenesPageComponent','Surface/ScenesPageComponent')}
a,b=CLASSES[TASK[-2:]];H='uc-library/include/presonus/'+a+'.hpp';S='uc-library/src/Presonus/'+b+'.cpp';C=str((T/'Replay.cpp').relative_to(R));OWNED=[H,S,C]
ROOT=native.ROOT;B=ROOT/'temp/recovery-work/reconstruction10x10-20261116';OVERLAY=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/production-20261112/agent-repos/worker11/temp/recovery-work/real10_g04-presets-provider');ADDENDUM=B/'provider-addenda/G04_PRESETS_PROVIDER_OVERLAY05.json';ARCHIVE_BINDINGS=B/'provider-addenda/READ_BINDINGS_CURRENT01.json';ARCHIVES=json.loads(ARCHIVE_BINDINGS.read_text())['groups']['g04']['archives'];LIBS=[Path(next(x for x in ARCHIVES if x['name']==n)['frozen_read_path']) for n in ['libpresonus_private_glibc29.a','libcorelib.a','libpresonus_core_allocator.a']]
TIMES=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,input=None):
 start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=R,capture_output=True,text=True,input=input,env={**os.environ,'TMPDIR':str(O)});TIMES.append(dict(argv=list(map(str,argv)),duration_seconds=time.monotonic()-start,exit_code=p.returncode));print(p.stdout,end='');print(p.stderr,end='',file=sys.stderr);p.check_returncode();return p.stdout

def bind_canonical_object(obj,exe):
 helper=R/'uc-library/tools/recovery/canonical_compile_bindings.py'
 spec=importlib.util.spec_from_file_location('canonical_compile_bindings',helper)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 binding=module.bind(R,obj,S,exe_path=exe,required_provider_sources=['uc-library/src/Presonus/Surface/PresetsPageComponent.cpp'],required_archive_names=('libcorelib.a','libpresonus_core_allocator.a','libpresonus_private_glibc29.a'))
 return binding,dict(path='uc-library/tools/recovery/canonical_compile_bindings.py',sha256=sha(helper)),module.load_transition(R,'temp/recovery-work/reconstruction10x10-20261116/workflow/checker-canonical-audit/review02/CANONICAL_BINDING_TRANSITION.json')

def bind_presets_source(sources, providers, canonical_mode, path, digest):
 if canonical_mode:
  assert path in {'uc-library/include/presonus/surface/PresetsPageComponent.hpp','uc-library/src/Presonus/Surface/PresetsPageComponent.cpp'}, 'Only approved actual Presets library sources may be rebound'
  name=path.removeprefix('uc-library/')
  assert name not in sources or sources[name]==digest, 'Conflicting actual Presets source hash'
  sources[name]=digest
 else:
  providers[path]=digest

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='replay');p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');args=p.parse_args();O.mkdir(parents=True,exist_ok=True);start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 canonical_mode=bool(args.integration)
 canonical_binding=None;canonical_binding_helper=None;canonical_binding_transition=None;canonical_provider_archives=None
 if canonical_mode:
  integration_path=Path(args.integration)
  integration_path=(R/integration_path).resolve() if not integration_path.is_absolute() else integration_path.resolve()
  assert integration_path==(R/'uc-library/validation/integration.json').resolve(), 'Canonical integration must be the actual canonical integration.json'
  assert args.exe and args.object, 'Canonical proof requires explicit supplied executable and object'
  assert args.mode in ('replay','symbols'), 'Canonical mode never invokes worker-local compilation'
  assert sha(ADDENDUM)=='2b6dc08f9345316fef3df33f2e3c13d1aa38be7b64e9695b023f25d476d587e4', 'Approved provider supplement changed'
  approved=json.loads(ADDENDUM.read_text())['copies']
  assert len(approved)==2 and {x['canonical_relative_path'] for x in approved}=={'uc-library/include/presonus/surface/PresetsPageComponent.hpp','uc-library/src/Presonus/Surface/PresetsPageComponent.cpp'}
  for copy in approved:
   assert sha(R/copy['canonical_relative_path'])==copy['overlay_sha256']==copy['source_sha256'], 'Actual canonical Presets provider differs from approved source/overlay'
 if args.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED]);return
 if args.mode=='compile':
  flags=['c++','-std=c++17','-O0','-fno-rtti','-ffunction-sections','-fdata-sections','-Wno-multichar','-I'+str(OVERLAY/'include'),'-Iuc-library/include','-Ithird_party/ccl-framework']
  run([*flags,'-MMD','-MF',O/'production.d','-c',S,'-o',O/'production.o']);run([*flags,'-MMD','-MF',O/'replay.d','-c',C,'-o',O/'driver.o'])
  run([*flags,'-MMD','-MF',O/'presets.d','-c',OVERLAY/'src/Presonus/Surface/PresetsPageComponent.cpp','-o',O/'presets.o'])
  extra=[O/'presets.o']
  if TASK.endswith('02'):
   # Existing canonical provider, no replacement implementation.
   run([*flags,'-c','uc-library/src/Presonus/PageComponent.cpp','-o',O/'page.o']);extra=[O/'page.o']
  run(['c++',O/'driver.o',O/'production.o',*extra,'-Wl,--gc-sections',*LIBS,'-l:libpng16.so.16','-lz','-lpthread','-ldl','-lm','-o',O/'replay']);return
 obj=Path(args.object) if args.object else O/'production.o';exe=Path(args.exe) if args.exe else O/'replay'
 if canonical_mode:
  canonical_binding,canonical_binding_helper,canonical_binding_transition=bind_canonical_object(obj,exe)
  assert canonical_binding['files'] and S in canonical_binding['files'], 'Actual nonempty canonical production dependency closure required'
  canonical_provider_archives={}
  for name in ('libcorelib.a','libpresonus_core_allocator.a','libpresonus_private_glibc29.a'):
   matches=[item for item in canonical_binding['link']['archives'] if Path(item['path']).name==name]
   assert len(matches)==1, 'Exactly one actual linked provider archive path required: '+name
   canonical_provider_archives[matches[0]['path']]=matches[0]['sha256']
 observation=native.generate();fixture=json.loads((T/'fixtures.json').read_text());assert fixture==observation
 symbols=run(['nm','--defined-only',obj]);assert observation['mangled'] in {x.split()[-1] for x in symbols.splitlines() if x.split()}
 if args.mode=='symbols':return
 payload=''.join(f"{int(c['provider'])} {int(c['parameter'])} {c['float_bits']}\n" for c in observation['cases'])
 rows=[list(map(int,line.split())) for line in run([exe],payload).splitlines()]
 assert len(rows)==6*len(observation['cases'])
 for i,c in enumerate(observation['cases']):
  for scenario in range(6):
   effect=int('PresetsPageComponent::recall' in c['trace'] and scenario==0)
   assert rows[6*i+scenario]==[scenario,int(scenario==0),int(scenario==0),effect,effect,c['float_bits'] if c['parameter'] else 0]
 domain='11 native guard cases on a receiver whose vptr is the exact original Scenes primary table+8: null provider, absent tag12, +/-zero, finite values, infinities, quiet NaN, subnormals. Original ARM target and __aeabi_fcmpgt execute. Concrete slot54 is independently verified as PresetsPageComponent::recall. Product uses borrowed actual canonical PresetsPageComponent composition and executes real recall across six states per guard case: eligible selection, absent mixer, handler unavailable, negative selection, out-of-range selection, null preset; 66 direct canonical provider baselines and 66 product scenarios verify actual recallOptions/recall identity/category/options outputs. Real pinned CCL tag lookup and AliasParam forwarding observed separately.'
 limits=['Portable source port; original return spelling, member types, inheritance, layout and ARM ABI unresolved','Primary original Scenes vptr/table+8 domain only; no arbitrary subclass dispatch claim. Host composition intentionally uses actual canonical PresetsPageComponent with explicitly borrowed lifetime','Native Core lookups/value and identified Presets recall entry are controlled boundaries; actual CCL and canonical Presets source run on host separately','Canonical Presets implementation has explicit required app boundaries; test boundaries capture handler/preset/recall transport without devices. No hardware scene recall, concurrent mutation or invalid lifetimes tested']
 dependency_files={}
 if canonical_mode:
  dependency_files=dict(canonical_binding['files'])
  assert dependency_files and S in dependency_files, 'Actual nonempty canonical production dependency closure required'
 else:
  for dep in ['production.d','replay.d','presets.d']:
   tokens=(O/dep).read_text().replace('\\\n',' ').split()[1:]
   for token in tokens:
    path=Path(token)
    if not path.is_absolute() and (R/path).is_file():dependency_files[str(path)]=sha(R/path)
 sources={x.removeprefix('uc-library/'):sha(R/x) for x in [H,S]};providers={x:sha(R/x) for x in ['third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/public/corevector.h']}
 for copy in json.loads(ADDENDUM.read_text())['copies']:
  provider_path=R/copy['canonical_relative_path'] if canonical_mode else Path(copy['overlay_read_path'])
  assert sha(provider_path)==copy['overlay_sha256']
  bind_presets_source(sources,providers,canonical_mode,copy['canonical_relative_path'],sha(provider_path))
 if canonical_mode:
  assert all(path.startswith('third_party/ccl-framework/') for path in providers), 'Canonical repository_sources must contain pinned Core sources only'
 entry=dict(original_elf_sha256=observation['elf_sha256'],mangled=observation['mangled'],sources=sources,repository_sources=providers,domain=domain,cpp_compiled=True,mangling_namespace_checked=True,portable_ready=False,declaration_uncertainties=limits)
 proof=dict(task_id=TASK,session_id=os.environ.get('CODEX_THREAD_ID'),desktop_session_id=os.environ.get('CODEX_SESSION_ID'),agent='/root/real10_g04',start_utc=start,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),native=observation,provider_and_product_rows=rows,cpp_differential_passed=True,compiled_mangled_names_matched=True,canonical_binding_pending=not bool(args.integration),sources=sources,repository_sources=providers,formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler=run(['c++','--version']).splitlines()[0],object=dict(path=str(obj),sha256=sha(obj)),executable=dict(path=str(exe),sha256=sha(exe)),provider_archives=canonical_provider_archives if canonical_mode else {str(x):sha(x) for x in LIBS},transitive_compile_dependencies=dependency_files,native_producer=dict(path=str(T/'native.py'),sha256=sha(T/'native.py')),fixture=dict(path=str(T/'fixtures.json'),sha256=sha(T/'fixtures.json')),checker=dict(path=str(T/'check.py'),sha256=sha(T/'check.py')),tool_timings=TIMES,proposed_readiness=dict(ready=[],pending=[entry]),limitations=limits,validation_domain=domain)
 if canonical_mode:
  proof['supplemental_provider_bindings']=dict(addendum=dict(path=str(ADDENDUM),sha256=sha(ADDENDUM)),canonical_sources={copy['canonical_relative_path']:sha(R/copy['canonical_relative_path']) for copy in approved},archive_bindings=dict(path=str(ARCHIVE_BINDINGS),sha256=sha(ARCHIVE_BINDINGS)))
 else:
  proof['supplemental_provider_bindings']=dict(addendum=dict(path=str(ADDENDUM),sha256=sha(ADDENDUM)),overlay={str(x):sha(x) for x in [OVERLAY/'include/presonus/surface/PresetsPageComponent.hpp',OVERLAY/'src/Presonus/Surface/PresetsPageComponent.cpp']},archive_bindings=dict(path=str(ARCHIVE_BINDINGS),sha256=sha(ARCHIVE_BINDINGS)))

 if canonical_mode:
  proof['canonical_compile_binding']=canonical_binding
  proof['canonical_compile_binding_helper']=canonical_binding_helper
  proof['canonical_binding_transition']=canonical_binding_transition
 if args.integration:proof['integration']=dict(path=args.integration,sha256=sha(R/args.integration))
 if args.out:Path(args.out).write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
