"""Bounded replay adapter. Canonical invocation accepts --exe --object --integration --out."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[4];BASE=pathlib.Path(__file__).parent;TASK=BASE.name
SCRATCH=ROOT/'temp/recovery-work'/TASK;SCRATCH.mkdir(parents=True,exist_ok=True)
SRC='uc-library/src/Presonus/Surface/DAWLoadDocumentPage.cpp';HDR='uc-library/include/presonus/surface/DAWLoadDocumentPage.hpp';TEST=str(BASE.relative_to(ROOT)/'Replay.cpp')
PACKET=pathlib.Path('temp/recovery-work/rolling10x10-20261114/prepared05/packets')/TASK
PY='uc-library/.venv/bin/python';FMT='uc-library/.venv/bin/clang-format'
PROVIDERS=['third_party/ccl-framework/core/public/corevector.h','uc-library/include/presonus/uc/file_services.hpp']
FLAGS=['/usr/bin/c++','-std=c++17','-O0','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework']
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def run(argv,**kw):
 p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,text=True,env={**os.environ,'TMPDIR':str(SCRATCH)},**kw)
 print(json.dumps(list(map(str,argv))),flush=True)
 if p.returncode:print(p.stdout,p.stderr);p.check_returncode()
 return p.stdout

def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',nargs='?',default='replay');ap.add_argument('--exe',type=pathlib.Path);ap.add_argument('--object',type=pathlib.Path);ap.add_argument('--integration',type=pathlib.Path);ap.add_argument('--out',type=pathlib.Path);a=ap.parse_args()
 exe=a.exe or SCRATCH/'replay';obj=a.object or SCRATCH/'production.o'
 if a.mode=='format':run([FMT,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',HDR,SRC,TEST]);return
 if a.mode=='compile':
  run([*FLAGS,'-c',SRC,'-o',obj]);run([*FLAGS,TEST,obj,'-Wl,--gc-sections','-o',exe]);return
 req=json.loads((ROOT/PACKET/'request.json').read_text());target=req['targets'][0]
 if a.mode=='symbols':assert target['mangled'] in {x.split()[-1] for x in run(['/usr/bin/nm','--defined-only',obj]).splitlines() if x.split()};return
 import native
 fresh=native.generate();fixture=json.loads((BASE/'fixtures.json').read_text());assert fresh==fixture
 if a.mode=='native':print(len(fixture['cases']),'fresh native cases');return
 assert a.mode=='replay'
 payload=''.join(f"{c['count']} {c['cursor']}\n" for c in fixture['cases'])
 actual=run([exe],input=payload).splitlines();assert len(actual)==len(fixture['cases'])
 for line,c in zip(actual,fixture['cases']):
  expected=[c['result'],c['count_after'],c['cursor_after']] if TASK.endswith('01') else [c['count_after'],c['cursor_after']]
  assert list(map(int,line.split()))==expected,(c,line)
 run([FMT,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',HDR,SRC,TEST]);assert target['mangled'] in run(['/usr/bin/nm','--defined-only',obj])
 domain='195 exact original ARM cases: valid caller-owned objects, count 0..64, cursor 0/7/UINT32_MAX. '+('Read-only count preserves all object bytes, no calls. Actual CCL Vector count with initialized entries and unchanged storage/capacity/content.' if TASK.endswith('01') else 'Opaque original Core resize boundary records vector+0x38, capacity0, count/cursor before explicit resets; no Core instructions executed. Host independently exercises actual pinned Vector<Entry>::resize(0), verifies count/capacity/storage release, empty/idempotent calls and refill/clear.')
 limits=['Original int/void return declarations, inheritance, vtable and ARM object layout unresolved; portable composition only. Native observed +0x4c is represented by an unsigned portable cursor, semantic interpretation provisional.','No original constructor/destructor reconstruction or lifecycle claim: caller owns a live host model, real CCL Vector owns only its storage/Entry values. No borrowed Entry pointers or ownership transfer.','Native Core resize is an explicitly opaque boundary; its behavior is not inferred or emulated. Host uses pinned source implementation. Null/dangling this, negative/corrupt counts, concurrency, allocation failure, hardware and ARM ABI excluded.','Root owns canonical global integration and guarded readiness admission.']
 sources={str(pathlib.Path(p).relative_to('uc-library')):sha(ROOT/p) for p in [HDR,SRC]};providers={p:sha(ROOT/p) for p in PROVIDERS}
 entry=dict(original_elf_sha256=target['original_elf_sha256'],mangled=target['mangled'],sources=sources,repository_sources=providers,domain=domain,portable_ready=False,declaration_uncertainties=limits[:1],cpp_compiled=True,mangling_namespace_checked=True)
 proof=dict(version=1,created=datetime.datetime.now(datetime.timezone.utc).isoformat(),task_id=TASK,session_id='/root/rolling10_daw_list',native_fixture=dict(path=str((BASE/'fixtures.json').relative_to(ROOT)),sha256=sha(BASE/'fixtures.json')),ranges=[fixture['range']],native_cases=len(fixture['cases']),functions=[entry],arm_differential_passed=True,compiled_mangled_names_matched=True,formatter_version=run([FMT,'--version']).strip(),compiler_version=run(['/usr/bin/c++','--version']).splitlines()[0],unicorn_version=__import__('unicorn').__version__,source_sha256={p:sha(ROOT/p) for p in [HDR,SRC,TEST]},provider_sources=providers,proposed_readiness=dict(canonical_binding_pending=a.integration is None,ready=[],pending=[entry]),validation_domain=domain,limitations=limits,executable=dict(path=str(exe),sha256=sha(exe)),object=dict(path=str(obj),sha256=sha(obj)),replay_producer_sha256=sha(__file__),native_producer_sha256=sha(BASE/'native.py'))
 if a.integration:assert a.integration.is_file();proof['integration']={'path':str(a.integration),'sha256':sha(a.integration)}
 out=a.out or SCRATCH/'local-proof.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(proof,indent=2)+'\n');print(len(actual),'native/C++ cases passed; proof',out)
if __name__=='__main__':main()
