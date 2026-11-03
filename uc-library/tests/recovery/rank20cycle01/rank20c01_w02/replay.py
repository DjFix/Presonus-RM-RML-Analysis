"""Compare source-port lifecycle against separately observed pinned provider."""
import json
from pathlib import Path
import subprocess
import sys
executable, fixture = sys.argv[1:]
f=json.loads(Path(fixture).read_text())
p=subprocess.run([executable,'port'],capture_output=True,text=True,check=True)
assert p.stdout==f['provider_stdout'],(p.stdout,f['provider_stdout'])
provider=subprocess.run([executable,'provider'],capture_output=True,text=True,check=True)
assert provider.stdout==f['provider_stdout']
print('4 CCL provider/portable lifecycle cases passed: 0, 1, 2, 7 owned children. Native validation is limited to the separate original call-boundary prefix; no ARM ABI/full lifecycle claim.')

inputs=''.join(' '.join(map(str,c['rect']))+'\n' for c in f['meter']['cases'])
expected=''.join(str(c['return_word'])+'\n' for c in f['meter']['cases'])
meter=subprocess.run([executable,'meter'],input=inputs,capture_output=True,text=True,check=True)
assert meter.stdout==expected,(meter.stdout,expected)
print(f"{len(f['meter']['cases'])} full original ARM application meter executions matched portable CCL state; getSize is an explicit immutable rectangle boundary adapter; no overflow or original return declaration claim.")
