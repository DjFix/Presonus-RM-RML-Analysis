"""Local and canonical replay gates for the two bounded Storm destructor variants."""
import argparse,datetime,hashlib,json,os,subprocess,sys,time
from pathlib import Path
from elftools.elf.elffile import ELFFile
R=Path(__file__).resolve().parents[4]
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
SUP=ROOT/'temp/recovery-work/trial10x2-20261115/root-review/provider-supplement'
MANIFEST=SUP/'PROVIDERS.json'
MANIFEST_SHA='0e4fc25d3383ae8609932b7e25c4d28bac3ee92b9435c11e8d63b61cd29f0c18'
SOURCES=['uc-library/include/presonus/mixer/StormMixerComponent.hpp','uc-library/src/Presonus/Mixer/StormMixerComponent.cpp']
T=R/'uc-library/tests/recovery/trial10x2_storm_d2'
O=R/'temp/recovery-work/trial10x2_storm_d2'
LOG=[]
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(argv):
 argv=list(map(str,argv));start=time.monotonic();p=subprocess.run(argv,cwd=R,capture_output=True,text=True,env={**os.environ,'TMPDIR':str(O)})
 LOG.append(dict(argv=argv,exit_code=p.returncode,seconds=time.monotonic()-start,stdout=p.stdout,stderr=p.stderr))
 print(json.dumps(argv),flush=True)
 if p.returncode:print(p.stdout,p.stderr);p.check_returncode()
 return p.stdout

def providers(extra):
 assert digest(MANIFEST)==MANIFEST_SHA
 m=json.loads(MANIFEST.read_text());approval=SUP/'ROOT_APPROVAL.json';assert json.loads(approval.read_text())['approved'];assert json.loads(approval.read_text())['provider_manifest_sha256']==MANIFEST_SHA
 readmap=R/'temp/recovery-work/trial10x2-20261115/READ_INPUTS-prepared01-trial10x2_storm.json'
 bindings={**m['read_inputs'],**json.loads(readmap.read_text())};seals={str(MANIFEST):digest(MANIFEST),str(approval):digest(approval),str(readmap.relative_to(R)):digest(readmap)}
 if extra:
  for path,sha in extra:
   path=Path(path);assert digest(path)==sha;data=json.loads(path.read_text());bindings.update(data.get('read_inputs',data.get('sources',{})));seals[str(path)]=sha
 for name,record in m['archives'].items():assert digest(record['frozen_read_path'])==record['sha256']
 snapshot=ROOT/'temp/recovery-work/trial10x2-20261115/prepared01/SNAPSHOT.json'
 assert digest(snapshot)==m['snapshot']['sha256']
 sm=json.loads(snapshot.read_text());seals[str(snapshot)]=digest(snapshot)
 for path in ['third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/corecomponent.cpp','uc-library/src/Presonus/Mixer/ChannelComponent.cpp']:
  frozen=snapshot.parent/'snapshot'/path
  assert digest(frozen)==sm['files'][path]
  bindings[path]=dict(sha256=sm['files'][path],frozen_read_path=str(frozen))
 return m,bindings,seals

def dependencies(bindings):
 deps=set()
 for src in [SOURCES[1],str((T/'Replay.cpp').relative_to(R))]:
  out=run(['c++','-std=c++17','-fno-rtti','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework','-MM',src]);deps.update(out.replace('\\\n',' ').split(':',1)[1].split())
 records={}
 deps.update(['third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/corecomponent.cpp','uc-library/src/Presonus/Mixer/ChannelComponent.cpp'])
 for dep in sorted(deps):
  if dep in SOURCES or dep==str((T/'Replay.cpp').relative_to(R)):continue
  b=bindings.get(dep);assert b is not None,('missing explicit transitive binding',dep)
  assert digest(R/dep)==b['sha256'],('workspace dependency mismatch',dep)
  assert digest(b['frozen_read_path'])==b['sha256'],('frozen dependency mismatch',dep)
  records[dep]=dict(sha256=b['sha256'],frozen_read_path=b['frozen_read_path'])
 return records

