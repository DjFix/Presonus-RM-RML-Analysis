import subprocess
out=subprocess.check_output(['nm','temp/recovery-work/frontier-scale02/frontier02_w08/NetworkSetupComponent.o'],text=True)
assert ' T _ZN8Presonus7Surface21NetworkSetupComponent9ListModel11setSelectedEPNS_2UC11NetworkItemE\n' in out
print('Exact original ELF mangling present; Linux ELF, no decoration')
