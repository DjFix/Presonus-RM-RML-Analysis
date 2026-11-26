"""Bounded observation of one exact systemd graph job; never starts/restarts work."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

PROPERTIES = ('Id', 'LoadState', 'ActiveState', 'SubState', 'MainPID',
              'ExecMainPID', 'ExecMainCode', 'ExecMainStatus', 'Result',
              'ExecMainStartTimestamp', 'ExecMainExitTimestamp', 'InvocationID')


def parse_show(text):
    return dict(line.split('=', 1) for line in text.splitlines() if '=' in line)


def classify(properties, returncode):
    """Missing, query failure and never-started are distinct from actual exit."""
    p = properties
    if p.get('LoadState') == 'not-found':
        return 'not_started', False
    if returncode or p.get('LoadState') != 'loaded':
        return 'unknown', False
    active, sub = p.get('ActiveState'), p.get('SubState')
    if active in ('activating', 'reloading', 'deactivating'):
        return active, False
    if active == 'active' and sub != 'exited':
        return 'running', False
    if active == 'failed':
        return 'failed', True
    exited = p.get('ExecMainExitTimestamp', '') not in ('', 'n/a', '0')
    if exited and (active == 'inactive' or (active == 'active' and sub == 'exited')):
        if p.get('ExecMainCode') == '1' and p.get('ExecMainStatus') == '0' and p.get('Result') == 'success':
            return 'finished', True
        return 'failed', True
    if active == 'inactive' and not p.get('InvocationID') and not p.get('ExecMainStartTimestamp'):
        return 'not_started', False
    return 'unknown', False


def bind_instance(properties, state, terminal, expected):
    invocation = properties.get('InvocationID', '')
    if expected and invocation != expected:
        return 'instance_mismatch', False, False
    if terminal and not expected:
        return 'unbound_' + state, False, False
    return state, terminal, bool(expected and invocation == expected)


def command(argv):
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=8)
        return {'argv': argv, 'returncode': r.returncode,
                'stdout': r.stdout[-32768:], 'stderr': r.stderr[-4096:]}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {'argv': argv, 'returncode': None, 'stdout': '', 'stderr': str(e)}


def tail(path, maximum=32768):
    try:
        with path.open('rb') as stream:
            stream.seek(0, os.SEEK_END)
            size = stream.tell()
            stream.seek(max(0, size - maximum))
            data = stream.read(maximum)
        return {'path': str(path), 'size': size, 'tail': data.decode(errors='replace')}
    except OSError as e:
        return {'path': str(path), 'error': str(e)}


def receipt(path):
    try:
        size = path.stat().st_size
        if size > 65536:
            return {'path': str(path), 'size': size, 'status': 'too_large_not_read'}
        data = json.loads(path.read_bytes())
        # Observations only; a progress receipt cannot declare systemd terminal.
        keys = ('status', 'phase', 'progress', 'completed', 'total', 'updated_utc',
                'timestamp_utc', 'log', 'log_path', 'result_path', 'error')
        return {'path': str(path), 'size': size,
                'summary': {k: data[k] for k in keys if k in data}}
    except (OSError, ValueError, TypeError) as e:
        return {'path': str(path), 'error': str(e)}


def observe(config):
    unit = config['job_unit']
    if not re.fullmatch(r'[A-Za-z0-9_.@:-]+\.service', unit):
        raise ValueError('One exact .service unit is required')
    result = command(['systemctl', '--user', 'show', unit, '--no-pager',
                      *['--property=' + p for p in PROPERTIES]])
    properties = parse_show(result['stdout'])
    state, terminal = classify(properties, result['returncode'])
    state, terminal, verified = bind_instance(properties, state, terminal, config.get('expected_invocation_id'))
    journal = command(['journalctl', '--user', '--unit=' + unit, '--lines=20',
                       '--no-pager', '--output=short-iso'])
    paths = config.get('progress_receipts', [])
    logs = config.get('log_paths', [])
    if len(paths) > 8 or len(logs) > 2:
        raise ValueError('At most8 exact receipt paths and2 exact log paths')
    memory = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        if key in ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'):
            memory[key] = value.strip()
    disk = shutil.disk_usage(config['disk_path'])
    return {'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'job_unit': unit, 'state': state, 'terminal': terminal,
            'expected_invocation_id': config.get('expected_invocation_id'),
            'job_instance_verified': verified, 'systemd': properties, 'show_query': result, 'journal_tail': journal,
            'log_tails': [tail(Path(p)) for p in logs],
            'progress_receipts': [receipt(Path(p)) for p in paths],
            'memory': memory, 'disk': dict(total=disk.total, used=disk.used, free=disk.free),
            'policy': 'Local observation only; no DB/graph access, messages, job start/restart or next cycle.'}


def atomic_json(path, data):
    tmp = path.with_name(path.name + '.new')
    with tmp.open('w') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)


def persist(output, data):
    output.mkdir(parents=True, exist_ok=True)
    with (output / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        name = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '.json'
        atomic_json(output / name, data)
        atomic_json(output / 'LATEST.json', data)
        with (output / 'HOURLY.jsonl').open('a') as stream:
            stream.write(json.dumps(data, separators=(',', ':')) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        if data['terminal'] and not (output / 'TERMINAL.json').exists():
            atomic_json(output / 'TERMINAL.json', data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    persist(args.out, observe(json.loads(args.config.read_text())))


if __name__ == '__main__':
    main()
