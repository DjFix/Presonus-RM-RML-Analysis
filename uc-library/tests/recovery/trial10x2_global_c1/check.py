"""Fresh Linux worker/canonical replay; no cached dependency files required."""
import argparse,hashlib,importlib.util,json,pathlib,subprocess,sys,time,shlex
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[3]
CANON=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis')
TRIAL=CANON/'temp/recovery-work/trial10x2-20261115'
PROVIDERS=TRIAL/'root-review/provider-supplement/PROVIDERS.json'
SOURCE='uc-library/src/Presonus/Mixer/GlobalComponent.cpp'
HEADER='uc-library/include/presonus/mixer/GlobalComponent.hpp'
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['all','format','compile','symbols','replay'],default='all');p.add_argument('--variant',choices=['c1','c2'],default=HERE.name.rsplit('_',1)[-1]);p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out',required=True);a=p.parse_args();requested_out=pathlib.Path(a.out).resolve();out=requested_out.parent/(requested_out.stem+'-artifacts') if requested_out.suffix=='.json' else requested_out;out.mkdir(parents=True,exist_ok=True);logs=[]
 def run(argv):
  t=time.monotonic();r=subprocess.run([str(x) for x in argv],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);logs.append({'argv':list(map(str,argv)),'returncode':r.returncode,'seconds':time.monotonic()-t,'output':r.stdout});(out/'commands.json').write_text(json.dumps(logs,indent=2)+'\n');assert r.returncode==0,r.stdout;return r.stdout
 provider=json.loads(PROVIDERS.read_text());assert digest(PROVIDERS)=='0e4fc25d3383ae8609932b7e25c4d28bac3ee92b9435c11e8d63b61cd29f0c18'
 for d in provider['archives'].values():assert digest(d['frozen_read_path'])==d['sha256']
 for d in provider['system_libraries']:assert digest(d['path'])==d['sha256']
 paths=[SOURCE,HEADER,str(HERE/'Replay.cpp')];fmt=ROOT/'uc-library/.venv/bin/clang-format'
 if a.mode in ['all','format','replay']:
  run([fmt,'--version']);run([fmt,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',*paths])
 flags=['-std=c++17','-O2','-pthread','-Ulinux','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-I'+str(ROOT/'uc-library/include'),'-I'+str(ROOT/'third_party/ccl-framework')]
 # Query the current compiler each time. Never read a worker-local cached depfile.
 snapshot=json.loads((TRIAL/'prepared01/SNAPSHOT.json').read_text())
 closure=[]
 for unit in [ROOT/SOURCE,HERE/'Replay.cpp']:
  deptext=run(['/usr/bin/c++',*flags,'-MM',unit])
  for word in shlex.split(deptext.replace('\\\n',' '))[1:]:
   path=pathlib.Path(word).resolve()
   if not path.is_file():continue
   if path==ROOT/SOURCE or path==ROOT/HEADER or path==HERE/'Replay.cpp':continue
   try:rel=str(path.relative_to(ROOT))
   except ValueError:
    try:rel=str(path.relative_to(CANON))
    except ValueError:raise AssertionError('Unbound compiler dependency: '+str(path))
   expected=snapshot['files'].get(rel)
   if expected is None:raise AssertionError('Missing frozen compiler dependency: '+rel)
   assert digest(path)==expected,('Changed compiler dependency',rel)
   frozen=TRIAL/'prepared01/snapshot'/rel
   assert digest(frozen)==expected
   closure.append({'path':rel,'actual_path':str(path),'frozen_path':str(frozen),'sha256':expected})
 (out/'compiler-closure.json').write_text(json.dumps(closure,indent=2)+'\n')
 obj=pathlib.Path(a.object).resolve() if a.object else out/'GlobalComponent.o';exe=pathlib.Path(a.exe).resolve() if a.exe else out/'replay'
 if a.mode in ['all','compile'] or (a.mode=='replay' and not a.exe):
  run(['/usr/bin/c++',*flags,'-c',SOURCE,'-o',obj]);run(['/usr/bin/c++',*flags,HERE/'Replay.cpp',obj,*provider['default_link_order'][1:],'-o',exe])
 if a.mode in ['all','symbols','replay']:
  symbols=run(['/usr/bin/nm','--defined-only',obj]);assert all('_ZN8Presonus5Mixer15GlobalComponent'+v+'ERNS0_18MixerComponentBaseE' in symbols for v in ['C1','C2'])
 if a.mode in ['all','replay']:
  spec=importlib.util.spec_from_file_location('native',HERE/'native.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native);observed=native.observe(a.variant);fixture=json.loads((HERE/'fixtures.json').read_text());assert observed==fixture
  native.write_provider(observed['descriptors'],out/'provider.txt');result=run([exe,out/'provider.txt'])
  proof={'version':1,'task_id':'trial10x2_global_'+a.variant,'namespace':'Presonus::Mixer','elf_sha256':observed['elf_sha256'],'ranges':observed['ranges'],'native_cases':len(observed['native_cases']),'provider_cases':106,'native_execution':'fresh original ARM application instructions; actual CCL boundaries intercepted','product_execution':'fresh supplied executable' if a.exe else 'fresh worker build','commands':logs,'sources':{s:digest(ROOT/s) for s in [SOURCE,HEADER]},'fixture':{'path':str(HERE/'fixtures.json'),'sha256':digest(HERE/'fixtures.json')},'producers':{str(HERE/x):digest(HERE/x) for x in ['check.py','native.py','Replay.cpp']},'object':{'path':str(obj),'sha256':digest(obj)},'executable':{'path':str(exe),'sha256':digest(exe)},'provider_manifest':{'path':str(PROVIDERS),'sha256':digest(PROVIDERS)},'integration':{'path':str(a.integration),'sha256':digest(a.integration)} if a.integration else {'path':str(TRIAL/'prepared01/snapshot/uc-library/validation/integration.json'),'sha256':digest(TRIAL/'prepared01/snapshot/uc-library/validation/integration.json')},'compiler_closure':closure,'behavior_success':True,'cpp_compiled':True,'mangling_namespace_checked':True,'portable_ready':False,'passed':True,'limits':observed['limits']}
  req=json.loads((ROOT/('temp/recovery-work/trial10x2-20261115/prepared01/packets/trial10x2_global_'+a.variant+'/request.json')).read_text())
  target=req['targets'][0]
  domain='Normal constructor, 53 literal-bound ARM32 descriptors, 4 prefills x 2 mixer identities per original variant; actual CCL factory types, values, metadata/list strings, controller/feedback, byTag20/21, cleanup; existing highDef/default-provider/temp-path source-port regression.'
  row={'original_elf_sha256':target['original_elf_sha256'],'mangled':target['mangled'],'sources':{s.removeprefix('uc-library/'):digest(ROOT/s) for s in [SOURCE,HEADER]},'repository_sources':{x['path']:x['sha256'] for x in closure if x['path'].startswith('third_party/ccl-framework/core/')},'cpp_compiled':True,'mangling_namespace_checked':True,'portable_ready':False,'behavior_success':True,'domain':domain,'declaration_uncertainties':['Original complete inheritance, class layout, ownership and ARM ABI are unresolved. Existing Component facade and explicit feedback flag are intentional CCL source-port adaptations.'],'limitations':observed['limits']}
  for provider_source in ['third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/corecomponent.cpp']:
   expected=snapshot['files'][provider_source];assert digest(ROOT/provider_source)==expected
   row['repository_sources'][provider_source]=expected
  proof['proposed_readiness']={'ready':[],'pending':[row]}
  proof['domain']=domain
  proof['format']={'version':run([fmt,'--version']).strip(),'paths':{str(x):digest(ROOT/x) if not pathlib.Path(x).is_absolute() else digest(x) for x in paths},'check':'clang-format --style=file --fallback-style=LLVM --dry-run --Werror'}
  proof['versions']={'compiler':run(['/usr/bin/c++','--version']).splitlines()[0],'python':sys.version,'unicorn':__import__('unicorn').__version__,'pinned_ccl_commit':provider['pinned_ccl_commit']}
  proof['commands']=logs
  (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');
  if requested_out.suffix=='.json':requested_out.write_text(json.dumps(proof,indent=2)+'\n');print(result)
if __name__=='__main__':main()
