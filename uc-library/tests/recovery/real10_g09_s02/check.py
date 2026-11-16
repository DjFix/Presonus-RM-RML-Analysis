"""Check supplied binaries against original ARM and independently executed real providers."""
import argparse,hashlib,json,subprocess
from pathlib import Path
TASK=Path(__file__).resolve().parent.name
NAMES={'02':'_ZN8Presonus5Mixer14MixerComponent20sendStageboxSceneMsgEPKcS3_i','04':'_ZN8Presonus5Mixer14MixerComponent8doSelectEPNS0_16ChannelComponentE','05':'_ZN8Presonus5Mixer14MixerComponent12panicMuteAllEb'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(exe,text,provider=False):
 p=subprocess.run([str(Path(exe).resolve()),*(['--provider'] if provider else [])],input=text,text=True,capture_output=True,check=True)
 return [x[7:] for x in p.stdout.splitlines() if x.startswith('RESULT ')]

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
 output=Path(a.out)
 if output.exists():raise FileExistsError('Preserve existing proof; choose a fresh --out: '+str(output))
 here=Path(__file__).resolve().parent;root=here.parents[3];fixture=here/'fixtures.json';data=json.loads(fixture.read_text());rows=data['cases'];suffix=TASK[-2:];mangled=NAMES[suffix]
 canonical_binding=_root_canonical_binding(root,a.object,a.exe,a.integration,'uc-library/src/Presonus/Mixer/MixerComponent.cpp',['uc-library/src/Presonus/Mixer/NetworkSetupComponent.cpp', 'uc-library/src/Presonus/UC/ClientTypedOrigins.cpp', 'uc-library/src/Presonus/UC/MessageAttributes.cpp', 'uc-library/src/Presonus/UC/MutableMessageEvent.cpp'])
 nm=subprocess.check_output(['nm','--defined-only',a.object],text=True);assert any(x.split()[-1]==mangled for x in nm.splitlines())
 if suffix=='02':
  def hx(x):return '-' if x is None else x.encode().hex() or '_'
  text=''
  for row in rows:
   mode,name,component,slot=row['input'];m=row['message'];attrs=m['attributes'] if m else {};keys=[c[1] for c in row['calls'] if c[0]=='lookup'];slotKey,componentKey=keys if m else ['unused-slot','unused-component']
   text+=f"{mode} {hx(name)} {hx(component)} {slot} {hx(attrs.get('url','unused'))} {hx(slotKey)} {hx(componentKey)} {m['type'] if m else 19021} {m['hint'] if m else 0}\n"
  actual=run(a.exe,text);provider=run(a.exe,text,True);assert len(actual)==len(rows)==len(provider);assert actual==provider,'native-driven provider serialization/provenance mismatch'
  for i,(row,line) in enumerate(zip(rows,actual)):
   count,type_,payload,retained=line.split();assert int(retained)==0,'RAII binding retained stack payload'
   if row['message'] is None:assert int(count)==0
   else:
    assert int(count)==1 and int(type_)==row['message']['type'];decoded=json.loads(bytes.fromhex(payload).decode());native=row['message']['attributes'];assert set(decoded)==set(native)
    for key,value in native.items():assert decoded[key]==('' if value is None else value),(i,key,value,decoded[key])
 else:
  codes={'debug':0,'set':1,'changed':2,'observer':3} if suffix=='04' else {'get':0,'set':1,'remember':2,'restore':3,'clear':4}
  def inputs(row):
   if suffix=='04':return ' '.join(map(str,row['input']))+' '
   x=row['input'];return f"{len(x['values'])} {int(x['mute'])} {int(x['saved'])} "+' '.join(str(v if v is not None else -1) for v in x['values'])+' '
  text=''.join(inputs(x)+'\n' for x in rows);schedule=''.join(inputs(x)+str(len(x['calls']))+' '+' '.join(' '.join(map(str,[codes[c[0]],*c[1:]])) for c in x['calls'])+'\n' for x in rows)
  actual=run(a.exe,text);provider=run(a.exe,schedule,True);assert len(actual)==len(rows)==len(provider)
  for i,(row,line,observed) in enumerate(zip(rows,actual,provider)):
   pieces=line.split('|');expected=observed.split('|');assert pieces[0]==expected[0] and pieces[-1]==expected[-1],(i,line,observed)
   calls=[]
   for event in pieces[0].split(';'):
    if event:
     kind,*values=event.split(':');names={'D':'debug','S':'set','X':'changed','O':'observer','G':'get','R':'remember','L':'restore','C':'clear'};calls.append([names[kind],*map(int,values)])
   assert calls==row['calls'],(i,calls,row['calls'])
   if suffix=='04':assert list(map(int,pieces[1].split()))==[row['output'][k] for k in ['selected','cascadeSelected','cascadeDirty']]
   else:assert bool(int(pieces[1].split()[0]))==row['output']['saved']
 sources={x:sha(root/'uc-library'/x) for x in ['include/presonus/mixer/MixerComponent.hpp','src/Presonus/Mixer/MixerComponent.cpp']};domain=data['domain']+'; original app orchestration separate from real canonical/pinned provider execution'
 entry={'original_elf_sha256':data['elf_sha256'],'mangled':mangled,'sources':sources,'cpp_compiled':True,'mangling_namespace_checked':True,'portable_ready':False,'declaration_uncertainties':['Original unencoded return declaration; full inheritance/state layout and ARM ABI unresolved.'],'validation_domain':domain}
 if canonical_binding is not None:
  entry['sources'].update(canonical_binding['sources'])
  entry['repository_sources']=canonical_binding['repository_sources']
 proof={'version':1,'task_id':TASK,'success':True,'case_count':len(rows),'functions':[dict(entry,success=True,domain=domain)],'proposed_readiness':{'ready':[],'pending':[entry]},'native':{'fixture_sha256':sha(fixture),'producer_sha256':sha(here/'native.py'),'range':data['range'],'oracle':data['producer']},'actual_provider_observations':provider,'supplied_binaries':{'exe':str(Path(a.exe).resolve()),'exe_sha256':sha(a.exe),'object':str(Path(a.object).resolve()),'object_sha256':sha(a.object)},'integration':{'path':a.integration,'sha256':sha(a.integration)},'checker_sha256':sha(__file__)}
 if canonical_binding is not None:
  proof['canonical_compile_binding']=canonical_binding['binding']
  proof['canonical_binding_transition']=canonical_binding['transition']
  proof['canonical_producer_helper']=canonical_binding['helper']
  proof['repository_sources']=canonical_binding['repository_sources']
  proof['provider_archives']={p['path']:p['sha256'] for p in canonical_binding['binding']['link']['archives']}
 output.parent.mkdir(parents=True,exist_ok=True)
 with output.open('x') as stream:stream.write(json.dumps(proof,indent=2)+'\n')
 print(f'{TASK}: {len(rows)} native/actual-provider cases passed')
if __name__=='__main__':main()
