"""Measure a completed trial batch's observed audit-to-sync interval."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--phase', required=True)
parser.add_argument('--sync-report', type=Path, required=True)
args = parser.parse_args()
root = Path('/home/rs/projects/opencs/ai-line-analysis')
report_path = args.sync_report.resolve()
assert re.fullmatch(r'[a-z0-9][a-z0-9-]*-root', args.phase)
assert report_path.is_relative_to(root / 'evidence/recovery')
report = json.loads(report_path.read_text())
assert report['passed'] and not report['dry_run'] and report['direction'] == 'push'
assert report['phase'] == args.phase.removesuffix('-root') + '-completion'
day = datetime.fromisoformat(report['finished_at'].replace('Z', '+00:00')).date().isoformat()
evidence = f'evidence/recovery/{day}/{args.phase}'
program = '''
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
request = json.load(sys.stdin)
folder = Path(request['evidence'])
assert folder.resolve().is_relative_to(Path.cwd()/'evidence/recovery')
audit = folder/'role-audit.log'
finished = datetime.fromisoformat(request['finished_at'].replace('Z', '+00:00'))
audit_end = datetime.fromtimestamp(audit.stat().st_mtime, timezone.utc)
seconds = (finished-audit_end).total_seconds()
assert seconds >= 0
result = dict(role_audit_log_finished_at=audit_end.isoformat(),
              role_audit_log_sha256=hashlib.sha256(audit.read_bytes()).hexdigest(),
              completion_sync_finished_at=finished.isoformat(), post_role_audit_seconds=seconds,
              proposed_target_seconds=300, within_target=seconds<=300,
              completion_sync_report=request['report'], sync_report_sha256=request['report_sha256'],
              scope='Observed event gap, not CPU accounting or an established throughput improvement')
text = json.dumps(result, indent=2)+'\\n'
(folder/'completion-timing.json').write_text(text)
print(text, end='')
'''
command = 'cd /home/rs/projects/opencs/ai-line-analysis && uc-library/.venv/bin/python -c ' + shlex.quote(program)
result = subprocess.run(['ssh', 'rs@192.168.50.238', command], text=True,
    input=json.dumps(dict(finished_at=report['finished_at'], evidence=evidence,
                          report=str(report_path.relative_to(root)),
                          report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest())),
    capture_output=True, check=True)
data = json.loads(result.stdout)
(root/evidence/'completion-timing.json').write_text(result.stdout)
print(json.dumps({key: data[key] for key in ('post_role_audit_seconds', 'proposed_target_seconds', 'within_target')}))
