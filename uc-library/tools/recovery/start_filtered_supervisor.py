"""Resume the verified non-Core supervisor with a durable project-local stdout."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

repository = Path('/home/rs/projects/opencs/ai-line-analysis')
os.chdir(repository)
state_path = repository / 'temp/recovery-work/batch-supervisor-state.json'
previous = json.loads(state_path.read_text())
processes = subprocess.run(['ps', '-eo', 'pid,args'], check=True, text=True,
                           capture_output=True).stdout.splitlines()
conflicts = [line for line in processes if any(name in line for name in
             ('run_decompilation_batches.py', 'decompile_uc.py', 'extraction_verify_bounded.py'))]
if conflicts:
    raise SystemExit('A supervisor/worker is already live: ' + repr(conflicts))
if (repository / 'temp/recovery-work/STOP').exists():
    raise SystemExit('STOP exists; do not override a stop request')
for field, name in (
    ('supervisor_sha256', 'run_decompilation_batches.py'),
    ('worker_sha256', 'decompile_uc.py'),
):
    path = repository / 'uc-library/tools' / name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == previous[field], name
implementation_sha256 = hashlib.sha256((repository / 'uc-library/tools/extraction_verify_bounded.py').read_bytes()).hexdigest()
# Bound to the preserved, scope-tested core-deferred-extraction source snapshot.
assert implementation_sha256 == '25f4f36aed5c2bf4d6b2222e3b4945dd552c4fc9fdbffe888ff405fce98dfa90'
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repository / 'evidence/recovery/2026-10-26/bounded-relaunch' / stamp
evidence.mkdir(parents=True)
(evidence / 'previous-supervisor-state.json').write_text(json.dumps(previous, indent=2) + '\n')
command = [str(repository / 'uc-library/.venv/bin/python'), '-u',
           str(repository / 'uc-library/tools/run_decompilation_batches.py'),
           str(repository), '--first-role', 'client', '--defer-namespace', 'Core',
           '--batch-size', '250', '--max-rss-mb', '2048', '--min-available-mb', '1024']
environment = os.environ.copy()
temporary = repository / 'temp/recovery-work/tool-tmp'
temporary.mkdir(exist_ok=True)
environment['TMPDIR'] = str(temporary)
with (evidence / 'supervisor.log').open('ab') as log:
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                               stderr=subprocess.STDOUT, start_new_session=True,
                               cwd=repository, env=environment)
    os.kill(process.pid, 0)
    identity = Path(f'/proc/{process.pid}/stat').read_text().rsplit(')', 1)[1].split()
report = dict(pid=process.pid, start_ticks=int(identity[19]), command=command,
              worker_implementation_sha256=implementation_sha256,
              stdout=str(evidence / 'supervisor.log'), evidence=str(evidence),
              previous_state=previous['state'], previous_reason=previous.get('reason'),
              core_deferred=True, source_policy='prefer pinned upstream; no Core binary recovery')
(evidence / 'launch.json').write_text(json.dumps(report, indent=2) + '\n')
(repository / 'temp/recovery-work/detached-launch.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
