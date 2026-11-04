"""Replay sealed native projections; each actual host process has a strict deadline."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--binary', required=True)
parser.add_argument('--fixtures', required=True)
parser.add_argument('--work', required=True)
parser.add_argument('--repeat', type=int, default=1)
parser.add_argument('--methods', help='Optional comma-separated method IDs for focused stress')
args = parser.parse_args()
assert args.repeat > 0
methods = {int(value) for value in args.methods.split(',')} if args.methods else None
base = Path(args.work)
base.mkdir(parents=True, exist_ok=True)
work = Path(tempfile.mkdtemp(prefix='replay-', dir=base))
fixtures = json.loads(Path(args.fixtures).read_text())
count = 0
for repetition in range(args.repeat):
    for row in fixtures['cases']:
        case = row['case']
        if methods is not None and case['method'] not in methods:
            continue
        case_id = f'{repetition:04}-{case["id"]}'
        directory = work / case_id
        argv = [str(Path(args.binary).resolve()), str(case['method']),
                str(case['variant']), str(directory.resolve())]
        record = {'argv': argv, 'repetition': repetition, 'case': case}
        try:
            result = subprocess.run(argv, text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=10)
        except subprocess.TimeoutExpired as error:
            # subprocess.run kills and reaps this confirmed child, including its
            # worker threads. Preserve failure; never leave an orphan replay.
            record.update(timed_out=True, deadline_seconds=10,
                          stdout=str(error.stdout), stderr=str(error.stderr))
            (work / (case_id + '.json')).write_text(json.dumps(record, indent=2) + '\n')
            raise
        record.update(returncode=result.returncode, stdout=result.stdout,
                      stderr=result.stderr)
        (work / (case_id + '.json')).write_text(json.dumps(record, indent=2) + '\n')
        assert result.returncode == 0, (case, result.stdout, result.stderr)
        observed = json.loads(result.stdout.strip().splitlines()[-1])
        expected = {key: str(value) for key, value in row['projection'].items()}
        assert observed == expected, (case, expected, observed)
        count += 1
assert count > 0
print(f'{count} sealed original-app projections passed against optimized real-provider '
      f'host executions; {args.repeat} repetition(s). Real async fence/idle/terminate '
      'and archive persistence assertions execute in methods17/19. '
      'Native external boundaries remain explicit fixture stubs.')
