import json,subprocess,sys,struct
from pathlib import Path
root=Path('uc-library/candidates/graph-live-trial-04-midi')
exe=sys.argv[2] if len(sys.argv)>2 else 'temp/recovery-work/graph-live-trial-04/midi-worker/replay'
mode=sys.argv[1]
if mode=='compile': subprocess.run(['c++','-std=c++17','-Iuc-library/include','uc-library/src/Presonus/Surface/MidiMixerHandler.cpp','uc-library/tests/graph_trial04_midi_tests.cpp','-o',exe],check=True)
elif mode=='symbols':
 out=subprocess.check_output(['nm',exe],text=True)
 for n in ['11resetColorsEv','14getMappingNameEi','17resetAccumulationEv','25updateRecordReadyMappingsEv','6onIdleEv']:assert '_ZN8Presonus7Surface16MidiMixerHandler'+n in out
elif mode=='replay':
 cases=json.loads((root/'native-observations.json').read_text())
 # Normalize native pointers to independently established boundary identities.
 # Compare outputs from actual C++ execution, never self-computed C++ expectations.
 for c in cases:
  n=c['name'];variant=c.get('variant',c.get('flag'))
  out=subprocess.check_output([exe,n,str(variant)],text=True)
  if n=='getMappingName':
   strings={0x1ea328:'MCU over MIDI',0x1f2670:''}
   actual=out.rstrip('\n');expected=strings[c['r0']]
  elif n=='resetAccumulation':
   actual=[int(v) for v in out.split()];expected=list(struct.unpack('<17I',bytes.fromhex(c['memory'])[160:228]))
  elif n=='resetColors':
   actual=out.splitlines();expected=[]
   for call in c['trace']:
    assert call[0]=='0x76c6c' and call[1]==0x284000 and call[3]==0x19b1c0
    expected.append('x') # Native initialized controls contain x\0.
  elif n=='onIdle':
   actual=out.splitlines();expected=[]
   for call in c['trace']:
    assert call[0]=='0x10100'
    expected.append({0x282000:'0',0x282080:'1'}[call[1]])
  elif n=='updateRecordReadyMappings':
   actual=out.splitlines();call=c['trace'][-1];assert call[0]=='0xbd854'
   expected=[{0x26cad0:'vpot',0x26c7e4:'record'}[call[2]]]
  assert actual==expected,(n,variant,actual,expected)
 print(f'{len(cases)} direct original ARM fixture -> C++ output/state/call-trace comparisons passed')
