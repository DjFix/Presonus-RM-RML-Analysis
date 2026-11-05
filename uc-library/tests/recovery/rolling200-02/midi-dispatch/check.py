"""Actual canonical Mackie/CCL provider replay of native boundary observations."""
import argparse,json,pathlib,subprocess,os
ROOT=pathlib.Path(__file__).resolve().parents[5]
SCRATCH=pathlib.Path('temp/recovery-work/rolling200-02/midi-dispatch');EXE=SCRATCH/'replay'
SOURCES=['uc-library/src/Presonus/Surface/MidiMixerHandler.cpp','uc-library/src/Presonus/Surface/MidiMixerControls.cpp','uc-library/src/Presonus/MackieControlComponentModel.cpp','uc-library/src/Presonus/MackieControlModel.cpp','uc-library/src/Presonus/MackieControlModelMappings.cpp','uc-library/src/Presonus/MackieControlComponent.cpp','uc-library/tests/recovery/MidiMixerHandlerDispatchReplay.cpp']
WRAPS=['_ZN8Presonus22MackieControlComponent8getModelEv','_ZN8Presonus18MackieControlModel17releaseAllButtonsEv','_ZN8Presonus18MackieControlModel14setButtonStateEib','_ZN8Presonus18MackieControlModel11turnEncoderEii','_ZN8Presonus18MackieControlModel14turnScrubwheelEi','_ZN8Presonus7Surface16MidiMixerHandler18setControlsEnabledEb','_ZNK8Presonus5Panel7Control12getParameterEv','_ZNK4Core8Portable9Component17getParameterByTagEi']
ARCH=pathlib.Path('temp/core-upstream/root-integration-01')
COMPILE=['/usr/bin/c++','-std=c++20','-O0','-fno-rtti','-ffunction-sections','-fdata-sections','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework']+SOURCES+[str(ARCH/'libpresonus_uc.a'),str(ARCH/'upstream-core/sdk/lib/libcorelib.a'),str(ARCH/'upstream-core/sdk/lib/libpresonus_core_allocator.a'),'-lz','-lpthread','-Wl,--gc-sections']+['-Wl,--wrap='+n for n in WRAPS]+['-o',str(EXE)]
def run(argv,**kwargs):
 print(json.dumps(argv),flush=True);r=subprocess.run(argv,cwd=ROOT,env={**os.environ,'TMPDIR':str(ROOT/SCRATCH)},text=True,capture_output=True,**kwargs)
 if r.returncode:print(r.stdout+r.stderr);r.check_returncode()
 return r

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['compile','symbols','replay','regression','guards']);p.add_argument('--executable',default=str(EXE));p.add_argument('--fixtures',default='evidence/recovery/2026-11-05/rolling200-02/midi-dispatch/native.json');a=p.parse_args()
 if a.mode=='compile':(ROOT/SCRATCH).mkdir(parents=True,exist_ok=True);print(run(COMPILE).stdout)
 elif a.mode=='guards':print(run([a.executable,'guards']).stdout)
 elif a.mode=='regression':
  sources=['uc-library/src/Presonus/StormMixSceneComponent.cpp','uc-library/src/Presonus/Panel/FxPresetComponent.cpp','uc-library/src/Presonus/Surface/MidiMixerHandler.cpp','uc-library/src/Presonus/Surface/MidiMixerControls.cpp','uc-library/src/Presonus/MappingTable.cpp','uc-library/src/Presonus/MappingTableConnect.cpp','uc-library/tests/recovery/rolling200-stage03-w01/driver.cpp']
  exe=str(SCRATCH/'regression');argv=COMPILE[:COMPILE.index(SOURCES[0])]+sources+[str(ARCH/'libpresonus_uc.a'),str(ARCH/'upstream-core/sdk/lib/libcorelib.a'),str(ARCH/'upstream-core/sdk/lib/libpresonus_core_allocator.a'),'-lz','-lpthread','-Wl,--gc-sections','-o',exe]
  for n in ['_ZNK4Core8Portable9Component17getParameterByTagEi','_ZN8Presonus12MappingTable7connectEPKcPN4Core8Portable9ParameterES2_b','_ZN8Presonus12MappingTable15setControlColorEPKcS2_','_ZN8Presonus12MappingTable17setControlEnabledEPKcb']:argv+=['-Wl,--wrap='+n]
  run(argv);print(run(['uc-library/.venv/bin/python','uc-library/tests/recovery/rolling200-stage03-w01/replay.py',exe,'uc-library/tests/recovery/rolling200-stage03-w01/fixtures.json']).stdout)
 elif a.mode=='symbols':
  names={s.split()[-1] for s in run(['/usr/bin/nm','--defined-only',a.executable]).stdout.splitlines()}
  for n in range(1,5):
   req=json.loads((ROOT/'temp/recovery-work/rolling200-02/next-implementation10/prepared-midi10/packets'/f'rolling200_02_midi_dispatch10_{n:02}'/'request.json').read_text());name=req['targets'][0]['mangled'];assert name in names,name;print(name)
  print('four exact original symbols, host ELF no decoration; original return/layout/ARM ABI unresolved')
 else:
  cases=json.loads((ROOT/a.fixtures).read_text())['cases'];lines=run([a.executable],input=''.join(' '.join(map(str,c['input']))+'\n' for c in cases)).stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases))
  for i,(c,line) in enumerate(zip(cases,lines)):
   events,acc,ctrl,midi=line.split('|');assert events==''.join(e+';' for e in c['trace']),(i,c['input'],events,c['trace']);assert list(map(int,acc.split()))==c['accumulation'],(i,acc,c['accumulation']);assert int(ctrl)==bool(c['controller'])
   observed=[[int(v) for v in msg.split(',') if v] for msg in midi.split(';') if msg]
   expected=[]
   for event in c['trace']:
    parts=event.split();name=parts[0]
    if name=='release':expected += [[144,42,0]]+[[144,104+j,0] for j in range(9)]
    elif name=='button' and int(parts[3])==0:expected.append([144,42,0])
    elif name=='encoder':
     d=int(parts[3]);mag=min(abs(d),63);expected.append([176,23,mag if d<0 else mag|64])
    elif name=='scrub':expected.append([176,60,65 if int(parts[2])<0 else 1])
   assert observed==expected,(i,c['input'],observed,expected)
  print(len(cases),'exact native-target/provider boundary, accumulator and controller differential cases; actual button/fader release effects checked')
if __name__=='__main__':main()
