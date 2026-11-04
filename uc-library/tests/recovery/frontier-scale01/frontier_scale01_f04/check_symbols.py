import subprocess,sys
s=subprocess.check_output(["nm","--defined-only",sys.argv[1]],text=True)
assert any(x.split()[-1]=="_ZNK8Presonus2UC11NetworkItem12getComponentEv" for x in s.splitlines())
print("exact original scoped accessor symbol verified; return declaration and ABI remain unresolved")
