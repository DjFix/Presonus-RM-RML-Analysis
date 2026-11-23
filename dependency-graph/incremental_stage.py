"""Owner-level compact staging; callers own BEGIN, rollback, commit and IO guard.

Only changed memberships/observation payloads contribute to estimates. Estimates
reserve encoded payload plus deliberately generous index/page overhead; they are
not physical-write guarantees. NetChanges retains merged values; pruning retains only touched IDs. No operational database or backup is opened by this module.
"""
import json
from pathlib import Path
from compact_facts import CompactFacts, PruneCandidates
from incremental_delta import NetChanges
from code_identity import VERSION, digest
from context_runtime import sha


def encoded(value):
    return len(json.dumps(value, sort_keys=True, ensure_ascii=False).encode('utf-8'))


def delta_reserve(connection, node_keys, plan):
    """Keep old cost unless this is the verified empty on-disk DELETE DB.

    Estimates remain estimates. Existing actual physical-I/O, file/sidecar,
    rows, wire and deferred-commit guards must remain in force.
    """
    database = next((row[2] for row in connection.execute('PRAGMA database_list')
                     if row[1] == 'main'), '')
    lengths = (len(key.encode('utf-8')) for key in node_keys)
    index_key_bytes = 0
    short_keys = True
    for length in lengths:
        index_key_bytes += length
        short_keys &= length <= 768
    fresh_db = bool(connection.in_transaction and database
                 and connection.execute('PRAGMA main.journal_mode').fetchone()[0] == 'delete'
                 and connection.execute('PRAGMA main.page_size').fetchone()[0] == 4096
                 and connection.execute('PRAGMA main.page_count').fetchone()[0] == 0
                 and not connection.execute('SELECT 1 FROM main.sqlite_schema LIMIT 1').fetchone()
                 and Path(database).is_file() and Path(database).stat().st_size == 0)
    fresh = fresh_db and short_keys
    index_keys = index_key_bytes if fresh else 0
    # changed_nodes(id TEXT PRIMARY KEY) stores a second copy of each full ID
    # in sqlite_autoindex_changed_nodes_1. Other delta indexes have integer keys;
    # retain the existing per-row/page/index reserve for them unchanged.
    payload_copies = 1 if fresh else 2
    journal = 32768 + plan['payload_bytes'] * payload_copies + index_keys + plan['rows'] * 128
    return dict(journal_estimate_bytes=journal, sqlite_write_estimate_bytes=2 * journal,
                storage_case='fresh_empty_delete' if fresh else 'conservative_old_state',
                fresh_empty_delete_database=fresh_db,
                additional_primary_key_index_bytes=index_keys,
                interpretation='No old delta row population exists in verified fresh DB; not a physical-write guarantee')


