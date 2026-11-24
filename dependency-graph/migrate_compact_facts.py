"""Explicit one-time legacy normalization into one reviewed replacement file.

Caller must hold the project context/writer lock and retain its VM snapshot.
This tool never switches paths, mutates source rows or retries numbered outputs.
A failed destination remains in place for operator inspection.
"""
import hashlib
import itertools
import json
import os
import pathlib
import sqlite3
import time

from compact_facts import CompactFacts
from refresh_facts import connect


class MigrationError(ValueError):
    pass


def _binding(path):
    result = {}
    for suffix in ('', '-wal'):
        candidate = pathlib.Path(str(path) + suffix)
        if candidate.exists():
            stat = candidate.stat()
            result[suffix or 'main'] = dict(device=stat.st_dev, inode=stat.st_ino,
                                            bytes=stat.st_size, mtime_ns=stat.st_mtime_ns)
    return result


def _io():
    try:
        return {key: int(value) for key, value in
                (line.split(':', 1) for line in pathlib.Path('/proc/self/io').read_text().splitlines())}
    except (OSError, ValueError):
        return None


def _decoded(text):
    return json.dumps(json.loads(text), sort_keys=True, separators=(',', ':'))


def _verify_owner(source, destination, owner):
    """Independent ordered cursor comparison; retain at most one row per side."""
    queries = [('nodes', 'SELECT id,kind,label,metadata FROM node_facts WHERE owner=? ORDER BY id'),
               ('edges', 'SELECT src,dst,kind,evidence FROM edge_facts WHERE owner=? ORDER BY src,dst,kind,evidence')]
    counts = {}
    absent = object()
    for category, query in queries:
        count = 0
        for before, after in itertools.zip_longest(source.execute(query, (owner,)),
                                                   destination.execute(query, (owner,)), fillvalue=absent):
            if before is absent or after is absent:
                raise MigrationError('Owner fact count differs: ' + owner + ':' + category)
            if category == 'nodes':
                before = (*before[:3], _decoded(before[3]))
                after = (*after[:3], _decoded(after[3]))
            if before != after:
                raise MigrationError('Owner facts differ: ' + owner + ':' + category)
            count += 1
        counts[category] = count
    return counts


def _unit(source, owner):
    row = source.execute('SELECT payload FROM units WHERE owner=?', (owner,)).fetchone()
    current = source.execute('SELECT observation_id FROM current_observations WHERE owner=?', (owner,)).fetchone()
    if row is None and current is None:
        return None
    if row is None or current is None:
        raise MigrationError('Unit/current observation binding absent: ' + owner)
    observation = source.execute('SELECT owner,payload FROM observations WHERE id=?', current).fetchone()
    if observation is None or observation[0] != owner:
        raise MigrationError('Current observation identity/owner differs: ' + owner)
    payload, observed = json.loads(row[0]), json.loads(observation[1])
    if not isinstance(payload, dict) or not isinstance(observed, dict):
        raise MigrationError('Unit observation payload is not an object: ' + owner)
    if any(key not in observed or _decoded(json.dumps(value)) != _decoded(json.dumps(observed[key]))
           for key, value in payload.items()):
        raise MigrationError('Current observation does not bind current unit: ' + owner)
    return current[0], row[0]


def _checkpoint(db):
    db.commit()
    if db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0] != 0:
        raise MigrationError('Replacement WAL checkpoint blocked')


