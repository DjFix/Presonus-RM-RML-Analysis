"""Transactional Memgraph delta publication with a durable retry journal."""
import json
import pathlib
import re
import shlex
import sqlite3
import sys
import time

from neo4j import GraphDatabase
from memgraph_endpoint import memgraph_uri
from code_identity import VERSION
from batch_publication import publish, BudgetedRequests
from context_runtime import ContextError, inventory, sha
from context_selector import register
from refresh_facts import connect, external_dependencies, facts, merged_node, replace

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / 'dependency-graph'
BUILD = ROOT / 'temp/core-upstream/root-integration-01'
BUILD_KINDS = ('compiler_input', 'compiles', 'link_input', 'HAS_TEST_TU', 'RUNS', 'USES_FIXTURE')


def build_facts(c, out):
    nodes = {}; edges = set(); inputs = {}
    def node(key, kind, label, meta=None):
        nodes[key] = {'kind': kind, 'label': label, 'metadata': meta or {}}
        return key
    previous_kinds = {}
    def prior_file_kind(key):
        if key not in previous_kinds:
            kinds = {row[0] for row in c.execute(
                'SELECT DISTINCT kind FROM node_facts WHERE id=?', (key,))}
            if len(kinds) > 1 or kinds - {'file', 'Fixture'}:
                raise ContextError('Conflicting prior file identity: ' + key)
            previous_kinds[key] = next(iter(kinds), None)
        return previous_kinds[key]
    def file(path):
        path = pathlib.Path(path).resolve()
        label = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        key = 'file:' + label
        return key if key in nodes else node(key, prior_file_kind(key) or 'file', label)
    source_units = {}; objects = {}; directories = set()
    for owner, payload in c.execute('SELECT * FROM units ORDER BY owner'):
        data = json.loads(payload); row = data['command']; directories.add(pathlib.Path(row['directory']))
        argv = row.get('arguments') or shlex.split(row['command'])
        obj = pathlib.Path(row['directory']) / argv[argv.index('-o') + 1]
        oid = file(obj); objects[oid] = owner
        edges.add((oid, file(row['file']), 'compiles', 'current compile_commands.json'))
        for path, digest in data['inputs'].items():
            if path in inputs and inputs[path] != digest: raise ContextError('Mixed source observations: ' + path)
            inputs[path] = digest
            edges.add((oid, file(path), 'compiler_input', 'current captured compiler/AST input'))
        external = data.get('external_inputs')
        if external is None: external = external_dependencies(ROOT, row)
        for path in external:
            edges.add((oid, file(path), 'compiler_input', 'external include path; compiler environment, not recovered source'))
        tu = [r[0] for r in c.execute('SELECT id FROM node_facts WHERE owner=? AND kind=?', (owner, 'TranslationUnit'))]
        if len(tu) != 1: raise ContextError('Exactly one TU required: ' + owner)
        source_units[oid] = tu[0]
        inputs[data['ast']] = data['ast_sha256']; inputs[data['gcc']] = data['gcc_sha256']
    linked = {}
    for directory in directories:
        for recipe in sorted(directory.glob('CMakeFiles/*/link.txt')):
            inputs[str(recipe)] = sha(recipe)
            argv = shlex.split(recipe.read_text())
            if not argv: continue
            if '-o' in argv: output = argv[argv.index('-o') + 1]
            elif pathlib.Path(argv[0]).name in ('ar', 'gcc-ar', 'llvm-ar'):
                output = next((s for s in argv[1:] if s.endswith('.a')), None)
            else: continue
            if not output: continue
            target = file(directory / output); linked[target] = []
            for token in argv:
                if token.endswith(('.o', '.a')) and token != output:
                    source = file(directory / token)
                    edges.add((target, source, 'link_input', str(recipe)))
                    if source in source_units: linked[target].append(source_units[source])
    tests = json.loads((out / 'ctest-inventory.log').read_text())['tests']
    for test in tests:
        tid = node('test:' + test['name'], 'Test', test['name'], test)
        argv = test.get('command', [])
        if not argv: raise ContextError('Configured test has no resolved CTest command: ' + test['name'])
        executable = file(argv[0]); edges.add((tid, executable, 'RUNS', 'current CTest inventory'))
        for tu in linked.get(executable, []): edges.add((tid, tu, 'HAS_TEST_TU', 'current CMake link operand + CTest command'))
        for arg in argv[1:]:
            p = pathlib.Path(arg)
            if p.is_absolute() and p.is_relative_to(ROOT) and p.is_file():
                digest = sha(p); inputs[str(p)] = digest
                label = str(p.relative_to(ROOT)); key = 'file:' + label
                # Preserve legacy Fixture identities; compiled/build file nodes
                # retain file kind. This refresh does not migrate graph kinds.
                prior_kind = prior_file_kind(key)
                kind = nodes[key]['kind'] if key in nodes else prior_kind or 'Fixture'
                if prior_kind is not None and prior_kind != kind:
                    raise ContextError('Conflicting current/prior file identity: ' + key)
                fid = node(key, kind, label, {'sha256': digest})
                edges.add((tid, fid, 'USES_FIXTURE', 'explicit existing file argument in CTest command'))
    return nodes, edges, inputs


