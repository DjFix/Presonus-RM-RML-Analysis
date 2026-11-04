import subprocess,sys
out=subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True)
for variant in ('C1','C2'):
 assert '_ZN8Presonus5Panel12ControlGroup'+variant+'Eii' in out
print('Original C1/C2 mangled names present; Linux ELF decoration none; not ARM ABI evidence')
