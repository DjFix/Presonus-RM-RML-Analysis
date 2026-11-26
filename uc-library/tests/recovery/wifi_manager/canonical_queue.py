import subprocess,sys
p=subprocess.run([sys.argv[1],"providerQueue"],check=True,text=True,capture_output=True,timeout=10)
assert p.stdout == "CCL queue work=3 destroy=3 status=Store to Join\n",repr(p.stdout)
print(p.stdout,end="")
