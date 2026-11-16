"""Fresh range-verified native / actual CCL provider / current app replay."""
import argparse,datetime,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import native
ROOT=Path(__file__).resolve().parents[4]
TEST=Path(__file__).resolve().parent
TASK='trial10x2_groupobserver_01'
VARIANT='C1'
BASE=native.B
SUP=BASE/'root-review/provider-supplement/PROVIDERS.json'
SUP_SHA='0e4fc25d3383ae8609932b7e25c4d28bac3ee92b9435c11e8d63b61cd29f0c18'
OWNED=['uc-library/include/presonus/mixer/GroupChangeObserver.hpp','uc-library/src/Presonus/Mixer/GroupChangeObserver.cpp']
FLAGS=['-std=c++17','-O2','-Wno-multichar','-UNDEBUG','-ffunction-sections','-fdata-sections','-fno-lto','-fno-rtti','-Ulinux','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Iuc-library/include','-Ithird_party/ccl-framework']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
RUNS=[]
def run(argv,stdin=None):
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();before=time.monotonic()
 p=subprocess.run(list(map(str,argv)),cwd=ROOT,input=stdin,text=True,capture_output=True)
 RUNS.append({'argv':list(map(str,argv)),'started_utc':started,'seconds':time.monotonic()-before,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'stdin':stdin})
 if p.returncode:raise RuntimeError(str(argv)+'\n'+p.stdout+p.stderr)
 return p.stdout
DOMAIN='Separately checked 112-byte original constructor range and 56-byte callback. 43 live executions (including ten non-destroyed callbacks with null ignored parameter): real channel tag25, 0/1/3 preexisting observers, signed extreme/negative/0..7/INT_MAX messages; real CCL registration, numeric parameter signal, callback, borrowed pointer update queue identity, detach and subsequent value notification/cleanup. Two native unchecked invalid boundaries null channel/missing tag25 are explicitly adapted to portable invalid_argument rejection; no native EH equivalence.'
LIMITS=['Portable source port only; original inheritance/member layout, return declarations, ARM ABI and hardware unresolved.','Core bodies are never executed from ELF; pinned CCL provider is independently exercised. Native hooks capture app boundary operations only.','Injected actual provider observer-vector bad_alloc cleanup tested only as source-port; no original full destructor/EH/unwind/deallocation credit. Explicit detach plus CCL base destructor is source-port lifecycle. Borrowed channel/manager must remain live until detach; no concurrent mutation or reentrant provider replacement.','Allocation failure and provider exceptions outside successful registration not native-validated; invalid required bindings intentionally throw before undefined original provider accesses.','Callback is required helper implementation, not an extra selected/admitted target. Native C1/C2 bodies differ in branch encodings and occupy distinct ranges; host compiler may emit C1/C2 aliases, no original alias claim.']
def providers():
 assert sha(SUP)==SUP_SHA
 data=json.load(open(SUP));read=dict(data['read_inputs']);read.update(native.READ)
 snap=json.load(open(BASE/'prepared01/SNAPSHOT.json'))
 for p in ['third_party/ccl-framework/core/public/corestringbuffer.h','third_party/ccl-framework/core/public/corestringtraits.h','third_party/ccl-framework/core/public/coretypes.h']:
  read[p]={'sha256':snap['files'][p],'frozen_read_path':str(BASE/'prepared01/snapshot'/p)}
 for p,item in read.items():
  f=Path(item['frozen_read_path']);assert sha(f)==item['sha256'],p
 # Only captured local provider/app files may be compiled. Validate generated
 # dependencies against this merged explicit immutable input manifest below.
 libs=[]
 for name in ['libpresonus_rm_components.a','libcorelib.a','libpresonus_core_allocator.a','libpresonus_private_glibc29.a']:
  item=data['archives'][name];assert sha(item['frozen_read_path'])==item['sha256'];libs.append(item['frozen_read_path'])
 return data,read,libs


