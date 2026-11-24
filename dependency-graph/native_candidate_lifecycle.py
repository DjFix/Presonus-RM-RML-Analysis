"""Bounded, certified native links after the immutable v1 source publication.

Caller holds the existing writer lock through registration. Unknown historical
links are retained verbatim. No full native rebuild or source journal edit.
"""
import json
import pathlib
import sqlite3
from native_candidate_ownership import pack_guard, unpack_guard
from native_candidate_guard_v3 import CODECS as BOUNDED_GUARD_CODECS
from collections import Counter
from context_runtime import ContextError, sha
from native_candidate_ownership import (BASIS, OWNER, canonical, checkpoint_id, claims_ownership,
    digest, owned_properties, read_checkpoint, validate_owned_edge, OwnershipVerification, canonical_matches)


def scope_edges(session, ids):
    from native_candidate_gate import incoming_edges
    return sorted([{'src': row['src'], 'dst': row['dst'], 'properties': dict(row['props'])}
                   for row in incoming_edges(session, ids)], key=canonical)


def orphan_snapshots(session, identities):
    """One physical-identity inventory, then bounded Artifact-indexed reads."""
    from native_candidate_gate import BATCH_SIZE, endpoint_inventory
    identities = list(identities)
    if len(identities) != len(set(identities)):
        raise ContextError('Duplicate lifecycle orphan scope')
    inventory = endpoint_inventory(session, identities)
    observed = {}
    for offset in range(0, len(identities), BATCH_SIZE):
        part = identities[offset:offset + BATCH_SIZE]
        if any(inventory.get(key, 0) > 1 for key in part):
            raise ContextError('Duplicate lifecycle orphan identity')
        for row in session.run('UNWIND $ids AS key MATCH(n:Artifact {id:key}) '
                'OPTIONAL MATCH(n)-[r]-() RETURN n.id AS identity, '
                'id(n) AS physical,properties(n) AS props,labels(n) AS labels,count(r) AS degree', ids=part):
            key = row['identity']
            if key not in part or key in observed or inventory.get(key, 0) != 1:
                raise ContextError('Duplicate/inconsistent lifecycle orphan identity')
            if 'Artifact' not in row['labels']:
                raise ContextError('Lifecycle orphan is not an Artifact')
            observed[key] = ({'id': key, 'node': {'properties': dict(row['props']),
                             'labels': sorted(row['labels'])}}, row['degree'])
        for key in part:
            if inventory.get(key, 0) and key not in observed:
                raise ContextError('Lifecycle orphan is not an Artifact')
    return [observed.get(key, ({'id': key, 'node': None}, None)) for key in identities]


def source_complete(session, delta_sha):
    rows = list(session.run('MATCH(g:ContextGeneration {id:"active"}),(p:PublicationCheckpoint {id:$id}) '
        'RETURN g.publication_checkpoint AS current,p.phase AS phase,p.last_row AS last_row,'
        'p.commits AS commits,p.verified_commits AS verified,p.contract_version AS version', id='source-delta:'+delta_sha))
    if len(rows) != 1 or rows[0]['current'] != 'source-delta:'+delta_sha or rows[0]['phase'] != 4 or rows[0]['last_row'] != 0 or rows[0]['version'] != 1 or rows[0]['commits'] < 4 or rows[0]['verified'] != rows[0]['commits']:
        raise ContextError('Lifecycle requires current completed verified source publication')


def refuse_other_pending(session, identity):
    rows = list(session.run('MATCH(p:NativeCandidateCheckpoint) WHERE p.id<>$id '
        'AND (p.owner=$owner OR p.id STARTS WITH "native-candidates:") '
        'AND (p.state IS NULL OR p.state<>"verified") RETURN properties(p) AS p',
        id=identity, owner=OWNER))
    if rows:
        raise ContextError('Another native candidate lifecycle checkpoint remains unverified')


