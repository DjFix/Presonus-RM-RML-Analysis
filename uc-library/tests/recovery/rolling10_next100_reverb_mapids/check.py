import argparse,datetime,hashlib,importlib.util,json,os,pathlib,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[4]
TASK='rolling10_next100_reverb_mapids'
SOURCE='uc-library/src/Presonus/Mixer/ReverbComponent.cpp'
HEADER='uc-library/include/presonus/mixer/ReverbComponent.hpp'
TEST='uc-library/tests/recovery/'+TASK
PACKET='temp/recovery-work/rolling10x10-20261114/prepared06/packets/'+TASK
OWNED=[SOURCE,HEADER,TEST+'/Replay.cpp',TEST+'/native.py',TEST+'/check.py',TEST+'/fixtures.json']
FLAGS=['c++','-std=c++17','-O2','-fno-lto','-fno-rtti','-ffunction-sections','-fdata-sections','-Iuc-library/include']
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='all',choices=['all','format','compile','symbols','replay']);p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');a=p.parse_args()
 work=ROOT/'temp/recovery-work'/TASK;work.mkdir(parents=True,exist_ok=True);exe=pathlib.Path(a.exe).resolve() if a.exe else work/'replay';obj=pathlib.Path(a.object).resolve() if a.object else work/'production.o';checks=[];start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 def run(argv,input=None):
  argv=list(map(str,argv));t=time.monotonic();r=subprocess.run(argv,cwd=ROOT,input=input,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(work)});checks.append(dict(argv=argv,returncode=r.returncode,seconds=time.monotonic()-t,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,(argv,r.stdout,r.stderr);return r.stdout
 if a.mode in ('all','format'):run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',SOURCE,HEADER,TEST+'/Replay.cpp'])
 if a.mode in ('all','compile') and not a.exe:
  run([*FLAGS,'-c',SOURCE,'-o',obj]);run([*FLAGS,TEST+'/Replay.cpp',obj,'-Wl,--gc-sections','-o',exe])
 req=json.loads((ROOT/PACKET/'request.json').read_text());name=req['targets'][0]['mangled']
 if a.mode in ('all','symbols','replay'):
  symbols={x.split()[-1] for x in run(['nm','--defined-only',obj]).splitlines() if x.split()};assert name in symbols
 if a.mode in ('all','replay'):
  spec=importlib.util.spec_from_file_location('native_oracle',ROOT/TEST/'native.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native);fixture=json.loads((ROOT/TEST/'fixtures.json').read_text());assert native.generate()==fixture
  payload=''.join(str(int(c['receiver']!=0x1000000))+' '+str(c['selector'])+'\n' for c in fixture['cases']);result=run([exe],payload);assert list(map(int,result.split()))==[c['result'] for c in fixture['cases']]
  domain=f"{len(fixture['cases'])} original ARM executions across two receivers, every selector -32..64, all 15 switch entries, signed32 extremes/wrapping-subtraction boundaries and 256 deterministic random selectors per receiver; exact result and stack-only writes; no external providers. Unsigned guard plus closed table partition covers all selector classes structurally, not exhaustive execution."
  limits=[fixture['limitations'],'Original unencoded return spelling remains unresolved; int is provisional. SourcePortConstruction is independent and no original lifecycle/inheritance/layout or ARM ABI claim. Existing getSelectTypeMap implementation preserved; no new readiness credit.']
  sources={str(pathlib.Path(x).relative_to('uc-library')):sha(ROOT/x) for x in OWNED}
  target=req['targets'][0];pending=dict(original_elf_sha256=target['original_elf_sha256'],mangled=name,sources=sources,repository_sources={},domain=domain,portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,declaration_uncertainties=limits)
  proof=dict(version=1,task_id=TASK,originals=req['targets'],source_hashes=sources,repository_sources={},native=fixture['range'],jump_table=fixture['jump_table'],native_case_count=len(fixture['cases']),validation_domain=domain,limitations=limits,checks=checks,formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler=run(['c++','--version']).splitlines()[0],unicorn=__import__('unicorn').__version__,object=dict(path=str(obj),sha256=sha(obj)),executable=dict(path=str(exe),sha256=sha(exe)),integration=dict(path=a.integration,sha256=sha(a.integration)) if a.integration else None,canonical_binding_pending=not bool(a.integration),proposed_readiness=dict(canonical_binding_pending=True,ready=[],pending=[pending]),session=dict(provider_thread_id=os.getenv('CODEX_THREAD_ID'),application_session_id=os.getenv('CODEX_SESSION_ID'),phase_start_utc=start,phase_end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
  out=pathlib.Path(a.out) if a.out else ROOT/'uc-library/candidates'/TASK/'worker-proof.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(proof,indent=2)+'\n');print(domain)
if __name__=='__main__':main()
