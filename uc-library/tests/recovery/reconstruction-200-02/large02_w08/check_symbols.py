import json,subprocess,sys
from pathlib import Path
fixtures=json.loads((Path(__file__).with_name('fixtures.json')).read_text())
output=subprocess.check_output(['/usr/bin/nm','--defined-only',sys.argv[1]],text=True)
symbols={line.split()[-1] for line in output.splitlines() if line.split()}
missing=[r['metadata']['mangled'] for r in fixtures['ranges'] if r['metadata']['mangled'] not in symbols]
if missing:raise SystemExit('Missing original symbols: '+str(missing))
print('19 exact original ELF names verified; Linux ELF no extra decoration; not ARM ABI/layout proof')