def migrate(source, destination, report, *, progress=None):
    """Normalize once, verify, and return a receipt; never rename/switch files.

    A mutation-denied read/write lock holder uses BEGIN IMMEDIATE to reject an
    active source writer and exclude new writers through verification. A separate
    read-only connection owns the read snapshot. SQLite sidecar housekeeping may
    occur, but source logical rows are never written. The caller must also hold
    the external lock. A data_version and main/WAL binding guard detects
    changes. Per-owner destination commits/checkpoints bound temporary WAL size;
    the replacement is usable only after the successful receipt is reviewed.
    """
    from production_write_stop import require_graph_storage_write
    require_graph_storage_write(source)
    require_graph_storage_write(destination)
    source, destination, report = (pathlib.Path(value).resolve() for value in (source, destination, report))
    if len({source, destination, report}) != 3:
        raise MigrationError('Source, destination and report must be different paths')
    for path in (destination, report):
        if path.exists():
            raise FileExistsError('Refusing existing one-time output: ' + str(path))
    for suffix in ('-wal', '-shm', '-journal'):
        if pathlib.Path(str(destination) + suffix).exists():
            raise FileExistsError('Replacement SQLite sidecar already exists')
    journal = pathlib.Path(str(source) + '-journal')
    if journal.exists() and journal.stat().st_size:
        raise MigrationError('Source has a nonempty rollback journal; resolve it before migration')
    start, io_start = time.perf_counter(), _io()
    receipt = {'version': 1, 'status': 'failed', 'scope': 'explicit_one_time_current_facts_normalization',
               'source': str(source), 'destination': str(destination),
               'external_context_lock_required': True, 'automatic_cutover': False,
               'history_copied': False, 'source_rows_mutated': False,
               'source_lock': 'mutation-denied RW BEGIN IMMEDIATE plus read-only snapshot',
               'source_sqlite_sidecar_housekeeping_permitted': True,
               'source_before_open_binding': _binding(source)}
    src = dst = lock_holder = None
    report_handle = None
    try:
        lock_holder = sqlite3.connect(source.as_uri() + '?mode=rw', uri=True, timeout=0)
        if hasattr(lock_holder, 'setconfig') and hasattr(sqlite3, 'SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE'):
            lock_holder.setconfig(sqlite3.SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE, True)
        # Let SQLite enforce its own WAL/rollback writer lock, while an
        # authorizer forbids DML/DDL and any other SQL on this lock-only handle.
        lock_holder.set_authorizer(lambda action, *args: sqlite3.SQLITE_OK
                                   if action == sqlite3.SQLITE_TRANSACTION else sqlite3.SQLITE_DENY)
        try:
            lock_holder.execute('BEGIN IMMEDIATE')
        except sqlite3.OperationalError as error:
            raise MigrationError('Source has an active writer or cannot provide a stable read transaction') from error
        src = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=0)
        src.execute('BEGIN')
        if src.execute("SELECT 1 FROM meta WHERE key='pending'").fetchone():
            raise MigrationError('Pending publication journal must be resolved explicitly')
        if not src.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='node_facts'").fetchone():
            raise MigrationError('Source is not the legacy backing-table store')
        source_binding = _binding(source)
        data_version = src.execute('PRAGMA data_version').fetchone()[0]
        receipt['source_binding'] = source_binding
        receipt['source_data_version'] = data_version
        # O_EXCL prevents silently reusing even an empty earlier replacement.
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        report_handle = report.open('x')
        dst = connect(destination)
        dst.executemany('INSERT INTO meta(key,value) VALUES(?,?)', src.execute('SELECT key,value FROM meta ORDER BY key'))
        store = CompactFacts(dst)
        owners = src.execute('''SELECT owner FROM node_facts UNION SELECT owner FROM edge_facts
            UNION SELECT owner FROM units UNION SELECT owner FROM current_observations ORDER BY owner''')
        counts = {'owners': 0, 'nodes': 0, 'edges': 0, 'units': 0}
        unit_binding = hashlib.sha256()
        for (owner,) in owners:
            nodes = ((key, {'kind': kind, 'label': label, 'metadata': json.loads(metadata)})
                     for key, kind, label, metadata in src.execute(
                         'SELECT id,kind,label,metadata FROM node_facts WHERE owner=?', (owner,)))
            edges = src.execute('SELECT src,dst,kind,evidence FROM edge_facts WHERE owner=?', (owner,))
            store.import_owner(owner, nodes, edges)  # No support snapshots or graph delta.
            unit = _unit(src, owner)
            if unit:
                dst.execute('INSERT INTO unit_observations(owner,observation_id,payload) VALUES(?,?,?)', (owner, *unit))
                unit_binding.update(json.dumps([owner, unit[0], _decoded(unit[1])], separators=(',', ':')).encode())
                unit_binding.update(b'\n')
                counts['units'] += 1
            _checkpoint(dst)
            verified = _verify_owner(src, dst, owner)
            counts['owners'] += 1
            counts['nodes'] += verified['nodes']
            counts['edges'] += verified['edges']
            if progress is not None:
                progress(dict(counts, destination_bytes=destination.stat().st_size,
                              elapsed_seconds=time.perf_counter() - start))
        for table, key in (('node_facts', 'nodes'), ('edge_facts', 'edges'), ('units', 'units'),
                           ('current_observations', 'units')):
            before = src.execute('SELECT count(*) FROM ' + table).fetchone()[0]
            after = dst.execute('SELECT count(*) FROM ' + table).fetchone()[0]
            if before != counts[key] or before != after:
                raise MigrationError('Global count mismatch: ' + table)
        for before, after in itertools.zip_longest(src.execute('SELECT owner,payload FROM units ORDER BY owner'),
                                                   dst.execute('SELECT owner,payload FROM units ORDER BY owner')):
            if before != after:
                raise MigrationError('Exact current unit payload binding differs')
        for table, columns in (('current_observations', 'owner,observation_id'), ('meta', 'key,value')):
            for before, after in itertools.zip_longest(src.execute(f'SELECT {columns} FROM {table} ORDER BY 1'),
                                                       dst.execute(f'SELECT {columns} FROM {table} ORDER BY 1')):
                if before != after:
                    raise MigrationError('Current source binding differs: ' + table)
        if dst.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
            raise MigrationError('Replacement quick_check failed')
        if dst.execute('PRAGMA foreign_key_check').fetchone() is not None:
            raise MigrationError('Replacement foreign_key_check failed')
        _checkpoint(dst)
        if src.execute('PRAGMA data_version').fetchone()[0] != data_version or _binding(source) != source_binding:
            raise MigrationError('Source binding/data_version changed during migration')
        receipt.update(status='verified', counts=counts, current_unit_binding_sha256=unit_binding.hexdigest(),
                       source_bytes=source_binding['main']['bytes'],
                       source_wal_bytes=source_binding.get('-wal', {}).get('bytes', 0),
                       destination_bytes=destination.stat().st_size,
                       destination_checks={'quick_check': 'ok', 'foreign_key_check': 'ok'},
                       destination_observations=dst.execute('SELECT count(*) FROM observations').fetchone()[0])
        return receipt
    except BaseException as error:
        receipt['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        if dst is not None:
            dst.close()
        if src is not None:
            src.rollback()
            src.close()
        if lock_holder is not None:
            lock_holder.rollback()
            lock_holder.close()
        receipt['source_after_close_binding'] = _binding(source)
        receipt['elapsed_seconds'] = time.perf_counter() - start
        io_end = _io()
        receipt['process_io_delta'] = ({key: value - io_start.get(key, 0) for key, value in io_end.items()}
                                       if io_start is not None and io_end is not None else None)
        if report_handle is not None:
            json.dump(receipt, report_handle, indent=2, sort_keys=True)
            report_handle.write('\n')
            report_handle.flush()
            os.fsync(report_handle.fileno())
            report_handle.close()
