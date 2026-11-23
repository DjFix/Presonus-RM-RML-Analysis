"""Hash-bound local and canonical native/provider/product lifecycle replay."""
import argparse,datetime,hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];BASE=Path(__file__).resolve().parent;TASK=BASE.name
PREFIX=Path('temp/recovery-work/trial10x2-20261115');PACKET=PREFIX/'prepared01/packets'/TASK
CANON=Path('/home/rs/projects/opencs/ai-line-analysis');SUPPLEMENT=CANON/PREFIX/'root-review/provider-supplement/PROVIDERS.json'
OUT=Path('temp/recovery-work')/TASK
SOURCE='uc-library/src/Presonus/Mixer/TapeInputComponent.cpp';HEADER='uc-library/include/presonus/mixer/TapeInputComponent.hpp'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_current_transition(args):
 if not (args.current_source_transition or args.current_source_transition_sha256):return {},None
 assert args.current_source_transition and args.current_source_transition_sha256
 receipt=Path(args.current_source_transition)
 assert sha(receipt)==args.current_source_transition_sha256
 data=json.loads(receipt.read_text())
 assert data['version']==1 and TASK in data['tests']
 assert set(data['current_sources'])=={'uc-library/include/presonus/mixer/ChannelComponent.hpp', 'uc-library/src/Presonus/Mixer/ChannelComponent.cpp'}
 for ref in data['previous_worker_proofs'].values():
  assert sha(ref['path'])==ref['sha256']
 previous_checker=data['previous_checkers'][TASK]
 assert sha(previous_checker['path'])==previous_checker['sha256']
 return data['current_sources'],dict(path=str(receipt),sha256=args.current_source_transition_sha256,previous_checker=previous_checker)

def current_input(path,historical,changes):
 if path not in changes:return historical
 row=changes[path]
 assert historical==row['previous_sha256']
 assert sha(row['previous_frozen_read_path'])==historical
 assert sha(row['current_frozen_read_path'])==row['current_sha256']
 return row['current_sha256']