def verify_scope(session, root, delta_path, seal, checkpoint, allow_committed=False):
    seal = unpack_guard(seal)
    from native_candidate_gate import verify_guard_inputs
    verify_guard_inputs(session, root, delta_path, seal)
    delta_sha = sha(delta_path)
    source_complete(session, delta_sha)
    p, before, after, decoded_seal = read_checkpoint(session, checkpoint, include_seal=True)
    verification = OwnershipVerification(session)
    verification.add(checkpoint, p, before, after, decoded_seal)
    del decoded_seal
    if p['source_delta_sha256'] != delta_sha or p['seal_sha256'] != seal['seal_sha256'] or p['native_generation'] != seal['native']['sha256'] or not canonical_matches(p['seal_json'], seal):
        raise ContextError('Lifecycle checkpoint binding mismatch')
    if p['state'] != 'verified' and not allow_committed:
        raise ContextError('Lifecycle checkpoint remains unverified')
    actual = scope_edges(session, seal['affected_ids'])
    if Counter(map(canonical, actual)) != Counter(map(canonical, after)):
        raise ContextError('Lifecycle after-scope differs from committed journal')
    for row in after:
        if claims_ownership(row['properties']):
            validate_owned_edge(session, row['src'], row['dst'], row['properties'], p['native_generation'],
                                allow_committed=checkpoint if allow_committed else None, verification=verification)
    wanted_orphans = json.loads(p['orphan_after_json'])
    observed_orphans = orphan_snapshots(session, (wanted['id'] for wanted in wanted_orphans))
    if [snapshot for snapshot, _ in observed_orphans] != wanted_orphans:
        raise ContextError('Lifecycle deferred orphan after-state mismatch')
    verify_guard_inputs(session, root, delta_path, seal)
    return p


def receipt_for(p):
    return {'version': 1, 'verified': True, 'checkpoint': p['id'],
            'source_delta_sha256': p['source_delta_sha256'], 'seal_sha256': p['seal_sha256'],
            'native_generation': p['native_generation'], 'journal_sha256': p['journal_sha256'],
            'scope': 'affected_candidate_multiset_and_explicit_deferred_orphans',
            'unknown_history': 'preserved; not adopted', 'untouched_join_verified': False}


def require_lifecycle(session, root, delta_path, seal, receipt):
    seal = unpack_guard(seal)
    if (not isinstance(seal, dict) or not isinstance(seal.get('seal_sha256'), str) or
            not isinstance(seal.get('native'), dict) or not isinstance(seal['native'].get('sha256'), str)):
        raise ContextError('Missing native candidate lifecycle seal')
    if not isinstance(receipt, dict):
        raise ContextError('Missing native candidate lifecycle receipt')
    identity = checkpoint_id(sha(delta_path), seal['seal_sha256'], seal['native']['sha256'])
    p = verify_scope(session, root, delta_path, seal, identity)
    expected = receipt_for(p)
    if receipt != expected:
        raise ContextError('Invalid native candidate lifecycle receipt')
    return expected