def symbol_check(obj,exe=None):
 result={}
 prefix='_ZN8Presonus5Mixer19StormMixerComponent'
 with Path(obj).open('rb') as f:
  e=ELFFile(f);symbols={s.name:s for s in e.get_section_by_name('.symtab').iter_symbols()}
  for variant in ['D2Ev','D1Ev','D0Ev']:
   name=prefix+variant;s=symbols[name];assert isinstance(s['st_shndx'],int)
   section=e.get_section(s['st_shndx']);calls=[]
   for rs in e.iter_sections():
    if rs['sh_type'] not in ['SHT_RELA','SHT_REL'] or rs['sh_info']!=s['st_shndx']:continue
    st=e.get_section(rs['sh_link'])
    for rel in rs.iter_relocations():
     if s['st_value']<=rel['r_offset']<s['st_value']+s['st_size']:calls.append(st.get_symbol(rel['r_info_sym']).name)
   result[name]=dict(section=section.name,offset=s['st_value'],size=s['st_size'],relocation_targets=calls)
  d0=result[prefix+'D0Ev'];assert '_ZdlPv' in d0['relocation_targets'];assert '_ZdlPvm' not in d0['relocation_targets']
  assert prefix+'D1Ev' in d0['relocation_targets']
  d1=result[prefix+'D1Ev'];d2=result[prefix+'D2Ev'];assert (d1['section'],d1['offset'],d1['size'])==(d2['section'],d2['offset'],d2['size'])
  assert '_ZN8Presonus5Mixer14MixerComponentD2Ev' in d2['relocation_targets']
 if exe:
  # Canonical optimized code may tail-jump. Require actual linked D0 to call
  # wrapped unsized global delete, then independently exercise its allocation.
  dis=run(['objdump','-d','--disassemble='+prefix+'D0Ev',exe]);assert '<__wrap__ZdlPv>' in dis;assert '<_ZdlPvm' not in dis
  result['linked_D0_disassembly']=dis
 return result


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

