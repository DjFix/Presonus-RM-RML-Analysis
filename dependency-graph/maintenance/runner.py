"""Single reviewed maintenance launch. No retry, readiness counting or next cycle."""
import argparse
import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

UNIT = 'opencs-graph-resume01.service'
POLICY = 'dependency-graph/PRODUCTION_GRAPH_STOP.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked(root, reference):
    path = (root / reference['path']).resolve()
    if Path(reference['path']).is_absolute() or not path.is_relative_to(root):
        raise ValueError('reference must stay inside project')
    data = path.read_bytes()
    if digest(data) != reference['sha256']:
        raise ValueError('reference hash mismatch: ' + reference['path'])
    return path, data


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def atomic(path, data):
    temporary = path.with_name(path.name + '.new')
    with temporary.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def run(config_path, invoke=subprocess.run):
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_bytes())
    root = Path(config['root']).resolve()
    job = config_path.parent
    if not job.is_relative_to(root) or config['unit'] != UNIT:
        raise ValueError('wrong job root/unit')
    started = dict(pid=os.getpid(), invocation_id=os.environ.get('INVOCATION_ID'),
                   unit=UNIT, config_sha256=digest(config_path.read_bytes()))
    # An attempted run consumes this one-shot launch, even on preflight failure.
    with (job / 'STARTED.json').open('x') as stream:
        json.dump(started, stream, indent=2)
    status = dict(started, phase='started', terminal=False, returncode=None,
                  policy_restored=False, refresh_argv=None)

    def record(phase, **values):
        status.update(phase=phase, observed_utc=datetime.datetime.now(
            datetime.timezone.utc).isoformat(), **values)
        atomic(job / 'STATUS.json', (json.dumps(status, indent=2) + '\n').encode())
        with (job / 'RUN.log').open('a') as log:
            log.write(status['observed_utc'] + ' ' + phase + ' ' +
                      json.dumps(values, sort_keys=True) + '\n')

    policy = root / POLICY
    prior = activation = None
    activated = False
    result = 1
    lock = None
    try:
        record('preflight')
        _, receipt_bytes = checked(root, config['boundary_receipt'])
        receipt = json.loads(receipt_bytes)
        if (receipt.get('accepted') is not True or receipt.get('committed') is not True
                or receipt.get('package_scope') != config['package_scope']):
            raise ValueError('actual accepted/committed scoped boundary required')
        head = invoke(['git', 'rev-parse', 'HEAD'], cwd=root,
                      capture_output=True, text=True, check=True).stdout.strip()
        if head != receipt['commit']:
            raise ValueError('actual HEAD differs from committed boundary')
        guard_path, _ = checked(root, config['guard'])
        if guard_path != root / 'dependency-graph/production_write_stop.py':
            raise ValueError('guard path differs')
        refresh_path, _ = checked(root, config['refresh'])
        if refresh_path != root / 'dependency-graph/refresh_graph.py':
            raise ValueError('refresh path differs')
        budget_path, _ = checked(root, config['budget'])
        if budget_path != root / 'dependency-graph/publication_budget.py':
            raise ValueError('budget path differs')
        budget = load_module(budget_path, 'graph_resume01_budget').BudgetLimits()
        limits = dict(journal_bytes=budget.journal_bytes,
                      sqlite_write_bytes=budget.sqlite_write_bytes,
                      transfer_bytes=budget.transfer_bytes, rows=budget.rows)
        if limits != dict(journal_bytes=3 * 1024**3,
                          sqlite_write_bytes=12 * 1024**3,
                          transfer_bytes=3 * 1024**3, rows=30000000):
            raise ValueError('routine budget defaults differ from reviewed profile')
        _, activation = checked(root, config['activation_policy'])
        permission = json.loads(activation)
        if (permission.get('version') != 2
                or permission.get('production_graph_updates') != 'maintenance_update'
                or permission.get('boundary', {}).get('receipt') != config['boundary_receipt']
                or permission.get('boundary', {}).get('commit') != head
                or permission.get('boundary', {}).get('package_scope') != config['package_scope']):
            raise ValueError('explicit reviewed activation policy differs')
        reason = config['compiler_rescan_reason']
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError('concrete authorized compiler rescan reason required')
        guard = load_module(guard_path, 'graph_resume01_guard')
        # Retain lock through the one launch and terminal restoration. Other
        # policy writers must honor the same lock; foreign changed bytes win.
        lock = (policy.parent / '.maintenance-policy.lock').open('a')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        prior = policy.read_bytes()
        if (digest(prior) != config['prior_stopped_policy_sha256']
                or json.loads(prior).get('production_graph_updates') != 'stopped'):
            raise ValueError('exact prior stopped policy differs')
        with (job / 'PRIOR-STOPPED-POLICY.json').open('xb') as stream:
            stream.write(prior)
        record('boundary_verified', head=head, package_scope=config['package_scope'],
               limits=limits, prior_policy_sha256=digest(prior),
               activation_policy_sha256=digest(activation))
        if policy.read_bytes() != prior:
            raise ValueError('foreign policy change before activation')
        atomic(policy, activation)
        activated = True
        guard.require_graph_updates(root)
        guard.require_graph_storage_write(root / 'dependency-graph/state/refresh-index.sqlite')
        argv = [str(root / 'uc-library/.venv/bin/python'), '-B',
                str(refresh_path), '--compiler-rescan', reason]
        record('refresh_running', refresh_argv=argv)
        with (job / 'REFRESH.log').open('x') as log:
            child = invoke(argv, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                           check=False)
        result = child.returncode
        record('refresh_terminal', refresh_returncode=result)
    except BaseException as error:
        record('failed', error=type(error).__name__ + ': ' + str(error))
        result = 1
    finally:
        if activated:
            try:
                if policy.read_bytes() == activation:
                    atomic(policy, prior)
                    record('stopped_policy_restored', policy_restored=True,
                           restored_policy_sha256=digest(prior))
                else:
                    record('foreign_policy_preserved', policy_restored=False,
                           restoration_blocked=True)
                    result = 1
            except BaseException as error:
                record('restoration_failed', policy_restored=False,
                       error=type(error).__name__ + ': ' + str(error))
                result = 1
        if lock is not None:
            lock.close()
        record('terminal', terminal=True, returncode=result,
               no_retry_or_next_cycle=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, type=Path)
    arguments = parser.parse_args()
    # A normal stop request must not detach a still-running attached Docker
    # publisher. Wait for the existing refresh to become terminal, then finally
    # restore policy. Unit disables forced kill; no restart/resume is attempted.
    def stop_requested(number, frame):
        with (arguments.config.parent / 'RUN.log').open('a') as log:
            log.write('signal ' + str(number) + ': retain attached job until terminal\n')
    signal.signal(signal.SIGTERM, stop_requested)
    signal.signal(signal.SIGINT, stop_requested)
    raise SystemExit(run(arguments.config))


if __name__ == '__main__':
    main()
