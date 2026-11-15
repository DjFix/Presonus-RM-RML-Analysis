"""Bounded real-owner fixture check; never open a canonical database for writing.

Explicit legacy files are read through a normal read-only SQLite snapshot. This is a synthetic
one-owner integration check, not a whole-graph benchmark or interoperability test.
"""
import argparse
import copy
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from compact_facts import CompactFacts
from incremental_stage import IncrementalStage
from publication_budget import PublicationBudget, read_proc_write_bytes, BudgetExceeded, AccountingUnavailable
from refresh_facts import connect

ROOT = Path(__file__).resolve().parents[1]
INPUT_LIMIT = 64 * 1024 * 1024
SUFFIX = 'uc-library/src/Presonus/Mixer/FXComponent.cpp'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(row):
    return json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def indexed_owner_query(db, table):
    # Fail closed rather than turn a missing index into a full fact-population scan.
    plan = list(db.execute('EXPLAIN QUERY PLAN SELECT * FROM ' + table + ' WHERE owner=?', ('probe',)))
    require(any('SEARCH' in row[3] and 'owner=?' in row[3] for row in plan),
            'Indexed owner lookup required: ' + table)


def source_bindings(path):
    bindings = {}
    for suffix in ('', '-wal'):
        candidate = Path(str(path) + suffix)
        try:
            stat = candidate.stat()
        except FileNotFoundError:
            bindings[suffix or 'main'] = None
        else:
            bindings[suffix or 'main'] = dict(device=stat.st_dev, inode=stat.st_ino,
                bytes=stat.st_size, mtime_ns=stat.st_mtime_ns)
    return bindings


def load_owner(db, selected=None, limit=INPUT_LIMIT):
    require(0 < limit < 64 * 1024 * 1024 + 1, 'Input ceiling cannot exceed 64 MiB')
    if selected is None:
        # This inspects unit descriptors only, never the complete graph facts.
        row = db.execute('''SELECT owner FROM units
            WHERE substr(json_extract(payload,'$.command.file'),-?)=?
            ORDER BY owner LIMIT 1''', (len(SUFFIX), SUFFIX)).fetchone()
        require(row is not None, 'FXComponent unit absent; supply explicit --owner')
        selected = row[0]
    unit = db.execute('SELECT payload FROM units WHERE owner=?', (selected,)).fetchone()
    require(unit is not None, 'Explicit owner must identify a unit')
    used = len(unit[0].encode('utf-8'))
    require(used < limit, 'Unit descriptor exceeds fixture input ceiling')
    checksum = hashlib.sha256()
    checksum.update(encoded(['unit', selected, unit[0]]) + b'\n')
    nodes, edges = {}, set()
    for table, query in (
            ('node_facts', 'SELECT id,kind,label,metadata FROM node_facts WHERE owner=? ORDER BY id'),
            ('edge_facts', 'SELECT src,dst,kind,evidence FROM edge_facts WHERE owner=? ORDER BY src,dst,kind,evidence')):
        indexed_owner_query(db, table)
        for row in db.execute(query, (selected,)):
            raw = encoded(tuple(row))
            used += len(raw)
            require(used < limit, 'Selected owner exceeds fixture input ceiling; no fallback')
            checksum.update(encoded([table, tuple(row)]) + b'\n')
            if table == 'node_facts':
                key, kind, label, metadata = row
                require(key not in nodes, 'Duplicate selected node')
                nodes[key] = dict(kind=kind, label=label, metadata=json.loads(metadata))
            else:
                edges.add(tuple(row))
    require(bool(nodes), 'Selected owner has no node to edit')
    return selected, nodes, edges, dict(encoded_input_bytes=used,
        selected_rows_sha256=checksum.hexdigest(), unit_payload_sha256=hashlib.sha256(unit[0].encode()).hexdigest(),
        node_rows=len(nodes), edge_rows=len(edges), input_ceiling_bytes=limit)


def current_facts(db, owner):
    nodes = {key: dict(kind=kind, label=label, metadata=json.loads(metadata))
             for key, kind, label, metadata in db.execute(
                 'SELECT id,kind,label,metadata FROM node_facts WHERE owner=?', (owner,))}
    edges = {tuple(row) for row in db.execute('SELECT src,dst,kind,evidence FROM edge_facts WHERE owner=?', (owner,))}
    return nodes, edges


def measure(db, owner, nodes, edges, delta_path):
    delta = sqlite3.connect(delta_path)
    delta.row_factory = sqlite3.Row
    delta.execute('PRAGMA journal_mode=DELETE')
    delta.execute('PRAGMA synchronous=FULL')
    db.execute('BEGIN')
    delta.execute('BEGIN')
    budget = PublicationBudget()
    budget.preflight(journal_estimate_bytes=0, sqlite_write_estimate_bytes=0, rows=0, transfer_bytes=0)
    stage = IncrementalStage(db, budget)
    before = db.total_changes
    before_io = read_proc_write_bytes()
    start = time.monotonic()
    def delta_progress():
        try:
            budget.observe()
        except (BudgetExceeded, AccountingUnavailable):
            return 1
        return 0

    delta.set_progress_handler(delta_progress, 10000)
    try:
        with budget.sqlite_progress_guard(db, opcode_interval=10000):
            stage.replace_facts(owner, nodes, edges)
            counts = stage.finish(delta)
        # Both guards have completed their required precommit checks.
        db.commit()
        delta.commit()
        budget.observe([delta_path])
        actual_nodes, actual_edges = current_facts(db, owner)
        require(actual_nodes == nodes, 'Exact selected-owner node verification failed')
        require(actual_edges == edges, 'Exact unchanged edge verification failed')
        return dict(elapsed_seconds=time.monotonic() - start,
                    source_total_changes_delta=db.total_changes - before,
                    delta_total_changes=delta.total_changes,
                    process_write_bytes_delta=read_proc_write_bytes() - before_io,
                    journal_actual_bytes=delta_path.stat().st_size,
                    fixture_files_bytes={suffix or 'main': Path(str(db.execute('PRAGMA database_list').fetchone()[2]) + suffix).stat().st_size
                        for suffix in ('', '-wal', '-shm')
                        if Path(str(db.execute('PRAGMA database_list').fetchone()[2]) + suffix).exists()},
                    emitted_rows=counts, exact_nodes_verified=len(nodes),
                    exact_edges_verified=len(edges), budget=budget.receipt(), stage=stage.receipt())
    except BaseException:
        delta.set_progress_handler(None, 0)
        db.rollback()
        delta.rollback()
        raise
    finally:
        delta.set_progress_handler(None, 0)
        delta.close()


