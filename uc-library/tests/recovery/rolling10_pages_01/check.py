"""Hash-bound local and canonical checks; never updates shared state."""
import argparse,datetime,hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
BASE=Path(__file__).resolve().parent
TASK=BASE.name
CLASS='PageComponent'
HEADER=Path('uc-library/include/presonus')/(CLASS+'.hpp')
SOURCE=Path('uc-library/src/Presonus')/(CLASS+'.cpp')
OUT=Path('temp/recovery-work')/TASK
PACKET=Path('temp/recovery-work/rolling10x10-20261114/prepared05/packets')/TASK
PROOF=Path('uc-library/candidates')/TASK/'worker-proof.json'
LIMITS=['Original ordinary return type and pointer qualification remain unresolved.','Original object layout, inheritance, ARM ABI and hardware behavior unverified.','Original C1/C2 calls establish CStringBuffer<32> initialization at +144 from constructor second argument. Source-port state uses pinned CCL CString32 and fixture text length0..31. Original getter return spelling remains unresolved. Getter returns a stable borrowed member buffer; original +144 offset is normalized to member identity, not matched to host layout. Source-port CCL buffer setup is independently exercised; target has no providers. Test bindings abort if unexpectedly called.']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument('mode',nargs='?',default='replay');a.add_argument('--exe');a.add_argument('--object');a.add_argument('--integration');a.add_argument('--out');args=a.parse_args()
 os.chdir(ROOT);OUT.mkdir(parents=True,exist_ok=True);logs=[]
 def run(argv,**kw):
  start=time.monotonic();r=subprocess.run(list(map(str,argv)),text=True,capture_output=True,**kw);logs.append(dict(argv=list(map(str,argv)),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,seconds=time.monotonic()-start));print(json.dumps(logs[-1]),flush=True);r.check_returncode();return r.stdout
 paths=[HEADER,SOURCE,BASE.relative_to(ROOT)/'Replay.cpp']
 exe=Path(args.exe) if args.exe else OUT/'Replay';obj=Path(args.object) if args.object else OUT/(CLASS+'.o')
 if args.mode=='format':
  run(['uc-library/.venv/bin/clang-format','--version']);run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+paths);return
 if args.mode=='compile':
  flags=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-Iuc-library/include','-isystem','third_party/ccl-framework','-Wno-multichar','-fno-rtti']
  run(flags+['-c',SOURCE,'-o',obj]);run(flags+[paths[2],obj,'/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','-pthread','-ldl','-o',exe]);(OUT/'compilation.json').write_text(json.dumps(logs,indent=2));return
 request=json.loads((PACKET/'request.json').read_text());t=request['targets'][0]
 symbols=run(['nm','--defined-only',obj]);assert t['mangled'] in {l.split()[-1] for l in symbols.splitlines() if l.split()}
 if args.mode=='symbols':return
 from native import generate
 fixture=json.loads((BASE/'fixtures.json').read_text());assert generate()==fixture
 if args.mode=='native':return
 run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+paths)
 lines=run([str(exe.resolve())],input=''.join(f"{c['input_hex'] or '-'} {c['object']}\n" for c in fixture['cases'])).splitlines()
 assert len(lines)==len(fixture['cases'])
 for l,c in zip(lines,fixture['cases']):assert l==(c['observed_hex'] or '-'),(l,c)
 bindings={str(p):sha(p) for p in paths+[BASE.relative_to(ROOT)/n for n in ('native.py','check.py','fixtures.json')]}
 entry=dict(original_elf_sha256=t['original_elf_sha256'],mangled=t['mangled'],sources={str(Path(p).relative_to('uc-library')):v for p,v in bindings.items()},repository_sources={p:sha(p) for p in ['third_party/ccl-framework/core/public/corestringbuffer.h','third_party/ccl-framework/core/public/corestringtraits.h']},domain=fixture['domain'],portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,declaration_uncertainties=LIMITS)
 proof=dict(version=1,task_id=TASK,producer_session_id=os.environ.get('CODEX_THREAD_ID','rolling10_pages'),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_bindings=bindings,functions=[entry],proposed_readiness=dict(canonical_binding_pending=args.integration is None,ready=[],pending=[entry]),commands=logs,compilation=json.loads((OUT/'compilation.json').read_text()) if (OUT/'compilation.json').exists() else [],original_range={k:fixture[k] for k in ('elf_sha256','address','size','section','file_offset','range_sha256')},native_fixture_sha256=sha(BASE/'fixtures.json'),case_count=len(lines),cpp_differential_passed=True,compiled_mangled_names_matched=True,cpp_compiled=True,portable_ready=False,original_arm_abi_verified=False,hardware_verified=False,limitations=LIMITS,executable=dict(path=str(exe),sha256=sha(exe)),object=dict(path=str(obj),sha256=sha(obj)),tools=dict(formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler=run(['g++','--version']).splitlines()[0]))
 proof['provider_archives']={p:sha(p) for p in ['/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a']}
 if args.integration:proof['integration']=dict(path=args.integration,sha256=sha(args.integration))
 dest=Path(args.out) if args.out else PROOF;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(proof,indent=2)+'\n')
 print(f'{TASK}: {len(lines)} native/C++ differential cases passed')
if __name__=='__main__':main()
