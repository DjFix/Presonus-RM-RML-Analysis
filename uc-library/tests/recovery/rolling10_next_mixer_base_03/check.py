"""Bounded fresh native/provider checks; canonical output replay supported."""
import argparse,datetime,hashlib,json,os,pathlib,shlex,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[4];NAME=pathlib.Path(__file__).parent.name
TEST=pathlib.Path('uc-library/tests/recovery')/NAME;SCRATCH=pathlib.Path('temp/recovery-work')/NAME
CPP=['uc-library/include/presonus/mixer/RackMixerComponent.hpp','uc-library/src/Presonus/Mixer/RackMixerComponent.cpp',str(TEST/'Replay.cpp')]
DEPS=['uc-library/include/presonus/mixer/MixerComponentBase.hpp','uc-library/include/presonus/mixer/ChannelComponent.hpp','uc-library/include/presonus/MuteGroupBase.hpp','uc-library/include/presonus/mixer/OutputComponent.hpp']
PROVIDERS=['core/portable/coreparams.h','core/portable/coreparams.cpp','core/portable/corecomponent.h','core/portable/corecomponent.cpp','core/public/corevector.h','core/public/corestringbuffer.h','core/public/corestringtraits.h','core/public/coreformatter.cpp','core/public/coreformatter.h']
def digest(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def run(argv,**kwargs):
 t=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=ROOT,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(ROOT/SCRATCH)},**kwargs)
 result=dict(argv=list(map(str,argv)),returncode=p.returncode,stdout=p.stdout,stderr=p.stderr,seconds=time.monotonic()-t)
 if p.returncode:raise RuntimeError(json.dumps(result))
 return result
FLAGS=['/usr/bin/c++','-std=c++17','-O2','-fno-rtti','-DNDEBUG=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-DCORE_USE_OPENSSL=1','-Ulinux','-Wno-multichar','-ffunction-sections','-fdata-sections','-pthread','-Iuc-library/include','-Ithird_party/ccl-framework']
def compile():
 commands=[run(FLAGS+['-c',CPP[1],'-o',SCRATCH/'production.o'])]
 commands.append(run(FLAGS+[TEST/'Replay.cpp',SCRATCH/'production.o','-Wl,--gc-sections','-Wl,--start-group','temp/provider-baseline08/libpresonus_rm_components.a','temp/provider-baseline08/libpresonus_uc.a','temp/provider-baseline08/libcorelib.a','temp/provider-baseline08/libpresonus_core_allocator.a','-Wl,--end-group','-lz','-lssl','-lcrypto','-ldl','-lm','-o',SCRATCH/'replay']))
 (ROOT/SCRATCH/'compile.json').write_text(json.dumps(commands,indent=2)+'\n');return commands

def replay(exe):
 f=json.loads((ROOT/TEST/'fixtures.json').read_text());cases=f['cases']
 if NAME.endswith('02'):
  lines=[]
  for c in cases:
   i=c['input'];v=[i['capacity'],int(i.get('fail',False)),len(i['seed']),len(i['channels']),*i['seed'],*[x for pair in i['channels'] for x in pair]];lines.append(' '.join(map(str,v)))
 else:lines=[str(c['input']['count']) for c in cases]
 text='\n'.join(lines)+'\n';r=run([exe],input=text);out=r['stdout'].splitlines();assert len(out)==len(cases),(len(out),len(cases))
 for ix,(c,line) in enumerate(zip(cases,out)):
  if NAME.endswith('02'):assert list(map(int,line.split()))==[len(c['items']),*c['items']],(ix,c,line)
  else:
   fields=shlex.split(line);n=len(c['items']);assert list(map(int,fields[:4]))==[n,1,n,n+1],(ix,c,line);assert fields[4:]==c['items'],(ix,c,line)
 return {'cases':len(cases),'domain':f['boundary_scope'],'cpp_differential_passed':True,'input_sha256':hashlib.sha256(text.encode()).hexdigest(),'output_sha256':hashlib.sha256(r['stdout'].encode()).hexdigest(),'seconds':r['seconds'],'native_range':f['range']}
