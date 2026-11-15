"""V1 post-commit verification of immutable delta batches; no graph mutation here."""
import json
import re
from context_runtime import ContextError

VERSION = 1
PHASES = ('nodes', 'old_edges', 'new_edges', 'orphan_nodes')


def require_managed_type_labels(key, kind, labels):
    """Current compiler fallback kinds own Function/Data, not case annotations."""
    if key.startswith('compiler:') and kind in ('Function', 'Data'):
        if set(labels).intersection({'Function', 'Data'}) != {kind}:
            raise ContextError('Incompatible managed type labels: ' + key)


def verify_rows(session, phase, rows):
    """Read committed effects independently of apply_rows. Caller holds writer lock."""
    if phase not in PHASES:
        raise ContextError('Unknown verification phase')
    if not rows:
        return
    if phase == 'nodes':
        found = list(session.run('UNWIND $rows AS row OPTIONAL MATCH(n:Artifact {id:row.id}) '
            'RETURN row.id AS id, properties(n) AS props, labels(n) AS labels', rows=rows))
        expected = {r['id']: r for r in rows}
        if len(expected) != len(rows) or len(found) != len(rows):
            raise ContextError('Duplicate/missing verification node')
        seen = set()
        for item in found:
            key = item['id']; row = expected[key]; props = item['props']; meta = json.loads(row['metadata'])
            wanted = {k: row[k] for k in ('id', 'kind', 'label', 'metadata')}
            wanted.update(mangled=meta.get('mangled'), path=meta.get('path') or meta.get('source'))
            label = {'file': 'File', 'symbol': 'OriginalSymbol'}.get(row['kind'], row['kind'])
            if key in seen or props is None or any(props.get(k) != v for k, v in wanted.items()) or label not in item['labels']:
                raise ContextError('Committed node mismatch: ' + key)
            require_managed_type_labels(key, row['kind'], item['labels'])
            seen.add(key)
    elif phase in ('old_edges', 'new_edges'):
        for kind in sorted({r['kind'] for r in rows}):
            if not re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', kind):
                raise ContextError('Invalid verification relationship kind')
            selected = [r for r in rows if r['kind'] == kind]
            result = list(session.run('UNWIND $rows AS row OPTIONAL MATCH(s:Artifact {id:row.src})'
                '-[r:' + kind + ' {evidence:row.evidence}]->(d:Artifact {id:row.dst}) '
                'RETURN row.journal_row AS journal_row,count(r) AS n', rows=selected))
            wanted = 1 if phase == 'new_edges' else 0
            if len(result) != len(selected) or {r['journal_row'] for r in result} != {r['journal_row'] for r in selected} or any(r['n'] != wanted for r in result):
                raise ContextError('Committed edge mismatch: ' + kind)
    else:
        # Historical incident edges preserve an orphan node; disconnected nodes
        # and outgoing name matches must have been removed by the publisher.
        result = list(session.run('UNWIND $rows AS row OPTIONAL MATCH(n:Artifact {id:row.id}) '
            'OPTIONAL MATCH(n)-[r]-() RETURN row.id AS id, count(DISTINCT n) AS nodes, '
            'count(r) AS degree, sum(CASE WHEN type(r)="ENCODED_NAME_MATCH" AND startNode(r)=n THEN 1 ELSE 0 END) AS names', rows=rows))
        if len(result) != len(rows) or any(r['nodes'] > 1 or (r['nodes'] and not r['degree']) or r['names'] for r in result):
            raise ContextError('Committed orphan cleanup mismatch')


def verify_pending(session, database, checkpoint):
    record = session.run('MATCH(p:PublicationCheckpoint {id:$id}) RETURN p.contract_version AS version, '
        'p.commits AS commits,p.verified_commits AS verified,p.event_phase AS phase,'
        'p.event_start AS start,p.event_end AS end', id=checkpoint).single()
    if not record or record['version'] != VERSION:
        raise ContextError('Legacy checkpoint: finish with sealed legacy producer before migration')
    require_current(session, checkpoint)
    if record['verified'] == record['commits']:
        return None
    if record['verified'] != record['commits'] - 1 or record['phase'] not in PHASES:
        raise ContextError('Invalid event verification cursor')
    phase = record['phase']
    rows = [dict(r) for r in database.execute('SELECT rowid AS journal_row,* FROM ' + phase +
        ' WHERE rowid>? AND rowid<=? ORDER BY rowid', (record['start'], record['end']))]
    verify_rows(session, phase, rows)
    n = session.run('MATCH(p:PublicationCheckpoint {id:$id}) WHERE p.commits=$commit AND '
        'p.verified_commits=$previous SET p.verified_commits=$commit RETURN count(p) AS n',
        id=checkpoint, commit=record['commits'], previous=record['verified']).single()['n']
    if n != 1:
        raise ContextError('Verification checkpoint conflict')
    return {'contract_version': VERSION, 'event_id': checkpoint + ':' + str(record['commits']),
        'checkpoint': checkpoint, 'commit': record['commits'], 'phase': phase,
        'row_start_exclusive': record['start'], 'row_end_inclusive': record['end'],
        'rows': len(rows), 'state': 'verified', 'scope': 'committed_batch_effects'}


def require_verified(session, receipt, delta_path):
    """Admission gate: bind report to sealed journal and durable server receipt."""
    from context_runtime import sha
    digest = sha(delta_path)
    if receipt.get('verification_contract') != VERSION or receipt.get('verification_state') != 'verified' or receipt.get('delta_sha256') != digest or receipt.get('checkpoint') != 'source-delta:' + digest:
        raise ContextError('Invalid event admission receipt')
    p = session.run('MATCH(p:PublicationCheckpoint {id:$id}) RETURN properties(p) AS p', id=receipt['checkpoint']).single()
    if not p:
        raise ContextError('Missing event admission checkpoint')
    require_current(session, receipt['checkpoint'])
    p = p['p']
    if p.get('contract_version') != VERSION or p.get('digest') != digest or p.get('batch_size') != receipt.get('batch_size') or p.get('phase') != len(PHASES) or p.get('last_row') != 0 or p.get('commits', 0) < len(PHASES) or p.get('verified_commits') != p.get('commits'):
        raise ContextError('Unverified publication cannot be registered')


def require_current(session, checkpoint):
    rows = list(session.run('MATCH(g:ContextGeneration {id:"active"}) RETURN g.publication_checkpoint AS checkpoint'))
    if len(rows) != 1 or rows[0]['checkpoint'] != checkpoint:
        raise ContextError('Publication is not the current generation transition')
