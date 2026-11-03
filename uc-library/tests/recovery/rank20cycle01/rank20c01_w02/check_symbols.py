import subprocess
import sys
p=subprocess.run(['nm','--defined-only',sys.argv[1]],capture_output=True,text=True,check=True)
symbols={line.split()[-1] for line in p.stdout.splitlines() if line.split()}
assert {'_ZN8Presonus17MackieControlUnitD1Ev','_ZNK8Presonus12MeterControl12isHorizontalEv'} <= symbols
print('Exact original ELF Mackie D1 and MeterControl isHorizontal manglings found; compiler D2/D0 are not admitted original targets. ELF has no extra leading underscore.')
