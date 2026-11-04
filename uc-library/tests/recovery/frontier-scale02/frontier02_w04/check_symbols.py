import subprocess,sys
symbols=subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True)
assert '_ZN8Presonus5Panel15SPIControlGroupC1Eiii' in {line.split()[-1] for line in symbols.splitlines() if line.split()}
print('original constructor C1 exact ELF name present; no decoration on Linux')