def run(source, out, owner=None, report_path=None):
    source = Path(source).resolve()
    out = Path(out).resolve()
    require(out.is_relative_to(ROOT / 'temp'), '--out must be beneath project temp/')
    require(source.is_file(), 'Explicit legacy baseline must exist')
    require(not out.exists(), '--out must be a new scratch directory')
    report_path = Path(report_path).resolve() if report_path else out / 'RESULT.json'
    require(report_path.is_relative_to(out), 'Report must stay inside --out')
    out.mkdir(parents=True)
    report = dict(version=1, source_baseline=str(source), synthetic_change=True,
                  scope='one selected owner only', caveats=[
                      'JSON payload bytes are not Bolt wire bytes; no Memgraph requests are made.',
                      'Process IO includes process-wide writes and deferred filesystem effects.',
                      'Owner-local check does not establish whole-graph migration/performance or shared-owner behavior.'])
    created = []
    db = None
    try:
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as baseline:
            baseline.execute('PRAGMA query_only=ON')
            baseline.execute('BEGIN')
            source_before = source_bindings(source)
            version_before = baseline.execute('PRAGMA data_version').fetchone()[0]
            owner, nodes, edges, binding = load_owner(baseline, owner)
            version_after = baseline.execute('PRAGMA data_version').fetchone()[0]
            source_after = source_bindings(source)
            report['source_read_snapshot'] = dict(before=source_before, after=source_after,
                data_version_before=version_before, data_version_after=version_after,
                uri_mode='ro', explicit_read_transaction=True)
            require(source_before == source_after and version_before == version_after,
                    'Source main/WAL bindings or data_version changed during selected reads')
            baseline.rollback()  # End read snapshot; never checkpoint the source.
        report.update(owner=owner, baseline=dict(**binding))
        store_path = out / 'fixture.sqlite'
        created.append(store_path)
        db = connect(store_path)
        import_before = read_proc_write_bytes()
        imported = CompactFacts(db).import_owner(owner, nodes, edges)
        db.commit()
        db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        report['import'] = dict(rows=imported, process_write_bytes_delta=read_proc_write_bytes() - import_before,
                                database_bytes=store_path.stat().st_size,
                                total_changes=db.total_changes)
        baseline_nodes, baseline_edges = current_facts(db, owner)
        require((baseline_nodes, baseline_edges) == (nodes, edges), 'Exact imported facts differ')
        edited = copy.deepcopy(nodes)
        selected_key = sorted(edited)[0]
        edited[selected_key]['label'] += ' [synthetic compact-update check]'
        edited[selected_key]['metadata']['synthetic_compact_update_check'] = True
        report['synthetic_node_id'] = selected_key
        results = {}
        for name, wanted, expected in [('noop', nodes, 0), ('edit', edited, 1), ('repeat_edit', edited, 0)]:
            delta_path = out / (name + '.sqlite')
            created.append(delta_path)
            results[name] = measure(db, owner, wanted, edges, delta_path)
            counts = results[name]['emitted_rows']
            require(counts == dict(nodes=expected, old_edges=0, new_edges=0, orphan_nodes=0),
                    'Unexpected emitted effects: ' + name)
            actual, actual_edges = current_facts(db, owner)
            require(actual_edges == baseline_edges, 'Other edges changed')
            require({k: v for k, v in actual.items() if k != selected_key} ==
                    {k: v for k, v in baseline_nodes.items() if k != selected_key}, 'Other nodes changed')
        report['measurements'] = results
        report['source_final_bindings'] = source_bindings(source)
        require(source_before == report['source_final_bindings'],
                'Source main/WAL bindings changed during check')
        report['passed'] = True
    except BaseException as exc:
        report.update(passed=False, error=type(exc).__name__ + ': ' + str(exc))
        raise
    finally:
        if db is not None:
            db.close()
        # Delete only files this invocation created; preserve the JSON report.
        removed = []
        for path in created:
            for suffix in ('', '-wal', '-shm', '-journal'):
                item = Path(str(path) + suffix)
                if item.exists():
                    item.unlink()
                    removed.append(item.name)
        report['scratch_databases_removed'] = removed
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--owner')
    parser.add_argument('--report')
    args = parser.parse_args()
    report = run(args.source, args.out, args.owner, args.report)
    print(json.dumps(dict(passed=report['passed'], owner=report['owner'], report=args.report or str(Path(args.out) / 'RESULT.json'))))


if __name__ == '__main__':
    main()
