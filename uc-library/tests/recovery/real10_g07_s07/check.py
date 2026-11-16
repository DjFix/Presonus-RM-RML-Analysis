"""Fresh source compile, exact symbols, and supplied-binary differential replay.
Proof mode NEVER compiles or substitutes local binaries for supplied inputs."""
import argparse,datetime,hashlib,importlib.util,json,os,shlex,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent;TASK=T.name
CPP='uc-library/src/Presonus/Panel/ChannelPresetComponent.cpp'
HPP='uc-library/include/presonus/panel/ChannelPresetComponent.hpp'
PROVIDER='uc-library/src/Presonus/Panel/PresetComponent.cpp'
DRIVER=str(T.relative_to(R)/'Replay.cpp')
BUILD=R/'temp/recovery-work/real10_g07'/TASK
CANONICAL_BUILD=Path(os.environ.get('PRESONUS_LOCAL_PROVIDER_BUILD','/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01'))
CORE_SOURCES=['third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparaminfo.h','third_party/ccl-framework/core/portable/coretypeinfo.h','third_party/ccl-framework/core/public/coreformatter.cpp','third_party/ccl-framework/core/public/coreformatter.h','third_party/ccl-framework/core/public/corestringbuffer.h','third_party/ccl-framework/core/public/corevector.h']
FLAGS=['-std=c++20','-O3','-DNDEBUG','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-pthread','-Ulinux','-fno-lto','-fno-fast-math','-ffp-contract=off','-fno-rtti','-Iuc-library/include','-isystem','third_party/ccl-framework']
TIMINGS=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,**kw):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
 p=subprocess.run([str(x) for x in argv],cwd=R,text=True,capture_output=True,timeout=120,**kw)
 TIMINGS.append(dict(argv=list(map(str,argv)),start_utc=start,seconds=time.monotonic()-tick,returncode=p.returncode))
 if p.returncode:raise RuntimeError(json.dumps(TIMINGS[-1])+'\n'+p.stdout+p.stderr)
 return p.stdout

