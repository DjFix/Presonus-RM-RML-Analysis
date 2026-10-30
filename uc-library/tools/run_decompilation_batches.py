#!/usr/bin/env python3
"""Run firmware pseudocode exports sequentially with preserved batch evidence."""

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def utc():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    temporary = path.with_name(path.name + f'.{os.getpid()}.new')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def emit(value):
    print(json.dumps(value), flush=True)


def worker_processes(repository):
    found = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name) == os.getpid():
            continue
        try:
            args = [x.decode() for x in (p/'cmdline').read_bytes().split(b'\0') if x]
            if not any(Path(x).name in ('decompile_uc.py', 'extraction_verify_bounded.py',
                                        'run_decompilation_batches.py') for x in args):
                continue
            if (p/'cwd').resolve() == repository:
                found.append({'pid': int(p.name), 'command': args})
        except (OSError, UnicodeError):
            continue
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    parser.add_argument('--first-role', choices=('client', 'server'), default='client')
    parser.add_argument('--stop-file', type=Path, default=Path('temp/recovery-work/STOP'))
    parser.add_argument('--batch-size', type=int, default=250)
    parser.add_argument('--max-rss-mb', type=int, default=2048)
    parser.add_argument('--min-available-mb', type=int, default=1024)
    parser.add_argument('--max-batches', type=int, default=0,
                        help='0 continues until complete, stop marker, or an actionable failure.')
    parser.add_argument('--plan-only', action='store_true')
    parser.add_argument('--defer-namespace', action='append', default=[],
                        help='Pass an exact original owning namespace exclusion to every worker.')
    args = parser.parse_args()
    if min(args.batch_size, args.max_rss_mb, args.min_available_mb) <= 0 or args.max_batches < 0:
        parser.error('batch size and memory limits must be positive; max batches nonnegative')
    repository = args.repository.resolve()
    stop_file = (repository/args.stop_file).resolve()
    if not stop_file.is_relative_to(repository):
        parser.error('stop file must be inside the repository')
    tool_dir = Path(__file__).resolve().parent
    worker = tool_dir/'decompile_uc.py'
    library = tool_dir.parent
    if not library.is_relative_to(repository):
        parser.error('supervisor must be installed inside the repository')
    recovery = library/'recovered-all'
    os.chdir(repository)
    control = repository/'temp/recovery-work'
    control.mkdir(parents=True, exist_ok=True)
    lock = (control/'batch-supervisor.lock').open('a+')
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error('another supervisor owns the project batch lock')
    live = worker_processes(repository)
    if live:
        parser.error(f'existing worker/supervisor in this project: {live}')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+f'-{os.getpid()}'
    evidence = repository/'evidence/recovery/2026-10-26/bounded-batches'/stamp
    evidence.mkdir(parents=True)
    state = {'schema': 1, 'session': stamp, 'pid': os.getpid(), 'started_utc': utc(),
             'state': 'starting', 'evidence': str(evidence), 'batches': [], 'roles': {},
             'stop_file': str(stop_file), 'pseudocode_validated': False,
             'supervisor_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'worker_sha256': hashlib.sha256(worker.read_bytes()).hexdigest(),
             'deferred_namespaces': args.defer_namespace,
             'limits': {'batch_size': args.batch_size, 'max_rss_mb': args.max_rss_mb,
                        'min_available_mb': args.min_available_mb}}
    current = control/'batch-supervisor-state.json'

    def seal(status, reason=None):
        state.update(state=status, reason=reason, updated_utc=utc())
        atomic_json(evidence/'state.json', state)
        atomic_json(current, state)

    def signal_stop(signum, frame):
        # Persist the shared cooperative marker so the child seals its current function.
        stop_file.parent.mkdir(parents=True, exist_ok=True)
        stop_file.touch(exist_ok=True)
        state['stop_signal'] = signum

    signal.signal(signal.SIGTERM, signal_stop)
    signal.signal(signal.SIGINT, signal_stop)

    def command(role):
        cmd = [sys.executable, '-u', str(worker), str(repository), role,
                '--recovery', str(recovery.relative_to(repository)),
                '--reuse-from', str((library/'recovered').relative_to(repository)),
                '--reuse-from', str((library/'recovered-dice').relative_to(repository)),
                '--priority', 'application', '--batch-size', str(args.batch_size),
                '--max-rss-mb', str(args.max_rss_mb),
                '--min-available-mb', str(args.min_available_mb),
                '--quarantine-untrusted', '--stop-file', str(stop_file)]
        for namespace in args.defer_namespace:
            cmd.extend(['--defer-namespace', namespace])
        return cmd

    def plan(role):
        cmd = command(role)+['--plan-only']
        result = subprocess.run(cmd, cwd=repository, capture_output=True, text=True)
        n = len(list(evidence.glob(f'plan-*-{role}.json')))
        (evidence/f'plan-{n:03d}-{role}.stdout.log').write_text(result.stdout)
        (evidence/f'plan-{n:03d}-{role}.stderr.log').write_text(result.stderr)
        if result.returncode:
            raise RuntimeError(f'{role} plan exited {result.returncode}')
        value = next(json.loads(line) for line in result.stdout.splitlines()
                     if line.startswith('{') and 'pending_attempts' in json.loads(line))
        atomic_json(evidence/f'plan-{n:03d}-{role}.json', dict(command=cmd, **value))
        if value['previous_failures']:
            raise RuntimeError(f'{role} has {value["previous_failures"]} recorded failures')
        state['roles'][role] = value
        return value

    seal('planning')
    try:
        for role in ('client', 'server'):
            plan(role)
        emit({'event': 'supervisor-plan', 'evidence': str(evidence), 'roles': state['roles']})
        if args.plan_only:
            seal('planned')
            return 0
        next_role = args.first_role
        while True:
            if stop_file.exists():
                seal('stopped', 'stop-file')
                break
            if all(v['pending_attempts'] == 0 for v in state['roles'].values()):
                deferred_remaining = any(v.get('deferred_pending_unique', 0) for v in state['roles'].values())
                seal('scope-complete' if deferred_remaining else 'complete',
                     'user-deferred-functions-remain' if deferred_remaining else None)
                break
            if args.max_batches and len(state['batches']) >= args.max_batches:
                seal('partial', 'supervisor-batch-limit')
                break
            role = next_role
            next_role = 'server' if role == 'client' else 'client'
            before = plan(role)
            if before['pending_attempts'] == 0:
                continue
            live = worker_processes(repository)
            if live:
                raise RuntimeError(f'worker appeared before batch launch: {live}')
            i = len(state['batches'])+1
            prefix = f'batch-{i:03d}-{role}'
            batch = {'index': i, 'role': role, 'started_utc': utc(),
                     'before': before, 'command': command(role),
                     'stdout': prefix+'.stdout.log', 'stderr': prefix+'.stderr.log'}
            state['active_batch'] = batch
            seal('running')
            emit({'event': 'batch-start', 'index': i, 'role': role,
                  'pending': before['pending_attempts'], 'evidence': str(evidence)})
            with (evidence/batch['stdout']).open('w') as stdout, (evidence/batch['stderr']).open('w') as stderr:
                process = subprocess.Popen(batch['command'], cwd=repository, stdout=stdout, stderr=stderr)
                batch['pid'] = process.pid
                atomic_json(evidence/(prefix+'.json'), batch)
                seal('running')
                exit_code = process.wait()
            batch.update(exit_code=exit_code, finished_utc=utc())
            output_state = recovery/role/'run-state.json'
            summary = json.loads(output_state.read_text()) if output_state.exists() else {}
            batch['summary'] = summary
            state['batches'].append(batch)
            state.pop('active_batch', None)
            atomic_json(evidence/(prefix+'.json'), batch)
            seal('checking')
            emit({'event': 'batch-finish', 'index': i, 'role': role, 'exit_code': exit_code,
                  'summary': summary})
            if exit_code:
                raise RuntimeError(f'{role} worker exited abnormally: {exit_code}')
            if summary.get('pid') != process.pid or summary.get('source_sha256') != before['source_sha256']:
                raise RuntimeError('stale/mismatched worker run state')
            if summary.get('failed'):
                raise RuntimeError(f'{role} recorded {summary["failed"]} failures')
            if summary.get('state') == 'stopped':
                seal('stopped', summary.get('reason'))
                break
            if summary.get('reason') in ('soft-rss-limit', 'low-available-memory'):
                raise RuntimeError('resource-block: '+summary['reason'])
            if summary.get('state') not in ('partial', 'complete', 'scope-complete'):
                raise RuntimeError('worker returned without final terminal state')
            if summary.get('reason') not in (None, 'batch-limit', 'no-selected-pending-functions'):
                raise RuntimeError('unexpected checkpoint reason: '+str(summary.get('reason')))
            old_exports = before['trusted_existing']+before['reusable_prior']
            if summary.get('exports', 0) <= old_exports:
                raise RuntimeError(f'{role} made no export progress')
            after = plan(role)
            if after['pending_attempts'] >= before['pending_attempts']:
                raise RuntimeError(f'{role} pending count did not decrease')
            seal('between-batches')
    except Exception as error:
        seal('aborted', f'{type(error).__name__}: {error}')
        emit({'event': 'supervisor-aborted', 'reason': state['reason'], 'evidence': str(evidence)})
        return 2
    emit({'event': 'supervisor-finish', 'state': state['state'], 'reason': state.get('reason'),
          'evidence': str(evidence), 'roles': state['roles'], 'batches': len(state['batches'])})
    return 0


if __name__ == '__main__':
    sys.exit(main())
