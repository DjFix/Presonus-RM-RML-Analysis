import subprocess,sys
symbols=subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True)
for variant in ['C1','C2']:
 name='_ZN8Presonus5Panel4Book'+variant+'Ei'
 assert any(line.split()[-1]==name for line in symbols.splitlines()),name
print('PASS both actual original constructor variant names (ELF host decoration: none)')
