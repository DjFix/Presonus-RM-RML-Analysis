"""Exercise automatic CLI refresh after a replayed journal and newer source edits."""
import fcntl
import json
import pathlib
import subprocess
import sys
import time

from refresh_facts import connect
from refresh_graph import BASE, ROOT, ensure_fresh


def main():
    out = ROOT / 'temp/test-work/refresh-recovery' / str(time.time_ns()); out.mkdir(parents=True)
    source = ROOT / 'uc-library/tests/panel_registrar_access_tests.cpp'
    before = source.read_bytes(); (out / source.name).write_bytes(before)
    prior = sorted((ROOT / 'temp/recovery-work/dependency-graph/refresh').glob('*/publication.json'))[-1].parent
    # Simulate the durable journal surviving a process exit after its transaction.
    # Replaying this sealed delta must be idempotent, then reconcile newer source.
    c = connect(BASE / 'state/refresh-index.sqlite')
    if c.execute('SELECT 1 FROM meta WHERE key="pending"').fetchone(): raise ValueError('Existing job: do not replace')
    c.execute('INSERT INTO meta VALUES(?,?)', ('pending', str(prior))); c.commit(); c.close()
    packet = ROOT / 'temp/recovery-work/context-gate' / ('auto-refresh-' + str(time.time_ns()))
    command = [sys.executable, str(ROOT / 'uc-library/tools/recovery/select_context.py'), 'prepare',
               '--task', 'dependency-graph/tasks/control-registrar-audit.json', '--out', str(packet.relative_to(ROOT))]
    start = time.perf_counter()
    try:
        source.write_bytes(before + b'\n// Reversible automatic prepare/recovery probe.\n')
        with (out / 'prepare.log').open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
        if result.returncode: raise ValueError('Automatic prepare failed: ' + str(out / 'prepare.log'))
        context = json.loads((packet / 'context.json').read_text())
        assert context['state'] == 'dispatch_ready'
        assert len(context['call_functions']) == 5
        assert len(context['context_nodes']) == 17
        assert (prior / 'superseded.json').exists()
        elapsed = time.perf_counter() - start
    finally:
        source.write_bytes(before)
        with (BASE / 'state/context.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            restored = ensure_fresh()
    (out / 'results.json').write_text(json.dumps({'passed': True, 'simulation': 'reinserted completed journal, then newer source comment',
        'prior_delta': str(prior.relative_to(ROOT)), 'automatic_prepare_argv': command,
        'packet': str(packet.relative_to(ROOT)), 'seconds_including_journal_retry': elapsed,
        'restoration': restored, 'source_bytes_restored': source.read_bytes() == before,
        'functions': 5, 'context_entities': 17}, indent=2) + '\n')
    print(str(out / 'results.json'), flush=True)


if __name__ == '__main__': main()
