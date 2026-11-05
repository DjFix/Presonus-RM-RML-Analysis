import json,subprocess,sys,shlex
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).parent;OUT=ROOT/'temp/recovery-work/rolling200-02/stage03-w01/build';OUT.mkdir(parents=True,exist_ok=True)
config=json.loads((HERE/'build_config.json').read_text());prefix=[x for x in config['compile_prefix'] if x!='-UNDEBUG'];prefix+=['-std=c++20','-ffunction-sections','-fdata-sections']
sources=['uc-library/src/Presonus/StormMixSceneComponent.cpp','uc-library/src/Presonus/Panel/FxPresetComponent.cpp','uc-library/src/Presonus/Surface/MidiMixerHandler.cpp','uc-library/src/Presonus/Surface/MidiMixerControls.cpp','uc-library/src/Presonus/MappingTable.cpp','uc-library/src/Presonus/MappingTableConnect.cpp','uc-library/tests/recovery/rolling200-stage03-w01/driver.cpp'];objects=[]
for i,s in enumerate(sources):
 obj=OUT/f'{i}.o';cmd=prefix+['-c',str(ROOT/s),'-o',str(obj)];print(shlex.join(cmd),flush=True);subprocess.run(cmd,check=True);objects.append(str(obj))
cmd=['/usr/bin/c++','-Wl,--gc-sections']+objects+['-o',str(OUT/'driver'),str(ROOT/'temp/core-upstream/root-integration-01/libpresonus_uc.a')]+config['link_suffix']
for sym in ['_ZNK4Core8Portable9Component17getParameterByTagEi','_ZN8Presonus12MappingTable7connectEPKcPN4Core8Portable9ParameterES2_b','_ZN8Presonus12MappingTable15setControlColorEPKcS2_','_ZN8Presonus12MappingTable17setControlEnabledEPKcb']:cmd+=['-Wl,--wrap='+sym]
print(shlex.join(cmd),flush=True);subprocess.run(cmd,check=True)