CLEAN_BASELINE = 'current_clean_rebuild'


def clean_catalog(c, plan):
    """Build explicit current catalog facts only for a new, empty source index."""
    mode = plan.get('baseline_mode')
    if mode is None:
        return None
    if mode != CLEAN_BASELINE:
        raise ContextError('Unknown source baseline mode')
    for table in ('units', 'node_facts', 'edge_facts', 'observations', 'current_observations'):
        if c.execute('SELECT 1 FROM ' + table + ' LIMIT 1').fetchone():
            raise ContextError('Clean source baseline requires empty index: ' + table)
    if plan.get('removed_units') or c.execute(
            'SELECT 1 FROM meta WHERE key IN ("pending", "unregistered_baseline")').fetchone():
        raise ContextError('Clean source baseline cannot reuse pending/removal state')
    return catalog_snapshot(plan.get('catalog_snapshot', {}))


def catalog_snapshot(binding):
    """Read one immutable current catalog, shared by node and name-link facts."""
    path = pathlib.Path(binding.get('path', '')).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ContextError('Clean baseline requires a repository-local catalog snapshot')
    for suffix in ('-wal', '-journal'):
        sidecar = pathlib.Path(str(path) + suffix)
        if sidecar.exists() and sidecar.stat().st_size:
            raise ContextError('Catalog snapshot has an unbound SQLite sidecar')
    if sha(path) != binding.get('sha256'):
        raise ContextError('Catalog snapshot hash mismatch')
    catalog = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)
    catalog.row_factory = sqlite3.Row
    try:
        records = [dict(row) for row in catalog.execute('SELECT * FROM catalog_symbols ORDER BY anchor')]
    finally:
        catalog.close()
    if not records or any(not row.get('anchor') or not row.get('demangled') for row in records):
        raise ContextError('Catalog snapshot lacks original symbol identities')
    if len({row['anchor'] for row in records}) != len(records):
        raise ContextError('Duplicate current catalog identities')
    return path, binding['sha256'], records


def publication_budget(plan):
    from publication_budget import BudgetLimits, PublicationBudget
    config = plan.get('publication_budget', {})
    if config.get('mode', 'routine') == 'full_rebuild':
        return PublicationBudget(mode='full_rebuild',
            rebuild_authorization=config.get('authorization'),
            rebuild_limits=BudgetLimits(**config['limits']))
    if config.get('mode', 'routine') != 'routine':
        raise ContextError('Unknown publication budget mode')
    return PublicationBudget(limits=BudgetLimits(**config.get('limits', {})))


