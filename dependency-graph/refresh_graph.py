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
from context_resources import choose_compiler_limits, MIB
from memgraph_endpoint import memgraph_network
from refresh_facts import connect, facts, replace, requires_reconfigure, stale_units
from test_build_invalidation import compiler_invalidation

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / 'dependency-graph'
BUILD = ROOT / 'temp/core-upstream/root-integration-01'
GROUPS = [('app', BUILD), ('core', BUILD / 'upstream-core/build')]
PRODUCERS = ('test_build_invalidation.py', 'refresh_graph.py', 'refresh_facts.py', 'refresh_extract.py',
             'refresh_publish.py', 'full_source_graph.py', 'gcc_source_graph.py',
             'context_selector.py', 'context_runtime.py', 'memgraph_endpoint.py', 'code_identity.py', 'batch_publication.py', 'publication_events.py', 'context_resources.py',
             'native_candidate_gate.py', 'native_candidate_ownership.py', 'native_candidate_guard_v3.py',
             'native_candidate_lifecycle.py', 'compact_facts.py', 'incremental_delta.py',
             'incremental_stage.py', 'bounded_net_changes.py', 'compact_identity_bitmap.py', 'owner_rekey_plan.py', 'stage_timing.py', 'stage_normalization.py', 'deferred_sqlite.py', 'publication_budget.py', 'reuse_observations.py', 'verified_build_reconfiguration.py', 'unchanged_observations.py')


