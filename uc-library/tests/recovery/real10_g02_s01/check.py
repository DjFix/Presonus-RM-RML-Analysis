#!/usr/bin/env python3
"""Exact identity lifecycle replay with explicit supplied canonical binaries."""
import argparse,datetime,hashlib,json,os,subprocess,time,sys
from pathlib import Path
T=Path(__file__).resolve().parent;R=T.parents[3];TASK=T.name
RUN=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116');P=RUN/'prepared-main/packets'/TASK
Q=json.loads((P/'request.json').read_text());TARGET=Q['targets'][0]
CLASS='PresetsPageComponent' if int(TASK[-2:])<6 else 'GeqPresetsPageComponent' if int(TASK[-2:])<9 else 'ChannelPresetsPageComponent'
CLASSES=['PresetsPageComponent','GeqPresetsPageComponent','ChannelPresetsPageComponent']
CPP=[f'uc-library/src/Presonus/Surface/{c}.cpp' for c in CLASSES]+['uc-library/src/Presonus/MixerClientComponentBase.cpp','uc-library/src/mixer_state/MixerState.cpp']
HEADERS=[f'uc-library/include/presonus/surface/{c}.hpp' for c in CLASSES]
TEST=str((T/'Replay.cpp').relative_to(R));SOURCES=CPP[:3]+HEADERS+[TEST]
WORK=R/'temp/recovery-work'/TASK
BUILD=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01');SDK=BUILD/'upstream-core/sdk/lib'
FLAGS=['/usr/bin/c++','-std=c++17','-O2','-fno-rtti','-fno-lto','-Wno-multichar','-ffunction-sections','-fdata-sections','-UNDEBUG','-Ulinux','-pthread','-Iuc-library/include','-Ithird_party/ccl-framework']
LIBS=['-Wl,--start-group',str(SDK/'libcorelib.a'),str(SDK/'libpresonus_core_allocator.a'),str(BUILD/'private-glibc29-provider/libpresonus_private_glibc29.a'),'-Wl,--end-group','-pthread','-ldl','-lm','-lz','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lssl','-lcrypto',str(BUILD.parent/'external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so')]
PROVIDERS=['third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/public/corevector.h']
DOMAIN='Exact original ARM app setMixer body over 24 null/empty/duplicate/capacity/address cases. C++ uses actual canonical MixerClient identity plus explicit borrowed binding to real pinned Core observer vector. Native caller output count/order/observer identity and mixer assignment compared with actual C++ output; all native writes and resize boundary arguments recorded.'
LIMITS=['Original return declaration, class inheritance/layout/observer subobject placement and ARM ABI remain unresolved. Void return is a source-port choice.','Source-port mixer association is explicit caller-provided borrowed typed state; canonical MixerClient has no original observer storage recovered. No original layout or ownership claim. A missing binding throws outside the validated domain.','Native Core resize is a captured successful-capacity boundary; pinned CCL vector operations execute in C++. Allocation failure/EH and inconsistent negative counts excluded. No observer callbacks, device or hardware execution.']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv):
 argv=list(map(str,argv));start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();p=subprocess.run(argv,cwd=R,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(WORK)})
 row=dict(start_utc=start,seconds=time.monotonic()-t,argv=argv,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
 with (WORK/'commands.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 if p.returncode:print(p.stdout,p.stderr);p.check_returncode()
 return p.stdout

def formatting():
 version=run(['uc-library/.venv/bin/clang-format','--version']).strip();run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES]);return version

def compile():
 objects=[]
 for source in CPP+[TEST]:
  obj=WORK/(Path(source).stem+'.o');run(FLAGS+['-MMD','-MF',str(obj)+'.d','-c',source,'-o',obj]);objects.append(obj)
 run(['/usr/bin/c++',*objects,'-Wl,--gc-sections',*LIBS,'-o',WORK/'replay'])

def symbols(obj):
 nm=run(['/usr/bin/nm','--defined-only',obj]);assert TARGET['mangled'] in [l.split()[-1] for l in nm.splitlines() if l.split()],TARGET['mangled'];return nm

