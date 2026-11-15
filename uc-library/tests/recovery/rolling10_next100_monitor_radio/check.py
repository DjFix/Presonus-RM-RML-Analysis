"""Fresh native/source-provider validation and supplied canonical output replay."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[4];NAME=pathlib.Path(__file__).parent.name
TEST=pathlib.Path('uc-library/tests/recovery')/NAME;SCRATCH=pathlib.Path('temp/recovery-work')/NAME
PACKET=pathlib.Path('temp/recovery-work/rolling10x10-20261114/prepared06/packets')/NAME
if 'mixer_base' in NAME:HEADER='uc-library/include/presonus/mixer/AutoFilterGroupManager.hpp';SOURCE='uc-library/src/Presonus/Mixer/AutoFilterGroupManager.cpp'
elif 'fatled' in NAME:HEADER='uc-library/include/presonus/panel/FATLEDOverridePage.hpp';SOURCE='uc-library/src/Presonus/Panel/FATLEDOverridePage.cpp'
else:HEADER='uc-library/include/presonus/surface/MonitorPageComponent.hpp';SOURCE='uc-library/src/Presonus/Surface/MonitorPageComponent.cpp'
CPP=[HEADER,SOURCE,str(TEST/'Replay.cpp')]
PROVIDERS=['third_party/ccl-framework/core/public/corevector.h']
if 'mixer_base' not in NAME:PROVIDERS+=['third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/coreparaminfo.h','third_party/ccl-framework/core/portable/coretypeinfo.h']
FLAGS=['/usr/bin/c++','-std=c++17','-O2','-fno-rtti','-DNDEBUG=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-DCORE_USE_OPENSSL=1','-Ulinux','-Wno-multichar','-ffunction-sections','-fdata-sections','-pthread','-Iuc-library/include','-Ithird_party/ccl-framework']
def digest(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def run(argv,**kwargs):
 start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=ROOT,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(ROOT/SCRATCH)},**kwargs)
 d=dict(argv=list(map(str,argv)),returncode=p.returncode,stdout=p.stdout,stderr=p.stderr,seconds=time.monotonic()-start)
 if p.returncode:raise RuntimeError(json.dumps(d))
 return d

def compile():
 cmds=[run(FLAGS+['-c',SOURCE,'-o',SCRATCH/'production.o'])]
 # All app code is compiled here from verified current owned sources. Only
 # pinned upstream Core and allocator archives are linked, never old app archives.
 libs=[] if 'mixer_base' in NAME else ['-Wl,--start-group','temp/provider-baseline08/libcorelib.a','temp/provider-baseline08/libpresonus_core_allocator.a','-Wl,--end-group','-lz','-lssl','-lcrypto','-ldl','-lm']
 cmds.append(run(FLAGS+[str(TEST/'Replay.cpp'),str(SCRATCH/'production.o'),'-Wl,--gc-sections',*libs,'-o',str(SCRATCH/'replay')]))
 (ROOT/SCRATCH/'compile.json').write_text(json.dumps(cmds,indent=2)+'\n');return cmds

def payload(case,variant=0,direct=False):
 i=case['input'];calls=[x for x in case['trace'] if x[0]=='setValue'];tokens=[]
 if 'mixer_base' in NAME:return ' '.join(map(str,[i['capacity'],int(i['fail']),len(i['seed']),i['pointer'],*i['seed']]))
 if 'fatled' in NAME:tokens=[int(i['present']),i['initial'],i['min'],i['max'],len(calls)]
 else:tokens=[i['selected'],i['first'],i['last'],len(i['tags']),len(calls),variant,*i['tags']]
 if direct:
  for _,identity,bits,edit in calls:tokens.extend(([identity] if 'monitor' in NAME else [])+[bits,edit])
 return ' '.join(map(str,tokens))

def replay(exe):
 f=json.loads((ROOT/TEST/'fixtures.json').read_text());cases=f['cases'];variants=[0] if 'mixer_base' in NAME or 'fatled' in NAME else [0,1];replays=[]
 for variant in variants:
  text='\n'.join(payload(c,variant) for c in cases)+'\n';app=run([exe],input=text);out=app['stdout'].splitlines();assert len(out)==len(cases),(len(out),len(cases))
  if 'mixer_base' in NAME:
   for ix,(c,line) in enumerate(zip(cases,out)):assert list(map(int,line.split()))==[len(c['items']),*c['items']],(ix,c,line)
  else:
   direct=run([exe,'--provider'],input='\n'.join(payload(c,variant,True) for c in cases)+'\n');assert out==direct['stdout'].splitlines(),{'app':out,'provider':direct['stdout']}
   if 'monitor' in NAME:
    for c,line in zip(cases,out):
     i=c['input'];fields=line.split();n=len(i['tags']);events=int(fields[n+1]);off=n+2+events*2;lookups=list(map(int,fields[off+1:]));count=int(fields[off]);assert count==len(lookups)
     observation=next(x for x in f['provider_lookup_observations'] if x['tags']==i['tags'])
     expected=observation['indices'][i['first']+3:i['last']+4] if i['first']<=i['last'] else []
     assert lookups==expected,(c,line,expected)
  replays.append({'variant':variant,'input_sha256':hashlib.sha256(text.encode()).hexdigest(),'output_sha256':hashlib.sha256(app['stdout'].encode()).hexdigest(),'seconds':app['seconds']})
 return {'cases':len(cases)*len(variants),'native_cases':len(cases),'cpp_differential_passed':True,'domain':f['boundary_scope'],'native_range':f['range'],'replays':replays,'actual_source_provider_replay':'Independent direct application of exact ARM-captured calls using real NumericParam/Component. Compare resulting values, notification order/identity/edit semantics, and real sparse/duplicate-tag lookup. No provider body reconstructed.' if 'mixer_base' not in NAME else 'Real CCL Vector append/resize and throwing-allocation adaptation; opaque borrowed identities not dereferenced.'}

def proof(exe,obj,integration,out):
 req=json.loads((ROOT/PACKET/'request.json').read_text());target=req['targets'][0]
 fm=run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*CPP]);r=replay(exe);sy=run(['/usr/bin/nm','--defined-only',obj]);assert target['mangled'] in {l.split()[-1] for l in sy['stdout'].splitlines() if l.split()}
 sources={p:digest(p) for p in [*CPP,str(TEST/'native.py'),str(TEST/'check.py'),str(TEST/'fixtures.json')]};providers={p:digest(p) for p in PROVIDERS};f={'original_elf_sha256':target['original_elf_sha256'],'mangled':target['mangled'],'cpp_compiled':True,'mangling_namespace_checked':True,'cpp_differential_passed':True,'portable_ready':False,'domain':r['domain'],'declaration_uncertainties':['Original ordinary return declaration unresolved; provisional source-port void. No original inheritance/layout/ownership/ARM ABI/hardware claim.']}
 now=datetime.datetime.now(datetime.timezone.utc).isoformat();d={'version':1,'task_id':NAME,'provider_thread_id':os.environ.get('CODEX_THREAD_ID'),'produced_utc':now,'producer':{'path':str(TEST/'check.py'),'sha256':digest(TEST/'check.py')},'functions':[f],'sources':sources,'repository_sources':providers,'cpp_differential_passed':True,'compiled_mangled_names_matched':True,'mangling_namespace_checked':True,'replay':r,'native':{'elf_sha256':target['original_elf_sha256'],'range':r['native_range'],'producer_sha256':digest(TEST/'native.py'),'fixture_sha256':digest(TEST/'fixtures.json'),'emulator_version':__import__('unicorn').__version__,'scope':'Exact bound application instructions only; original Core bodies excluded.'},'format':{'formatter_version':run(['uc-library/.venv/bin/clang-format','--version'])['stdout'].strip(),'check':fm},'compiler_version':run(['/usr/bin/c++','--version'])['stdout'].splitlines()[0],'executable':{'path':str(exe),'sha256':digest(exe)},'object':{'path':str(obj),'sha256':digest(obj)},'proposed_readiness':{'canonical_binding_pending':True,'ready':[],'pending':[{**f,'sources':{p.removeprefix('uc-library/'):v for p,v in sources.items()},'repository_sources':providers}]},'remarks':[{'date':now,'original_elf_sha256':target['original_elf_sha256'],'mangled':target['mangled'],'status':'compiled_declaration_pending','observation':r['domain'],'retry_condition':'Independent original declaration evidence for promotion; new evidence for wider behavior.'}]}
 d['remarks'].append({'date':now,'original_elf_sha256':target['original_elf_sha256'],'mangled':target['mangled'],'status':'resolved_boundary_model_discrepancy','observation':'Provisional first-wins duplicate lookup model rejected by actual CCL ParamList. Original draft native script/fixtures retained in temp/recovery-work/rolling10x10-20261114/monitor-duplicate-draft01/. Corrected boundary queries actual CCL Component lookup independently, without invoking reconstructed method.','resolution':'Fresh native fixtures carry real provider lookup indices and full differential replay now covers duplicate tags.'})
 d['remarks'].append({'date':now,'original_elf_sha256':target['original_elf_sha256'],'mangled':target['mangled'],'status':'resolved_test_range_initialization','observation':'Self-review rejected initial raw ParamInfo aggregate because max was 0 and mid was 1; real 0/1 state variants were thereby lost. Preserved initial Replay.cpp locally; now uses pinned PARAM_FLOAT macro for explicit [0,1] bounds.','resolution':'Fresh replay compares distinct initial-state output hashes and real value/notification effects.'})
 if integration:d['integration']={'path':str(integration),'sha256':digest(integration)}
 else:
  d['canonical_replay_pending']=True;d['local_compile_commands']=json.loads((ROOT/SCRATCH/'compile.json').read_text());d['provider_provenance']={'path':'temp/provider-baseline08/PROVENANCE.json','sha256':digest('temp/provider-baseline08/PROVENANCE.json'),'scope':'Only pinned Core/allocator archives, no historical app archive'}
  d['provider_archives']={p:digest(p) for p in ['temp/provider-baseline08/libcorelib.a','temp/provider-baseline08/libpresonus_core_allocator.a']} if 'mixer_base' not in NAME else {}
 (ROOT/out).parent.mkdir(parents=True,exist_ok=True);(ROOT/out).write_text(json.dumps(d,indent=2)+'\n');return d
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='proof',choices=['compile','format','symbols','native','replay','proof']);p.add_argument('--exe',type=pathlib.Path);p.add_argument('--object',type=pathlib.Path);p.add_argument('--integration',type=pathlib.Path);p.add_argument('--out',type=pathlib.Path);a=p.parse_args();os.chdir(ROOT);(ROOT/SCRATCH).mkdir(parents=True,exist_ok=True);exe=a.exe or SCRATCH/'replay';obj=a.object or SCRATCH/'production.o'
 if a.mode=='compile':print(json.dumps(compile()))
 elif a.mode=='format':print(json.dumps(run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*CPP])))
 elif a.mode=='symbols':
  target=json.loads((ROOT/PACKET/'request.json').read_text())['targets'][0];s=run(['/usr/bin/nm','--defined-only',obj]);assert target['mangled'] in {l.split()[-1] for l in s['stdout'].splitlines() if l.split()};print(target['mangled'])
 elif a.mode=='native':
  import native
  assert native.generate()==json.loads((ROOT/TEST/'fixtures.json').read_text());print('Fresh exact ARM execution reproduces all fixtures')
 elif a.mode=='replay':print(json.dumps(replay(exe)))
 else:proof(exe,obj,a.integration,a.out or pathlib.Path('uc-library/candidates')/NAME/'worker-proof.json');print('Fresh proof written')
