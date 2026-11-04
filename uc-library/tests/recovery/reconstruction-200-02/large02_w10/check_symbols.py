import json,subprocess,sys
from pathlib import Path
fixture=json.loads(Path(__file__).with_name('fixtures.json').read_text())
actual=set(line.split()[-1] for line in subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True).splitlines() if line.split())
missing=[]
for row in fixture['ranges']:
 if row['n'] in fixture['covered_targets'] and row['mangled'] not in actual:missing.append(row['mangled'])
assert not missing,missing
import hashlib
print(json.dumps({'object_sha256':hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest(),'matched_original_names':sorted(row['mangled'] for row in fixture['ranges'] if row['n'] in fixture['covered_targets'])}))
print('ELF host exact original mangling checked',len(fixture['covered_targets']),'no decoration; no ARM ABI claim')
