from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import catalog
import sqlite_admission as admission
import sqlite_packet as packet
from test_sqlite_packet import fixture


class CompletionTest(unittest.TestCase):
    def test_scoped_completion_idempotence_and_proof_drift(self):
        workspace = packet.ROOT / 'temp/recovery-work'
        with TemporaryDirectory(prefix='sqlite-admission-test-', dir=workspace) as scratch:
            root, db, plan = fixture(Path(scratch))
            packet_dir = root / 'temp/recovery-work/packet'
            index = packet.prepare(root, plan, packet_dir, db)
            packet.dispatch(root, packet_dir, db)
            targets = [packet.load(packet_dir/'tasks'/task/'CONTEXT.json')['originals'][0]['original']
                       for task in sorted(index['tasks'])]
            proof = root/'uc-library/current-proof.json'
            packet.write(proof, {'passed': True})
            rows = [
                {'original_elf_sha256': row['elf'], 'mangled': row['mangled'],
                 'portable_ready': True, 'domain': 'Synthetic journal fixture.',
                 'validation': proof.name, 'validation_sha256': packet.digest(proof)}
                for row in targets
            ]
            pending = dict(rows[1], portable_ready=False, cpp_compiled=True,
                           mangling_namespace_checked=True, declaration_uncertainties=['fixture return'],
                           behavior_validation=proof.name, behavior_validation_sha256=packet.digest(proof))
            with packet.adapter.snapshot(root/'uc-library', db=db) as prior:
                guard = prior.guard
            commit = packet.adapter.commit_snapshot(rows[:1], [pending], guard, library=root/'uc-library',
                db=db, actor='fixture', reason='Synthetic guarded admission')
            result = root/'guarded-receipt.json'
            packet.write(result, {'sqlite_commit': commit})
            first = sorted(index['tasks'])[0]
            dry = admission.finalize(root, packet_dir, result, db, [first])
            self.assertTrue(dry['catalog']['dry_run'])
            self.assertEqual(dry['catalog']['operations'], 1)
            self.assertEqual([r['state'] for r in catalog.query(db)], ['assigned', 'assigned'])
            admission.finalize(root, packet_dir, result, db, [first], apply=True)
            replay = admission.finalize(root, packet_dir, result, db, [first], apply=True)
            self.assertTrue(replay['catalog']['idempotent_replay'])
            self.assertEqual(sorted(r['state'] for r in catalog.query(db)), ['assigned', 'done'])
            second = sorted(index['tasks'])[1]
            self.assertEqual(admission.finalize(root, packet_dir, result, db, [second])
                             ['readback'][0]['classification'], 'pending')
            proof.write_text('proof drift')
            with self.assertRaisesRegex(ValueError, 'Admitted proof changed'):
                admission.finalize(root, packet_dir, result, db, list(index['tasks']), apply=True)
            self.assertEqual(sorted(r['state'] for r in catalog.query(db)), ['assigned', 'done'])