def proof(exe,obj,integration,out):
 packet=pathlib.Path('temp/recovery-work/rolling10x10-20261114/prepared05/packets')/NAME
 req=json.loads((ROOT/packet/'request.json').read_text());target=req['targets'][0]
 fm=run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*CPP]);result=replay(exe)
 sy=run(['/usr/bin/nm','--defined-only',obj]);assert target['mangled'] in {l.split()[-1] for l in sy['stdout'].splitlines() if l.split()}
 sources={x:digest(x) for x in [*CPP,*DEPS,str(TEST/'native.py'),str(TEST/'check.py'),str(TEST/'fixtures.json')]};providers={'third_party/ccl-framework/'+x:digest('third_party/ccl-framework/'+x) for x in PROVIDERS}
 f={'original_elf_sha256':target['original_elf_sha256'],'mangled':target['mangled'],'cpp_compiled':True,'mangling_namespace_checked':True,'portable_ready':False,'domain':result['domain']+' Source port only; ordinary return declaration pending. setupAllMutesGroup preserves preexisting entries and duplicates, skips null mute, catches provider allocation failure and continues. buildAuxRouteList sampled signed counts -2^31,-1,0..6,8,12,16,32,64; actual CCL changed/rangeChanged notifications tested. No original layout, inheritance, ARM ABI, hardware or Core binary behavior claim.','cpp_differential_passed':True,'declaration_uncertainties':['Original unencoded return declaration unresolved: portable void. Layout/inheritance/ARM ABI/hardware unverified.']}
 now=datetime.datetime.now(datetime.timezone.utc).isoformat();d={'version':1,'task_id':NAME,'provider_thread_id':os.environ.get('CODEX_THREAD_ID'),'produced_utc':now,'compiler_version':run(['/usr/bin/c++','--version'])['stdout'].splitlines()[0],'producer':{'path':str(TEST/'check.py'),'sha256':digest(TEST/'check.py')},'functions':[f],'sources':sources,'repository_sources':providers,'cpp_differential_passed':True,'compiled_mangled_names_matched':True,'mangling_namespace_checked':True,'replay':result,'native':{'emulator_version':__import__('unicorn').__version__,'execution':'Exact bound non-Core ARM instructions; no original Core binary executed','elf_sha256':target['original_elf_sha256'],'range':result['native_range'],'producer_sha256':digest(TEST/'native.py'),'fixture_sha256':digest(TEST/'fixtures.json')},'format':{'formatter_version':run(['uc-library/.venv/bin/clang-format','--version'])['stdout'].strip(),'check':fm},'executable':{'path':str(exe),'sha256':digest(exe)},'object':{'path':str(obj),'sha256':digest(obj)},'proposed_readiness':{'canonical_binding_pending':True,'ready':[],'pending':[{**f,'sources':{x.removeprefix('uc-library/'):v for x,v in sources.items()},'repository_sources':providers}]},'remarks':[{'date':now,'original_elf_sha256':target['original_elf_sha256'],'mangled':target['mangled'],'status':'compiled_declaration_pending','observation':result['domain'],'retry_condition':'Independent original return declaration evidence required for promotion.'}]}
 if integration:d['integration']={'path':str(integration),'sha256':digest(integration)}
 else:d['canonical_replay_pending']=True;d['provider_archives']={str(x):digest(x) for x in pathlib.Path('temp/provider-baseline08').glob('*.a')};d['local_compile_commands']=json.loads((ROOT/SCRATCH/'compile.json').read_text())
 (ROOT/out).parent.mkdir(parents=True,exist_ok=True);(ROOT/out).write_text(json.dumps(d,indent=2)+'\n');return d
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='proof',choices=['compile','format','symbols','native','replay','proof']);p.add_argument('--exe',type=pathlib.Path);p.add_argument('--object',type=pathlib.Path);p.add_argument('--integration',type=pathlib.Path);p.add_argument('--out',type=pathlib.Path);a=p.parse_args();os.chdir(ROOT);(ROOT/SCRATCH).mkdir(parents=True,exist_ok=True);exe=a.exe or SCRATCH/'replay';obj=a.object or SCRATCH/'production.o'
 if a.mode=='compile':print(json.dumps(compile()))
 elif a.mode=='format':print(json.dumps(run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*CPP])))
 elif a.mode=='symbols':
  target=json.loads((ROOT/'temp/recovery-work/rolling10x10-20261114/prepared05/packets'/NAME/'request.json').read_text())['targets'][0];s=run(['/usr/bin/nm','--defined-only',obj]);assert target['mangled'] in {l.split()[-1] for l in s['stdout'].splitlines() if l.split()};print(target['mangled'])
 elif a.mode=='native':
  import native
  assert native.generate()==json.loads((ROOT/TEST/'fixtures.json').read_text());print('Fresh exact ARM execution reproduces all fixtures')
 elif a.mode=='replay':print(json.dumps(replay(exe)))
 else:proof(exe,obj,a.integration,a.out or pathlib.Path('uc-library/candidates')/NAME/'worker-proof.json');print('Fresh proof written')
