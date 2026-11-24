"""Hash-bound local and canonical checks; never updates shared state."""
import argparse,datetime,hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
BASE=Path(__file__).resolve().parent
TASK=BASE.name
CLASS='LinkableComponent'
HEADER=Path('uc-library/include/presonus')/(CLASS+'.hpp')
SOURCE=Path('uc-library/src/Presonus')/(CLASS+'.cpp')
OUT=Path('temp/recovery-work')/TASK
PACKET=Path('temp/recovery-work/rolling10x10-20261114/prepared06/packets')/TASK
PROOF=Path('uc-library/candidates')/TASK/'worker-proof.json'
LIMITS=['Original ordinary return type and pointer qualification remain unresolved.','Original object layout, inheritance, ARM ABI and hardware behavior unverified.','Actual CCL Component is explicitly composed into existing State; not original inheritance/layout. Existing application Boundary remains borrowed and unused by these storage methods. One actual shared CCL lock replaces legacy CoreLock. Native uses actual CCL-provider RPC with explicit mapped ARM object/storage/attribute identities; no binary Core or exception/unwind paths executed.']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument('mode',nargs='?',default='replay');a.add_argument('--exe');a.add_argument('--object');a.add_argument('--integration');a.add_argument('--out');a.add_argument('--source-transition', type=Path);a.add_argument('--source-transition-sha256');args=a.parse_args()
 os.chdir(ROOT);OUT.mkdir(parents=True,exist_ok=True);logs=[]
 def run(argv,**kw):
  start=time.monotonic();r=subprocess.run(list(map(str,argv)),text=True,capture_output=True,**kw);logs.append(dict(argv=list(map(str,argv)),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,seconds=time.monotonic()-start));print(json.dumps(logs[-1]),flush=True);r.check_returncode();return r.stdout
 paths=[HEADER,SOURCE,BASE.relative_to(ROOT)/'Replay.cpp']
 exe=Path(args.exe) if args.exe else OUT/'Replay';obj=Path(args.object) if args.object else OUT/(CLASS+'.o')
 if args.mode=='format':
  run(['uc-library/.venv/bin/clang-format','--version']);run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+paths);return
 if args.mode=='compile':
  flags=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-Iuc-library/include','-isystem','third_party/ccl-framework','-Wno-multichar','-fno-rtti','-Wno-misleading-indentation','-Wno-unused-parameter']
  run(flags+['-c',SOURCE,'-o',obj]);run(flags+[paths[2],obj,'uc-library/src/Presonus/AltMemoryFilter.cpp','/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','-pthread','-ldl','-lz','-o',exe]);(OUT/'compilation.json').write_text(json.dumps(logs,indent=2));return
 request=json.loads((PACKET/'request.json').read_text());t=request['targets'][0]
 snapshot=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared06/snapshot')
 contract=request['reconstruction_contract'];cp=snapshot/contract['path'];assert sha(cp)==contract['sha256'];typed=json.loads(cp.read_text());evidence={}
 for group in list(typed['requirements'].values())+typed['dependencies']:
  for ref in group.get('evidence',[]):
   ep=snapshot/ref['path'];assert sha(ep)==ref['sha256'];evidence[str(ep)]=ref['sha256']

 symbols=run(['nm','--defined-only',obj]);assert t['mangled'] in {l.split()[-1] for l in symbols.splitlines() if l.split()}
 if args.mode=='symbols':return
 from native import generate
 fixture=json.loads((BASE/'fixtures.json').read_text());assert generate(exe)==fixture
 if args.mode=='native':return
 run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+paths)
 lines=[run([str(exe.resolve())],input=' '.join(map(str,c['inputs']))+'\n').strip() for c in fixture['cases']]
 assert len(lines)==len(fixture['cases'])
 for l,c in zip(lines,fixture['cases']):assert l==c['expected'],(l,c)
 bindings={str(p):sha(p) for p in paths+[BASE.relative_to(ROOT)/n for n in ('native.py','check.py','fixtures.json')]}
 entry=dict(original_elf_sha256=t['original_elf_sha256'],mangled=t['mangled'],sources={str(Path(p).relative_to('uc-library')):v for p,v in bindings.items()},repository_sources={p:v['sha256'] for p,v in json.loads(Path('temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared06-rolling10_pages.json').read_text()).items() if p.startswith('third_party/ccl-framework/core/')},domain=fixture['domain'],portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,declaration_uncertainties=LIMITS)
 proof=dict(version=1,task_id=TASK,producer_session_id=os.environ.get('CODEX_THREAD_ID','rolling10_pages'),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_bindings=bindings,functions=[entry],proposed_readiness=dict(canonical_binding_pending=args.integration is None,ready=[],pending=[entry]),commands=logs,compilation=json.loads((OUT/'compilation.json').read_text()) if (OUT/'compilation.json').exists() else [],original_range={k:fixture[k] for k in ('elf_sha256','address','size','section','file_offset','range_sha256')},native_fixture_sha256=sha(BASE/'fixtures.json'),case_count=len(lines),cpp_differential_passed=True,compiled_mangled_names_matched=True,cpp_compiled=True,portable_ready=False,original_arm_abi_verified=False,hardware_verified=False,limitations=LIMITS,executable=dict(path=str(exe),sha256=sha(exe)),object=dict(path=str(obj),sha256=sha(obj)),tools=dict(formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler=run(['g++','--version']).splitlines()[0]))
 proof['provider_archives']={p:sha(p) for p in ['/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a']}
 addendum=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/root-review/generation06/addenda/pages-filter.json');supplement=json.loads(addendum.read_text());assert sha(addendum)=='a52849ca893b37a103ec8698df23a4d58ed649ff9919e27b0b21b6201d8347a9'
 assert bool(args.source_transition)==bool(args.source_transition_sha256)
 approved_transitions={}
 if args.source_transition:
  assert sha(args.source_transition)==args.source_transition_sha256
  transition=json.loads(args.source_transition.read_text())
  predecessor=transition['previous_addendum']
  assert predecessor['sha256']==sha(predecessor['path'])==sha(addendum)
  for row in transition['source_transitions']:
   path='uc-library/'+row['path']
   original=supplement['files'][path]
   assert path not in approved_transitions and row['previous_sha256']==original['sha256']
   assert sha(row['previous_frozen_read_path'])==row['previous_sha256']
   assert sha(row['current_frozen_read_path'])==row['current_sha256']
   approved_transitions[path]=row['current_sha256']
  proof['current_source_transition']=dict(path=str(args.source_transition),sha256=args.source_transition_sha256)
 for dep,rec in supplement['files'].items():
  expected=approved_transitions.get(dep,rec['sha256'])
  if args.source_transition:
   assert sha(rec['frozen_read_path'])==rec['sha256']
   assert sha(dep)==expected
  else:
   assert sha(rec['workspace_path'])==expected
  for item in proof['functions']:
   item['sources' if dep.startswith('uc-library/') else 'repository_sources'][str(Path(dep).relative_to('uc-library')) if dep.startswith('uc-library/') else dep]=expected
 proof['filter_addendum']=dict(path=str(addendum),sha256=sha(addendum));proof['typed_contract']=dict(path=str(cp),sha256=sha(cp));proof['typed_evidence']=evidence;proof['native_provider_domain']='Original non-Core target executes; original Core code excluded. RPC provider mode has actual CCL Component with empty params/children, real Attributes nested/int/string operations, CCL lock and pool suspension. Actual Component cancellation failure/success tested for save; concurrency/exceptions excluded.'
 if args.integration:proof['integration']=dict(path=args.integration,sha256=sha(args.integration))
 dest=Path(args.out) if args.out else PROOF;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(proof,indent=2)+'\n')
 print(f'{TASK}: {len(lines)} native/C++ differential cases passed')
if __name__=='__main__':main()
