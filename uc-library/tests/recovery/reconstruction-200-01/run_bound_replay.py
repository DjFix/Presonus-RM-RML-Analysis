"""Canonical executable replay with explicit immutable fixture/provenance binding."""
import argparse, hashlib, pathlib, subprocess
p=argparse.ArgumentParser()
p.add_argument('--executable', required=True)
p.add_argument('--fixtures', required=True)
p.add_argument('--fixture-sha256', required=True)
p.add_argument('--replay', required=True)
p.add_argument('--replay-sha256', required=True)
p.add_argument('--style', choices=['flag','positional'], required=True)
a=p.parse_args()
fixture=pathlib.Path(a.fixtures).resolve(); replay=pathlib.Path(a.replay).resolve()
assert fixture == replay.with_name('fixtures.json'), 'Legacy replay must use the explicit canonical fixture'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(fixture)==a.fixture_sha256 and sha(replay)==a.replay_sha256
root=pathlib.Path(__file__).resolve().parents[4]
python=root/'uc-library/.venv/bin/python'
argv=[str(python),str(replay)]
if a.style=='flag': argv += ['--executable',a.executable]
else: argv += [a.executable]
subprocess.run(argv,cwd=root,check=True)
assert sha(fixture)==a.fixture_sha256 and sha(replay)==a.replay_sha256
