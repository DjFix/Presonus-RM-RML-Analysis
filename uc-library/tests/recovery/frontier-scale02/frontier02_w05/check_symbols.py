import argparse,subprocess
p=argparse.ArgumentParser();p.add_argument('--object',required=True);a=p.parse_args()
s=subprocess.check_output(['nm','--defined-only',a.object],text=True)
for name in ['_ZN8Presonus5Mixer15GlobalComponent15getTempFilePathEv','_ZN8Presonus5Mixer14FXBusComponent12paramChangedEPN4Core8Portable9ParameterEi']:
 assert any(line.split()[-1]==name for line in s.splitlines()),name
 print(name)
