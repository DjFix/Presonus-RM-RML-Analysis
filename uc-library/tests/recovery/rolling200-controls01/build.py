import json,subprocess,sys,shlex
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'temp/recovery-work/rolling200-controls01/build'
OUT.mkdir(parents=True,exist_ok=True)
BUILD=ROOT/'temp/core-upstream/root-integration-01'
config=json.loads((Path(__file__).with_name('build_config.json')).read_text());cmd=config['compile_prefix']
# Compile current owned production directly, use real canonical archive/provider for other methods.
sources=['uc-library/src/Presonus/McuVpotControl.cpp','uc-library/src/Presonus/Panel/GeqUIComponent.cpp','uc-library/tests/recovery/rolling200-controls01/driver.cpp','uc-library/src/Presonus/Panel/GeqAssignedChannel.cpp']
objects=[]
for n,s in enumerate(sources):
 obj=OUT/f'{n}.o';argv=cmd+['-std=c++17','-c',str(ROOT/s),'-o',str(obj)];print(shlex.join(argv),flush=True);subprocess.run(argv,cwd=ROOT,check=True);objects.append(str(obj))
link=['/usr/bin/c++','-O3','-DNDEBUG']+objects+['-o',str(OUT/'driver')]+config['link_suffix']
for sym in ['_ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE','_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE','_ZN4Core8Portable7Control12paramChangedEPNS0_9ParameterEi','_ZN4Core8Portable8ValueBar13setAttributesERKNS0_10AttributesE','_ZN4Core8Portable14ViewAttributes9getBitmapERKNS0_10AttributesEPKc']:link.append('-Wl,--wrap='+sym)
print(shlex.join(link),flush=True);subprocess.run(link,cwd=BUILD,check=True)
