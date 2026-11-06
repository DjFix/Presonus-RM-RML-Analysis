#!/usr/bin/env python3
"""Reject local recovery artifacts in the Git index, including force-added files."""
import argparse
import json
from pathlib import PurePosixPath
import subprocess
import sys


def git(repo, *args):
    return subprocess.check_output(['git', '-C', repo, *args])


def forbidden(path, policy):
    if path in policy['legacy_test_inputs']:
        return None
    if path.startswith(('temp/', 'evidence/', 'uc-library/validation/')):
        return 'local evidence, validation output or scratch'
    if path == 'uc-library/tracking/coverage.json':
        return 'generated machine coverage snapshot'
    name = PurePosixPath(path).name.lower()
    if path.startswith('uc-library/candidates/') and name.endswith(('.json', '.log', '.stdout', '.stderr', '.jsonl')):
        return 'worker metadata/log; put new replay fixtures under uc-library/tests/'
    if name.startswith(('final_source_drift', 'source_drift_precheck', 'handoff_inputs', 'staged_review', 'commit_input_plan')):
        return 'generated coordinator report'
    return None


def check(repo, tracked=False):
    # Read the staged policy, so an unstaged exception cannot bless a commit.
    policy = json.loads(git(repo, 'show', ':tools/git-artifact-policy.json'))
    entries = {}
    for row in git(repo, 'ls-files', '--stage', '-z').split(b'\0'):
        if not row:
            continue
        meta, path = row.split(b'\t', 1)
        mode, oid, stage = meta.decode().split()
        if stage != '0':
            raise ValueError('Unmerged index entry: ' + path.decode())
        entries[path.decode()] = (mode, oid)
    changed = {p.decode() for p in git(repo, 'diff', '--cached', '--name-only', '--diff-filter=ACMRT', '-z').split(b'\0') if p}
    errors = []
    for path in sorted(entries if tracked else changed):
        reason = forbidden(path, policy)
        if reason:
            errors.append(f'{path}: {reason}')
        mode, oid = entries[path]
        # Existing firmware/images outside this cleanup are not reclassified.
        if path in changed and mode != '160000':
            size = int(git(repo, 'cat-file', '-s', oid))
            if size > policy['max_added_blob_bytes']:
                errors.append(f'{path}: {size} bytes exceeds the staged-blob limit')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='.')
    parser.add_argument('--tracked', action='store_true', help='Also audit all tracked paths for local-only artifacts')
    args = parser.parse_args()
    try:
        errors = check(args.repo, args.tracked)
    except (subprocess.CalledProcessError, ValueError, KeyError) as exc:
        print(f'Git artifact policy could not be checked: {exc}', file=sys.stderr)
        return 1
    if errors:
        print('Do not commit generated recovery artifacts:\n' + '\n'.join(errors), file=sys.stderr)
        return 1
    print('Git artifact policy: passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
