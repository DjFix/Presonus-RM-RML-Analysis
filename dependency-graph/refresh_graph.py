"""Host coordinator: refresh affected compiler contexts before packet preparation."""
import concurrent.futures
import fcntl
import json
import pathlib
import shlex
import shutil
import sqlite3
import subprocess
import sys
import time

from context_runtime import ContextError, guard, inventory, sha
from code_identity import VERSION, owner_id
from refresh_facts import connect, facts, replace, requires_reconfigure, stale_units

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / 'dependency-graph'
BUILD = ROOT / 'temp/core-upstream/root-integration-01'
GROUPS = [('app', BUILD), ('core', BUILD / 'upstream-core/build')]
PRODUCERS = ('refresh_graph.py', 'refresh_facts.py', 'refresh_extract.py',
             'refresh_publish.py', 'full_source_graph.py', 'gcc_source_graph.py',
             'context_selector.py', 'context_runtime.py', 'memgraph_endpoint.py', 'code_identity.py', 'batch_publication.py')


def run(argv, out, label):
    start = time.perf_counter()
    with (out / (label + '.log')).open('w') as log:
        result = subprocess.run(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    (out / (label + '.json')).write_text(json.dumps({'argv': argv, 'returncode': result.returncode,
        'seconds': time.perf_counter() - start}, indent=2) + '\n')
    if result.returncode:
        raise ContextError(label + ' failed; retained log: ' + str(out / (label + '.log')))


def docker(script, out, label, analysis=False):
    argv = ['docker', 'run', '--name', 'graph-' + label + '-' + str(time.time_ns()),
            '--network=' + ('none' if analysis else 'dependency-graph-experiment'),
            '--memory=4g', '--cpus=2', '--user', '1000:1000',
            '-v', str(ROOT) + ':' + str(ROOT) + ':ro',
            '-v', str(out) + ':' + str(out) + ':rw',
            '-v', str(BASE / 'state') + ':' + str(BASE / 'state') + ':rw',
            '-e', 'DEPENDENCY_GRAPH_ROOT=' + str(ROOT), '-e', 'TMPDIR=' + str(out)]
    if not analysis:
        # Packet/registration code uses its repository root, without hard-coded /workspace paths.
        argv += ['-v', str(BASE) + ':' + str(BASE) + ':rw']
    if analysis:
        for path in ['/usr/include/openssl', '/usr/include/x86_64-linux-gnu/openssl']:
            argv += ['-v', path + ':' + path + ':ro']
    argv += ['dependency-graph-analysis:01' if analysis else 'dependency-graph-runner:01', *script]
    run(['sg', 'docker', '-c', shlex.join(argv)], out, label)


def rows():
    return sorted({owner_id(ROOT, group, row): row for group, build in GROUPS
                   for row in json.loads((build / 'compile_commands.json').read_text())}.items())


def seed(c, out):
    """One-time ownership index over preserved observations; no compiler replays."""
    if c.execute('SELECT count(*) FROM units').fetchone()[0]: return
    for group, name, ast_dir in [('app', 'full-01', 'ast2'), ('core', 'core-source-01', 'ast3')]:
        source = BASE / 'runs' / name
        gcc = next(source.glob('gcc-all-*'))
        for index, row in enumerate(json.loads((source / 'compile_commands.json').read_text())):
            owner = owner_id(ROOT, group, row)
            ap, gp = source / ast_dir / f'{index:04d}.json', gcc / f'{index:04d}.json'
            ast = json.loads(ap.read_text())
            nodes, edges = facts(ROOT, owner, row, ap, gp)
            replace(c, owner, row, nodes, edges, ast['input_sha256'], ap, gp)
        print('Indexed preserved observations: ' + group, flush=True)
    c.execute('INSERT OR REPLACE INTO meta VALUES(?,?)', ('identity_version', str(VERSION)))
    c.commit()
    (out / 'seed.json').write_text(json.dumps({'units': c.execute('SELECT count(*) FROM units').fetchone()[0],
        'scope': 'ownership of preserved TU observations, not a fresh compiler validation'}) + '\n')


def require_identity_version(c):
    version = c.execute('SELECT value FROM meta WHERE key="identity_version"').fetchone()
    if not version or int(version[0]) != VERSION:
        raise ContextError('Source identity migration required: legacy index/pending delta must not be replayed by v2 producers; use reviewed isolated migration')


def check_existing_identity(path):
    if path.exists():
        with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as c:
            require_identity_version(c)


def ensure_fresh(force=False):
    """Caller holds context.lock for refresh plus packet selection; no background watcher."""
    index_path = BASE / 'state/refresh-index.sqlite'
    check_existing_identity(index_path)
    baseline = None
    if index_path.exists():
        recovery = connect(index_path)
        require_identity_version(recovery)
        pending = recovery.execute('SELECT value FROM meta WHERE key="pending"').fetchone()
        recovery.close()
        if pending:
            output = pathlib.Path(pending[0])
            docker([str(BASE / 'refresh_publish.py'), str(output)], output, 'resume-' + str(time.time_ns()))
        recovery = connect(index_path)
        row = recovery.execute('SELECT value FROM meta WHERE key="unregistered_baseline"').fetchone()
        recovery.close()
        if row: baseline = json.loads((pathlib.Path(row[0]) / 'refresh-report.json').read_text())
    active = json.loads((BASE / 'ACTIVE.json').read_text())
    try:
        if baseline: raise ContextError('Reconcile an interrupted generation against current source')
        state = guard(ROOT, active)
        if not force and state.get('automatic_refresh_version') == 1:
            return {'refreshed': False}
    except ContextError:
        state_path = ROOT / active['state']
        if sha(state_path) != active['state_sha256']: raise
        state = json.loads(state_path.read_text())
        if baseline:
            state = {'files': {str(pathlib.Path(p).relative_to(ROOT)): {'sha256': digest}
                              for p, digest in baseline['input_sha256'].items()},
                     'source_inventory': baseline.get('source_inventory', state['source_inventory'])}
    out = ROOT / 'temp/recovery-work/dependency-graph/refresh' / str(time.time_ns())
    out.mkdir(parents=True, exist_ok=False)
    producer_hashes = {}
    (out / 'producers').mkdir()
    for name in PRODUCERS:
        shutil.copy2(BASE / name, out / 'producers' / name)
        producer_hashes[str((BASE / name).relative_to(ROOT))] = sha(out / 'producers' / name)
    start = time.perf_counter()
    changed = {str(ROOT / p) for p, v in state['files'].items()
               if not (ROOT / p).is_file() or sha(ROOT / p) != v['sha256']}
    inventory_delta = set(inventory(ROOT)) ^ set(state['source_inventory'])
    changed.update(str(ROOT / p) for p in inventory_delta)
    configuration = force or requires_reconfigure(changed, inventory_delta)
    if configuration:
        for group, build in GROUPS:
            home = next(line.split('=', 1)[1] for line in (build / 'CMakeCache.txt').read_text().splitlines()
                        if line.startswith('CMAKE_HOME_DIRECTORY:'))
            run([str(ROOT / 'uc-library/.venv/bin/cmake'), '-S', home, '-B', str(build),
                 '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON'], out, 'configure-' + group)
    wanted = rows()
    c = connect(index_path)
    try:
        # A publication journal is resumable; never bless a partially applied generation.
        seed(c, out)
        dirty, removed = stale_units(c, wanted, changed, configuration)
        plan = {'identity_version': VERSION, 'previous_active': active, 'changed': sorted(changed), 'affected_units': sorted(dirty),
                'removed_units': sorted(removed), 'total_units': len(wanted), 'configuration_refresh': configuration,
                'producer_sha256': producer_hashes}
        (out / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
        selected = [(owner, row) for owner, row in wanted if owner in dirty]
        (out / 'units.json').write_text(json.dumps(selected) + '\n')
        if selected:
            docker([str(BASE / 'refresh_extract.py'), str(out)], out, 'extract', analysis=True)
        run([str(ROOT / 'uc-library/.venv/bin/ctest'), '--test-dir', str(BUILD), '--show-only=json-v1'],
            out, 'ctest-inventory')
        # Current build facts and publication report are constructed by the worker,
        # with all prior TU contributors available for exact retraction.
        docker([str(BASE / 'refresh_publish.py'), str(out)], out, 'publish')
        if c.execute('SELECT 1 FROM meta WHERE key="unregistered_baseline"').fetchone():
            raise ContextError('Sources moved during publication; next prepare will reconcile them: ' + str(out))
        elapsed = time.perf_counter() - start
        result = {'refreshed': True, 'recompiled_units': len(dirty), 'reused_units': len(wanted) - len(dirty),
                  'removed_units': len(removed), 'seconds': elapsed, 'out': str(out.relative_to(ROOT))}
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
        return result
    finally:
        c.close()


if __name__ == '__main__':
    lock = BASE / 'state/context.lock'; lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        if len(sys.argv) > 1 and sys.argv[1] == '--resume':
            check_existing_identity(BASE / 'state/refresh-index.sqlite')
            c = connect(BASE / 'state/refresh-index.sqlite')
            require_identity_version(c)
            pending = c.execute('SELECT value FROM meta WHERE key="pending"').fetchone(); c.close()
            if not pending: raise SystemExit('No pending publication')
            output = pathlib.Path(pending[0])
            docker([str(BASE / 'refresh_publish.py'), str(output)], output,
                   'resume-' + str(time.time_ns()))
        else:
            ensure_fresh('--force' in sys.argv)
