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

def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['all','format','compile','symbols','replay'],default='all');p.add_argument('--variant',choices=['c1','c2'],default=HERE.name.rsplit('_',1)[-1]);p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out',required=True);a=p.parse_args();requested_out=pathlib.Path(a.out).resolve();out=requested_out.parent/(requested_out.stem+'-artifacts') if requested_out.suffix=='.json' else requested_out;out.mkdir(parents=True,exist_ok=True);logs=[]
 def run(argv):
  t=time.monotonic();r=subprocess.run([str(x) for x in argv],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);logs.append({'argv':list(map(str,argv)),'returncode':r.returncode,'seconds':time.monotonic()-t,'output':r.stdout});(out/'commands.json').write_text(json.dumps(logs,indent=2)+'\n');assert r.returncode==0,r.stdout;return r.stdout
 canonical_binding=_current_canonical_binding(ROOT,a.object,a.exe,a.integration,SOURCE)
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
 if canonical_binding is None:
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
 if canonical_binding is not None:closure=[{'path':p,'actual_path':str(ROOT/p),'sha256':h,'scope':'actual canonical compiled dependency'} for p,h in canonical_binding['binding']['files'].items()]
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
  _attach_current_canonical(proof,canonical_binding)
  proof['domain']=domain
  proof['format']={'version':run([fmt,'--version']).strip(),'paths':{str(x):digest(ROOT/x) if not pathlib.Path(x).is_absolute() else digest(x) for x in paths},'check':'clang-format --style=file --fallback-style=LLVM --dry-run --Werror'}
  proof['versions']={'compiler':run(['/usr/bin/c++','--version']).splitlines()[0],'python':sys.version,'unicorn':__import__('unicorn').__version__,'pinned_ccl_commit':provider['pinned_ccl_commit']}
  proof['commands']=logs
  (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');
  if requested_out.suffix=='.json':requested_out.write_text(json.dumps(proof,indent=2)+'\n');print(result)
if __name__=='__main__':main()
