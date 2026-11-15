import argparse,datetime,hashlib,importlib.util,json,os,pathlib,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[4]
TASK='rolling10_next100_scenes_disconnect'
SOURCE='uc-library/src/Presonus/Surface/ScenesPageComponent.cpp'
HEADER='uc-library/include/presonus/surface/ScenesPageComponent.hpp'
TEST='uc-library/tests/recovery/'+TASK
PACKET='temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/packets/'+TASK
OWNED=[SOURCE,HEADER,TEST+'/Replay.cpp',TEST+'/native.py',TEST+'/check.py',TEST+'/fixtures.json']
FLAGS=['c++','-std=c++17','-O2','-fno-lto','-fno-rtti','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework','-Wno-multichar','-Ulinux']
CANON=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
ARCHIVES=[CANON/'upstream-core/sdk/lib/libcorelib.a',CANON/'upstream-core/sdk/lib/libpresonus_core_allocator.a']
CCL=['third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/coreparaminfo.h','third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/public/corevector.h']
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='all',choices=['all','format','compile','symbols','replay']);p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');a=p.parse_args()
 work=ROOT/'temp/recovery-work'/TASK;work.mkdir(parents=True,exist_ok=True);exe=pathlib.Path(a.exe).resolve() if a.exe else work/'replay';obj=pathlib.Path(a.object).resolve() if a.object else work/'production.o';checks=[];start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 def run(argv,input=None):
  argv=list(map(str,argv));t=time.monotonic();r=subprocess.run(argv,cwd=ROOT,input=input,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(work)});checks.append(dict(argv=argv,returncode=r.returncode,seconds=time.monotonic()-t,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,(argv,r.stdout,r.stderr);return r.stdout
 if a.mode in ('all','format'):run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',SOURCE,HEADER,TEST+'/Replay.cpp'])
 if a.mode in ('all','compile') and not a.exe:
  run([*FLAGS,'-c',SOURCE,'-o',obj]);run([*FLAGS,TEST+'/Replay.cpp',obj,'-Wl,--gc-sections','-Wl,--start-group',*ARCHIVES,'-Wl,--end-group','-lpthread','-ldl','-o',exe])
 assert sha(ARCHIVES[0])=='3c4f0825acb529fda135587b7ff5cb92ca0100bb417a20c034d3fdef80a93e0c'
 assert sha(ARCHIVES[1])=='69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d'
 req=json.loads((ROOT/PACKET/'request.json').read_text());name=req['targets'][0]['mangled']
 if a.mode in ('all','symbols','replay'):
  symbols={x.split()[-1] for x in run(['nm','--defined-only',obj]).splitlines() if x.split()};assert name in symbols
 if a.mode in ('all','replay'):
  spec=importlib.util.spec_from_file_location('native_oracle',ROOT/TEST/'native.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native);fixture=json.loads((ROOT/TEST/'fixtures.json').read_text());assert native.generate(exe)==fixture
  payload=''.join(native.payload(c['input']) for c in fixture['cases']);result=run([exe],payload);assert result.splitlines()==[c['provider_effects'] for c in fixture['cases']]
  domain=f"{len(fixture['cases'])} original ARM executions covering empty, sparse, mixed Numeric/String/Alias vectors, null/non-null originals, duplicates, repeated calls and sizes through129. Actual provider cast observations feed original RTTI adaptation; native ordered setOriginal trace drives independent actual provider effects, compared with production effects including observers and retained original connections."
  limits=[fixture['limitations']]
  sources={str(pathlib.Path(x).relative_to('uc-library')):sha(ROOT/x) for x in OWNED}
  repository={x:sha(ROOT/x) for x in CCL}
  target=req['targets'][0];pending=dict(original_elf_sha256=target['original_elf_sha256'],mangled=name,sources=sources,repository_sources=repository,domain=domain,portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,declaration_uncertainties=limits)
  proof=dict(version=1,task_id=TASK,originals=req['targets'],source_hashes=sources,repository_sources=repository,provider_archives={str(x):sha(x) for x in ARCHIVES},native_ranges=[fixture['range']],original_type_identities=fixture['identities'],native_case_count=len(fixture['cases']),validation_domain=domain,limitations=limits,checks=checks,formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler=run(['c++','--version']).splitlines()[0],unicorn=__import__('unicorn').__version__,object=dict(path=str(obj),sha256=sha(obj)),executable=dict(path=str(exe),sha256=sha(exe)),integration=dict(path=a.integration,sha256=sha(a.integration)) if a.integration else None,canonical_binding_pending=not bool(a.integration),proposed_readiness=dict(canonical_binding_pending=True,ready=[],pending=[pending]),session=dict(provider_thread_id=os.getenv('CODEX_THREAD_ID'),application_session_id=os.getenv('CODEX_SESSION_ID'),phase_start_utc=start,phase_end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
  out=pathlib.Path(a.out) if a.out else ROOT/'uc-library/candidates'/TASK/'worker-proof.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(proof,indent=2)+'\n');print(domain)
if __name__=='__main__':main()
