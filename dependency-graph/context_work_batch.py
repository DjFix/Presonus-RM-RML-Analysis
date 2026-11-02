"""Invocation-local dedup input verification; current claims are never cached.

The canonical dedup producers remain unchanged. Immutable native/report/release/
producer inputs are verified by their existing verifier on entry and exit. Every
claim, work status and decision revision is read afresh for every packet and again
at the final barrier. This is analysis input reuse, never readiness proof reuse.
"""
import json
from context_runtime import ContextError, inside, sha
from dedup_work import active_index, evidence
from dedup_index import meta, verify_inputs


class BatchWorkValidator:
    def __init__(self, root):
        self.root = root
        self.connection, self.pointer = active_index(root)
        self.database = inside(root,self.pointer['database'])
        observed = self.database.stat()
        self.database_identity = (observed.st_dev,observed.st_ino)
        self.metadata = self._metadata()
        self.native_pointer = json.loads((root/'dependency-graph/NATIVE_ACTIVE.json').read_text())
        self.packets = []

    def _metadata(self):
        return {key:meta(self.connection,key) for key in
                ('complete','generation','native_generation','release_inputs','producer_inputs')}

    def _identity(self):
        observed = self.database.stat()
        if (observed.st_dev,observed.st_ino) != self.database_identity:
            raise ContextError('Batch dedup database replaced; connection is stale')
        if (json.loads((self.root/'dependency-graph/DEDUP_ACTIVE.json').read_text()) != self.pointer or
                json.loads((self.root/'dependency-graph/NATIVE_ACTIVE.json').read_text()) != self.native_pointer or
                self._metadata() != self.metadata):
            raise ContextError('Immutable batch dedup input identity changed')

    def validate(self, packet, path, remember=True):
        self._identity()
        binding = packet.get('work_binding')
        if not binding:
            raise ContextError('Packet predates unique-work gate; prepare again')
        if binding['database'] != self.pointer['database'] or binding['generation'] != self.metadata['generation']:
            raise ContextError('Dedup generation switched; prepare again')
        c = self.connection
        row = c.execute('SELECT * FROM work_claims WHERE id=?',(binding['claim_id'],)).fetchone()
        if (not row or row['state'] != 'active' or row['owner'] != binding['claim_owner'] or
                row['packet_path'] != path or row['work_item_id'] != binding['work_item_id'] or
                row['generation'] != binding['generation'] or row['decision_id'] != binding['equivalence_decision_id']):
            raise ContextError('Claim is inactive, foreign, or changed')
        job = c.execute('SELECT status FROM reconstruction_work_items WHERE id=?',(row['work_item_id'],)).fetchone()
        if not job or job['status'] in ('completed','superseded'):
            raise ContextError('Work no longer active')
        if row['decision_id']:
            decision = c.execute('SELECT * FROM equivalence_decisions WHERE id=?',(row['decision_id'],)).fetchone()
            revision = c.execute('SELECT max(revision) FROM equivalence_decisions WHERE subject_id=?',(decision['subject_id'],)).fetchone()[0]
            if revision != binding['decision_revision']:
                raise ContextError('Equivalence revision changed; prepare a new packet')
            refs = json.loads(decision['evidence_refs'])
            if refs:
                evidence(refs,root=self.root)
        for payload in binding['unique_payload_dependencies']:
            file = inside(self.root,payload['object_path'])
            if file.stat().st_size != payload['size'] or sha(file) != payload['content_sha256']:
                raise ContextError('Shared payload object changed')
        if {str(item['original']['anchor']) for item in packet['originals']} != {item['catalog_anchor'] for item in binding['covered_occurrences']}:
            raise ContextError('Packet must include every covered original body/identity')
        if remember:
            self.packets.append((packet,path))

    def finish(self):
        self._identity()
        verify_inputs(self.connection,self.root)
        for packet,path in self.packets:
            self.validate(packet,path,remember=False)
        self._identity()

    def close(self):
        self.connection.close()
