"""Supplied-binary native/provider checker; no compile, worker .d, session or archive dependency."""
import argparse,hashlib,json,subprocess
from pathlib import Path
TASK='real10_g09_s09'
MANGLED='_ZN8Presonus5Mixer18RackMixerComponent20setDanteStaticRoutesEv'
APP_SOURCES=['include/presonus/MuteGroupBase.hpp', 'include/presonus/device_dfu.hpp', 'include/presonus/dice/packet_services.hpp', 'include/presonus/dice/response_services.hpp', 'include/presonus/mixer/ChannelComponent.hpp', 'include/presonus/mixer/DigitalInputComponent.hpp', 'include/presonus/mixer/MixerComponentBase.hpp', 'include/presonus/mixer/RackMixerComponent.hpp', 'include/presonus/mixer/StereoLineComponent.hpp', 'include/presonus/mixer/TalkbackInputComponent.hpp', 'include/presonus/noaa/card.hpp', 'include/presonus/noaa/card_handler.hpp', 'include/presonus/noaa/card_handler_state.hpp', 'include/presonus/noaa/router.hpp', 'include/presonus/noaa/router_slot_tables.hpp', 'include/presonus/noaa/setup_property.hpp', 'include/presonus/noaa/spi_packets.hpp', 'include/presonus/noaa/spi_service.hpp', 'include/presonus/noaa/sysex_packet.hpp', 'include/presonus/noaa/sysex_receiver.hpp', 'include/presonus/surface_panel/InputPin.hpp', 'src/Presonus/Mixer/ChannelComponent.cpp', 'src/Presonus/Mixer/RackMixerComponent.cpp', 'src/Presonus/NOAA/TCardHandlerLifecycle.cpp', 'src/Presonus/NOAA/TCardHandlerProperties.cpp', 'src/Presonus/NOAA/TCardResources.cpp', 'src/Presonus/NOAA/TCardRouterBusRoutes.cpp', 'src/Presonus/NOAA/TCardRouterControl.cpp']
CORE_SOURCES=['third_party/ccl-framework/core/platform/corefeatures.h', 'third_party/ccl-framework/core/platform/linux/corethread.linux.h', 'third_party/ccl-framework/core/platform/shared/coreplatformthread.h', 'third_party/ccl-framework/core/platform/shared/corerecursivereadwritelock.h', 'third_party/ccl-framework/core/platform/shared/posix/corethread.posix.h', 'third_party/ccl-framework/core/portable/coreattributes.cpp', 'third_party/ccl-framework/core/portable/coreattributes.h', 'third_party/ccl-framework/core/portable/corecomponent.cpp', 'third_party/ccl-framework/core/portable/corecomponent.h', 'third_party/ccl-framework/core/portable/corecomponentflags.h', 'third_party/ccl-framework/core/portable/corefilename.h', 'third_party/ccl-framework/core/portable/coreparaminfo.h', 'third_party/ccl-framework/core/portable/coreparams.cpp', 'third_party/ccl-framework/core/portable/coreparams.h', 'third_party/ccl-framework/core/portable/corepersistence.cpp', 'third_party/ccl-framework/core/portable/coresingleton.h', 'third_party/ccl-framework/core/portable/corestorage.h', 'third_party/ccl-framework/core/portable/coretypeinfo.h', 'third_party/ccl-framework/core/public/corebasicmacros.h', 'third_party/ccl-framework/core/public/corebuffer.cpp', 'third_party/ccl-framework/core/public/corebuffer.h', 'third_party/ccl-framework/core/public/coreclassmacros.h', 'third_party/ccl-framework/core/public/coreclibrary.h', 'third_party/ccl-framework/core/public/corecontainer.h', 'third_party/ccl-framework/core/public/coreformatter.h', 'third_party/ccl-framework/core/public/coreinterpolator.h', 'third_party/ccl-framework/core/public/coremacros.h', 'third_party/ccl-framework/core/public/coremalloc.h', 'third_party/ccl-framework/core/public/coreplatform.h', 'third_party/ccl-framework/core/public/coreproperty.h', 'third_party/ccl-framework/core/public/corestringbuffer.h', 'third_party/ccl-framework/core/public/corestringtraits.h', 'third_party/ccl-framework/core/public/corethreading.h', 'third_party/ccl-framework/core/public/coretypes.h', 'third_party/ccl-framework/core/public/coreuid.h', 'third_party/ccl-framework/core/public/corevector.h', 'third_party/ccl-framework/core/system/coredebug.h', 'third_party/ccl-framework/core/system/corethread.h', 'third_party/ccl-framework/core/text/coreattributehandler.h']
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(exe,text,provider=False):
 result=subprocess.run([str(Path(exe).resolve()),*(['--provider'] if provider else [])],input=text,text=True,capture_output=True,check=True)
 return [line[7:] for line in result.stdout.splitlines() if line.startswith('RESULT ')]
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
 p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--object',required=True);p.add_argument('--integration',required=True);p.add_argument('--out',required=True);args=p.parse_args()
 output=Path(args.out)
 if output.exists():raise FileExistsError('Existing proof is immutable; supply a NEW --out path')
 here=Path(__file__).resolve().parent;root=here.parents[3];fixture=here/'fixtures.json';data=json.loads(fixture.read_text());all_rows=data['cases']
 canonical_binding=_root_canonical_binding(root,args.object,args.exe,args.integration,'uc-library/src/Presonus/Mixer/RackMixerComponent.cpp',('uc-library/src/Presonus/Mixer/ChannelComponent.cpp', 'uc-library/src/Presonus/NOAA/TCardHandlerLifecycle.cpp', 'uc-library/src/Presonus/NOAA/TCardHandlerProperties.cpp', 'uc-library/src/Presonus/NOAA/TCardResources.cpp', 'uc-library/src/Presonus/NOAA/TCardRouterBusRoutes.cpp', 'uc-library/src/Presonus/NOAA/TCardRouterControl.cpp', 'uc-library/src/Presonus/LinkableComponent.cpp', 'uc-library/include/presonus/mixer/DigitalInputComponent.hpp', 'uc-library/include/presonus/mixer/StereoLineComponent.hpp'))
 symbols=subprocess.check_output(['nm','--defined-only',args.object],text=True);assert any(line.split()[-1]==MANGLED for line in symbols.splitlines()),MANGLED
 # UINT32_MAX original collection count is not a constructible valid Core vector.
 rows=[row for row in all_rows if row['input']['first']<=32]
 def inputs(row):
  value=row['input'];return f"{value['first']} {value['aux']} {value['fx']} {len(value['inputs'])} "+' '.join(' '.join(map(str,pair)) for pair in value['inputs'])+' '
 def instructions(row):
  result=[]
  for call in row['calls']:
   if call[0]=='debug':result.append([0,*call[1:]])
   elif call[0]=='route':result.append([1,*row['routes'][call[1]]])
   else:result.append([{'cast':2,'get':3,'changed':4}[call[0]],*call[1:]])
  return str(len(result))+' '+' '.join(' '.join(map(str,c)) for c in result)
 text=''.join(inputs(row)+'\n' for row in rows);schedule=''.join(inputs(row)+instructions(row)+'\n' for row in rows)
 actual=run(args.exe,text);provider=run(args.exe,schedule,True);assert len(actual)==len(rows)==len(provider);assert actual==provider,'actual property/queue/projection/notification mismatch'
 for i,(row,line) in enumerate(zip(rows,actual)):
  calls=[];routes=[]
  for event in line.split('|')[0].split(';'):
   if event:
    code,*v=event.split(':');v=list(map(int,v))
    if code=='E':routes.append(v);calls.append(['route',len(routes)-1])
    else:calls.append([{'D':'debug','T':'cast','G':'get','X':'changed'}[code],*v])
  assert calls==row['calls'] and routes==row['routes'],(i,calls,row['calls'],routes,row['routes'])

 sources={name:sha(root/'uc-library'/name) for name in APP_SOURCES}
 repository_sources={name:sha(root/name) for name in CORE_SOURCES}
 assert repository_sources and all(name.startswith('third_party/ccl-framework/') for name in repository_sources)
 if canonical_binding is not None:
  sources.update(canonical_binding['sources'])
  repository_sources.update(canonical_binding['repository_sources'])
  assert all(name.startswith('third_party/ccl-framework/core/') for name in repository_sources)
 domain=data['domain']+'; concrete original application call/state observations are separate from independently executed actual canonical/pinned providers'
 entry={'original_elf_sha256':data['elf_sha256'],'mangled':MANGLED,'sources':sources,'repository_sources':repository_sources,'cpp_compiled':True,'mangling_namespace_checked':True,'portable_ready':False,'declaration_uncertainties':['Unencoded original return declaration; complete original state/inheritance/layout and ARM ABI unresolved.'],'validation_domain':domain}
 proof={'version':1,'task_id':TASK,'success':True,'case_count':len(rows),'native_case_count':len(all_rows),'native_only_exclusions':len(all_rows)-len(rows),'functions':[dict(entry,success=True,domain=domain)],'proposed_readiness':{'ready':[],'pending':[entry]},'native':{'fixture_sha256':sha(fixture),'producer_sha256':sha(here/'native.py'),'range':data['range'],'oracle':data['producer'],'helper_ranges':data.get('helper_ranges',[])},'actual_provider_observations':provider,'supplied_binaries':{'exe':str(Path(args.exe).resolve()),'exe_sha256':sha(args.exe),'object':str(Path(args.object).resolve()),'object_sha256':sha(args.object)},'integration':{'path':args.integration,'sha256':sha(args.integration)},'checker_sha256':sha(__file__),'repository_sources':repository_sources}
 if canonical_binding is not None:
  proof['canonical_compile_binding']=canonical_binding['binding']
  proof['canonical_binding_transition']=canonical_binding['transition']
  proof['canonical_producer_helper']=canonical_binding['helper']
  proof['provider_archives']={x['path']:x['sha256'] for x in canonical_binding['binding']['link']['archives']}
 output.parent.mkdir(parents=True,exist_ok=True)
 with output.open('x') as stream:json.dump(proof,stream,indent=2);stream.write('\n')
 print(f'{TASK}: {len(rows)} supplied-binary native/provider cases passed; {len(all_rows)-len(rows)} native-only exclusions')
if __name__=='__main__':main()