def stage(c, out, budget=None):
    # A failed/uncommitted attempt is never silently reused or overwritten.
    path = out / 'delta.sqlite'
    if path.exists():
        raise ContextError('Existing incomplete staging output; explicit recovery required: ' + str(path))
    plan = json.loads((out / 'plan.json').read_text())
    selected = json.loads((out / 'units.json').read_text())
    budget = budget or publication_budget(plan)
    budget.preflight(journal_estimate_bytes=0, sqlite_write_estimate_bytes=0, rows=0, transfer_bytes=0)
    delta = sqlite3.connect(path)
    delta.execute('BEGIN')
    c.execute('BEGIN IMMEDIATE')
    # Keep the bounded dirty working set in memory instead of repeatedly
    # spilling the same index pages. The publisher has a separate 4 GiB cap;
    # this changes cache capacity, not durability, atomicity or IO accounting.
    from deferred_sqlite import staging_cache_kib
    cache_kib = staging_cache_kib(budget.limits.sqlite_write_bytes)
    c.execute('PRAGMA cache_size=' + str(-cache_kib))
    c.execute('PRAGMA wal_autocheckpoint=0')
    assert c.execute('PRAGMA wal_autocheckpoint').fetchone()[0] == 0
    sqlite_paths = [pathlib.Path(row[2]) for row in c.execute('PRAGMA database_list')
                    if row[1] == 'main' and row[2]] + [path]
    try:
        with budget.sqlite_progress_guard(c, opcode_interval=100000, journal_paths=[path],
                                          sqlite_paths=sqlite_paths, other_connections=(delta,)):
            _stage_compact(c, out, delta, plan, selected, budget)
        from deferred_sqlite import commit_and_close
        # Helper inserts pending before the final reserve and owns both closes.
        commit_and_close(c, delta, budget, sqlite_paths, pending_value=str(out))
    except BaseException:
        if not getattr(budget, 'deferred_sqlite', {}).get('closed'):
            c.rollback()
            delta.rollback()
        raise
    finally:
        if not getattr(budget, 'deferred_sqlite', {}).get('closed'):
            # Includes body failures before the deferred commit helper is entered.
            try:
                delta.close()
            finally:
                c.close()
        try:
            budget.observe_final_io()
        finally:
            receipt = budget.receipt()
            receipt['deferred_sqlite'] = getattr(budget, 'deferred_sqlite', None)
            receipt['staging_cache_kib'] = cache_kib
            (out / 'stage-budget.json').write_text(json.dumps(receipt, indent=2) + '\n')


