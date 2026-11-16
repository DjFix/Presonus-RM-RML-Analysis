"""Replay supplied production object/executable; never compile or substitute binaries."""
import argparse,hashlib,json,subprocess,sys
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
 here=Path(__file__).resolve().parent; root=here.parents[3]
 canonical_binding=_root_canonical_binding(root,a.object,a.exe,a.integration,'uc-library/src/Presonus/Mixer/RackMixerComponent.cpp',[])
 fixture=here/'fixtures.json';data=json.loads(fixture.read_text());rows=data['cases']
 mangled='_ZN8Presonus5Mixer18RackMixerComponent12getTDMRoutesEiRhS2_Rj'
 nm=subprocess.check_output(['nm','--defined-only',a.object],text=True)
 assert any(line.split()[-1]==mangled for line in nm.splitlines()),mangled
 text=''.join(' '.join(map(str,row['input']))+'\n' for row in rows)
 proc=subprocess.run([str(Path(a.exe).resolve())],input=text,text=True,capture_output=True,check=True)
 outputs=[list(map(int,line.split())) for line in proc.stdout.splitlines()]
 assert len(outputs)==len(rows)
 for i,(actual,row) in enumerate(zip(outputs,rows)):
  assert actual==row['output'],(i,row['input'],actual,row['output'])
 sources={x:sha(root/'uc-library'/x) for x in ['include/presonus/mixer/RackMixerComponent.hpp','src/Presonus/Mixer/RackMixerComponent.cpp']}
 domain=data['domain']+'; C++ replays real Channel/Talkback objects and actual runtime dynamic_cast, source-port relocated typed route storage; negative native count cases correspond to empty valid portable vector'
 entry={'original_elf_sha256':data['elf_sha256'],'mangled':mangled,'sources':sources,'cpp_compiled':True,'mangling_namespace_checked':True,'portable_ready':False,'declaration_uncertainties':['Unencoded original return declaration; original full class inheritance/layout and ARM ABI remain unresolved.'],'validation_domain':domain}
 if canonical_binding is not None:
  entry['sources'].update(canonical_binding['sources'])
  entry['repository_sources']=canonical_binding['repository_sources']
 proof={'version':1,'success':True,'case_count':len(rows),'functions':[dict(entry,success=True,domain=domain)],'proposed_readiness':{'ready':[],'pending':[entry]},'native':{'fixture_sha256':sha(fixture),'producer_sha256':sha(here/'native.py'),'range':data['range'],'oracle':data['producer']},'supplied_binaries':{'exe':str(Path(a.exe).resolve()),'exe_sha256':sha(a.exe),'object':str(Path(a.object).resolve()),'object_sha256':sha(a.object)},'integration':{'path':a.integration,'sha256':sha(a.integration)},'checker_sha256':sha(__file__)}
 if canonical_binding is not None:
  proof['canonical_compile_binding']=canonical_binding['binding']
  proof['canonical_binding_transition']=canonical_binding['transition']
  proof['canonical_producer_helper']=canonical_binding['helper']
  proof['repository_sources']=canonical_binding['repository_sources']
  proof['provider_archives']={p['path']:p['sha256'] for p in canonical_binding['binding']['link']['archives']}
 Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(proof,indent=2)+'\n');print(f'{len(rows)} routing cases matched original ARM observations')
if __name__=='__main__':main()