def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',nargs='?',default='replay')
 for k in ('exe','object','integration','out'):ap.add_argument('--'+k)
 ap.add_argument('--current-source-transition');ap.add_argument('--current-source-transition-sha256');args=ap.parse_args();os.chdir(ROOT);OUT.mkdir(parents=True,exist_ok=True);logs=[]
 def run(argv,**kw):
  a=list(map(str,argv));start=time.monotonic();r=subprocess.run(a,text=True,capture_output=True,**kw);logs.append(dict(argv=a,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,seconds=time.monotonic()-start));print(json.dumps(logs[-1]),flush=True);r.check_returncode();return r.stdout
 exe=Path(args.exe) if args.exe else OUT/'Replay';obj=Path(args.object) if args.object else OUT/'target.o'
 replay=str(BASE.relative_to(ROOT)/'Replay.cpp');paths=[SOURCE,HEADER,replay]
 flags=['g++','-std=c++17','-O2','-fno-rtti','-fno-sized-deallocation','-ffunction-sections','-fdata-sections','-Wno-multichar','-Iuc-library/include','-isystem','third_party/ccl-framework']
 assert sha(SUPPLEMENT)=='0e4fc25d3383ae8609932b7e25c4d28bac3ee92b9435c11e8d63b61cd29f0c18'
 approval=SUPPLEMENT.with_name('ROOT_APPROVAL.json');approval_record=json.loads(approval.read_text());assert approval_record['approved'] and approval_record['provider_manifest_sha256']==sha(SUPPLEMENT)
 provider=json.loads(SUPPLEMENT.read_text());archives=[provider['archives'][n]['frozen_read_path'] for n in ('libcorelib.a','libpresonus_core_allocator.a')]
 for n in ('libcorelib.a','libpresonus_core_allocator.a'):assert sha(provider['archives'][n]['frozen_read_path'])==provider['archives'][n]['sha256']
 if args.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+paths);return
 extras=['uc-library/src/Presonus/Mixer/ChannelComponent.cpp']
 if args.mode=='compile':
  run(flags+['-c',SOURCE,'-o',obj]);run(flags+[replay,obj]+extras+['-Wl,--gc-sections']+archives+['-pthread','-ldl','-lz','-o',exe])
  deps=set(paths+extras)
  for cpp in [SOURCE,replay]+extras:
   d=run(flags+['-M',cpp]);deps.update(p for p in d.replace('\\\n',' ').split()[1:] if p.startswith(('uc-library/','third_party/ccl-framework/')))
  reads=json.loads((ROOT/PREFIX/'READ_INPUTS-prepared01-trial10x2_tape.json').read_text());reads.update(provider['read_inputs']);transitive=SUPPLEMENT.with_name('COMPILER_TRANSITIVE_HEADERS.json');assert sha(transitive)=='4fcea37e6ec6a3ab4d7d2bf49ec246ad66d5b11c6765ad5fa8e6d7a905b9a82e';extra_reads=json.loads(transitive.read_text());assert extra_reads['approved'];reads.update(extra_reads['read_inputs'])
  for p in deps-set(paths):
   if p not in reads:raise RuntimeError('Missing frozen transitive dependency: '+p)
   assert sha(p)==reads[p]['sha256']==sha(reads[p]['frozen_read_path']),('changed dependency',p)
  (OUT/'dependencies.json').write_text(json.dumps({p:sha(p) for p in sorted(deps)},indent=2));(OUT/'compilation.json').write_text(json.dumps(logs,indent=2));return
 t=json.loads((ROOT/PACKET/'request.json').read_text())['targets'][0]
 syms=run(['nm','--defined-only',obj]);assert t['mangled'] in {l.split()[-1] for l in syms.splitlines() if l.split()}
 dis=run(['objdump','-dr',obj]);d0=dis.split('<_ZN8Presonus5Mixer18TapeInputComponentD0Ev>:')[1].split('\n\n')[0];assert '_ZdlPv' in d0 and '_ZdlPvm' not in d0
 if args.mode=='symbols':return
 from native import generate
 fixture=generate(exe)
 if args.mode=='native':(BASE/'fixtures.json').write_text(json.dumps(fixture,indent=2)+'\n');return
 assert json.loads((BASE/'fixtures.json').read_text())==fixture
 for case in fixture['cases']:
  actual=run([exe.resolve()],input=' '.join(map(str,case['inputs']))+'\n').strip();assert actual==case['expected'],(actual,case)
 run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+paths)
 prior_path=Path('uc-library/candidates')/TASK/'worker-proof.json'
 canonical=bool(args.exe or args.object or args.integration)
 prior=json.loads(prior_path.read_text()) if canonical else None
 deps=prior['source_bindings'].copy() if canonical else json.loads((OUT/'dependencies.json').read_text())
 changes,transition=load_current_transition(args)
 assert (not changes or canonical) and set(changes)<=set(deps)
 deps={p:current_input(p,d,changes) for p,d in deps.items()}
 if transition:
  name=str((BASE/'check.py').relative_to(ROOT))
  assert deps[name]==transition['previous_checker']['sha256']
  deps[name]=sha(BASE/'check.py')
 assert all(sha(p)==d for p,d in deps.items())
 for n in ('check.py','native.py','fixtures.json'):deps[str(BASE.relative_to(ROOT)/n)]=sha(BASE/n)
 limits=['Independent tagged source-port construction; original full constructor, derived members/inheritance, ARM object layout, EH and hardware behavior unresolved.','No Core binary reconstruction: original ARM target calls actual canonical ChannelComponent/CCL provider over typed host lifecycle RPC; native vptr writes checked separately; portable vptr layout differs.','Normal finite 1/2/4/8 owned-child and owned real-parameter domains; no allocation failure, exception, concurrency or device test.','Services test boundary methods are unused in destructor; borrowed state/environment/parameter remain live and unchanged.']
 entry=dict(original_elf_sha256=t['original_elf_sha256'],mangled=t['mangled'],sources={p.removeprefix('uc-library/'):d for p,d in deps.items() if p.startswith('uc-library/')},repository_sources={p:d for p,d in deps.items() if p.startswith('third_party/')},domain=fixture['domain'],cpp_compiled=True,mangling_namespace_checked=True,portable_ready=False,declaration_uncertainties=limits)
 proof=dict(version=1,task_id=TASK,producer_session_id=os.environ.get('CODEX_THREAD_ID'),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_bindings=deps,functions=[entry],proposed_readiness=dict(ready=[],pending=[entry],canonical_binding_pending=args.integration is None),original_range={k:v for k,v in fixture.items() if k not in ('cases','domain')},fixture_sha256=sha(BASE/'fixtures.json'),case_count=len(fixture['cases']),native_tooling=dict(unicorn_version=__import__('unicorn').__version__,unicorn_module_sha256=sha(__import__('unicorn').__file__),pyelftools_version=__import__('elftools').__version__,python_executable=__import__('sys').executable),commands=logs,compilation=prior['compilation'] if canonical else json.loads((OUT/'compilation.json').read_text()),provider_supplement=dict(path=str(SUPPLEMENT),sha256=sha(SUPPLEMENT)),provider_approval=dict(path=str(approval),sha256=sha(approval)),transitive_header_approval=dict(path=str(SUPPLEMENT.with_name('COMPILER_TRANSITIVE_HEADERS.json')),sha256=sha(SUPPLEMENT.with_name('COMPILER_TRANSITIVE_HEADERS.json'))),provider_archives={p:sha(p) for p in archives},executable=dict(path=str(exe),sha256=sha(exe)),object=dict(path=str(obj),sha256=sha(obj)),cpp_compiled=True,compiled_mangled_names_matched=True,cpp_differential_passed=True,portable_ready=False,original_arm_abi_verified=False,hardware_verified=False,limitations=limits,tools=dict(formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler=run(['g++','--version']).splitlines()[0]))
 if transition:proof['current_source_transition']=transition
 if args.integration:proof['integration']=dict(path=args.integration,sha256=sha(args.integration))
 dest=Path(args.out) if args.out else OUT/'replay-proof.json';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(proof,indent=2)+'\n')
 print(TASK,len(fixture['cases']),'actual native/provider/product cases passed')
if __name__=='__main__':main()
