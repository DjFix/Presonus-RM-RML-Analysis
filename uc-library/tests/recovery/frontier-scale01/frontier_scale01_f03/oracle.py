"""Replay the saved instruction producer, changing only project/output locations."""
import json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
S=ROOT/'temp/recovery-work/frontier-scale01/frontier_scale01_f03'
PRODUCER=ROOT/'evidence/recovery/2026-11-03/dependency-graph/frontier-scale01/root-equivalence-review01/frontier_scale01_r05/compare.py'
assert hashlib.sha256(PRODUCER.read_bytes()).hexdigest()=='3bd39676f1bff5efb34a2014207d419a7e6beb7465cf2bc2d501ade0c0bf87cc'
code=PRODUCER.read_text().replace('ROOT=Path(__file__).resolve().parents[4]',f'ROOT=Path({str(ROOT)!r})').replace('OUT=Path(__file__).parent',f'OUT=Path({str(S)!r})')
exec(compile(code,str(PRODUCER),'exec'),{'__file__':str(PRODUCER)})
obs=json.loads((S/'NATIVE_OBSERVATIONS.json').read_text())
fixture=Path(__file__).with_name('fixtures.json')
if fixture.exists():
 assert json.loads(fixture.read_text())==obs
else: fixture.write_text(json.dumps(obs,indent=2)+'\n')