class IncrementalStage:
    def __init__(self, c, budget, *, bounded=False):
        self.c = c
        self.budget = budget
        self.store = CompactFacts(c)
        self.bounded = bounded
        if bounded:
            from bounded_net_changes import BoundedNetChanges
            from compact_identity_bitmap import IdentityBitmap
            self.prune_candidates = PruneCandidates(
                nodes=IdentityBitmap(), values=IdentityBitmap(), observations=IdentityBitmap())
            self.net = BoundedNetChanges(c, self.prune_candidates)
        else:
            self.prune_candidates = PruneCandidates()
            self.net = NetChanges()
        self.costs = []
        self.finished = False
        self.failure = None
        self.actual_storage_rows = 0
        self.actual_delta_rows = 0
        self.totals = dict(changed_nodes=0, changed_edges=0, observation_updates=0,
                           encoded_changed_bytes=0, journal_estimate_bytes=0,
                           sqlite_write_estimate_bytes=0, rows=0, transfer_estimate_bytes=0)

    def close(self):
        if self.bounded:
            self.net.close()

    def _active(self):
        if self.finished:
            raise RuntimeError('Incremental stage already finished')
        if not self.c.in_transaction:
            raise RuntimeError('Caller must BEGIN before incremental staging')

    def _preview(self, owner, nodes, edges, observation=None, remove=False):
        self._active()
        old_nodes = {key: (kind, label, metadata) for key, kind, label, metadata in self.c.execute(
            'SELECT id,kind,label,metadata FROM node_facts WHERE owner=?', (owner,))}
        new_nodes = {key: (node['kind'], node['label'], json.dumps(node['metadata'], sort_keys=True))
                     for key, node in nodes.items()}
        old_edges = {tuple(row) for row in self.c.execute('SELECT src,dst,kind,evidence FROM edge_facts WHERE owner=?', (owner,))}
        changed_nodes = {key for key in old_nodes.keys() | new_nodes.keys()
                         if old_nodes.get(key) != new_nodes.get(key)}
        changed_edges = old_edges ^ edges
        values = []
        for key in changed_nodes & new_nodes.keys():
            # Preserve early kind-conflict validation without expanding every
            # other owner's metadata. API writes enforce homogeneous kinds.
            existing = self.c.execute('SELECT kind FROM node_facts WHERE id=? AND owner<>? LIMIT 1',
                                      (key, owner)).fetchone()
            if existing is not None and existing[0] != new_nodes[key][0]:
                raise ValueError('Conflicting node kinds for ' + key)
        old_observation = None
        updates = 0
        if observation is not None or remove:
            old_observation = self.c.execute('SELECT observation_id,payload FROM unit_observations WHERE owner=?', (owner,)).fetchone()
            old_observation = tuple(old_observation) if old_observation is not None else None
            updates = int(old_observation != observation)
            if updates:
                values.append((owner, old_observation, observation))
        storage_plan = self.store.plan_owner_rows(owner, nodes, edges, changed_nodes, changed_edges)
        byte_count = storage_plan['payload_bytes'] + sum(encoded(value) for value in values)
        operations = storage_plan['rows'] + updates
        cost = dict(owner=owner, changed_nodes=len(changed_nodes), changed_edges=len(changed_edges),
                    observation_updates=updates, encoded_changed_bytes=byte_count,
                    journal_estimate_bytes=byte_count * 2 + operations * 128 + (4096 if operations else 0),
                    sqlite_write_estimate_bytes=byte_count * 4 + operations * 256 + (8192 if operations else 0),
                    rows=operations, transfer_estimate_bytes=0,
                    storage_row_plan=storage_plan)
        self._reserve(cost)
        return cost

    def _reserve(self, cost):
        projected = {key: self.totals[key] + cost[key] for key in self.totals}
        # Check every cumulative ceiling before charging rows or mutating facts.
        attempted = dict(journal_estimate_bytes=projected['journal_estimate_bytes'],
                         sqlite_write_estimate_bytes=projected['sqlite_write_estimate_bytes'],
                         rows=max(self.budget.rows + cost['rows'], projected['rows']),
                         transfer_bytes=projected['transfer_estimate_bytes'])
        try:
            self.budget.preflight(**attempted)
            self.budget.charge_rows(cost['rows'])
        except Exception as error:
            # Retain the rejected owner and its complete projection even when
            # preflight refuses before PublicationBudget stores its estimates.
            self.failure = dict(owner=cost['owner'], cost=dict(cost),
                                previous_totals=dict(self.totals),
                                projected_totals=projected, preflight=attempted,
                                storage_rows_before=self.c.total_changes,
                                error=str(error), mutation_started=False)
            if self.budget.failure:
                self.budget.failure += '; incremental_stage=' + json.dumps(self.failure, sort_keys=True)
            raise
        self.totals = projected
        self.costs.append(cost)

    def _replace(self, owner, nodes, edges, observation=None, remove=False):
        edges = set(map(tuple, edges))
        cost = self._preview(owner, nodes, edges, observation, remove)
        before_rows = self.c.total_changes
        changes = self.store.replace_owner(owner, nodes, edges,
                                           merged='touched' if self.bounded else True, savepoint=False)
        if remove:
            self.c.execute('DELETE FROM unit_observations WHERE owner=?', (owner,))
        elif observation is not None and cost['observation_updates']:
            self.c.execute('''INSERT INTO unit_observations(owner,observation_id,payload) VALUES(?,?,?)
                ON CONFLICT(owner) DO UPDATE SET observation_id=excluded.observation_id,payload=excluded.payload''',
                (owner, *observation))
        cost['actual_storage_mutation_rows'] = self.c.total_changes - before_rows
        self.actual_storage_rows += cost['actual_storage_mutation_rows']
        if cost['actual_storage_mutation_rows'] != cost['rows']:
            self.c.rollback()
            raise ValueError('Storage row plan changed for ' + owner)
        if self.bounded:
            self.prune_candidates.add(changes)
        else:
            self.net.add_merged(changes)
            self.prune_candidates.add(changes.prune)
        return changes

    def rekey_owner(self, old, new):
        self._active()
        if not self.bounded or old == new or self.c.execute(
                'SELECT 1 FROM compact_owners WHERE value=? UNION ALL SELECT 1 FROM unit_observations WHERE owner=?',
                (new, new)).fetchone():
            raise ValueError('Rekey requires an unused new identity in bounded staging')
        identity, = self.c.execute('SELECT owner_id FROM compact_owners WHERE value=?', (old,)).fetchone()
        old_observation, payload = self.c.execute(
            'SELECT observation_id,payload FROM unit_observations WHERE owner=?', (old,)).fetchone()
        # Common memberships survive the rename, but all old nodes must be
        # checked for changed owner-lexical merge precedence.
        self.prune_candidates.nodes.update(row[0] for row in self.c.execute(
            'SELECT node_id FROM compact_node_memberships WHERE owner_id=?', (identity,)))
        payload_bytes = encoded((old, new, old_observation, payload))
        cost = dict(owner=old, new_owner=new, observation_updates=1, changed_nodes=0, changed_edges=0,
                    encoded_changed_bytes=payload_bytes, journal_estimate_bytes=2 * payload_bytes + 8192,
                    sqlite_write_estimate_bytes=4 * payload_bytes + 16384, rows=2, transfer_estimate_bytes=0)
        self._reserve(cost)
        before = self.c.total_changes
        self.c.execute('UPDATE compact_owners SET value=? WHERE owner_id=? AND value=?', (new, identity, old))
        self.c.execute('DELETE FROM unit_observations WHERE owner=?', (old,))
        exposed = self.c.total_changes - before
        if exposed != cost['rows']:
            raise ValueError(f'Owner rekey row plan changed: {old}')
        self.actual_storage_rows += exposed
        cost['actual_storage_mutation_rows'] = exposed
        return old_observation

    def replace_facts(self, owner, nodes, edges):
        return self._replace(owner, nodes, edges)

    def replace_unit(self, owner, row, nodes, edges, inputs, ast, gcc, external_inputs=None):
        payload = dict(command=row, inputs=inputs, ast=str(ast), gcc=str(gcc),
                       ast_sha256=sha(ast), gcc_sha256=sha(gcc))
        if external_inputs is not None:
            payload['external_inputs'] = external_inputs
        observation = (digest(dict(payload, owner=owner, identity_version=VERSION)),
                       json.dumps(payload, sort_keys=True))
        return self._replace(owner, nodes, edges, observation)

    def remove_owner(self, owner):
        return self._replace(owner, {}, (), remove=True)

    def finish(self, delta_db):
        self._active()
        if delta_db is self.c:
            raise ValueError('Delta requires a separate caller-owned connection')
        if not delta_db.in_transaction:
            raise RuntimeError('Caller must BEGIN on delta connection')
        # Fixed byte overhead plus exact logical delta rows, before DDL/inserts.
        delta_plan = self.net.plan()
        reserve = delta_reserve(delta_db, self.net.nodes, delta_plan)
        delta_plan['storage_reserve'] = reserve
        base = dict(owner='@delta-schema', changed_nodes=0, changed_edges=0,
                    observation_updates=0, encoded_changed_bytes=delta_plan['payload_bytes'],
                    journal_estimate_bytes=reserve['journal_estimate_bytes'],
                    sqlite_write_estimate_bytes=reserve['sqlite_write_estimate_bytes'],
                    rows=delta_plan['rows'], transfer_estimate_bytes=delta_plan['graph_payload_bytes'], delta_row_plan=delta_plan)
        self._reserve(base)
        before_delta = delta_db.total_changes
        counts = self.net.write(delta_db)
        self.actual_delta_rows = delta_db.total_changes - before_delta
        if self.actual_delta_rows != base['rows']:
            self.c.rollback()
            delta_db.rollback()
            raise ValueError('Delta row plan changed')
        from batch_publication import request_forecast
        # Read the same uncommitted journal; no DB copy, second serializer,
        # extra mutation charge, server request or checkpoint hash is required.
        # Placeholder digest has exactly the future SHA256 string envelope size.
        previous_row_factory = delta_db.row_factory
        try:
            delta_db.row_factory = __import__('sqlite3').Row
            wire_plan = request_forecast(delta_db)
        finally:
            delta_db.row_factory = previous_row_factory
        delta_plan['request_forecast'] = wire_plan
        self._reserve(dict(owner='@exact-transfer-plan', changed_nodes=0,
                           changed_edges=0, observation_updates=0,
                           encoded_changed_bytes=0, journal_estimate_bytes=0,
                           sqlite_write_estimate_bytes=0, rows=0,
                           transfer_estimate_bytes=wire_plan['json_request_estimate_bytes']
                           - base['transfer_estimate_bytes']))
        before_prune = self.c.total_changes
        def reserve_prune(table, rows, payload_bytes):
            self._reserve(dict(owner='@prune:' + table, changed_nodes=0, changed_edges=0,
                               observation_updates=0, encoded_changed_bytes=payload_bytes,
                               journal_estimate_bytes=payload_bytes * 2 + rows * 128,
                               sqlite_write_estimate_bytes=payload_bytes * 4 + rows * 256,
                               rows=rows, transfer_estimate_bytes=0))
        try:
            self.pruned = self.store.prune_unreferenced(
                self.prune_candidates, reserve_prune, max_batch=1024 if self.bounded else None)

        except BaseException:
            self.c.rollback()
            delta_db.rollback()
            raise
        self.actual_prune_rows = self.c.total_changes - before_prune
        if self.actual_prune_rows != sum(self.pruned.values()):
            self.c.rollback()
            delta_db.rollback()
            raise ValueError('Prune row plan changed')
        self.finished = True
        # Set only AFTER successful exact delta writes and prune row accounting.
        self.budget.completed_stage_estimate = dict(
            complete=True, estimates=dict(self.budget.estimates))
        return counts

    def receipt(self):
        return dict(version=1, finished=self.finished, totals=dict(self.totals),
                    owners=list(self.costs), pruned=getattr(self, 'pruned', None),
                    rejected_owner=self.failure,
                    actual_mutation_rows=dict(storage=self.actual_storage_rows,
                                              delta=self.actual_delta_rows,
                                              prune=getattr(self, 'actual_prune_rows', 0)),
                    uncertainty='Logical mutation rows are planned exactly and verified against SQLite total_changes; encoded payload/index/page byte reserves are conservative estimates, not physical-write guarantees. Caller must use SQLite progress/IO guard.')
