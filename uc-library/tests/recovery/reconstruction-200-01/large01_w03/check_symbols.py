import subprocess,sys
from oracle import targets
out=subprocess.check_output(['/usr/bin/nm','--defined-only',sys.argv[1]],text=True)
names={l.split()[-1] for l in out.splitlines() if l.split()}
for t in targets():
 assert t['mangled'] in names,t['mangled']
 print(t['mangled'])
print('Eight exact ELF names present, ELF host needs no decoration. Return/layout/ARM ABI not established.')
