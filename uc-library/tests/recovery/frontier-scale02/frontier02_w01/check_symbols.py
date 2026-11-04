import subprocess,sys
s=subprocess.check_output(["nm","--defined-only",sys.argv[1]],text=True)
assert " _ZN8Presonus5Panel9SceneBookC1Ei\n" in s
print("Exact C1 present; generated C2 not separately admitted")
