import subprocess,sys
symbols=subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True)
assert '_ZNK8Presonus5Panel17PresetNameManager8getCacheEi' in {r.split()[-1] for r in symbols.splitlines() if r.split()}
assert '_ZN8Presonus5Panel14GeqUIComponent30getChannelAssignedToCurrentGeqEv' in {r.split()[-1] for r in symbols.splitlines() if r.split()}
assert '_ZN8Presonus5Panel15SPIControlGroup6onIdleEv' in {r.split()[-1] for r in symbols.splitlines() if r.split()}
print('exact ELF mangling present; native Linux no decoration; ordinary return/layout/ARM ABI unresolved')
