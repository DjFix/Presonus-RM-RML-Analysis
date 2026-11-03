import argparse,subprocess
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);a=p.parse_args()
symbols=subprocess.check_output(['nm','--defined-only',a.executable],text=True)
expected=['_ZN8Presonus5Mixer18MixerComponentBase18resetPermissionsPWEv','_ZN8Presonus5Mixer18MixerComponentBase20onCascadeStateChangeEv','_ZZN8Presonus5Mixer18MixerComponentBase10savePresetERKN4Core8Portable8FileNameEPKcNS2_11ConstStringEEN24StorageCompletionHandlerD0Ev','_ZZN8Presonus5Mixer18MixerComponentBase9saveSceneERKN4Core8Portable8FileNameEPKcbEN17CompletionHandlerD0Ev']
for name in expected:
 found=[line for line in symbols.splitlines() if line.split()[-1]==name]
 assert len(found)==1,(name,found)
 print(found[0])
print('PASS exact original four encoded symbols on Linux ELF; no decoration adjustment; portable layout/ABI scope only')
