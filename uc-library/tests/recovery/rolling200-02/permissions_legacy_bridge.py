"""Preserve legacy cases; bind restored filename behavior to fresh helper evidence.

Historical selected-name fixtures intercepted getFileName as a no-op. Their
callback trace is not a current end-to-end assertion after restoring that helper.
Other cases retain exact historical comparisons, including all 128 output bytes.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
exe, legacy_path, helper_path = sys.argv[1:]
legacy_path, helper_path = Path(legacy_path), Path(helper_path)
legacy = json.loads(legacy_path.read_text())
helper = json.loads(helper_path.read_text())
assert hashlib.sha256(legacy_path.read_bytes()).hexdigest() == helper['historical_input']['sha256']
helpers = {case['historical_case_id']: case for case in helper['cases']}
assert len(helpers) == 6
out = ROOT / 'temp/test-work/rolling200-closeout02' / ('legacy-permissions-' + str(time.time_ns()))
out.mkdir(parents=True, exist_ok=False)
reports = []
for case in legacy['cases']:
    args = case['input']
    argv = [exe, str(case['target']), str(int(args.get('selected', False))),
            args.get('name', 'client'), args.get('payload', ''),
            str(int(args.get('enabled', False))), str(args.get('restricted', 0)),
            str(args.get('dirty', 0))]
    refreshed = None
    if case['target'] == 0:
        refreshed = helpers[case['case_id']]
        assert refreshed['task'] == 'existing_helper'
        assert {k: v for k, v in refreshed['input'].items() if k != 'root'} == args
        root = Path(refreshed['input']['root'])
        assert root.resolve().is_relative_to(ROOT / 'temp/recovery-work')
        argv.append(str(root))
    result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, (argv, result.stderr)
    actual = json.loads(result.stdout)
    filename = actual.pop('filename', None)
    if case['target'] == 0:
        assert filename == refreshed['output']['filename']
        assert actual['dirty'] == refreshed['output']['dirty']
    if case['target'] == 0 and args['selected']:
        # A real helper replaces the old no-op callback. Never manufacture its
        # historical callback event or claim that the old no-op output replayed.
        assert actual['trace'] == []
        prefix = (filename.encode() + b'\0')[:128]
        assert bytes.fromhex(actual['output_hex']).startswith(prefix)
        domain = 'Fresh original helper range plus real CCL filename/dirty observation'
    else:
        assert actual == case['observed'], (case['case_id'], actual, case['observed'])
        domain = 'Exact unchanged historical native boundary replay'
    reports.append({'case_id': case['case_id'], 'target': case['target'],
                    'argv': argv, 'returncode': result.returncode,
                    'actual': actual, 'filename': filename, 'domain': domain})
(out / 'results.json').write_text(json.dumps(reports, indent=2) + '\n')
print('Permissions legacy coverage passed:', len(reports),
      'cases; three former no-op selected-name cases use fresh helper evidence')