def _stage_compact(c, out, delta, plan, selected, budget):
    from incremental_stage import IncrementalStage
    catalog = clean_catalog(c, plan)
    existing_catalog = c.execute('SELECT value FROM meta WHERE key="catalog_snapshot"').fetchone()
    lookup_catalog = catalog or (catalog_snapshot(json.loads(existing_catalog[0])) if existing_catalog else None)
    if not lookup_catalog and c.execute('SELECT 1 FROM node_facts WHERE owner="@catalog" LIMIT 1').fetchone():
        raise ContextError('Catalog facts lack their immutable input binding')
    catalog_lookup = None
    if lookup_catalog:
        catalog_lookup = {}
        for row in lookup_catalog[2]:
            catalog_lookup.setdefault(row['mangled'], []).append('catalog:' + row['anchor'])
    legacy = not catalog and not c.execute('SELECT 1 FROM node_facts WHERE owner="@build" LIMIT 1').fetchone()
    update = IncrementalStage(c, budget)
    from unchanged_observations import ObservationEquivalence
    equivalence = ObservationEquivalence(ROOT)
    diagnostic = {'processed_units': 0, 'selected_units': len(selected), 'owner': None, 'phase': 'start'}
    progress_log = (out / 'stage-progress.jsonl').open('x')

    def progress(phase, owner):
        diagnostic.update(phase=phase, owner=owner,
                          retained_units=len(equivalence.receipt['eligible']),
                          normal_fact_units=len(equivalence.receipt['rejected']))
        # Small append-only records survive a transaction rollback; never copy
        # observations/facts or repeatedly serialize the complete receipt here.
        progress_log.write(json.dumps(diagnostic, sort_keys=True) + '\n')
        progress_log.flush()

    try:
        for owner in plan['removed_units']:
            progress('remove_owner', owner)
            update.remove_owner(owner)
            progress('removed', owner)
        for owner, row in selected:
            progress('selected_owner', owner)
            dest = out / 'observations' / owner.replace(':', '-')
            ast, gcc = dest / 'ast.json', dest / '0000.json'
            previous = c.execute('SELECT payload FROM units WHERE owner=?', (owner,)).fetchone()
            if not catalog and equivalence.check(owner, row, json.loads(previous[0]) if previous else None, ast, gcc):
                diagnostic['processed_units'] += 1
                progress('retained', owner)
                continue
            progress('generate_facts', owner)
            if catalog_lookup is None:
                nodes, edges = facts(ROOT, owner, row, ast, gcc)
            else:
                nodes, edges = facts(ROOT, owner, row, ast, gcc, catalog_lookup=catalog_lookup)
            captured = json.loads(ast.read_text())
            progress('replace_unit', owner)
            update.replace_unit(owner, row, nodes, edges, captured['input_sha256'],
                                ast, gcc, captured['external_inputs'])
            diagnostic['processed_units'] += 1
            progress('replaced', owner)
        if catalog:
            progress('catalog_facts', '@catalog')
            nodes = {'catalog:' + row['anchor']: dict(kind='OriginalSymbol', label=row['demangled'], metadata=row)
                     for row in catalog[2]}
            update.replace_facts('@catalog', nodes, [])
        progress('build_facts', '@build')
        nodes, edges, inputs = build_facts(c, out)
        if catalog:
            c.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',
                      ('catalog_snapshot', json.dumps(dict(path=str(catalog[0]), sha256=catalog[1]), sort_keys=True)))
        if lookup_catalog:
            inputs[str(lookup_catalog[0])] = lookup_catalog[1]
        update.replace_facts('@build', nodes, edges)
        progress('finish_delta', '@delta')
        counts = update.finish(delta)
        delta.execute('INSERT INTO settings VALUES(?,?)', ('replace_legacy_build', int(legacy)))
        if catalog:
            delta.execute('INSERT INTO settings VALUES(?,?)', ('source_baseline_mode', CLEAN_BASELINE))
        progress('seal_inputs', '@sealing')
        # Configs/commands and CMake generated recipes are captured independently.
        for path in [ROOT / 'uc-library/CMakeLists.txt', *ROOT.glob('uc-library/cmake/**/*.cmake'),
                     BUILD / 'compile_commands.json', BUILD / 'upstream-core/build/compile_commands.json',
                     BUILD / 'CMakeCache.txt', BUILD / 'upstream-core/build/CMakeCache.txt']:
            inputs[str(path)] = sha(path)
        for build in (BUILD, BUILD / 'upstream-core/build'):
            makefile = build / 'CMakeFiles/Makefile.cmake'
            if makefile.exists():
                inputs[str(makefile)] = sha(makefile)
                block = re.search(r'set\(CMAKE_MAKEFILE_DEPENDS\s+(.*?)\)', makefile.read_text(), re.S)
                for token in shlex.split(block[1] if block else ''):
                    path = (build / token).resolve()
                    if path.is_relative_to(ROOT) and path.is_file(): inputs[str(path)] = sha(path)
        for relative in inventory(ROOT):
            path = ROOT / relative
            if path.suffix == '.cmake' or path.name == 'CMakeLists.txt': inputs[str(path)] = sha(path)
        for path, digest in inputs.items():
            if not pathlib.Path(path).is_file() or sha(path) != digest:
                raise ContextError('Inputs changed before publication: ' + path)
        equivalence.verify_retained()
        for relative, digest in plan.get('producer_sha256', {}).items():
            if sha(ROOT / relative) != digest:
                raise ContextError('Producer changed before publication: ' + relative)
        from native_candidate_gate import seal_guard
        from native_candidate_ownership import pack_guard
        candidate_guard = pack_guard(seal_guard(ROOT, c, delta))
        guard_json = json.dumps(candidate_guard, sort_keys=True)
        (out / 'unchanged-observations.json').write_text(json.dumps(equivalence.receipt, indent=2) + '\n')
        report = {'native_candidate_guard': candidate_guard,
                  'input_sha256': inputs, 'source_graph_refresh': True,
                  'source_inventory': inventory(ROOT),
                  'producer_sha256': plan.get('producer_sha256', {}),
                  'observation_provenance': plan.get('observation_provenance', {}),
                  'observation_equivalence': {
                      'path': str(out / 'unchanged-observations.json'),
                      'sha256': sha(out / 'unchanged-observations.json'),
                      'retained_owners': len(equivalence.receipt['eligible']),
                      'normal_fact_owners': len(selected) - len(equivalence.receipt['eligible'])},
                  'runtime_or_original_firmware_callgraph_complete': False}
        if catalog:
            report.update(source_baseline_mode=CLEAN_BASELINE, catalog_snapshot=plan['catalog_snapshot'])
        report_json = json.dumps(report, indent=2) + '\n'
        # This delta is new in this transaction: append one compact setting,
        # not a rewrite of an existing logical guard. Fail before any persistence.
        fresh_case = next((cost.get('delta_row_plan', {}).get('storage_reserve', {}).get('fresh_empty_delete_database')
                           for cost in update.costs if cost['owner'] == '@delta-schema'), None)
        if (fresh_case is not True or not delta.in_transaction or
                delta.execute('PRAGMA journal_mode').fetchone()[0] != 'delete' or
                delta.execute('SELECT 1 FROM settings WHERE key=?',
                              ('native_candidate_guard',)).fetchone()):
            raise ContextError('Candidate guard append requires fresh DELETE delta')
        guard_bytes = len(guard_json.encode())
        report_bytes = len(report_json.encode())
        reserve = guard_bytes + 65536
        update._reserve(dict(owner='@candidate-guard', changed_nodes=0, changed_edges=0,
            observation_updates=0, encoded_changed_bytes=guard_bytes + report_bytes,
            journal_estimate_bytes=reserve,
            sqlite_write_estimate_bytes=2 * reserve + report_bytes,
            rows=1, transfer_estimate_bytes=0))
        delta.execute('INSERT INTO settings VALUES(?,?)',
                      ('native_candidate_guard', guard_json))
        (out / 'refresh-report.json').write_text(report_json)
        (out / 'stage-changes.json').write_text(json.dumps(dict(counts=counts, staging=update.receipt()), indent=2) + '\n')
        budget.completed_stage_estimate = dict(complete=True, estimates=dict(budget.estimates))
    except BaseException as exc:
        failure = dict(diagnostic, error_type=type(exc).__name__, error=str(exc)[:4096],
                       retained_units=len(equivalence.receipt['eligible']),
                       normal_fact_units=len(equivalence.receipt['rejected']))
        (out / 'stage-failure.json').write_text(json.dumps(failure, indent=2) + '\n')
        raise
    finally:
        progress_log.close()
        (out / 'unchanged-observations.json').write_text(json.dumps(equivalence.receipt, indent=2) + '\n')


