import subprocess,sys
symbol='_ZN8Presonus3Dsp10Controller12setupProcessERKNS0_13SetupPropertyE'
rows=subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True).splitlines()
assert any(r.split()[-1]==symbol for r in rows)
print(symbol)
