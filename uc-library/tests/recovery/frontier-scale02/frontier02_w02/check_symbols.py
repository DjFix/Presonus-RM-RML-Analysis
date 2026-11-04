import subprocess,sys
symbol='_ZN8Presonus5Panel6FXBookC2EiPNS0_17FxPresetComponentEPN4Core8Portable9ParameterE'
s=subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True)
assert any(line.split()[-1]==symbol for line in s.splitlines()),s
print(symbol)
