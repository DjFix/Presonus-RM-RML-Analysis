import subprocess,sys
from pathlib import Path
import json
symbols=subprocess.check_output(['nm',sys.argv[1]],text=True)
for p in sorted(Path('temp/recovery-work/reconstruction-200-01/large-batch01/packets').glob('large01_w10_*')):
 d=json.loads((p/'request.json').read_text());assert any(line.endswith(' T '+d['targets'][0]['mangled']) for line in symbols.splitlines())
print('All nine original mangled identities present')