def run(argv, out, label):
    start = time.perf_counter()
    with (out / (label + '.log')).open('w') as log:
        result = subprocess.run(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    (out / (label + '.json')).write_text(json.dumps({'argv': argv, 'returncode': result.returncode,
        'seconds': time.perf_counter() - start}, indent=2) + '\n')
    if result.returncode:
        raise ContextError(label + ' failed; retained log: ' + str(out / (label + '.log')))


def docker(script, out, label, analysis=False):
    if not analysis:
        from production_write_stop import require_graph_updates
        require_graph_updates(ROOT)
    memory_args = []
    cpus = 2
    if analysis:
        count = len(json.loads((out / 'units.json').read_text()))
        profile = choose_compiler_limits(max(1, count))
        cpus = profile['builder_jobs']
        available = profile['resources'].get('available_memory_bytes')
        budget = (cpus * 1536 + 3072) * MIB
        if available is not None:
            budget = min(budget, max(512 * MIB, available - 2048 * MIB))
        else:
            budget = 4 * 1024 * MIB
        memory = str(max(512, budget // MIB)) + 'm'
        memory_args = ['--memory=' + memory]
        profile.update(docker_memory=memory, docker_cpus=cpus, task_count=count)
        (out / 'compiler-host-resources.json').write_text(json.dumps(profile, indent=2) + '\n')
    argv = ['docker', 'run', '--name', 'graph-' + label + '-' + str(time.time_ns()),
            '--network=' + ('none' if analysis else memgraph_network(ROOT)),
            *memory_args, '--cpus=' + str(cpus), '--user', '1000:1000',
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


def publisher_script(output):
    # Internal entry: ensure_fresh / --resume retain the host exclusive lock
    # across this child. The publisher CLI takes its own lock for direct use.
    return ['-c',
            'import pathlib,sys;sys.path.insert(0,sys.argv[1]);'
            'from refresh_publish import main;main(pathlib.Path(sys.argv[2]))',
            str(BASE), str(output)]


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


def reviewed_row_allowance(path, bounded_rekey_pairs=None):
    """Read an explicit rescan exception; automatic preparation never inherits it."""
    path = pathlib.Path(path).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ContextError('Row-budget review must be a repository-local file')
    review = json.loads(path.read_text())
    rows_limit = review.get('rows')
    maintenance = bounded_rekey_pairs is not None
    max_rows = 64_000_000 if maintenance else 30_000_000
    if type(rows_limit) is not int or not 100000 < rows_limit <= max_rows:
        raise ContextError(f'Reviewed rows must be finite and in 100001..{max_rows}')
    if maintenance and (review.get('scope') != 'bounded_owner_rekey_recovery'
                        or review.get('expected_pairs') != bounded_rekey_pairs):
        raise ContextError('Bounded owner reconciliation requires a separately bound finite budget review')
    estimate = review.get('journal_estimate_limit')
    if estimate is not None and (not maintenance or type(estimate) is not int
                                 or not 10 * 1024**3 <= estimate <= 20 * 1024**3):
        raise ContextError('Separate estimate reserve is available only within finite scoped recovery bounds')
    if 'maintenance_guard' in review and (not maintenance or review['maintenance_guard'] is not True):
        raise ContextError('Expanded native guard requires the scoped rekey review')
    if not isinstance(review.get('reason'), str) or not review['reason'].strip():
        raise ContextError('Row-budget review requires a concrete reason')
    evidence = review.get('evidence', {})
    evidence_path = (ROOT / evidence.get('path', '')).resolve()
    if (not evidence_path.is_relative_to(ROOT) or not evidence_path.is_file()
            or sha(evidence_path) != evidence.get('sha256')):
        raise ContextError('Row-budget forecast evidence mismatch')
    byte_limits = review.get('byte_limits', {})
    if not isinstance(byte_limits, dict):
        raise ContextError('Reviewed byte limits must be an object')
    if byte_limits:
        gib = 1024**3
        ceilings = {'journal_bytes': (10 if maintenance else 3) * gib,
                    'sqlite_write_bytes': (40 if maintenance else 12) * gib,
                    'transfer_bytes': (20 if maintenance else 3) * gib}
        if not isinstance(byte_limits, dict) or set(byte_limits) - ceilings.keys():
            raise ContextError('Only bounded journal/write/transfer rescan exceptions are supported')
        if any(type(value) is not int or not 0 < value <= ceilings[key]
               for key, value in byte_limits.items()):
            raise ContextError('Reviewed byte limits exceed finite configured ceilings')
        resource = review.get('resource_evidence', {})
        resource_path = (ROOT / resource.get('path', '')).resolve()
        if (not resource_path.is_relative_to(ROOT) or not resource_path.is_file()
                or sha(resource_path) != resource.get('sha256')):
            raise ContextError('Measured resource evidence mismatch')
    return {'path': str(path), 'sha256': sha(path), 'review': review}


def ensure_fresh(force=False, *, full_rebuild=False, rebuild_authorization=None,
                 reuse_capture=None, verify_build_plan=None, compiler_rescan=None,
                 row_budget_review=None, bounded_rekey_pairs=None):
    """Caller holds context.lock for refresh plus packet selection; no background watcher."""
    from production_write_stop import require_graph_updates
    require_graph_updates(ROOT)
    index_path = BASE / 'state/refresh-index.sqlite'
    if bounded_rekey_pairs is not None and (
            compiler_rescan is None or reuse_capture is None or type(bounded_rekey_pairs) is not int
            or bounded_rekey_pairs <= 0):
        raise ContextError('Bounded owner reconciliation requires explicit compiler rescan and verified capture reuse')
    if row_budget_review is not None and compiler_rescan is None:
        raise ContextError('Reviewed row allowance requires explicit compiler rescan')
    if compiler_rescan is not None:
        if not isinstance(compiler_rescan, str) or not compiler_rescan.strip():
            raise ContextError('Compiler rescan requires an explicit reason')
        if full_rebuild or force or verify_build_plan is not None:
            raise ContextError('Compiler rescan cannot be combined with force, full rebuild, build-only verification')
    if bounded_rekey_pairs is not None and row_budget_review is None:
        raise ContextError('Bounded owner reconciliation needs reviewed finite limits')
    row_review = reviewed_row_allowance(row_budget_review, bounded_rekey_pairs) if row_budget_review is not None else None
    maintenance = row_review['review'] if bounded_rekey_pairs is not None else None
    if full_rebuild and (not isinstance(rebuild_authorization, str) or not rebuild_authorization.strip()):
        raise ContextError('Full rebuild requires an explicit reason')
    if force and not full_rebuild:
        raise ContextError('Forced global refresh requires explicit --full-rebuild REASON')
    force = force or full_rebuild
    check_existing_identity(index_path)
    baseline = None
    if index_path.exists():
        recovery = connect(index_path)
        require_identity_version(recovery)
        pending = recovery.execute('SELECT value FROM meta WHERE key="pending"').fetchone()
        recovery.close()
        if pending and maintenance:
            raise ContextError('Scoped rekey recovery requires an empty prior publication journal')
        if pending:
            output = pathlib.Path(pending[0])
            docker(publisher_script(output), output, 'resume-' + str(time.time_ns()))
        recovery = connect(index_path)
        row = recovery.execute('SELECT value FROM meta WHERE key="unregistered_baseline"').fetchone()
        recovery.close()
        if row: baseline = json.loads((pathlib.Path(row[0]) / 'refresh-report.json').read_text())
    active = json.loads((BASE / 'ACTIVE.json').read_text())
    if maintenance:
        source = pathlib.Path(reuse_capture).resolve()
        proof = ROOT / 'uc-library/validation/integration.json'
        approved_capture = maintenance['capture_plan']
        if (baseline or active['state_sha256'] != maintenance['prior_state_sha256']
                or approved_capture != {'path': str((source / 'plan.json').relative_to(ROOT)),
                                        'sha256': sha(source / 'plan.json')}
                or sha(proof) != maintenance['canonical_proof_sha256']
                or shutil.disk_usage(BASE / 'state').free < maintenance['min_free_storage_bytes']):
            raise ContextError('Scoped rekey baseline, capture, proof or storage reserve has changed')
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
    configuration = force or verify_build_plan is not None or requires_reconfigure(changed, inventory_delta)
    if configuration:
        for group, build in GROUPS:
            home = next(line.split('=', 1)[1] for line in (build / 'CMakeCache.txt').read_text().splitlines()
                        if line.startswith('CMAKE_HOME_DIRECTORY:'))
            run([str(ROOT / 'uc-library/.venv/bin/cmake'), '-S', home, '-B', str(build),
                 '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON'], out, 'configure-' + group)
    wanted = rows()
    if maintenance and (len(wanted) != maintenance['expected_units']
                        or sha(dict(GROUPS)['app'] / 'compile_commands.json') != maintenance['compile_db_sha256']):
        raise ContextError('Scoped recovery compile database or configured unit count differs')
    run([str(ROOT / 'uc-library/.venv/bin/ctest'), '--test-dir', str(BUILD), '--show-only=json-v1'],
        out, 'ctest-inventory')
    tests = json.loads((out / 'ctest-inventory.log').read_text())['tests']
    c = connect(index_path)
    try:
        # A publication journal is resumable; never bless a partially applied generation.
        if not c.execute('SELECT 1 FROM units LIMIT 1').fetchone():
            if not full_rebuild:
                raise ContextError('Empty source index requires an explicit initial rebuild')
            seed(c, out)
        invalidate_all, invalidation_reason = compiler_invalidation(
            ROOT, c, wanted, changed, inventory_delta, configuration, force,
            builds=[build for _, build in GROUPS], tests=tests)
        build_proof = None
        if verify_build_plan is not None:
            if full_rebuild:
                raise ContextError('Build-only verification cannot be combined with full rebuild')
            from verified_build_reconfiguration import verify_build_only
            original_plan = pathlib.Path(verify_build_plan).resolve()
            original = json.loads(original_plan.read_text())
            build_proof = verify_build_only(
                ROOT, c, wanted, changed, inventory_delta, GROUPS,
                original['producer_sha256'])
            build_proof['original_plan'] = str(original_plan)
            build_proof['original_plan_sha256'] = sha(original_plan)
            build_proof['configure_receipts'] = {
                group: sha(out / ('configure-' + group + '.json')) for group, _ in GROUPS}
            (out / 'build-reconfiguration-proof.json').write_text(json.dumps(build_proof, indent=2) + '\n')
            invalidate_all = False
            invalidation_reason = 'explicit exact ALL-unit command/input equivalence after configure'
        dirty, removed = stale_units(c, wanted, changed, invalidate_all)
        plan = {'identity_version': VERSION, 'previous_active': active, 'changed': sorted(changed), 'affected_units': sorted(dirty),
                'removed_units': sorted(removed), 'total_units': len(wanted), 'configuration_refresh': configuration,
                'compiler_invalidation_all': invalidate_all, 'compiler_invalidation_reason': invalidation_reason,
                'producer_sha256': producer_hashes}
        if compiler_rescan is not None:
            # Observation breadth alone never increases publication allowances.
            plan['compiler_rescan'] = {'authorization': compiler_rescan,
                                       'scope': 'permit conservative all-unit compiler invalidation'}
            plan['publication_budget'] = {'mode': 'routine'}
            if row_review is not None:
                plan['publication_budget']['limits'] = {
                    'rows': row_review['review']['rows'], **row_review['review'].get('byte_limits', {})}
                plan['publication_budget']['row_budget_review'] = row_review
                if maintenance and maintenance.get('journal_estimate_limit') is not None:
                    plan['publication_budget']['journal_estimate_limit'] = maintenance['journal_estimate_limit']
        if bounded_rekey_pairs is not None:
            plan['bounded_owner_reconciliation'] = {
                'expected_pairs': bounded_rekey_pairs,
                'min_free_storage_bytes': maintenance['min_free_storage_bytes'],
                'maintenance_guard': maintenance.get('maintenance_guard', False),
            }
        if build_proof is not None:
            plan['build_reconfiguration_proof'] = {
                'path': str(out / 'build-reconfiguration-proof.json'),
                'sha256': sha(out / 'build-reconfiguration-proof.json')}
        (out / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
        if invalidate_all and not full_rebuild and compiler_rescan is None:
            raise ContextError('Automatic full rebuild refused before extraction/publication: ' +
                               invalidation_reason + '; inspect plan ' + str(out / 'plan.json'))
        if full_rebuild:
            # Separate, explicit operation; routine preparation never inherits it.
            plan['publication_budget'] = dict(mode='full_rebuild', authorization=rebuild_authorization,
                limits=dict(journal_bytes=1024**3, sqlite_write_bytes=8*1024**3,
                            rows=10_000_000, transfer_bytes=2*1024**3))
            (out / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
        selected = [(owner, row) for owner, row in wanted if owner in dirty]
        (out / 'units.json').write_text(json.dumps(selected) + '\n')
        reused_captures = 0
        if selected and reuse_capture is not None:
            from reuse_observations import reuse_verified, METADATA
            source = pathlib.Path(reuse_capture).resolve()
            # These are observed/approved input bindings NOW, not a claim that
            # the prior extractor recorded hashes which it did not record.
            bindings = dict(producers=producer_hashes,
                            source_metadata={name: sha(source / name) for name in METADATA})
            (out / 'reuse-input-bindings.json').write_text(json.dumps(bindings, indent=2) + '\n')
            reuse = reuse_verified(ROOT, source, out, selected, bindings)
            (out / 'observation-reuse.json').write_text(json.dumps(reuse, indent=2) + '\n')
            if reuse['rejected']:
                raise ContextError('Capture reuse rejected; no automatic re-extraction: ' +
                                   str(out / 'observation-reuse.json'))
            reused_captures = len(reuse['eligible'])
            plan['observation_provenance'] = {'reuse_receipt': str(out / 'observation-reuse.json'),
                                             'sha256': sha(out / 'observation-reuse.json'),
                                             'reused_compiler_captures': reused_captures}
            (out / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
        elif selected:
            docker([str(BASE / 'refresh_extract.py'), str(out)], out, 'extract', analysis=True)
        # Current build facts and publication report are constructed by the worker,
        # with all prior TU contributors available for exact retraction.
        docker(publisher_script(out), out, 'publish')
        if c.execute('SELECT 1 FROM meta WHERE key="unregistered_baseline"').fetchone():
            raise ContextError('Sources moved during publication; next prepare will reconcile them: ' + str(out))
        elapsed = time.perf_counter() - start
        result = {'refreshed': True, 'recompiled_units': len(dirty) - reused_captures,
                  'reused_compiler_captures': reused_captures, 'reprocessed_fact_units': len(dirty),
                  'reused_units': len(wanted) - len(dirty),
                  'removed_units': len(removed), 'seconds': elapsed, 'out': str(out.relative_to(ROOT))}
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
        return result
    finally:
        c.close()


if __name__ == '__main__':
    from production_write_stop import require_graph_updates
    require_graph_updates(ROOT)
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
            docker(publisher_script(output), output,
                   'resume-' + str(time.time_ns()))
        else:
            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument('--force', action='store_true')
            parser.add_argument('--full-rebuild', metavar='REASON')
            parser.add_argument('--compiler-rescan', metavar='REASON',
                                help='Permit conservative all-TU extraction with unchanged routine publication budgets')
            parser.add_argument('--reuse-capture', type=pathlib.Path)
            parser.add_argument('--bounded-rekey-pairs', type=int,
                                help='Explicit exact old/new owner pairs for an observed reconfiguration recovery')
            parser.add_argument('--row-budget-review', '--publication-budget-review', type=pathlib.Path,
                                help='Explicit hash-bound rescan budget review; never inherited by automatic preparation')
            parser.add_argument('--verify-build-plan', type=pathlib.Path,
                                help='Explicit retained extraction plan for exact build-only verification')
            args = parser.parse_args()
            ensure_fresh(args.force, full_rebuild=args.full_rebuild is not None,
                         rebuild_authorization=args.full_rebuild, reuse_capture=args.reuse_capture,
                         verify_build_plan=args.verify_build_plan, compiler_rescan=args.compiler_rescan,
                         row_budget_review=args.row_budget_review, bounded_rekey_pairs=args.bounded_rekey_pairs)
