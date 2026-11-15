"""Fresh exact ARM/real-deallocation proof; canonical output replay supported."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[4];NAME='rolling10_next100_omap_release';TEST=pathlib.Path('uc-library/tests/recovery')/NAME;SCRATCH=pathlib.Path('temp/recovery-work')/NAME
HEADER='uc-library/include/presonus/dsp/OMAPTargetHandler.hpp';SOURCE='uc-library/src/Presonus/Dsp/OMAPTargetHandler.cpp';CPP=[HEADER,SOURCE,str(TEST/'Replay.cpp')]
PACKET=pathlib.Path('temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/packets')/NAME
SNAP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/snapshot')
MANGLED='_ZN8Presonus3Dsp17OMAPTargetHandler7releaseEv';STARTED='2026-11-14T10:12:23.158532185Z'
FLAGS=['/usr/bin/c++','-std=c++17','-O2','-fno-rtti','-Iuc-library/include']
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def run(argv,env=None,**kwargs):
 t=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=ROOT,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(ROOT/SCRATCH),**(env or {})},**kwargs)
 d={'argv':list(map(str,argv)),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'seconds':time.monotonic()-t}
 if p.returncode:raise RuntimeError(json.dumps(d))
 return d

def compile(bridge_only=False):
 cmds=[run(FLAGS+['-fPIC','-shared','-DNATIVE_BRIDGE',str(TEST/'Replay.cpp'),'-Wl,--wrap=_ZdlPv','-ldl','-o',str(SCRATCH/'native-bridge.so')])]
 if not bridge_only:
  cmds.append(run(FLAGS+['-c',SOURCE,'-o',str(SCRATCH/'production.o')]))
  cmds.append(run(FLAGS+[str(TEST/'Replay.cpp'),str(SCRATCH/'production.o'),'-Wl,--wrap=_ZdlPv','-ldl','-o',str(SCRATCH/'replay')]))
 out=SCRATCH/('compile-bridge.json' if bridge_only else 'compile.json');(ROOT/out).write_text(json.dumps(cmds,indent=2)+'\n');return cmds

def native():
 stamp=str(time.time_ns());out=SCRATCH/('native-fresh-'+stamp+'.json');mappings=SCRATCH/('native-mappings-'+stamp+'.json');bridge=ROOT/SCRATCH/'native-bridge.so'
 r=run(['uc-library/.venv/bin/python',str(TEST/'native.py'),str(ROOT/out)],env={'LD_PRELOAD':str(bridge),'OMAP_MAPPING_OUT':str(ROOT/mappings)})
 generated=json.loads((ROOT/out).read_text());sealed=json.loads((ROOT/TEST/'fixtures.json').read_text());assert generated==sealed
 return {'output':str(out),'sha256':sha(out),'mappings':str(mappings),'mappings_sha256':sha(mappings),'bridge':str(SCRATCH/'native-bridge.so'),'bridge_sha256':sha(SCRATCH/'native-bridge.so'),'emulator_version':generated['emulator_version'],'case_count':len(generated['cases']),'argv':r['argv'],'environment':{'LD_PRELOAD':str(bridge),'OMAP_MAPPING_OUT':str(ROOT/mappings)},'seconds':r['seconds']}

def symbols(obj):
 d=run(['/usr/bin/nm','--defined-only',str(obj)]);matches=[l.split() for l in d['stdout'].splitlines() if l.split() and l.split()[-1]==MANGLED];assert len(matches)==1 and matches[0][-2]=='W',matches
 undefined=run(['/usr/bin/nm','-u',str(obj)]);assert '_ZdlPv' in {l.split()[-1] for l in undefined['stdout'].splitlines() if l.split()}
 return {'mangled':MANGLED,'compiled_binding':'W (ELF weak matches original STB_WEAK)','mangling_namespace_checked':True,'original_binding':'STB_WEAK','compiled_symbols':d['stdout'],'undefined_symbols':undefined['stdout']}

def replay(exe):
 # Every source allocation is separate from oracle allocations, avoiding
 # double-free. Watched free is real libc deallocation, not an appended event.
 cycles=[1,2,3,16,32,64,256,1024];text='\n'.join(map(str,cycles))+'\n';r=run([exe],input=text);lines=r['stdout'].splitlines();expected=[' '.join(map(str,[n]*5)) for n in cycles];assert lines==expected,(lines,expected)
 f=json.loads((ROOT/TEST/'fixtures.json').read_text());assert all(c['delete']['allocations']==c['delete']['unsized_delete_calls']==c['delete']['actual_free_calls']==c['delete']['unchanged_host_pointer_matches']==1 for c in f['cases'])
 return {'domain':f['domain'],'cycles':cycles,'source_allocation_release_cycles':sum(cycles),'native_allocation_release_cycles':len(f['cases']),'actual_allocations_deletes_frees_pointer_matches_equal':True,'cpp_differential_passed':True,'input_sha256':hashlib.sha256(text.encode()).hexdigest(),'output_sha256':hashlib.sha256(r['stdout'].encode()).hexdigest(),'seconds':r['seconds']}

def proof(exe,obj,integration,out):
 fresh=native();r=replay(exe);sy=symbols(obj);fmt=run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*CPP]);fixture=json.loads((ROOT/TEST/'fixtures.json').read_text());req=json.loads((ROOT/PACKET/'request.json').read_text());t=req['targets'][0]
 sources={p:sha(p) for p in [*CPP,str(TEST/'native.py'),str(TEST/'check.py'),str(TEST/'fixtures.json')]};f={'original_elf_sha256':t['original_elf_sha256'],'mangled':t['mangled'],'cpp_compiled':True,'mangling_namespace_checked':True,'cpp_differential_passed':True,'portable_ready':False,'domain':r['domain'],'declaration_uncertainties':['Original ordinary return declaration unresolved; explicit portable void. Full original class/inheritance/layout/size/ownership/constructor/destructor/ARM ABI/hardware unverified.']}
 now=datetime.datetime.now(datetime.timezone.utc).isoformat();d={'version':1,'task_id':NAME,'session_id':os.environ.get('CODEX_THREAD_ID'),'phase_timestamps':{'first_recorded_contract_review_utc':STARTED,'proof_seal_utc':now},'producer':{'path':str(TEST/'check.py'),'sha256':sha(TEST/'check.py')},'created_utc':now,'cpp_differential_passed':True,'compiled_mangled_names_matched':True,'mangling_namespace_checked':True,'functions':[f],'sources':sources,'repository_sources':{},'native':fresh,'range':fixture['range'],'elf_sha256':fixture['elf_sha256'],'provider':fixture['provider'],'libc_free_provider':{'path':'/usr/lib/x86_64-linux-gnu/libc.so.6','sha256':sha('/usr/lib/x86_64-linux-gnu/libc.so.6'),'instrumentation':'Replay free interposer forwards to actual __libc_free; GNU ld --wrap=_ZdlPv forwards to actual exported C++ runtime unsized operator delete. Preload activates free observation in native oracle process.'},'replay':r,'symbols':sy,'format':{'formatter_version':run(['uc-library/.venv/bin/clang-format','--version'])['stdout'].strip(),'check':fmt},'compiler_version':run(['/usr/bin/c++','--version'])['stdout'].splitlines()[0],'object':{'path':str(obj),'sha256':sha(obj)},'executable':{'path':str(exe),'sha256':sha(exe)},'proposed_readiness':{'canonical_binding_pending':True,'ready':[],'pending':[{**f,'sources':{p.removeprefix('uc-library/'):v for p,v in sources.items()},'repository_sources':{}}]},'remarks':[{'date':now,'original_elf_sha256':t['original_elf_sha256'],'mangled':t['mangled'],'status':'compiled_declaration_pending','observation':'Only exact release body reconstructed: unchanged this tail-deallocation. Native boundary independently deletes a fresh actual explicit-port object and instruments real libc free; production release does not call destructor. ELF weak symbol binding preserved. No other OMAP implementation is supplied.','retry_condition':'Independent original ordinary return declaration evidence for promotion; explicit future typed scope for other methods.'}]}
 evidence={};binding=req['reconstruction_contract'];contract=json.loads((SNAP/binding['path']).read_text());evidence[str(SNAP/binding['path'])]=binding['sha256']
 def refs(x):
  if isinstance(x,dict):
   if 'path' in x and 'sha256' in x:evidence[str(SNAP/x['path'])]=x['sha256']
   for v in x.values():refs(v)
  elif isinstance(x,list):
   for v in x:refs(v)
 refs(contract)
 for p,v in evidence.items():assert sha(p)==v
 d['typed_contract_evidence']=evidence
 if integration:d['integration']={'path':str(integration),'sha256':sha(integration)}
 else:d['canonical_replay_pending']=True;d['local_compile_commands']=json.loads((ROOT/SCRATCH/'compile.json').read_text())
 (ROOT/out).parent.mkdir(parents=True,exist_ok=True);(ROOT/out).write_text(json.dumps(d,indent=2)+'\n');return d
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='proof',choices=['compile','format','symbols','native','replay','proof']);p.add_argument('--exe',type=pathlib.Path);p.add_argument('--object',type=pathlib.Path);p.add_argument('--integration',type=pathlib.Path);p.add_argument('--out',type=pathlib.Path);a=p.parse_args();os.chdir(ROOT);(ROOT/SCRATCH).mkdir(parents=True,exist_ok=True);exe=a.exe or SCRATCH/'replay';obj=a.object or SCRATCH/'production.o'
 if a.mode=='compile':print(json.dumps(compile()))
 elif a.mode=='format':print(json.dumps(run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*CPP])))
 elif a.mode=='symbols':print(json.dumps(symbols(obj)))
 elif a.mode=='native':print(json.dumps(native()))
 elif a.mode=='replay':print(json.dumps(replay(exe)))
 else:
  if a.exe:compile(bridge_only=True)
  proof(exe,obj,a.integration,a.out or pathlib.Path('uc-library/candidates')/NAME/'worker-proof.json');print('Fresh proof written')