def reconcile(session, root, delta_path, seal, stop_after_commit=False):
    from production_write_stop import require_graph_updates
    require_graph_updates(root)
    from native_candidate_gate import verify_guard_inputs
    root = pathlib.Path(root).resolve()
    packed = seal if isinstance(seal, dict) and seal.get('guard_codec') in BOUNDED_GUARD_CODECS else None
    seal = unpack_guard(seal)
    verify_guard_inputs(session, root, delta_path, seal)
    delta_sha = sha(delta_path)
    source_complete(session, delta_sha)
    generation = seal['native']['sha256']
    identity = checkpoint_id(delta_sha, seal['seal_sha256'], generation)
    refuse_other_pending(session, identity)
    existing = list(session.run('MATCH(p:NativeCandidateCheckpoint {id:$id}) RETURN properties(p) AS p', id=identity))
    if not existing:
        with sqlite3.connect(pathlib.Path(delta_path).resolve().as_uri()+'?mode=ro&immutable=1', uri=True) as delta:
            orphan_ids = sorted(r[0] for r in delta.execute('SELECT id FROM orphan_nodes'))
        if len(orphan_ids) != len(set(orphan_ids)) or not set(orphan_ids) <= set(seal['affected_ids']) or set(orphan_ids) & {s['properties']['id'] for s in seal['sources']}:
            raise ContextError('Invalid sealed deferred orphan scope')
        with session.begin_transaction() as tx:
            source_complete(tx, delta_sha)
            refuse_other_pending(tx, identity)
            verify_guard_inputs(tx, root, delta_path, seal)
            before = scope_edges(tx, seal['affected_ids'])
            desired = {(e['src'], e['dst']) for e in seal['expected']}
            remove = []
            verification = OwnershipVerification(tx)
            certified_native = {}
            owned_destinations = {}
            for row in before:
                if claims_ownership(row['properties']):
                    validate_owned_edge(tx, row['src'], row['dst'], row['properties'], generation,
                                        verification=verification)
                    owned_destinations[row['dst']] = {'id': row['dst']}
                    cert, cert_seal, _, _, _ = verification.read(row['properties']['candidate_created_by'])
                    native = cert_seal[row['src']]
                    if row['src'] in certified_native and canonical(certified_native[row['src']]) != canonical(native):
                        raise ContextError('Conflicting certified native endpoint snapshots')
                    certified_native[row['src']] = native
                    if (row['src'], row['dst']) not in desired:
                        remove.append(row)
            from native_candidate_gate import endpoint_batch, endpoint_inventory
            inventory = endpoint_inventory(tx, set(owned_destinations) | set(certified_native))
            endpoint_batch(tx, owned_destinations.values(), ('Artifact',), inventory)
            endpoint_batch(tx, certified_native.values(), ('NativeArtifact',), inventory)
            after = list(before)
            for row in remove:
                result = tx.run('MATCH(n {id:$src})-[r:NATIVE_SOURCE_CANDIDATE]->(f {id:$dst}) '
                    'WHERE properties(r)=$props DELETE r RETURN count(r) AS n', src=row['src'], dst=row['dst'], props=row['properties']).single()['n']
                if result != 1:
                    raise ContextError('Exact owned candidate deletion conflict')
                after.remove(row)
            indexed_after = {}
            for row in after:
                indexed_after.setdefault((row['src'], row['dst']), []).append(row)
            for src, dst in sorted(desired):
                present = indexed_after.get((src, dst), [])
                if present:
                    if len(present) != 1 or (present[0]['properties'] != {'basis': BASIS} and not claims_ownership(present[0]['properties'])):
                        raise ContextError('Duplicate/different expected candidate relationship')
                    continue
                props = owned_properties(src, dst, generation, identity)
                n = tx.run('MATCH(n:NativeArtifact {id:$src}),(f:Artifact {id:$dst}) '
                    'CREATE(n)-[r:NATIVE_SOURCE_CANDIDATE]->(f) SET r=$props RETURN count(r) AS n', src=src, dst=dst, props=props).single()['n']
                if n != 1:
                    raise ContextError('Missing/duplicate lifecycle candidate endpoints')
                after.append({'src': src, 'dst': dst, 'properties': props})
            orphan_before = []
            # Snapshot before node deletion, after candidate reconciliation; the
            # edge before/after journal independently records removed ownership.
            for key, (snapshot, degree) in zip(orphan_ids, orphan_snapshots(tx, orphan_ids)):
                orphan_before.append(snapshot)
                if snapshot['node'] is not None and degree == 0:
                    n = tx.run('MATCH(n:Artifact {id:$id}) WHERE NOT(n)--() DELETE n RETURN count(n) AS n', id=key).single()['n']
                    if n != 1:
                        raise ContextError('Deferred orphan deletion conflict')
            orphan_after = [snapshot for snapshot, _ in orphan_snapshots(tx, orphan_ids)]
            after = sorted(after, key=canonical)
            p = {'id': identity, 'contract_version': 1, 'owner': OWNER, 'state': 'committed',
                 'source_delta_sha256': delta_sha, 'seal_sha256': seal['seal_sha256'], 'native_generation': generation,
                 'seal_json': canonical(packed if packed is not None else pack_guard(seal)), 'before_json': canonical(before), 'after_json': canonical(after),
                 'orphan_before_json': canonical(orphan_before), 'orphan_after_json': canonical(orphan_after),
                 'journal_sha256': digest({'before': before, 'after': after, 'orphan_before': orphan_before, 'orphan_after': orphan_after})}
            tx.run('CREATE(p:NativeCandidateCheckpoint) SET p=$props', props=p).consume()
            verify_scope(tx, root, delta_path, seal, identity, allow_committed=True)
            tx.commit()
        if stop_after_commit:
            raise ContextError('Injected interruption after candidate lifecycle commit')
    p = verify_scope(session, root, delta_path, seal, identity, allow_committed=True)
    if p['state'] == 'committed':
        count = session.run('MATCH(p:NativeCandidateCheckpoint {id:$id}) WHERE p.state="committed" '
            'AND p.journal_sha256=$journal SET p.state="verified" RETURN count(p) AS n', id=identity, journal=p['journal_sha256']).single()['n']
        if count != 1:
            raise ContextError('Lifecycle verification checkpoint conflict')
        p['state'] = 'verified'
    return receipt_for(p)
