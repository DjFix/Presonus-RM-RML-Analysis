import argparse,datetime,hashlib,importlib.util,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[4]
COMMON='uc-library/tests/recovery/rolling10_presets_01'
HEADER='uc-library/include/presonus/panel/PresetNameManager.hpp'
SOURCE='uc-library/src/Presonus/Panel/PresetNameManager.cpp'
DEPENDENCIES=['uc-library/src/Presonus/Panel/PresetNameCache.cpp','uc-library/include/presonus/panel/PresetNameCache.hpp']
CANON=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
ARCHIVES=[CANON/'upstream-core/sdk/lib/libcorelib.a',CANON/'upstream-core/sdk/lib/libpresonus_core_allocator.a',CANON/'private-glibc29-provider/libpresonus_private_glibc29.a']
WRAPS=['_ZN8Presonus5Panel15PresetNameCache11cachePresetEPKcS3_i','_ZN8Presonus5Panel15PresetNameCache13getPresetInfoERN4Core13CStringBufferILi64EEERNS3_ILi32EEEi','_ZN8Presonus5Panel15PresetNameCache18getFileNameForSlotEjb']
CCL=['third_party/ccl-framework/core/portable/corefilename.h','third_party/ccl-framework/core/portable/corefilename.cpp','third_party/ccl-framework/core/public/corestringbuffer.h','third_party/ccl-framework/core/public/corevector.h','third_party/ccl-framework/core/portable/corefile.h']
FLAGS=['c++','-std=c++17','-O0','-fno-rtti','-fno-lto','-Wno-multichar','-Ulinux','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework']
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main(task='rolling10_presets_01'):
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='all',choices=['all','format','compile','symbols','replay']);p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');a=p.parse_args()
 test='uc-library/tests/recovery/'+task;candidate='uc-library/candidates/'+task
 work=ROOT/'temp/recovery-work/rolling10-presets-local'/task;work.mkdir(parents=True,exist_ok=True)
 exe=pathlib.Path(a.exe).resolve() if a.exe else work/'replay';obj=pathlib.Path(a.object).resolve() if a.object else work/'manager.o'
 checks=[]
 def run(argv):
  argv=list(map(str,argv));start=time.time();r=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,env={**os.environ,'TMPDIR':str(work)});checks.append(dict(argv=argv,returncode=r.returncode,seconds=time.time()-start,stdout=r.stdout,stderr=r.stderr))
  if r.returncode:print(r.stdout,r.stderr);raise RuntimeError(argv)
  return r.stdout
 fmt=[HEADER,SOURCE,COMMON+'/Replay.cpp',test+'/Replay.cpp'];fmt=list(dict.fromkeys(fmt))
 if a.mode in ('all','format'):run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*fmt])
 if a.mode in ('all','compile') and not a.exe:
  run([*FLAGS,'-c',SOURCE,'-o',obj]);run([*FLAGS,test+'/Replay.cpp',obj,DEPENDENCIES[0],'-Wl,--gc-sections',*['-Wl,--wrap='+n for n in WRAPS],'-Wl,--start-group',*ARCHIVES,'-Wl,--end-group','-lpthread','-ldl','-o',exe])
 req=json.loads((ROOT/'temp/recovery-work/rolling10x10-20261114/prepared05/packets'/task/'request.json').read_text());name=req['targets'][0]['mangled']
 if a.mode in ('all','symbols','replay'):
  symbols={x.split()[-1] for x in run(['nm','--defined-only',obj]).splitlines() if x.split()};assert name in symbols,name
 if a.mode in ('all','replay'):
  spec=importlib.util.spec_from_file_location('presets_native',ROOT/COMMON/'native.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
  fixture=json.loads((ROOT/test/'fixtures.json').read_text());assert native.generate(task)==fixture,'fresh native observations differ'
  for i,c in enumerate(fixture['cases']):
   s=c['input'];arg=lambda x:'~' if x is None else str(x)
   argv=[exe,task,str(s.get('slot',0)),str(int(s.get('flag',False))),arg(s.get('name')),arg(s.get('category')),arg(s.get('kind')),arg(s.get('url')),'0',str(len(s['types'])),*s['types']]
   got=run(argv);lines=[]
   for trace in c['trace']:
    if trace[0]!='lookup':lines.append('|'.join(arg(v) for v in trace))
   o=c['output']
   if task=='rolling10_presets_02':lines.append('result|'+str(o['result'])+'|'+o['name']+'|'+o['category'])
   elif task=='rolling10_presets_03':lines.append('result|'+o['path'])
   elif task=='rolling10_replacement_presets_01':lines.append('result|'+str(o['index']))
   expected=''.join(x+'\n' for x in lines);assert got==expected,(i,s,got,expected)
  provider_output=run([exe,'providers'])
  domain=f"{len(fixture['cases'])} fresh original ARM target executions; exact cache selection and forwarded signed/unsigned slots, nullable string arguments, branch outcomes and result/buffer observations; independent actual cache/CCL provider replay. Typed cache boundaries exclude original callee behavior."
  paths=list(dict.fromkeys([HEADER,SOURCE,*DEPENDENCIES,COMMON+'/Replay.cpp',COMMON+'/native.py',COMMON+'/check.py',test+'/Replay.cpp',test+'/native.py',test+'/check.py',test+'/fixtures.json']))
  limitations=[fixture['limitations'],'Unencoded original return declarations unresolved; portable void/bool/FileName/pointer declarations selected from native register usage and existing provider contracts, pending independent original declaration evidence.','Borrowed live cache entries; canonical Core::Vector and FileName providers; original field layout, inheritance, ownership, ARM ABI and hardware unverified.','Negative slots are routing-only boundary tests; actual cache getPresetInfo and getFileNameForSlot require valid nonnegative indices.','Existing dependency implementations are source ports; actual provider replay verifies finite current-source behavior only.']
  sourcehash={str(pathlib.Path(x).relative_to('uc-library')):sha(ROOT/x) for x in paths}
  repository={x:sha(ROOT/x) for x in CCL}
  target=req['targets'][0]
  pending=dict(original_elf_sha256=target['original_elf_sha256'],mangled=name,sources=sourcehash,repository_sources=repository,domain=domain,portable_ready=False,declaration_uncertainties=limitations,cpp_compiled=True,mangling_namespace_checked=True)
  proof=dict(version=1,task_id=task,originals=req['targets'],elf_sha256=fixture['elf_sha256'],native_range=fixture['range'],fixture_sha256=sha(ROOT/test/'fixtures.json'),native_case_count=len(fixture['cases']),validation_domain=domain,limitations=limitations,source_hashes=sourcehash,repository_sources=repository,provider_archives={str(x):sha(x) for x in ARCHIVES},provider_observation=provider_output,formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler=run(['c++','--version']).splitlines()[0],unicorn=__import__('unicorn').__version__,object=dict(path=str(obj),sha256=sha(obj)),executable=dict(path=str(exe),sha256=sha(exe)),checks=checks,canonical_binding_pending=not bool(a.integration),integration=dict(path=a.integration,sha256=sha(a.integration)) if a.integration else None,proposed_readiness=dict(canonical_binding_pending=True,ready=[],pending=[pending]),session=dict(agent_task='/root/rolling10_presets',application_session='01a1b0c8-21eb-7e43-afb2-d5fa8e409a99',phase_end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
  out=pathlib.Path(a.out) if a.out else ROOT/candidate/'worker-proof.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(proof,indent=2)+'\n');print(domain)
if __name__=='__main__':main()
