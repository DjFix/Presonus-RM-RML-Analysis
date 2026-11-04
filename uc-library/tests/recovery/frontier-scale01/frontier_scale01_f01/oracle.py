"""Re-execute saved original ARM producer in assigned scratch; no C++ oracle."""
import json, hashlib, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
S=ROOT/'temp/recovery-work/frontier-scale01/frontier_scale01_f01'
PRODUCER=ROOT/'evidence/recovery/2026-11-03/dependency-graph/frontier-scale01/root-equivalence-review01/frontier_scale01_r02/compare.py'
def run():
 S.mkdir(parents=True,exist_ok=True)
 code=PRODUCER.read_bytes()
 assert hashlib.sha256(code).hexdigest()=='dc89f6330bbd68ce1a225edd8a95b9b5ece76030587d1ab51ed95d733168adef'
 (S/'native_producer.py').write_bytes(code)
 subprocess.run([str(ROOT/'uc-library/.venv/bin/python'),str(S/'native_producer.py')],cwd=ROOT,check=True)
 data=json.loads((S/'NATIVE_OBSERVATIONS.json').read_text())
 rows=json.loads((S/'COMPARISON.json').read_text())['originals']
 cases=[]
 for x in data['cases']:
  writes={w['address']-0x500000:w['value'] for w in x['writes'] if 0x500000<=w['address']<0x500100}
  cases.append(dict(elf=x['elf'],mangled=x['mangled'],address=x['address'],argument_bits=x['argument_bits'],initial_fill=x['initial_fill'],expected=[writes[140],writes[8],writes[144],writes[148]],opaque_dispatch=writes[0],self_relative_storage=writes[4]-0x500000))
 return dict(originals=rows,cases=cases,scope='native six stores, untouched object bytes and no calls; portable comparison projects argument and three zero scalars only; opaque dispatch and self+12 are not C++ layout')
if __name__=='__main__':
 data=run()
 if '--write' in sys.argv: Path(__file__).with_name('fixtures.json').write_text(json.dumps(data,indent=2)+'\n')
 else: assert data==json.loads(Path(__file__).with_name('fixtures.json').read_text())
