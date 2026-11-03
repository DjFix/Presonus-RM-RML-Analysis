from pathlib import Path
import subprocess,sys,json
packets=Path('temp/recovery-work/frontier-small01/batch01/packets')
nm=subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True)
found={line.split()[-1] for line in nm.splitlines() if line.split()}
for p in sorted(packets.glob('frontier01_w04_*')):
 c=json.loads((p/'context.json').read_text());n=c['native_context']['nodes'][c['native_roots'][0]]['metadata']['mangled'];assert n in found,n
 print(n)
print('8 exact ELF mangled identities; Linux ELF no object-format prefix adjustment; D2/D0 are compiler emissions, outside selected original D1 claims')