def batches(cursor, size=500):
    while True:
        batch = cursor.fetchmany(size)
        if not batch: return
        yield [dict(r) for r in batch]


def apply(tx, d):
    # One-time conversion removes legacy unowned build edges. Later generations
    # retract exact old tuples; unchanged build links never cross Bolt again.
    settings = d.execute("SELECT 1 FROM sqlite_master WHERE name='settings'").fetchone()
    legacy = not settings or d.execute('SELECT value FROM settings WHERE key="replace_legacy_build"').fetchone()[0]
    if legacy:
        for kind in BUILD_KINDS:
            print('publication: retract legacy ' + kind, flush=True)
            tx.run('MATCH ()-[r:' + kind + ']->() DELETE r').consume()
    print('publication: nodes', flush=True)
    for batch in batches(d.execute('SELECT * FROM nodes')):
        for row in batch:
            metadata = json.loads(row['metadata']); row['mangled'] = metadata.get('mangled')
            row['path'] = metadata.get('path') or metadata.get('source')
        for kind in sorted({r['kind'] for r in batch}):
            label = {'file': 'File', 'symbol': 'OriginalSymbol'}.get(kind, kind)
            if not re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', label): raise ValueError(label)
            tx.run('UNWIND $rows AS row MERGE(n:Artifact {id:row.id}) SET n:' + label +
                   ' SET n.kind=row.kind,n.label=row.label,n.metadata=row.metadata,n.mangled=row.mangled,n.path=row.path',
                   rows=[r for r in batch if r['kind'] == kind]).consume()
    for table, operation in [('old_edges', 'delete'), ('new_edges', 'merge')]:
        total = d.execute('SELECT count(*) FROM ' + table).fetchone()[0]
        done = 0
        print(f'publication: {table} 0/{total}', flush=True)
        for batch in batches(d.execute('SELECT * FROM ' + table)):
            for kind in sorted({r['kind'] for r in batch}):
                if not re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', kind): raise ValueError(kind)
                if operation == 'delete':
                    query = ('UNWIND $rows AS row MATCH(s:Artifact {id:row.src})-[r:' + kind +
                             ' {evidence:row.evidence}]->(d:Artifact {id:row.dst}) DELETE r')
                else:
                    query = ('UNWIND $rows AS row MATCH(s:Artifact {id:row.src}),(d:Artifact {id:row.dst}) '
                             'MERGE(s)-[:' + kind + ' {evidence:row.evidence}]->(d)')
                selected = [r for r in batch if r['kind'] == kind]
                if operation == 'merge':
                    count = tx.run(query + ' RETURN count(*) AS n', rows=selected).single()['n']
                    if count != len(selected): raise ContextError('Missing edge endpoints: ' + kind)
                else:
                    tx.run(query, rows=selected).consume()
            done += len(batch)
            if done % 10000 == 0 or done == total:
                print(f'publication: {table} {done}/{total}', flush=True)
    for batch in batches(d.execute('SELECT * FROM orphan_nodes')):
        # Legacy proof/catalog bindings remain historical. Remove a code entity's
        # name match when its last current TU definition/reference disappeared.
        tx.run('UNWIND $rows AS row MATCH(n:Artifact {id:row.id}) '
               'OPTIONAL MATCH(n)-[r:ENCODED_NAME_MATCH]->() DELETE r', rows=batch).consume()
        tx.run('UNWIND $rows AS row MATCH(n:Artifact {id:row.id}) WHERE NOT (n)--() DELETE n', rows=batch).consume()



