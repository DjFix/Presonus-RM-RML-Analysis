import subprocess,sys
s=subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True)
assert any(l.split()[-1]=='_ZN8Presonus14DisplayManager11getInstanceEv' for l in s.splitlines())
assert any(l.split()[-1]=='_ZN8Presonus14DisplayManager11theInstanceE' for l in s.splitlines())
print('Exact original accessor and data mangling present; declaration/ABI unresolved')