def main(variant='d2'):
 p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',default='replay');p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');p.add_argument('--source-bindings',action='append',nargs=2,metavar=('PATH','SHA256'));a=p.parse_args()
 O.mkdir(parents=True,exist_ok=True);started=datetime.datetime.now(datetime.timezone.utc).isoformat();start=time.monotonic()
 owned=SOURCES+[str((T/'Replay.cpp').relative_to(R)),'uc-library/tests/recovery/trial10x2_storm_d0/Replay.cpp']
 if a.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*owned]);return
 canonical_binding=_current_canonical_binding(R,a.object,a.exe,a.integration,SOURCES[1],('uc-library/src/Presonus/Mixer/ChannelComponent.cpp',))
 manifest,bindings,seals=providers(a.source_bindings)
 if canonical_binding is None:deps=dependencies(bindings)
 else:deps={p:{'sha256':h,'scope':'actual canonical compiled dependency'} for p,h in canonical_binding['binding']['files'].items()}
 if a.mode=='compile':
  flags=['c++','-std=c++17','-O0','-fno-sized-deallocation','-fno-rtti','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework']
  run([*flags,'-c',SOURCES[1],'-o',O/'production.o']);run([*flags,'-c',T/'Replay.cpp','-o',O/'driver.o'])
  paths=[manifest['archives'][k]['frozen_read_path'] for k in ['libpresonus_rm_components.a','libpresonus_private_glibc29.a','libcorelib.a','libpresonus_core_allocator.a']]
  run(['c++',O/'production.o',O/'driver.o','-Wl,--gc-sections','-Wl,--wrap=_ZdlPv',*paths,'-l:libpng16.so.16','-lz','-lpthread','-ldl','-lm','-o',O/'replay'])
  (O/'compile-observation.json').write_text(json.dumps(dict(commands=LOG,sources={s:digest(R/s) for s in SOURCES},object_sha256=digest(O/'production.o'),executable_sha256=digest(O/'replay')),indent=2)+'\n');return
 obj=Path(a.object) if a.object else O/'production.o';exe=Path(a.exe).resolve() if a.exe else O/'replay'
 symbols=symbol_check(obj,exe)
 if a.mode=='symbols':return
 import native
 fixture_path=R/('uc-library/tests/recovery/trial10x2_storm_'+variant+'/fixtures.json')
 fixture=json.loads(fixture_path.read_text());fresh=native.generate(exe,variant);assert fresh==fixture
 outputs=[]
 for case in fresh['cases']:
  out=run([exe,'--product',variant,str(case['count'])]).strip();assert out==case['result'];outputs.append(out)
 domain='Three nonempty actual canonical MixerComponent borrowed-state lifecycles per exact original range: Core vector lengths 1,3,17 referencing real ChannelComponent and LinkableComponent; actual CCL owned child with numeric parameter 0.75 and string borrowed-live; both vectors, flags, child/parameters/pointers survive target destruction; actual external owner then destroys the child once. Original ARM instruction dispatch stores, exact call targets/order, object return and stack restored. Original base/free boundaries execute real host qualified MixerComponent destruction and genuine unsized global deletion. Product D2 direct exact-symbol call does not free; virtual D0 performs one wrapped real unsized free with base dispatch already restored.'
 limitations=['Portable source model only: full original Storm constructor, member layout, inheritance beyond bounded actual base delegation, EH paths and ARM ABI/hardware unresolved.','No original MixerComponent/Core binary execution. Original ARM dispatch writes remain raw emulator evidence; native boundary adapter substitutes actual approved source-port base lifecycle.','MixerComponent owns borrowed state/services references only; destruction must preserve external nonempty vectors/resources, not fabricate original resource cleanup. External actual CCL owner cleanup is separately observed.','Only requested D2/D0 original identities credited; host D1/D2 alias does not grant readiness to other original variants/thunks.','Canonical integration/readiness not performed by worker; production CPP requires -O0 and -fno-sized-deallocation to retain the explicit actual-base relocation gate; canonical replay must link --wrap=_ZdlPv.']
 full_source_hashes={s:digest(R/s) for s in SOURCES}
 source_hashes={k.removeprefix('uc-library/'):v for k,v in full_source_hashes.items()}
 source_hashes.update({k.removeprefix('uc-library/'):v['sha256'] for k,v in deps.items() if k.startswith('uc-library/')})
 repo_sources={k:v['sha256'] for k,v in deps.items() if k.startswith('third_party/ccl-framework/core/')}
 req=json.loads((native.packet(variant)/'request.json').read_text());original=req['targets'][0]
 pending=dict(original_elf_sha256=native.SHA,mangled=original['mangled'],original_address=original['address'],sources=source_hashes,repository_sources=repo_sources,domain=domain,declaration_uncertainties=limitations,portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,canonical_binding_pending=not bool(a.integration))
 proof=dict(version=1,task_id='trial10x2_storm_'+variant,namespace='Presonus::Mixer',checks='passed',cpp_compiled=True,mangling_namespace_checked=True,behavior_validated=True,binary_behavior_verified=False,original_arm_abi_verified=False,hardware_validated=False,original_elf_sha256=native.SHA,mangled_names=[original['mangled']],native_observation=fresh,case_count=3,product_outputs=outputs,sources=source_hashes,repository_sources=repo_sources,transitive_inputs=deps,provider_archives=manifest['archives'],provider_seals=seals,object=dict(path=str(obj),sha256=digest(obj)),executable=dict(path=str(exe),sha256=digest(exe)),compiled_variant_symbols=symbols,validation_domain=domain,limitations=limitations,fixture=dict(path=str(fixture_path.relative_to(R)),sha256=digest(fixture_path)),producer_hashes={str((T/n).relative_to(R)):digest(T/n) for n in ['native.py','check.py','Replay.cpp']},formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler=run(['c++','--version']).splitlines()[0],python=sys.version,session_id=os.environ.get('CODEX_THREAD_ID','unavailable'),worker_task='/root/trial10x2_storm',phase_timestamps=dict(start_utc=started,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start),proposed_readiness=dict(ready=[],pending=[pending]))
 _attach_current_canonical(proof,canonical_binding)
 if a.integration:
  ip=Path(a.integration);ip=ip if ip.is_absolute() else R/ip;proof['integration']=dict(path=str(ip),sha256=digest(ip))
 if not a.object and not a.exe:
  local=json.loads((O/'compile-observation.json').read_text());assert local['sources']==full_source_hashes;assert local['object_sha256']==digest(obj) and local['executable_sha256']==digest(exe);proof['local_compile_observation']=local
 else:proof['canonical_compilation_provenance']='Supplied canonical executable/object actually used; integration binding and exact compiled relocations/disassembly recorded. No worker cache compile proof substituted.'
 proof['commands']=LOG
 if a.out:Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
 print('PASS',variant,'3 original/provider/product comparisons')
if __name__=='__main__':main()