def native_module():
 spec=importlib.util.spec_from_file_location(TASK+'_native',T/'native.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def compile_local():
 BUILD.mkdir(parents=True,exist_ok=True)
 for source,name in [(CPP,'production'),(PROVIDER,'provider')]:
  run(['/usr/bin/c++',*FLAGS,'-MMD','-MF',BUILD/(name+'.d'),'-c',source,'-o',BUILD/(name+'.o')])
 libs=[CANONICAL_BUILD/'libpresonus_rm_components.a',CANONICAL_BUILD/'upstream-core/sdk/lib/libcorelib.a',CANONICAL_BUILD/'upstream-core/sdk/lib/libpresonus_core_allocator.a',Path('/usr/lib/x86_64-linux-gnu/libpng16.so.16'),Path('/usr/lib/x86_64-linux-gnu/libz.so.1'),Path('/usr/lib/x86_64-linux-gnu/libssl.so'),Path('/usr/lib/x86_64-linux-gnu/libcrypto.so'),CANONICAL_BUILD.parents[1]/'core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so',CANONICAL_BUILD/'private-glibc29-provider/libpresonus_private_glibc29.a']
 run(['/usr/bin/c++',*FLAGS,'-MMD','-MF',BUILD/'replay.d',DRIVER,BUILD/'production.o',BUILD/'provider.o',*libs,'-ldl','-lm','-o',BUILD/'replay'])
 deps={}
 for dep in BUILD.glob('*.d'):
  for item in dep.read_text().replace('\\\n',' ').split(':',1)[1].split():
   q=Path(item);q=q if q.is_absolute() else R/q
   if q.is_file():deps[str(q)]=sha(q)
 receipt=dict(phase='local_compile',timings=TIMINGS,compile_dependencies=deps,linked_provider_binaries={str(p):sha(p) for p in libs},source_provider_hashes={p:sha(R/p) for p in CORE_SOURCES+[PROVIDER]})
 (BUILD/'compile-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

def format_check():
 return run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',CPP,HPP,DRIVER])
def symbols(obj,name):
 lines=run(['/usr/bin/nm','--defined-only',obj]);entries=[x.split() for x in lines.splitlines() if x.split()]
 assert any(x[-1]==name for x in entries),name
 return [x for x in entries if x[-1]==name]

def _canonical_observation(root, obj, exe, integration, source, providers=(), archives=()):
 if not integration or Path(integration).resolve() != (root/'uc-library/validation/integration.json').resolve():return None
 import importlib.util
 path=root/'uc-library/tools/recovery/canonical_compile_bindings.py'
 spec=importlib.util.spec_from_file_location('canonical_compile_bindings',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 result=module.bind(root,obj,source,exe_path=exe,required_provider_sources=providers,required_archive_names=archives)
 result['Root_canonical_transition']=module.load_transition(root,'temp/recovery-work/reconstruction10x10-20261116/workflow/checker-canonical-audit/review02/CANONICAL_BINDING_TRANSITION.json')
 result['Root_helper']={'path':'uc-library/tools/recovery/canonical_compile_bindings.py','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 return result

def _canonical_fields(binding):
 return {} if binding is None else {'canonical_compile_binding':binding,'canonical_binding_transition':binding['Root_canonical_transition'],'canonical_producer_helper':binding['Root_helper']}

def proof(a):
 # Canonical invocation must supply all four concrete paths; no build/cache access.
 for label in ['exe','object','integration','out']:assert getattr(a,label),label+' is required for proof'
 exe=Path(a.exe).resolve();obj=Path(a.object).resolve();integration=Path(a.integration).resolve()
 assert exe.is_file() and obj.is_file() and integration.is_file()
 canonical_binding=_canonical_observation(R,obj,exe,str(integration),CPP,providers=(PROVIDER,),archives=('libcorelib.a','libpresonus_core_allocator.a'))
 native=native_module();fixture=json.loads((T/'fixtures.json').read_text())
 assert fixture['elf_sha256']==native.SHA and fixture['range']==native.RANGE
 for case in fixture['cases']:assert native.execute(case['mode'])==case['observed']
 syms=symbols(obj,native.NAME)
 lines=run([exe],input=''.join(str(c['mode'])+'\n' for c in fixture['cases'])).splitlines();assert len(lines)==len(fixture['cases'])
 observations=[]
 for case,line in zip(fixture['cases'],lines):
  parts=shlex.split(line);m=case['observed']['metadata'];p=m['parameter']
  expected=[m['name'],m['display'],m['formatter'],'5',str(p['tag']),str(p['type']),str(int(p['min'])),str(int(p['max'])),str(int(p['default'])),str(int(not bool(p['flags']&4))),*p['strings'],str(int(case['observed']['found'])),str(int(case['observed']['cast']))]
  assert parts==expected,(case['mode'],parts,expected)
  assert case['observed']['receiver_return'] and m['borrowed_mixer']
  observations.append(dict(mode=case['mode'],actual=parts))
 format_check()
 sources={p.removeprefix('uc-library/'):sha(R/p) for p in [CPP,HPP,PROVIDER,'uc-library/include/presonus/panel/PresetComponent.hpp']}
 repository_sources={p:sha(R/p) for p in CORE_SOURCES}
 if canonical_binding is not None:
  unexpected_ccl=[p for p in canonical_binding['files'] if p.startswith('third_party/ccl-framework/') and not p.startswith('third_party/ccl-framework/core/')]
  assert not unexpected_ccl, 'Unexpected non-Core CCL dependency paths: '+repr(unexpected_ccl)
  sources.update({p.removeprefix('uc-library/'):h for p,h in canonical_binding['files'].items() if p.startswith('uc-library/')})
  repository_sources.update({p:h for p,h in canonical_binding['files'].items() if p.startswith('third_party/ccl-framework/core/')})
  assert sources and repository_sources and all(p.startswith('third_party/ccl-framework/core/') for p in repository_sources), 'Actual canonical app/Core closure required'
 domain='Three separately executed original ARM boundary cases: lookup absent, runtime cast failure, valid ListParam. Three actual C1/C2 host constructions, genuine Preset base/name/display/formatter + five CCL parameters; all nine category strings/limits/default/privacy and actual provider null/wrong/right type-query casts. Later unbound channel operations, hardware, original EH/ARM ABI/layout excluded.'
 row=dict(original_elf_sha256=native.SHA,mangled=native.NAME,sources=sources,repository_sources=repository_sources,cpp_compiled=True,mangling_namespace_checked=True,portable_ready=False,declaration_uncertainties=['Original complete class declaration, fields, ownership and ARM layout are unresolved; independent portable state and pinned-provider behavior are used.'],validation_domain=domain)
 result=dict(version=1,task_id=TASK,success=True,case_count=len(lines),original_elf_sha256=native.SHA,original_range=native.RANGE,native_cases=[dict(mode=x['mode'],trace=x['observed']['calls'],object_writes=x['observed']['object_writes']) for x in fixture['cases']],portable_observations=observations,compiled_symbols=syms,source_hashes=sources,repository_sources=repository_sources,producer_hashes={str(T.relative_to(R)/f):sha(T/f) for f in ['Replay.cpp','native.py','check.py','fixtures.json']},executable_sha256=sha(exe),object_sha256=sha(obj),integration=dict(path=str(integration),sha256=sha(integration)),formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler=run(['/usr/bin/c++','--version']).splitlines()[0],timings=TIMINGS,proposed_readiness=dict(ready=[],pending=[row]),limitations=fixture['domain'],worker_session_id='01a1e2e7-ac91-7df0-95b5-ad1fb13f29e0',phase_end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 result.update(_canonical_fields(canonical_binding))
 if canonical_binding is not None:result['provider_archives']={p['path']:p['sha256'] for p in canonical_binding['link']['archives']}
 Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(task_id=TASK,success=True,case_count=len(lines),proof=a.out)))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('mode',nargs='?',default='proof',choices=['compile','format','symbols','proof']);parser.add_argument('--exe');parser.add_argument('--object');parser.add_argument('--integration');parser.add_argument('--out');a=parser.parse_args()
 if a.mode=='compile':compile_local()
 elif a.mode=='format':format_check()
 elif a.mode=='symbols':
  assert a.object;symbols(Path(a.object),native_module().NAME)
 else:proof(a)