def _current_canonical_binding(root, obj, exe, integration, source, providers=()):
 from pathlib import Path
 if not integration or Path(integration).resolve() != (root/'uc-library/validation/integration.json').resolve():return None
 assert obj and exe, 'Canonical replay requires explicit actual object and executable'
 import importlib.util
 helper=root/'uc-library/tools/recovery/canonical_compile_bindings.py'
 spec=importlib.util.spec_from_file_location('actual_canonical_bindings',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 value=module.bind(root,Path(obj),source,exe_path=Path(exe),required_provider_sources=providers,required_archive_names=('libcorelib.a','libpresonus_core_allocator.a'))
 unexpected=[p for p in value['files'] if p.startswith('third_party/ccl-framework/') and not p.startswith('third_party/ccl-framework/core/')]
 assert not unexpected, ('Unexpected non-Core CCL inputs',unexpected)
 core={p:h for p,h in value['files'].items() if p.startswith('third_party/ccl-framework/core/')}
 library={p.removeprefix('uc-library/'):h for p,h in value['files'].items() if p.startswith('uc-library/')}
 assert core and source.removeprefix('uc-library/') in library, 'Actual canonical production/Core closure required'
 return {'binding':value,'sources':library,'repository_sources':core,'helper_sha256':hashlib.sha256(helper.read_bytes()).hexdigest()}

def _attach_current_canonical(proof, current):
 if current is None:return
 proof['actual_canonical_compile_binding']=current['binding']
 proof['canonical_producer_helper_sha256']=current['helper_sha256']
 proof['canonical_source_binding_scope']='Current actual Release object/depfile/link/archive inputs; historical frozen dependency expectations retained in original archived producer/proof, not refreshed or relabeled'
 proof['historical_provider_archives']=proof.get('provider_archives')
 proof['provider_archives']={v['path']:v['sha256'] for v in current['binding']['link']['archives']}
 proof['local_compile_defaults']=proof.get('compile_flags')
 proof['actual_canonical_compile_entries']=[x['compile_entry'] for x in current['binding']['objects']]
 proof['actual_canonical_sources']=current['sources']
 proof['actual_canonical_repository_sources']=current['repository_sources']
 for row in [*proof.get('proposed_readiness',{}).get('ready',[]),*proof.get('proposed_readiness',{}).get('pending',[])]:
  row.setdefault('sources',{}).update(current['sources'])
  repository=__import__('pathlib').Path(__file__).resolve().parents[4]
  for p,h in row['sources'].items():
   relative=__import__('pathlib').Path(p)
   assert not relative.is_absolute() and '..' not in relative.parts, ('Invalid library source binding',p)
   assert hashlib.sha256((repository/'uc-library'/relative).read_bytes()).hexdigest()==h, ('Retained library source binding changed outside actual closure',p)
  prior=row.setdefault('repository_sources',{})
  assert all(p.startswith('third_party/ccl-framework/core/') for p in prior), 'Unexpected prior non-Core repository dependency'
  repository=__import__('pathlib').Path(__file__).resolve().parents[4]
  for p,h in prior.items():assert hashlib.sha256((repository/p).read_bytes()).hexdigest()==h, ('Prior verified Core implementation changed',p)
  for p,h in current['repository_sources'].items():
   assert p not in prior or prior[p]==h, ('Conflicting verified Core source binding',p)
  prior.update(current['repository_sources'])

def main(task=TASK,variant=VARIANT,test=TEST):
 a=argparse.ArgumentParser();a.add_argument('mode',nargs='?',default='replay',choices=['format','compile','symbols','replay']);a.add_argument('--exe',type=Path);a.add_argument('--object',type=Path);a.add_argument('--integration',type=Path);a.add_argument('--out',type=Path);args=a.parse_args();os.chdir(ROOT)
 out=ROOT/'temp/recovery-work'/task;out.mkdir(parents=True,exist_ok=True)
 obj=args.object or out/'GroupChangeObserver.o';exe=(args.exe or out/'replay').resolve()
 replay=test/'Replay.cpp';fmt=['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED,str(replay)]
 if args.mode=='format':run(fmt);print('PASS format');return
 canonical_binding=_current_canonical_binding(ROOT,args.object,args.exe,args.integration,OWNED[1],('uc-library/src/Presonus/Mixer/AutoFilterGroupManager.cpp',))
 data,read,libs=providers()
 if args.mode=='compile':
  objects=[]
  for source in [OWNED[1],'uc-library/src/Presonus/Mixer/AutoFilterGroupManager.cpp',str(replay)]:
   dest=obj if source==OWNED[1] else out/(Path(source).stem+'.o')
   run(['/usr/bin/c++',*FLAGS,'-MMD','-MF',str(dest)+'.d','-c',source,'-o',dest]);objects.append(dest)
  run(['/usr/bin/c++',*objects,'-Wl,--gc-sections','-Wl,--start-group',*libs,'-Wl,--end-group',*[item['path'] for item in data['system_libraries']],'-lpthread','-ldl','-lm','-o',exe]);(out/'compile.json').write_text(json.dumps({'commands':RUNS,'sources':{p:sha(p) for p in OWNED},'object':{'path':str(obj),'sha256':sha(obj)},'exe':{'path':str(exe),'sha256':sha(exe)}},indent=2)+'\n');print('PASS compile actual provider');return
 original=json.load(open(ROOT/f'temp/recovery-work/trial10x2-20261115/prepared01/packets/{task}/request.json'))['targets'][0]
 symbols=run(['nm','--defined-only',obj]);assert original['mangled'] in {l.split()[-1] for l in symbols.splitlines() if l.split()}
 if args.mode=='symbols':print(symbols);return
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();before=time.monotonic();run(fmt)
 fixture=json.load(open(test/'fixtures.json'));fresh=native.generate(variant);assert fresh==fixture,'fresh original fixture mismatch'
 results=[]
 for case in fresh['cases']:
  parameters=list(map(str,case['args']));observed=run([exe,'application',*parameters])
  if case['native']['invalid']:
   assert observed=='rejected 1\n';expected=observed
  else:
   op=case['native']['events'][-1][0];assert op in ('update','remove')
   expected=run([exe,'provider',*parameters],op+'\n');assert observed==expected,(parameters,expected,observed)
  results.append(dict(args=case['args'],native_operations=case['native']['events'],source_provider_and_product_output=observed))
 lifecycle=[]
 for count in [0,1,3]:
  for scenario in ['destroy','observer-first']:
   parameters=['1',str(count),'5',scenario]
   observed=run([exe,'application',*parameters])
   expected=run([exe,'provider',*parameters],'remove\n')
   assert observed==expected,(scenario,count,observed,expected)
   lifecycle.append({'scenario':scenario,'existing_observers':count,'actual_provider_and_product_output':observed,'native_callback_message':5 if scenario=='destroy' else None})
 allocation=run([exe,'application','1','0','5','allocation']);assert allocation=='allocation 1 0 0\n'
 files=set(OWNED)|{'uc-library/src/Presonus/Mixer/AutoFilterGroupManager.cpp',str(replay.relative_to(ROOT))}
 # Query the actual current compiler closure even on a clean canonical build.
 # Supplied binaries are used above; optional scratch depfiles are never evidence.
 if canonical_binding is None:
  dependency_queries=[]
  for source in [OWNED[1],'uc-library/src/Presonus/Mixer/AutoFilterGroupManager.cpp',str(replay)]:
   argv=['/usr/bin/c++',*FLAGS,'-MM','-MT','dependency',source]
   output=run(argv);dependency_queries.append({'argv':argv,'output':output})
   assert ':' in output,('empty compiler dependency query',source)
   for name in output.replace('\\\n',' ').split(':',1)[1].split():
    absolute=(ROOT/Path(name)).resolve()
    assert absolute.is_relative_to(ROOT),('dependency escapes repository',name)
    relative=str(absolute.relative_to(ROOT))
    assert '..' not in Path(relative).parts and not Path(relative).is_absolute()
    assert absolute.is_file(),('missing compiler dependency',relative)
    if relative.startswith(('uc-library/','third_party/')):files.add(relative)
  for p in files:
   if p in OWNED or p.startswith('uc-library/tests/recovery/trial10x2_groupobserver_'):continue
   assert p in read,('missing captured dependency',p)
   assert sha(p)==read[p]['sha256'],('changed dependency',p)
 if canonical_binding is not None:
  files.update(canonical_binding['binding']['files'])
  dependency_queries=[{'scope':'Actual canonical compile entries and depfiles','binding':canonical_binding['binding']}]
 sources={p.removeprefix('uc-library/'):sha(p) for p in sorted(files) if p.startswith('uc-library/')}
 providersources={p:sha(p) for p in sorted(files) if p.startswith('third_party/')}
 for p in ['third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.cpp']:providersources[p]=sha(read[p]['frozen_read_path'])
 entry=dict(original_elf_sha256=native.ELF_SHA,mangled=original['mangled'],original_address=original['address'],portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,original_function_verified=False,hardware_verified=False,canonical_binding_pending=not bool(args.integration),sources=sources,repository_sources=providersources,domain=DOMAIN,declaration_uncertainties=LIMITS)
 proof=dict(version=1,task_id=task,session_id=json.load(open(ROOT/'temp/recovery-work/trial10x2-timing/groupobserver-start.json'))['session_id'],validation_start_utc=started,validation_end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),validation_seconds=time.monotonic()-before,argv=sys.argv,cpp_compiled=True,mangling_namespace_checked=True,format_check_passed=True,behavior_validation_passed=True,portable_ready=False,canonical_binding_pending=not bool(args.integration),sources=sources,repository_sources=providersources,domain=DOMAIN,limitations=LIMITS,proposed_readiness={'ready':[],'pending':[entry]},supplementary_callback_evidence={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'uc-library/candidates/trial10x2_groupobserver_01/callback-evidence').iterdir()},native=fresh,cases=results,lifecycle=lifecycle,allocation_failure_source_port_only=allocation,provider_approval={'path':str(SUP.parent/'ROOT_APPROVAL.json'),'sha256':sha(SUP.parent/'ROOT_APPROVAL.json')},object={'path':str(obj),'sha256':sha(obj)},executable={'path':str(exe),'sha256':sha(exe)},symbols=symbols,dependency_queries=dependency_queries,executed_commands=RUNS,producer_hashes={str(p.relative_to(ROOT)):sha(p) for p in set([test/n for n in ['check.py','native.py','fixtures.json','Replay.cpp']]+[TEST/n for n in ['check.py','native.py','Replay.cpp']])},provider_manifest={'path':str(SUP),'sha256':sha(SUP)},snapshot_manifest={'path':str(BASE/'prepared01/SNAPSHOT.json'),'sha256':sha(BASE/'prepared01/SNAPSHOT.json')},provider_archives={p:sha(p) for p in libs},compile_flags=FLAGS,versions={'compiler':run(['/usr/bin/c++','--version']).splitlines()[0],'formatter':run(['uc-library/.venv/bin/clang-format','--version']).strip(),'unicorn':__import__('unicorn').__version__})
 _attach_current_canonical(proof,canonical_binding)
 if args.integration:proof['integration']={'path':str(args.integration),'sha256':sha(args.integration)}
 if args.out:args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(proof,indent=2)+'\n')
 print('PASS',task,len(results),'fresh native / actual provider / current product')
if __name__=='__main__':main()
