"""Fresh native/provider and compiled replay, including canonical proof binding."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[4];BASE=pathlib.Path(__file__).parent;TASK=BASE.name
PACKET=ROOT/'temp/recovery-work/rolling10x10-20261114/prepared06/packets'/TASK
REQ=json.loads((PACKET/'request.json').read_text());HDR=REQ['owned_files'][0];SRC=REQ['owned_files'][1];TEST=str(BASE.relative_to(ROOT)/'Replay.cpp')
SCRATCH=ROOT/'temp/recovery-work'/TASK;SCRATCH.mkdir(parents=True,exist_ok=True)
PY='uc-library/.venv/bin/python';FMT='uc-library/.venv/bin/clang-format';LIB=pathlib.Path('temp/provider-baseline08')
FLAGS=['/usr/bin/c++','-std=c++20','-fno-rtti','-fno-lto','-Wno-multichar','-ffunction-sections','-fdata-sections','-UNDEBUG','-Iuc-library/include','-Ithird_party/ccl-framework']
PROVIDERS=['third_party/ccl-framework/core/portable/'+x for x in ['coreparams.h','coreparams.cpp','corecomponent.h','corecomponent.cpp']]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(argv,**kw):
 p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,text=True,env={**os.environ,'TMPDIR':str(SCRATCH)},**kw);print(json.dumps(list(map(str,argv))),flush=True)
 if p.returncode:print(p.stdout,p.stderr);p.check_returncode()
 return p.stdout

def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',nargs='?',default='replay')
 for name in ['exe','object','integration','out']:ap.add_argument('--'+name,type=pathlib.Path)
 a=ap.parse_args();exe=a.exe or SCRATCH/'replay';obj=a.object or SCRATCH/'production.o';start=now()
 if a.mode=='format':run([FMT,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',HDR,SRC,TEST]);return
 if a.mode=='compile':
  for x in json.loads((ROOT/LIB/'PROVENANCE.json').read_text())['files']:
   if x['local'].endswith(('libcorelib.a','libpresonus_core_allocator.a')):assert sha(ROOT/x['local'])==x['sha256']
  run([*FLAGS,'-O3','-c',SRC,'-o',obj]);run([*FLAGS,'-O0',TEST,obj,'-Wl,--gc-sections',LIB/'libcorelib.a',LIB/'libpresonus_core_allocator.a','-lz','-lpthread','-ldl','-lm','-o',exe]);return
 target=REQ['targets'][0]
 if a.mode=='symbols':assert target['mangled'] in {x.split()[-1] for x in run(['/usr/bin/nm','--defined-only',obj]).splitlines() if x.split()};return
 import native
 fresh=native.generate(exe);fixture=json.loads((BASE/'fixtures.json').read_text());assert fresh==fixture
 if a.mode=='native':print(len(fixture['cases']),'fresh native app/helper executions');return
 assert a.mode=='replay'
 payload=''.join(' '.join(map(str,c['input']))+'\n' for c in fixture['cases']);actual=run([exe],input=payload).splitlines();assert len(actual)==len(fixture['cases'])
 for line,c in zip(actual,fixture['cases']):assert line==str(c['expected']),(line,c)
 run([FMT,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',HDR,SRC,TEST]);assert target['mangled'] in {x.split()[-1] for x in run(['/usr/bin/nm','--defined-only',obj]).splitlines() if x.split()}
 domain=fixture['scope'];limits=['Original ordinary return declaration, field/bases/layout, vtable and ARM ABI remain unresolved. Portable source model only.','Native executes exact original application and full non-Core comparison closure where applicable; Core boundaries bridge independently observed actual pinned source provider results only. No original Core execution.','Finite values, valid caller-owned typed receiver and parameter lifetimes. Missing required parameters, unknown virtual overrides, invalid pointers, concurrent mutation and hardware excluded.','Root owns canonical full integration, active-source proof and guarded SQLite admission.']
 sources={str(pathlib.Path(p).relative_to('uc-library')):sha(ROOT/p) for p in [HDR,SRC]};providers={p:sha(ROOT/p) for p in PROVIDERS};entry=dict(original_elf_sha256=target['original_elf_sha256'],mangled=target['mangled'],sources=sources,repository_sources=providers,domain=domain,portable_ready=False,declaration_uncertainties=limits[:1],cpp_compiled=True,mangling_namespace_checked=True)
 proof=dict(version=1,task_id=TASK,session_id='/root/rolling10_daw_list',phase_timestamps={'replay_start':start,'replay_end':now()},functions=[entry],native_cases=len(fixture['cases']),native_fixture={'path':str((BASE/'fixtures.json').relative_to(ROOT)),'sha256':sha(BASE/'fixtures.json')},original_elf_sha256=fixture['elf_sha256'],native_ranges=fixture.get('helper_ranges',[])+[fixture['target_range']],formatter_version=run([FMT,'--version']).strip(),compiler_version=run(['/usr/bin/c++','--version']).splitlines()[0],native_producer_sha256=sha(BASE/'native.py'),replay_producer_sha256=sha(__file__),unicorn_version=__import__('unicorn').__version__,source_sha256={p:sha(ROOT/p) for p in [HDR,SRC,TEST]},provider_sources=providers,arm_differential_passed=True,compiled_mangled_names_matched=True,validation_domain=domain,limitations=limits,proposed_readiness=dict(canonical_binding_pending=True,ready=[],pending=[entry]),executable={'path':str(exe),'sha256':sha(exe)},object={'path':str(obj),'sha256':sha(obj)})
 if a.integration:
  assert a.integration.is_file();proof['integration']={'path':str(a.integration),'sha256':sha(a.integration)};proof['proposed_readiness']['canonical_binding_pending']=False
 out=a.out or SCRATCH/'local-proof.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(proof,indent=2)+'\n');print(len(actual),'native/C++ cases; fresh proof',out)
if __name__=='__main__':main()
