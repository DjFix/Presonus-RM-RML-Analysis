import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--object',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
# Original identities are separately copied into the maintained fixture; never
# silently use a friendly reconstructed name as a replacement.
f=json.loads(Path(a.fixtures).read_text())
symbols={line.split()[-1] for line in subprocess.check_output(['/usr/bin/nm','--defined-only',a.object],text=True).splitlines() if line.split()}
for original in f['originals']:
 if original['mangled'] not in symbols:raise SystemExit('missing original: '+original['mangled'])
print('exact original ELF manglings matched',len(f['originals']),'ELF host decoration: none; no ARM ABI claim')