def native():
 import native as oracle
 data=oracle.generate();bound=json.loads((T/'fixtures.json').read_text());assert data==bound,'original observations changed';return data

def replay(exe,data):
 cases=[]
 for c in data['cases']:
  actual=run([exe,*c['argv']]).strip()
  assert actual==c['expected'],(c['argv'],actual,c['expected'])
  cases.append(dict(argv=c['argv'],native=c['expected'],port=actual))
 return cases


# Root canonical-only source/OBJECT/link provenance; local execution is retained.
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
 binding=_canonical_observation(R,Path(a.object),Path(a.exe),a.integration,'uc-library/src/Presonus/Surface/PresetsPageComponent.cpp',providers=tuple(p for p in CPP if p!='uc-library/src/Presonus/Surface/PresetsPageComponent.cpp'))
 fmt=formatting();data=native();nm=symbols(a.object);cases=replay(a.exe,data)
 sources={p.removeprefix('uc-library/'):sha(R/p) for p in CPP+HEADERS};providers={p:sha(R/p) for p in PROVIDERS}
 entry=dict(original_elf_sha256=TARGET['original_elf_sha256'],mangled=TARGET['mangled'],firmware=TARGET['firmware'],role=TARGET['role'],address=TARGET['address'],size=TARGET['size'],section=TARGET['section'],sources=sources,repository_sources=providers,cpp_compiled=True,mangling_namespace_checked=True,portable_ready=False,original_function_verified=False,hardware_verified=False,validation_domain=DOMAIN,declaration_uncertainties=LIMITS)
 deps={}
 if binding is not None:
  deps.update(binding['files']);providers.update({p:v for p,v in binding['files'].items() if p.startswith('third_party/')})
 for dep in ([] if binding is not None else WORK.glob('*.o.d')):
  for name in dep.read_text().replace('\\\n',' ').split()[1:]:
   p=R/name
   if p.is_file() and not name.startswith('temp/'):deps[name]=sha(p)
 result=dict(version=1,task_id=TASK,worker_session_id=os.environ.get('CODEX_THREAD_ID','unavailable'),timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),platform='Linux',native=data,provider_and_port_cases=cases,portable_case_count=len(cases),validation_domain=DOMAIN,limitations=LIMITS,sources=sources,repository_sources=providers,transitive_compile_dependencies=deps,cpp_differential_passed=True,compiled_original_mangled_names_matched=True,mangling_namespace_checked=True,portable_ready=False,original_function_verified=False,hardware_verified=False,canonical_binding_pending=not bool(a.integration),formatting=dict(version=fmt,source_hashes=sources,passed=True),proposed_readiness=dict(ready=[],pending=[entry]),compiled_symbols=nm,binary_bindings={str(a.exe):sha(a.exe),str(a.object):sha(a.object)},provider_binary_bindings={v:sha(v) for v in LIBS if Path(v).is_file()},compiler_version=run(['/usr/bin/c++','--version']).splitlines()[0],fixture_sha256=sha(T/'fixtures.json'),producer_sha256=sha(__file__),integration=a.integration,commands_log=str((WORK/'commands.jsonl').relative_to(R)))
 result.update(_canonical_fields(binding))
 out=Path(a.out);assert not (out.exists() and 'candidates' in out.parts), 'sealed candidate proof is immutable; choose scratch --out';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(out)

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','native','replay','proof']);p.add_argument('--exe',default=str(WORK/'replay'));p.add_argument('--object',default=str(WORK/(CLASS+'.o')));p.add_argument('--integration');p.add_argument('--out',default=str(WORK/'replay-proof.json'));a=p.parse_args();WORK.mkdir(parents=True,exist_ok=True)
 if a.mode=='format':formatting()
 elif a.mode=='compile':compile()
 elif a.mode=='symbols':symbols(a.object)
 elif a.mode=='native':
  import native as oracle
  (T/'fixtures.json').write_text(json.dumps(oracle.generate(),indent=2)+'\n')
 elif a.mode=='replay':print(len(replay(a.exe,native())))
 else:proof(a)
if __name__=='__main__':main()
