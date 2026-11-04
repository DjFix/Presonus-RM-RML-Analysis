"""Replay original instructions into a fresh directory; sealed inputs are immutable."""
from pathlib import Path
import json
import runpy
import tempfile

ROOT = Path(__file__).resolve().parents[5]
SCRATCH = ROOT / 'temp/recovery-work/frontier-scale01/frontier_scale01_f02'
PRODUCER = ROOT / 'evidence/recovery/2026-11-03/dependency-graph/frontier-scale01/root-equivalence-review01/frontier_scale01_r03/compare.py'
FIXTURE = Path(__file__).with_name('fixtures.json')

if __name__ == '__main__':
    out = Path(tempfile.mkdtemp(prefix='native-replay-', dir=SCRATCH))
    g = runpy.run_path(str(PRODUCER))
    g['main'].__globals__.update(
        BASE=ROOT, OUT=out,
        PACKET=ROOT / 'temp/recovery-work/frontier-scale01/research-batch02/packets/frontier_scale01_r03')
    g['main']()
    observed = json.loads((out / 'NATIVE_OBSERVATIONS.json').read_text())
    expected = json.loads(FIXTURE.read_text())
    assert observed == expected, 'fresh native observations differ from sealed fixture'
    print(json.dumps({'fixture_verified': True, 'native_cases': 60,
                      'fresh_output': str(out.relative_to(ROOT))}))
