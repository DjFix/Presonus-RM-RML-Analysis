import subprocess,json,sys
from pathlib import Path
expected=json.loads(Path('uc-library/tests/recovery/reconstruction-200-01/large01_w04/fixtures.json').read_text())['originals']
symbols={line.split()[-1] for line in subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True).splitlines() if line.split()}
for original in expected: assert original['mangled'] in symbols,original['mangled']
print('10 exact ELF mangled identities present; ordinary return/layout/ARM ABI unresolved')
