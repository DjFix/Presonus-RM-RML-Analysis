import json,subprocess,sys
from pathlib import Path
names={x['mangled'] for x in json.loads(Path('uc-library/tests/recovery/stabilized01_channels/fixtures.json').read_text())['ranges']}
text=subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True)
found={l.split()[-1] for l in text.splitlines() if l.split()}
assert names<=found,sorted(names-found)
print(json.dumps({'passed':True,'original_mangled_names':sorted(names),'format':'Linux ELF, no object decoration'}))
