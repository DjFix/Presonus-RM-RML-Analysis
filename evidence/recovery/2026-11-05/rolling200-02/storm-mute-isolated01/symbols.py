import subprocess,sys
s=subprocess.check_output(['/usr/bin/nm','--defined-only',sys.argv[1]],text=True)
assert '_ZNK8Presonus23StormMuteGroupComponent17createDefaultNameEi' in {x.split()[-1] for x in s.splitlines() if x.split()}
print('PASS exact original mangled symbol')