PUBLICATION_RUNTIME_CHANGES = {
    # Request-envelope planning is publication-only; staged facts stay immutable.
    'dependency-graph/batch_publication.py',
    'dependency-graph/refresh_publish.py',
    'dependency-graph/native_candidate_gate.py',
    'dependency-graph/native_candidate_lifecycle.py',
    'dependency-graph/native_candidate_ownership.py',
}


def same_json_value(left, right):
    """Typed equality without serializing another full-size guard string."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same_json_value(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(same_json_value(a, b) for a, b in zip(left, right))
    if isinstance(left, float):
        return repr(left) == repr(right)  # Also preserve -0.0 versus 0.0.
    return left == right


def publication_runtime(out, plan, pending):
    """Explicit publication-only supersession; the staged facts/producers stay factual.

    A reviewed override cannot change compiler/fact producers, the original plan,
    delta, or stage report. Its first use pins the exact runtime across resumes.
    No graph writes occur here. The coordinator retains the normal writer lock.
    """
    original = plan.get('producer_sha256', {})
    actual = {path: sha(ROOT / path) for path in original}
    actual['dependency-graph/memgraph_endpoint.py'] = sha(BASE / 'memgraph_endpoint.py')
    actual['dependency-graph/deferred_sqlite.py'] = sha(BASE / 'deferred_sqlite.py')
    override = out / 'publication-runtime.json'
    accepted = out / 'publication-runtime.accepted.json'
    if not override.exists():
        if accepted.exists() or actual != original:
            raise ContextError('Publication producer changed; explicit reviewed supersession required')
        return actual, None
    if not pending:
        raise ContextError('Publication runtime supersession requires the exact pending staged journal')
    manifest = json.loads(override.read_text())
    if (type(manifest.get('version')) is not int or manifest['version'] != 1 or
            manifest.get('scope') != 'publication_runtime_only' or manifest.get('approved') is not True or
            not isinstance(manifest.get('reason'), str) or not manifest['reason'].strip()):
        raise ContextError('Invalid reviewed publication runtime manifest')
    if manifest.get('stage_plan_sha256') != sha(out / 'plan.json'):
        raise ContextError('Original stage plan changed')
    for suffix in ('-wal', '-journal'):
        sidecar = pathlib.Path(str(out / 'delta.sqlite') + suffix)
        if sidecar.exists() and sidecar.stat().st_size:
            raise ContextError('Publication runtime requires an immutable delta without sidecars')
    if manifest.get('delta_sha256') != sha(out / 'delta.sqlite'):
        raise ContextError('Original staged delta changed')
    desired = manifest.get('publication_producer_sha256', {})
    if (manifest.get('stage_producer_sha256') != original or set(desired) != set(original) or
            actual != desired):
        raise ContextError('Publication runtime producer binding mismatch')
    changed = {path for path in original if original[path] != desired[path]}
    if not changed or not changed <= PUBLICATION_RUNTIME_CHANGES:
        raise ContextError('Supersession cannot change compiler or fact producers')

    def archived(binding):
        path = (out / binding['path']).resolve()
        if not path.is_relative_to(out.resolve()) or not path.is_file() or sha(path) != binding['sha256']:
            raise ContextError('Missing or changed original stage archive')
        return path

    archives = manifest.get('stage_producers', {})
    if set(archives) != set(original):
        raise ContextError('Incomplete original stage producer archive')
    for path, expected in original.items():
        if archives[path].get('sha256') != expected:
            raise ContextError('Original stage producer archive binding differs')
        archived(archives[path])
    stage_report = archived(manifest['stage_report'])
    current_report = out / 'refresh-report.json'
    if sha(current_report) != manifest['stage_report']['sha256']:
        # A resumed publication may have added only its own receipts. Never
        # rewrite or reinterpret any original stage field as a new execution.
        before = json.loads(stage_report.read_text())
        current = json.loads(current_report.read_text())
        additions = {'event_verification', 'native_candidate_lifecycle', 'validation_scope', 'publication_runtime'}
        if (any(key not in current or not same_json_value(current[key], value) for key, value in before.items()) or
                not set(current) <= set(before) | additions):
            raise ContextError('Original stage report fields changed')
    provenance = {'version': 1, 'manifest': str(override.relative_to(ROOT)),
                  'manifest_sha256': sha(override), 'stage_plan_sha256': manifest['stage_plan_sha256'],
                  'delta_sha256': manifest['delta_sha256'], 'stage_report': manifest['stage_report'],
                  'publication_producer_sha256': actual, 'changed_producers': sorted(changed),
                  'scope': 'publication_runtime_only; original compiler/fact execution unchanged'}
    if accepted.exists():
        if not same_json_value(json.loads(accepted.read_text()), provenance):
            raise ContextError('Previously accepted publication runtime changed; no silent resume upgrade')
    else:
        with accepted.open('x') as stream:
            json.dump(provenance, stream, sort_keys=True, indent=2)
            stream.write('\n')
            stream.flush()
            import os
            os.fsync(stream.fileno())
        directory = os.open(out, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    return actual, provenance


def main(out):
    plan = json.loads((out / 'plan.json').read_text())
    if plan.get('identity_version') != VERSION:
        raise ContextError('Legacy sealed delta requires explicit identity migration; publication blocked')
    initial_budget = publication_budget(plan)
    c = connect(BASE / 'state/refresh-index.sqlite')
    c.execute('CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT)'); c.commit()
    pending = c.execute('SELECT value FROM meta WHERE key="pending"').fetchone()
    if pending and pending[0] != str(out): raise ContextError('Another refresh is pending')
    actual, runtime_provenance = publication_runtime(out, plan, bool(pending))
    if pending:
        (out / ('resume-producers-' + str(time.time_ns()) + '.json')).write_text(json.dumps(actual, indent=2) + '\n')
    else:
        if actual != plan.get('producer_sha256', {}): raise ContextError('Refresh producer changed before staging')
        stage(c, out, budget=initial_budget)
    request_budget = initial_budget if pending else publication_budget(plan)
    if not pending:
        c = connect(BASE / 'state/refresh-index.sqlite')
    d = sqlite3.connect(out / 'delta.sqlite'); d.row_factory = sqlite3.Row
    driver = GraphDatabase.driver(memgraph_uri(ROOT), auth=None)
    try:
        with driver.session() as session:
            # publish preflights the complete compact journal before the first
            # graph mutation, and owns the atomic refreshing/checkpoint switch.
            publication = publish(session, d, out / 'delta.sqlite', out / 'batch-commits.jsonl',
                                  budget=request_budget)
            session = BudgetedRequests(session, request_budget)
            print('publication: delta committed; checking and registering', flush=True)
            if plan.get('migration'):
                from migrate_source_identity import verify
                verify(session, out)
            from publication_events import require_verified
            require_verified(session, publication, out / 'delta.sqlite')
            report_path = out / 'refresh-report.json'; report = json.loads(report_path.read_text())
            from native_candidate_lifecycle import reconcile
            candidate_lifecycle = reconcile(
                session, ROOT, out / 'delta.sqlite', report.get('native_candidate_guard'))
            if runtime_provenance is not None:
                report['publication_runtime'] = runtime_provenance
            report.update(event_verification=publication,
                          native_candidate_lifecycle=candidate_lifecycle,
                          validation_scope='committed_batch_effects')
            report_path.write_text(json.dumps(report, indent=2) + '\n')
            changed = [path for path, digest in report['input_sha256'].items()
                       if not pathlib.Path(path).is_file() or sha(path) != digest]
            if changed:
                # The journal's snapshot was published atomically, but sources
                # have moved since it was staged. Keep the graph unavailable;
                # next prepare reconciles current TUs against this exact index.
                c.execute('INSERT OR REPLACE INTO meta VALUES(?,?)', ('unregistered_baseline', str(out)))
                c.execute('DELETE FROM meta WHERE key="pending"'); c.commit()
                (out / 'superseded.json').write_text(json.dumps({'changed': changed}, indent=2) + '\n')
                return
            register(session, out, reports=[report_path])
            session.run('MATCH(p:PublicationCheckpoint {id:$id}),(g:ContextGeneration {id:"active"}) '
                        'SET p.state="published",p.generation=g.digest',id=publication['checkpoint']).consume()
        c.execute('DELETE FROM meta WHERE key="pending"'); c.commit()
        c.execute('DELETE FROM meta WHERE key="unregistered_baseline"'); c.commit()
        (out / 'publication.json').write_text(json.dumps({'published': True, 'validation_scope': 'committed_batch_effects', **publication}, indent=2) + '\n')
    finally:
        d.close(); c.close(); driver.close()
        try:
            request_budget.observe([out / 'delta.sqlite'])
        finally:
            receipt = request_budget.receipt()
            receipt['transfer_measurement'] = 'UTF-8 JSON request envelopes; not Bolt wire bytes or responses'
            (out / 'publication-budget.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    from context_writer_lock import exclusive_writer
    with exclusive_writer():
        main(pathlib.Path(sys.argv[1]))
