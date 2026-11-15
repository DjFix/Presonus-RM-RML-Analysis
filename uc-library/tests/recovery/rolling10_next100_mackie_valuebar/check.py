"""Exact packet local/canonical replay; all executed producer inputs hash bound."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[4];BASE=pathlib.Path(__file__).parent;TASK=BASE.name
PACKET=ROOT/'temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/packets'/TASK
REQ=json.loads((PACKET/'request.json').read_text());HDR=REQ['owned_files'][0];SRC=REQ['owned_files'][1];TEST=str(BASE.relative_to(ROOT)/'Replay.cpp')
SCRATCH=ROOT/'temp/recovery-work'/TASK;SCRATCH.mkdir(parents=True,exist_ok=True)
PY='uc-library/.venv/bin/python';FMT='uc-library/.venv/bin/clang-format';LIB=pathlib.Path('temp/provider-baseline08')
MODELS=['uc-library/src/Presonus/MackieControlModel.cpp','uc-library/src/Presonus/MackieControlModelMappings.cpp']
FLAGS=['/usr/bin/c++','-std=c++20','-fno-rtti','-fno-lto','-Wno-multichar','-ffunction-sections','-fdata-sections','-UNDEBUG','-Iuc-library/include','-Ithird_party/ccl-framework']
PROVIDERS=['third_party/ccl-framework/core/portable/'+x for x in ['coreparams.h','coreparams.cpp','corecomponent.h','corecomponent.cpp','coreparaminfo.h']]+['third_party/ccl-framework/core/public/corevector.h']
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
  run([*FLAGS,'-O3','-c',SRC,'-o',obj]);run([*FLAGS,'-O0',TEST,obj,*MODELS,'-Wl,--gc-sections',LIB/'libcorelib.a',LIB/'libpresonus_core_allocator.a','-lz','-lpthread','-ldl','-lm','-o',exe]);return
 target=REQ['targets'][0]
 if a.mode=='symbols':assert target['mangled'] in {x.split()[-1] for x in run(['/usr/bin/nm','--defined-only',obj]).splitlines() if x.split()};return
 import native
 fresh=native.generate(exe);fixture=json.loads((BASE/'fixtures.json').read_text());assert fresh==fixture
 if a.mode=='native':print(len(fixture['cases']),'fresh native/provider sequences');return
 assert a.mode=='replay';count=0
 for c in fixture['cases']:
  payload=f'{native.KIND} {c["scenario"]}\n'
  for action in c['sequence']:
   if 'mutate' in action:payload+=action['mutate']+'\n'
   else:payload+='CALL '+' '.join(map(str,action['call']))+'\nREPORT\n'
  out=run([exe],input=payload).splitlines();expect=[];i=0
  for action in c['sequence']:
   expect.append('1')
   if 'call' in action:expect.append(c['expected'][i]);i+=1
  assert out==expect,(c['scenario'],c['sequence'],out,expect);count+=i
 run([FMT,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',HDR,SRC,TEST]);assert target['mangled'] in {x.split()[-1] for x in run(['/usr/bin/nm','--defined-only',obj]).splitlines() if x.split()}
 domain=fixture['scope'];limits=['Original ordinary return declarations, complete fields/inheritance/vtable and ARM ABI remain unresolved. New declarations use provisional void; original constructors not reconstructed or credited.','Original application caller and full original non-Core i2f closure execute where applicable. Actual CCL and existing canonical model are source providers, not original binary behavior claims; no Core firmware body execution.','ParamArrayAccessor safe signed index-addition domain only; default null ConstVector error sentinel. Parameters and metadata remain live. Bounded post-cache append/null/alias mutation is restored before teardown; no ownership transfer, concurrency, observers mutating membership, allocation failure or hardware covered.','Observer value snapshots/MIDI bytes and native cache writes/receiver calls compared in bounded cases; C++ private accessor lookup call count is source-reviewed and miss/position behavior tested, not separately instrumented original-layout parity.','Root owns canonical integration, fresh active-source bindings and guarded SQLite admission.']
 deps=[HDR,SRC,'uc-library/include/presonus/MackieControlModel.hpp',*MODELS];sources={str(pathlib.Path(p).relative_to('uc-library')):sha(ROOT/p) for p in deps};providers={p:sha(ROOT/p) for p in PROVIDERS};entry=dict(original_elf_sha256=target['original_elf_sha256'],mangled=target['mangled'],sources=sources,repository_sources=providers,domain=domain,portable_ready=False,declaration_uncertainties=limits[:1],cpp_compiled=True,mangling_namespace_checked=True)
 proof=dict(error_sentinel_identities=fixture['error_sentinel_identities'],version=1,task_id=TASK,producer_session_id=os.environ.get('CODEX_THREAD_ID'),phase_timestamps={'replay_start':start,'replay_end':now()},functions=[entry],native_sequences=len(fixture['cases']),native_calls=count,native_fixture={'path':str((BASE/'fixtures.json').relative_to(ROOT)),'sha256':sha(BASE/'fixtures.json')},original_elf_sha256=fixture['elf_sha256'],native_ranges=fixture['helper_ranges']+[fixture['target_range']],constructor_peers_static_only=fixture['constructor_peers_static_only'],formatter_version=run([FMT,'--version']).strip(),compiler_version=run(['/usr/bin/c++','--version']).splitlines()[0],native_producer_sha256=sha(BASE/'native.py'),replay_producer_sha256=sha(__file__),unicorn_version=__import__('unicorn').__version__,source_sha256={p:sha(ROOT/p) for p in deps+[TEST]},provider_sources=providers,provider_archives={str(LIB/x):sha(ROOT/LIB/x) for x in ['libcorelib.a','libpresonus_core_allocator.a']},arm_differential_passed=True,compiled_mangled_names_matched=True,validation_domain=domain,limitations=limits,proposed_readiness=dict(canonical_binding_pending=True,ready=[],pending=[entry]),executable={'path':str(exe),'sha256':sha(exe)},object={'path':str(obj),'sha256':sha(obj)})
 proof['producer_inputs']={str(BASE.relative_to(ROOT)/x):sha(BASE/x) for x in ['native.py','check.py','Replay.cpp','fixtures.json']}
 proof['producer_inputs'].update({str(PACKET.relative_to(ROOT)/x):sha(PACKET/x) for x in ['context.json','request.json']})
 req,ev=native.evidence(); cp=native.SNAP/req['reconstruction_contract']['path']; proof['native_contract']={'path':str(cp),'sha256':sha(cp)}
 if a.integration:
  assert a.integration.is_file();proof['integration']={'path':str(a.integration),'sha256':sha(a.integration)};proof['proposed_readiness']['canonical_binding_pending']=False
 out=a.out or SCRATCH/'local-proof.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(proof,indent=2)+'\n');print(count,'native/C++ calls; fresh proof',out)
if __name__=='__main__':main()
