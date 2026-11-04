import subprocess,sys
s=subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True)
for v in ['C1','C2']:
 name='_ZN8Presonus3Dsp10Controller'+v+'EiPKNS0_19ParamDescriptorListE'
 assert any(line.split()[-1]==name for line in s.splitlines()),name
print('Both exact original constructor symbols emitted; compiler aliases allowed; no ARM ABI claim')
