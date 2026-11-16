"""Deterministic supplied object/executable checker. No implicit canonical rebuild."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,time
import native
import re
ROOT=native.ROOT;BASE=native.BASE;TASK=native.TASK;PACKET=native.PACKET
HDR='uc-library/include/presonus/surface/MainScreenComponent.hpp';SRC='uc-library/src/Presonus/Surface/MainScreenComponent.cpp';TEST=str(BASE.relative_to(ROOT)/'Replay.cpp')
EXTRA=['uc-library/src/Presonus/MainLCDComponent.cpp','uc-library/src/Presonus/MainLCDPageStack.cpp','uc-library/src/Presonus/PageComponent.cpp','uc-library/src/Presonus/Surface/MappingMeterRouting.cpp'];FORMAT=[HDR,SRC,TEST,'uc-library/include/presonus/MainLCDComponent.hpp',*EXTRA[:2]];PROVIDERS=['third_party/ccl-framework/core/portable/'+x for x in ['corecomponent.cpp','corecomponent.h','coreparams.cpp','coreparams.h']]
FLAGS=['/usr/bin/c++','-std=c++20','-O2','-fno-rtti','-fno-sized-deallocation','-fno-lto','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework'];LIB='temp/provider-baseline08/'
SCRATCH=ROOT/'temp/recovery-work'/TASK;SCRATCH.mkdir(parents=True,exist_ok=True)
def sha(p):return native.sha(p)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
commands=[]
def run(argv,**kw):
 start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,text=True,env={**os.environ,'TMPDIR':str(SCRATCH)},**kw);commands.append(dict(argv=list(map(str,argv)),duration_seconds=time.monotonic()-start,returncode=p.returncode));print(json.dumps(commands[-1]),flush=True)
 if p.returncode:print(p.stdout,p.stderr);p.check_returncode()
 return p.stdout
def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',nargs='?',default='replay')
 for name in ['exe','object','integration','out']:ap.add_argument('--'+name,type=pathlib.Path)
 a=ap.parse_args();assert bool(a.exe)==bool(a.object), 'Supply both --exe and --object';exe=a.exe or SCRATCH/'replay';obj=a.object or SCRATCH/'production.o';start=now();target=json.loads((PACKET/'request.json').read_text())['targets'][0]
 if a.mode=='compile':
  for x in json.loads((ROOT/LIB/'PROVENANCE.json').read_text())['files']:
   if x['local'].endswith(('libcorelib.a','libpresonus_core_allocator.a')):assert sha(ROOT/x['local'])==x['sha256']
  run([*FLAGS,'-MMD','-MF',SCRATCH/'production.d','-c',SRC,'-o',obj]);run([*FLAGS,'-MMD','-MF',SCRATCH/'replay.d',TEST,obj,*EXTRA,'-Wl,--gc-sections','-Wl,--wrap=_ZN8Presonus7Surface16MappingComponent19setPreampsMeterModeEb','-Wl,--wrap=_ZN8Presonus7Surface16MappingComponent10setGeqModeEb',LIB+'libpresonus_cs18_components.a',LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a','-lz','-lpthread','-ldl','-lm','-o',exe]);return
 if a.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*FORMAT]);return
 if a.mode=='symbols':assert target['mangled'] in {line.split()[-1] for line in run(['/usr/bin/nm','--defined-only',obj]).splitlines() if line.split()};return
 fresh=native.generate(exe)
 if a.mode=='generate':(BASE/'fixtures.json').write_text(json.dumps(fresh,indent=2)+'\n');return
 assert a.mode=='replay';fixture=json.loads((BASE/'fixtures.json').read_text());assert fresh==fixture
 payload=''.join(' '.join(map(str,c['input']))+'\n' for c in fixture['cases']);actual=run([exe],input=payload).splitlines();assert actual==[c['expected'] for c in fixture['cases']]
 assert target['mangled'] in {line.split()[-1] for line in run(['/usr/bin/nm','--defined-only',obj]).splitlines() if line.split()};run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*FORMAT])
 limits=['Original ordinary return declarations, source-port class inheritance/state layout and ARM ABI unresolved; tagged initialization is independent. Destructor identities are compiler ABI variants, not invented ordinary methods.',fixture['scope']]
 sources={str(pathlib.Path(p).relative_to('uc-library')):sha(ROOT/p) for p in [HDR,SRC,*EXTRA]};providers={p:sha(ROOT/p) for p in PROVIDERS};entry=dict(original_elf_sha256=target['original_elf_sha256'],mangled=target['mangled'],sources=sources,repository_sources=providers,domain=fixture['scope'],portable_ready=False,declaration_uncertainties=limits[:1],cpp_compiled=True,mangling_namespace_checked=True)
 deps={}
 scan=run([*FLAGS,'-MM',SRC,TEST,*globals().get('EXTRA',[])])
 for chunk in re.split(r'\S+\.o:\s*',scan.replace('\\\n',' ')):
  for p in chunk.split():
   if pathlib.Path(p).is_file():deps[p]=sha(p)
 providers.update({p:v for p,v in deps.items() if p.startswith('third_party/ccl-framework/')})
 entry['repository_sources']=providers
 oracle_inputs={str(native.SNAP/'rootfs/CS18_v13840/home/root/surface'):fixture['elf_sha256']}
 ev=native.SNAP/('temp/recovery-work/reconstruction10x10-20261116/native/'+TASK+'.json');oracle_inputs[str(ev)]=sha(ev)
 if hasattr(native,'EXP') and fixture.get('helper_ranges'):oracle_inputs[str(native.EXP)]=sha(native.EXP)

 proof=dict(version=1,task_id=TASK,session_id='01a1e2e7-2df1-7401-a1eb-3538e24b27c3',phase_timestamps={'replay_start':start,'replay_end':now()},functions=[entry],native_cases=len(fixture['cases']),native_fixture={'path':str(BASE.relative_to(ROOT)/'fixtures.json'),'sha256':sha(BASE/'fixtures.json')},native_ranges=[fixture['target_range'],*fixture.get('helper_ranges',[])],original_elf_sha256=fixture['elf_sha256'],source_sha256={p:sha(ROOT/p) for p in FORMAT},repository_sources=providers,compile_dependencies=deps,oracle_inputs=oracle_inputs,formatter_version=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler_version=run(['/usr/bin/c++','--version']).splitlines()[0],unicorn_version=__import__('unicorn').__version__,commands=commands,arm_differential_passed=True,compiled_mangled_names_matched=True,validation_domain=fixture['scope'],limitations=limits,proposed_readiness=dict(ready=[],pending=[entry],canonical_binding_pending=not bool(a.integration)),executable={'path':str(exe),'sha256':sha(exe)},object={'path':str(obj),'sha256':sha(obj)},producer_sha256={str(BASE.relative_to(ROOT)/x):sha(BASE/x) for x in ['native.py','check.py']})
 if a.integration:assert a.integration.is_file();proof['integration']={'path':str(a.integration),'sha256':sha(a.integration)}
 out=a.out or ROOT/'uc-library/candidates'/TASK/'worker-proof.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(proof,indent=2)+'\n');print(len(actual),'native/product cases passed')
if __name__=='__main__':main()
