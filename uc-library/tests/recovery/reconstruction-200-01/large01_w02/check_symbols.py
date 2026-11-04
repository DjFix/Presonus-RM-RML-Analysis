import json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[5]
packets=root/'temp/recovery-work/reconstruction-200-01/large-batch01/packets'
expected=[json.loads((packets/f'large01_w02_{i:02}'/'request.json').read_text())['targets'][0]['mangled'] for i in range(1,11)]
text=subprocess.check_output(['nm','--defined-only',*sys.argv[1:]],text=True)
names={line.split()[-1] for line in text.splitlines() if line.split()}
assert not (set(expected)-names),set(expected)-names
print(json.dumps({'exact_original_symbols':expected,'object_format':'ELF x86_64; no underscore decoration','scope':'Names and encoded parameter scopes only; original returns/layout/ARM ABI unresolved'}))
