import argparse,datetime,hashlib,json,os,subprocess,sys,time,importlib.util
from pathlib import Path
import native
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent;TASK=T.name;O=R/'temp/recovery-work'/TASK
CLASSES={'01':('surface/PreampsPageComponent','Surface/PreampsPageComponent'),'02':('surface/CapturePageComponent','Surface/CapturePageComponent'),'06':('TargetedComponent','TargetedComponent'),'07':('TargetedComponent','TargetedComponent'),'09':('surface/StChannelSettingsPageComponent','Surface/StChannelSettingsPageComponent')}
a,b=CLASSES[TASK[-2:]];H='uc-library/include/presonus/'+a+'.hpp';S='uc-library/src/Presonus/'+b+'.cpp';C=str((T/'Replay.cpp').relative_to(R));OWNED=[H,S,C]
ROOT=native.ROOT;B=ROOT/'temp/recovery-work/reconstruction10x10-20261116';ARCHIVE_BINDINGS=B/'provider-addenda/READ_BINDINGS_CURRENT01.json';ARCHIVES=json.loads(ARCHIVE_BINDINGS.read_text())['groups']['g04']['archives'];LIBS=[Path(next(x for x in ARCHIVES if x['name']==n)['frozen_read_path']) for n in ['libpresonus_private_glibc29.a','libcorelib.a','libpresonus_core_allocator.a']]
TIMES=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,input=None):
 start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=R,capture_output=True,text=True,input=input,env={**os.environ,'TMPDIR':str(O)});TIMES.append(dict(argv=list(map(str,argv)),duration_seconds=time.monotonic()-start,exit_code=p.returncode));print(p.stdout,end='');print(p.stderr,end='',file=sys.stderr);p.check_returncode();return p.stdout

def bind_canonical_object(obj,exe):
 helper=R/'uc-library/tools/recovery/canonical_compile_bindings.py'
 spec=importlib.util.spec_from_file_location('canonical_compile_bindings',helper)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 binding=module.bind(R,obj,S,exe_path=exe,required_provider_sources=[],required_archive_names=('libcorelib.a','libpresonus_core_allocator.a','libpresonus_private_glibc29.a'))
 return binding,dict(path='uc-library/tools/recovery/canonical_compile_bindings.py',sha256=sha(helper)),module.load_transition(R,'temp/recovery-work/reconstruction10x10-20261116/workflow/checker-canonical-audit/review02/CANONICAL_BINDING_TRANSITION.json')

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
 if args.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED]);return
 if args.mode=='compile':
  flags=['c++','-std=c++17','-O0','-fno-rtti','-ffunction-sections','-fdata-sections','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework']
  run([*flags,'-MMD','-MF',O/'production.d','-c',S,'-o',O/'production.o']);run([*flags,'-MMD','-MF',O/'replay.d','-c',C,'-o',O/'driver.o'])
  extra=[]
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
 payload=''.join(' '.join(str(c[x]) for x in ['message','name_kind','original_kind','controller_kind','available'])+'\n' for c in observation['cases'])
 rows=[list(map(int,line.split())) for line in run([exe],payload).splitlines()]
 assert len(rows)==len(observation['cases'])
 for row,c in zip(rows,observation['cases']):
  writes=c['writes'];changed=int(bool(writes));destination=writes[0]['float_bits'] if writes else 0x3e800000
  expected=[int(c['message']==3),destination,changed,changed,int(c['original_kind']),int(c['original_kind'] and c['controller_kind']>0),int(c['original_kind'] and c['controller_kind']==2),int(c['original_kind'] and c['controller_kind']==2 and c['available']),0x3f800000 if c['available'] else 0,1,1]
  assert row==expected,(row,expected,c)
 domain='144 Cartesian guarded cases: messages -1,2,3,4; exact ch_select/other/empty names; absent/present original; absent/wrong-type/Component controller; absent/present source tag360. Original ARM app instructions execute, preserving exact call order and optional setValue(value,edit=true). Host uses real CCL AliasParam, getOriginal, getController and core_cast<Component> as explicit RTTI adaptation; actual source tag360 lookup and NumericParam value/edit/changed provider-only baselines observed independently. Product destination tag1000 is present with initial .25f; result bits, edit controller calls, observer changes and base dirty marking compared.'
 limits=['Portable source port; original return declaration, inheritance, fields/layout and ARM ABI unresolved','Intentional pinned CCL type-ID adaptation replaces original IParamObserver-to-Component dynamic_cast, independently exercised for null/wrong-type/Component controllers','Destination parameter tag1000 must exist whenever native guarded path reaches it; original also has no null guard','Native provider calls and strcmp are bounded controlled boundaries; actual CCL provider observations are separate host executions. No hardware, concurrency, allocation failure, throwing providers or invalid parameter lifetimes tested']
 dependency_files={}
 if canonical_mode:
  dependency_files=dict(canonical_binding['files'])
  assert dependency_files and S in dependency_files, 'Actual nonempty canonical production dependency closure required'
 else:
  for dep in ['production.d','replay.d']:
   tokens=(O/dep).read_text().replace('\\\n',' ').split()[1:]
   for token in tokens:
    path=Path(token)
    if not path.is_absolute() and (R/path).is_file():dependency_files[str(path)]=sha(R/path)
 sources={x.removeprefix('uc-library/'):sha(R/x) for x in [H,S]};providers={x:sha(R/x) for x in ['third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/public/corevector.h']}
 entry=dict(original_elf_sha256=observation['elf_sha256'],mangled=observation['mangled'],sources=sources,repository_sources=providers,domain=domain,cpp_compiled=True,mangling_namespace_checked=True,portable_ready=False,declaration_uncertainties=limits)
 proof=dict(task_id=TASK,session_id=os.environ.get('CODEX_THREAD_ID'),desktop_session_id=os.environ.get('CODEX_SESSION_ID'),agent='/root/real10_g04',start_utc=start,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),native=observation,provider_and_product_rows=rows,cpp_differential_passed=True,compiled_mangled_names_matched=True,canonical_binding_pending=not bool(args.integration),sources=sources,repository_sources=providers,formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler=run(['c++','--version']).splitlines()[0],object=dict(path=str(obj),sha256=sha(obj)),executable=dict(path=str(exe),sha256=sha(exe)),provider_archives=canonical_provider_archives if canonical_mode else {str(x):sha(x) for x in LIBS},transitive_compile_dependencies=dependency_files,native_producer=dict(path=str(T/'native.py'),sha256=sha(T/'native.py')),fixture=dict(path=str(T/'fixtures.json'),sha256=sha(T/'fixtures.json')),checker=dict(path=str(T/'check.py'),sha256=sha(T/'check.py')),tool_timings=TIMES,proposed_readiness=dict(ready=[],pending=[entry]),limitations=limits,validation_domain=domain)
 if canonical_mode:
  proof['canonical_compile_binding']=canonical_binding
  proof['canonical_compile_binding_helper']=canonical_binding_helper
  proof['canonical_binding_transition']=canonical_binding_transition
 if args.integration:proof['integration']=dict(path=args.integration,sha256=sha(R/args.integration))
 if args.out:Path(args.out).write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
