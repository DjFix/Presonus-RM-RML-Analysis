"""Check and replay a worker handoff; never write readiness or build configuration."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(value):
    path = Path(value)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Expected repository-relative path: ' + value)
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError('Path escapes repository: ' + value)
    return resolved


def validate(data):
    if data['version'] != 1:
        raise ValueError('Unsupported handoff version')
    for name in ('task_id', 'packet_manifest', 'namespace', 'validation_domain',
                 'limitations', 'build_integration'):
        if not data.get(name):
            raise ValueError('Missing handoff field: ' + name)
    artifacts = data['artifacts']
    for kind in ('source', 'test', 'fixture', 'replay', 'proof'):
        if not any(a['kind'] == kind for a in artifacts):
            raise ValueError('Missing artifact kind: ' + kind)
    paths = [a['path'] for a in artifacts]
    if len(paths) != len(set(paths)):
        raise ValueError('Duplicate artifact path')
    for artifact in artifacts:
        if digest(inside(artifact['path'])) != artifact['sha256']:
            raise ValueError('Stale artifact: ' + artifact['path'])
    if data['packet_manifest'] not in paths:
        raise ValueError('Packet manifest must be hash-bound as an artifact')
    identities = data['originals']
    if not identities:
        raise ValueError('Empty original identity set')
    for identity in identities:
        for key in ('elf_sha256', 'firmware', 'role', 'mangled', 'address', 'size', 'section'):
            if key not in identity or identity[key] is None:
                raise ValueError('Missing original field: ' + key)
        if len(identity['elf_sha256']) != 64 or not identity['mangled']:
            raise ValueError('Invalid original identity')
    checks = data['checks']
    for kind in ('format', 'compile', 'symbols', 'replay'):
        if not any(c['kind'] == kind for c in checks):
            raise ValueError('Missing check: ' + kind)
    for check in checks:
        argv = check['argv']
        if not argv or not all(isinstance(a, str) for a in argv):
            raise ValueError('Expected argv array')
        if not isinstance(check['timeout_seconds'], int) or check['timeout_seconds'] <= 0:
            raise ValueError('Expected positive command timeout')
    return data


def accept(manifest, output):
    data = validate(json.loads(manifest.read_text()))
    output.mkdir(parents=True, exist_ok=False)
    receipt = {'version': 1, 'task_id': data['task_id'],
               'handoff_sha256': digest(manifest), 'checks': [],
               'local_acceptance_passed': False, 'readiness_admitted': False}
    started = time.monotonic()
    try:
        for index, check in enumerate(data['checks']):
            before = time.monotonic()
            item = {'kind': check['kind'], 'argv': check['argv'],
                    'start_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
            receipt['checks'].append(item)
            with (output / f'{index:02d}-{check["kind"]}.log').open('w') as log:
                try:
                    result = subprocess.run(check['argv'], cwd=ROOT, stdout=log,
                                            stderr=subprocess.STDOUT,
                                            timeout=check['timeout_seconds'], check=False)
                    item['returncode'] = result.returncode
                except subprocess.TimeoutExpired:
                    item['timed_out'] = True
                    raise ValueError('Check timed out: ' + check['kind'])
                finally:
                    item['seconds'] = time.monotonic() - before
            if result.returncode:
                raise ValueError('Check failed: ' + check['kind'])
        validate(data)
        if digest(manifest) != receipt['handoff_sha256']:
            raise ValueError('Handoff changed during acceptance')
        receipt['local_acceptance_passed'] = True
    except Exception as error:
        receipt['error'] = str(error)
        raise
    finally:
        receipt['seconds'] = time.monotonic() - started
        (output / 'acceptance.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--handoff', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    print(json.dumps(accept(inside(args.handoff), inside(args.out))))
