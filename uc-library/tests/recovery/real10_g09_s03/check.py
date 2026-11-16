"""Compare supplied Mixer object/executable to original ARM dispatch observations."""
import argparse,hashlib,json,subprocess
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def _root_canonical_binding(root, obj, exe, integration, source, providers):
 if Path(integration).resolve() != (root/'uc-library/validation/integration.json').resolve():return None
 import importlib.util
 helper=root/'uc-library/tools/recovery/canonical_compile_bindings.py'
 spec=importlib.util.spec_from_file_location('canonical_compile_bindings',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 value=module.bind(root,Path(obj),source,exe_path=Path(exe),required_provider_sources=providers,required_archive_names=('libcorelib.a','libpresonus_core_allocator.a'))
 unexpected_ccl=[p for p in value['files'] if p.startswith('third_party/ccl-framework/') and not p.startswith('third_party/ccl-framework/core/')]
 assert not unexpected_ccl, 'Unexpected non-Core CCL dependency paths: '+repr(unexpected_ccl)
 core={p:h for p,h in value['files'].items() if p.startswith('third_party/ccl-framework/core/')}
 library={p.removeprefix('uc-library/'):h for p,h in value['files'].items() if p.startswith('uc-library/')}
 assert core and library and source.removeprefix('uc-library/') in library, 'Actual nonempty canonical library/CCL dependency closure required'
 return {'binding':value,'sources':library,'repository_sources':core,'transition':module.load_transition(root,'temp/recovery-work/reconstruction10x10-20261116/workflow/checker-canonical-audit/review02/CANONICAL_BINDING_TRANSITION.json'),'helper':{'path':'uc-library/tools/recovery/canonical_compile_bindings.py','sha256':hashlib.sha256(helper.read_bytes()).hexdigest()}}

def main():
 p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--object',required=True);p.add_argument('--integration',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 here=Path(__file__).resolve().parent;root=here.parents[3];fixture=here/'fixtures.json';data=json.loads(fixture.read_text());rows=data['cases']
 canonical_binding=_root_canonical_binding(root,a.object,a.exe,a.integration,'uc-library/src/Presonus/Mixer/MixerComponent.cpp',['uc-library/src/Presonus/LinkableComponent.cpp'])
 mangled='_ZN8Presonus5Mixer14MixerComponent6doLinkEPNS0_12GEQComponentEb'
 nm=subprocess.check_output(['nm','--defined-only',a.object],text=True);assert any(x.split()[-1]==mangled for x in nm.splitlines())
 pairs=[(row,seeded) for row in rows for seeded in [0,1]]
 text=''.join(f"{len(row['input']['entries'])} {row['input']['target']} {int(row['input']['link'])} {seeded} "+' '.join(map(str,row['input']['entries']))+'\n' for row,seeded in pairs)
 proc=subprocess.run([str(Path(a.exe).resolve())],input=text,text=True,capture_output=True,check=True)
 lines=[list(map(int,x.split())) for x in proc.stdout.splitlines()];assert len(lines)==len(pairs)
 provider=[]
 for i,((row,seeded),got) in enumerate(zip(pairs,lines)):
  assert len(got)==7
  call=row['calls'];assert len(call)<=1
  expected=[call[0]['slot'],call[0]['receiver'],call[0]['partner'] if call[0]['slot']==60 else 0,call[0]['flag'] or 0] if call else [0,0,0,0]
  assert got[:4]==expected,(i,row,got,expected)
  provider.append({'case':i//2,'prelinked':bool(seeded),'boundary_set_remove_master_counts':got[4:]})
 sources={x:sha(root/'uc-library'/x) for x in ['include/presonus/mixer/MixerComponent.hpp','src/Presonus/Mixer/MixerComponent.cpp']}
 domain=data['domain']+'; actual canonical Linkable provider called through entry-observation wrappers on initially unlinked and prelinked portable states; downstream application boundaries traced separately'
 entry={'original_elf_sha256':data['elf_sha256'],'mangled':mangled,'sources':sources,'cpp_compiled':True,'mangling_namespace_checked':True,'portable_ready':False,'declaration_uncertainties':['Original unencoded return declaration, GEQ/Linkable original inheritance and ARM layout/ABI remain unresolved.'],'validation_domain':domain}
 if canonical_binding is not None:
  entry['sources'].update(canonical_binding['sources'])
  entry['repository_sources']=canonical_binding['repository_sources']
 proof={'version':1,'success':True,'case_count':len(pairs),'native_case_count':len(rows),'functions':[dict(entry,success=True,domain=domain)],'proposed_readiness':{'ready':[],'pending':[entry]},'native':{'fixture_sha256':sha(fixture),'producer_sha256':sha(here/'native.py'),'range':data['range'],'receiver_vptr':data['receiver_vptr'],'oracle':data['producer']},'actual_provider_observations':provider,'supplied_binaries':{'exe':str(Path(a.exe).resolve()),'exe_sha256':sha(a.exe),'object':str(Path(a.object).resolve()),'object_sha256':sha(a.object)},'integration':{'path':a.integration,'sha256':sha(a.integration)},'checker_sha256':sha(__file__)}
 if canonical_binding is not None:
  proof['canonical_compile_binding']=canonical_binding['binding']
  proof['canonical_binding_transition']=canonical_binding['transition']
  proof['canonical_producer_helper']=canonical_binding['helper']
  proof['repository_sources']=canonical_binding['repository_sources']
  proof['provider_archives']={p['path']:p['sha256'] for p in canonical_binding['binding']['link']['archives']}
 Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(proof,indent=2)+'\n');print(f'{len(pairs)} GEQ dispatch/provider cases matched {len(rows)} original ARM observations')
if __name__=='__main__':main()
