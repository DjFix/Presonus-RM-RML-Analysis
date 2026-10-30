"""Linux-first reproducible configure/build/test/install for UC recovery."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

p = argparse.ArgumentParser()
p.add_argument('--platform', choices=('mac', 'linux'), default='linux')
p.add_argument('--allow-mac-validation', action='store_true')
p.add_argument('--attempt', default='initial')
p.add_argument('--phase', default='file-misc-integration')
p.add_argument('--additional-list', default='validation/integration-file-misc-additions.json')
p.add_argument('--expected-suites', type=int, default=22)
p.add_argument('--install-tag', default='file-misc')
p.add_argument('--build-dir', type=Path)
p.add_argument('--configure-arg', action='append', default=[])
p.add_argument('--jobs', type=int, default=2)
a = p.parse_args()
if a.platform == 'mac' and not a.allow_mac_validation:
    p.error('macOS validation is optional and disabled; use Linux unless explicitly requested')
repo = Path('/home/rs/projects/opencs/ai-line-analysis')
lib = repo / ('uc-library' if a.platform == 'mac' else 'uc-library')
evidence = repo / 'evidence/recovery/2026-10-27' / a.phase / a.platform
if a.attempt != 'initial':
    evidence = evidence / a.attempt
evidence.mkdir(parents=True, exist_ok=True)
scratch = repo / 'temp/recovery-work/file-misc-tmp' / a.platform
scratch.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, TMPDIR=str(scratch), TMP=str(scratch), TEMP=str(scratch))
cmake = '/opt/homebrew/bin/cmake' if a.platform == 'mac' else str(lib / '.venv/bin/cmake')
ctest = '/opt/homebrew/bin/ctest' if a.platform == 'mac' else str(lib / '.venv/bin/ctest')
build = repo / ('temp/recovery-work/build-mac' if a.platform == 'mac' else 'temp/recovery-work/build-linux')
if a.build_dir:
    build = (repo / a.build_dir).resolve()
    if not build.is_relative_to(repo / 'temp'):
        p.error('--build-dir must be within project temp/')
prefix = repo / 'temp/recovery-work' / ('install-' + a.install_tag + '-' + a.platform)
baseline = evidence / 'input-baseline.json'
commands = [
    ('inputs', [sys.executable, str(lib / 'tools/capture_integration_inputs.py'), '--library', str(lib), '--additional-list', str(lib / a.additional_list), '--expected-suites', str(a.expected_suites), '--output', str(baseline)]),
    ('configure', [cmake, '-S', str(lib), '-B', str(build), '-DBUILD_TESTING=ON', '-DCMAKE_BUILD_TYPE=Release', '-DPython3_EXECUTABLE=' + sys.executable] + a.configure_arg),
    ('build', [cmake, '--build', str(build), '-j', str(a.jobs)]),
    ('tests', [ctest, '--test-dir', str(build), '--output-on-failure']),
    ('seal', [sys.executable, str(lib / 'tools/seal_integration.py'), '--library', str(lib), '--repository', str(repo), '--evidence', str(evidence), '--platform', a.platform, '--baseline', str(baseline), '--output', str(lib / 'validation/integration.json')]),
    ('install', [cmake, '--install', str(build), '--prefix', str(prefix)]),
]
results = []
events = evidence / 'events.jsonl'
def record_event(event):
    with events.open('a') as stream:
        stream.write(json.dumps(event) + '\n')

for name, command in commands:
    log = evidence / (name + '.log')
    started_at = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    record_event(dict(event='step_started', step=name, started_at=started_at,
                      command=command, log=str(log.relative_to(repo))))
    with log.open('w') as stream:
        try:
            result = subprocess.run(command, cwd=repo, env=env, stdout=stream, stderr=subprocess.STDOUT)
        except OSError as error:
            stream.write(str(error) + '\n')
            result = subprocess.CompletedProcess(command, 127)
    results.append(dict(step=name, command=command, returncode=result.returncode,
                        log=str(log.relative_to(repo)), started_at=started_at,
                        finished_at=datetime.now(timezone.utc).isoformat(),
                        elapsed_seconds=round(time.monotonic() - start, 6)))
    record_event(dict(event='step_finished', **results[-1]))
    (evidence / 'commands.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps({key: results[-1][key] for key in
                      ('step', 'returncode', 'elapsed_seconds', 'log')}), flush=True)
    if result.returncode:
        print(log.read_text()[-4000:], flush=True)
        raise SystemExit(result.returncode)
    if name == 'seal' and a.platform == 'linux':
        (lib / 'validation/integration-linux.json').write_bytes((lib / 'validation/integration.json').read_bytes())
print('All integration steps passed', flush=True)
