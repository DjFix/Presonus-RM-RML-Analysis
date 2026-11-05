import subprocess
symbol='_ZN8Presonus4NOAA17TCardUCNetHandler6idleIOEv'
out=subprocess.check_output(['nm','--defined-only','temp/recovery-work/ucnet-idle-local/handler.o'],text=True)
assert any(line.split()[-1]==symbol for line in out.splitlines())
print(next(line for line in out.splitlines() if line.split()[-1]==symbol))
print(subprocess.check_output(['c++filt',symbol],text=True).strip())
