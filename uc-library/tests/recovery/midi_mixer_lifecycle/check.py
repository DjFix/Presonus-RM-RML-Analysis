"""Local Linux worker checks. Compile current owned sources with real CCL."""
import argparse,json,pathlib,subprocess,os,runpy
ROOT=pathlib.Path(__file__).resolve().parents[4]
HERE=pathlib.Path('uc-library/tests/recovery/midi_mixer_lifecycle')
OUT=pathlib.Path('temp/recovery-work/rolling200-02/midi-lifecycle16');EXE=OUT/'replay'
ARCH=pathlib.Path('temp/core-upstream/root-integration-01');SDK=ARCH/'upstream-core/sdk'
NEW=['uc-library/src/Presonus/Surface/MidiMixerLifecycle.cpp','uc-library/src/Presonus/Surface/PanelRegistrarMidiDispatch.cpp']
SOURCES=NEW+['uc-library/src/Presonus/Surface/MidiMixerHandler.cpp','uc-library/src/Presonus/Surface/MidiMixerControls.cpp','uc-library/src/Presonus/MackieControlComponentModel.cpp','uc-library/src/Presonus/MackieControlModel.cpp','uc-library/src/Presonus/MackieControlModelMappings.cpp','uc-library/src/Presonus/MackieControlComponent.cpp','uc-library/tests/recovery/MidiMixerLifecycleReplay.cpp']
PREFIX=['/usr/bin/c++','-std=c++20','-O0','-UNDEBUG','-fno-rtti','-fno-lto','-fsized-deallocation','-fno-devirtualize','-fno-devirtualize-speculatively','-ffunction-sections','-fdata-sections','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework']
LINK=[str(ARCH/'libpresonus_uc.a'),str(SDK/'lib/libcorelib.a'),str(SDK/'lib/libpresonus_core_allocator.a'),'-lz','-lpthread','-Wl,--gc-sections']
WRAPS=['_ZdlPv','_ZdlPvm','_ZNK4Core8Portable9Component17getParameterByTagEi','_ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE','_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE','_ZN4Core8Portable9ComponentD2Ev']
def run(argv,**kwargs):
 print(json.dumps(list(map(str,argv))),flush=True)
 r=subprocess.run(list(map(str,argv)),cwd=ROOT,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(ROOT/OUT)},**kwargs)
 if r.returncode:print(r.stdout+r.stderr,flush=True);r.check_returncode()
 return r.stdout

def regression():
 # Rebuild every historical driver against current lifecycle definitions.
 dispatch=runpy.run_path(str(ROOT/'uc-library/tests/recovery/rolling200-02/midi-dispatch/check.py'))
 cmd=dispatch['COMPILE'];i=cmd.index(dispatch['SOURCES'][0]);cmd=cmd[:i]+NEW+cmd[i:];cmd[cmd.index('-o')+1]=str(OUT/'dispatch')
 run(cmd)
 for mode in ['symbols','replay','guards']:
  print(run(['uc-library/.venv/bin/python','uc-library/tests/recovery/rolling200-02/midi-dispatch/check.py',mode,'--executable',str(OUT/'dispatch')]))
 sources=['uc-library/src/Presonus/StormMixSceneComponent.cpp','uc-library/src/Presonus/Panel/FxPresetComponent.cpp','uc-library/src/Presonus/Surface/MidiMixerHandler.cpp','uc-library/src/Presonus/Surface/MidiMixerControls.cpp','uc-library/src/Presonus/MappingTable.cpp','uc-library/src/Presonus/MappingTableConnect.cpp','uc-library/tests/recovery/rolling200-stage03-w01/driver.cpp']
 wraps=['_ZNK4Core8Portable9Component17getParameterByTagEi','_ZN8Presonus12MappingTable7connectEPKcPN4Core8Portable9ParameterES2_b','_ZN8Presonus12MappingTable15setControlColorEPKcS2_','_ZN8Presonus12MappingTable17setControlEnabledEPKcb']
 run(PREFIX+NEW+sources+LINK+['-Wl,--wrap='+n for n in wraps]+['-o',str(OUT/'mapping')])
 print(run(['uc-library/.venv/bin/python','uc-library/tests/recovery/rolling200-stage03-w01/replay.py',str(OUT/'mapping'),'uc-library/tests/recovery/rolling200-stage03-w01/fixtures.json']))
 run(PREFIX+NEW+['uc-library/src/Presonus/Surface/MidiMixerHandler.cpp','uc-library/tests/graph_trial04_midi_tests.cpp']+LINK+['-o',str(OUT/'helpers')])
 for mode in ['symbols','replay']:
  print(run(['uc-library/.venv/bin/python','uc-library/candidates/graph-live-trial-04-midi/check.py',mode,str(OUT/'helpers')]))
 param='uc-library/candidates/rolling200_02_midi_param_01'
 run(PREFIX+NEW+['uc-library/src/Presonus/Surface/MidiMixerHandler.cpp','uc-library/tests/recovery/MidiMixerParamReplay.cpp']+LINK+['-Wl,--wrap=_ZNK4Core8Portable9Component17getParameterByTagEi','-o',str(OUT/'param')])
 print(run(['uc-library/.venv/bin/python',param+'/check.py','replay',str(OUT/'param')]))

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['compile','symbols','replay','regression','guards','header']);p.add_argument('--executable',default=str(EXE));p.add_argument('--fixtures',default=str(HERE/'fixtures.json'));a=p.parse_args();(ROOT/OUT).mkdir(parents=True,exist_ok=True)
 if a.mode=='header':print(run(PREFIX+['-fsyntax-only',str(HERE/'HeaderConsumer.cpp')]))
 elif a.mode=='compile':print(run(PREFIX+SOURCES+LINK+['-Wl,--wrap='+n for n in WRAPS]+['-o',str(EXE)]))
 elif a.mode=='symbols':
  out=run(['/usr/bin/nm','--defined-only',a.executable]);names={s.split()[-1]:s.split()[0] for s in out.splitlines()}
  for variant in [0,1,2]:
   name=f'_ZN8Presonus7Surface16MidiMixerHandlerD{variant}Ev';assert name in names;print(name,names[name])
  print('Three exact symbols; compiled D1/D2 alias',names['_ZN8Presonus7Surface16MidiMixerHandlerD1Ev']==names['_ZN8Presonus7Surface16MidiMixerHandlerD2Ev'],'; original D1/D2 distinct entry addresses; no ABI equivalence claim')
 elif a.mode=='regression':regression()
 elif a.mode=='guards':print(run([a.executable,'guards']))
 else:
  fixture=json.loads((ROOT/a.fixtures).read_text());cases=fixture['cases']
  for c in cases:
   args=[a.executable,str(c['variant']),str(c['present']),''.join(map(str,c['entries']))]
   for missing in [False,True] if c['present'] else [False]:
    line=run(args+(['missing'] if missing else [])).strip();events,remaining=line.split('|');assert events==''.join(t+';' for t in c['trace']),(c,line);assert remaining==''.join(map(str,c['remaining_at_cleanup'])),(c,line)
  print('PASS',len(cases),'native target cases /',sum(2 if c['present'] else 1 for c in cases),'real CCL lifecycle replays: observer removal (installed/missing), registry order, owned child/parameter destruction, live parameter notification, switch+encoder MIDI before, no callbacks after, actual forwarded D0 deallocation; D1/D2 no deallocation')
if __name__=='__main__':main()
