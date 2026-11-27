import json
import sqlite3
import unittest
from contextlib import closing
import orm
import registry
import schema
import test_workflow


class DeclarationStatusTests(unittest.TestCase):
    setUp = test_workflow.WorkflowTests.setUp

    def test_explicit_status_preserves_readiness_and_expires_with_proof(self):
        with closing(orm.Unit(self.db, write=True)) as u:
            row = u.session.query(orm.Record).filter_by(mangled='b').one()
            original = json.loads(row.metadata_json)
            u.session.add(orm.DeclarationAssessment(record_id=row.id,
                proof_sha256=original['validation_sha256'], declaration_status='return_type_unresolved',
                reason='No original typed evidence', portable_return='int',
                evidence_json='{}', assessed_at='fixture'))
            u.commit()
        with sqlite3.connect(self.db) as c:
            self.assertEqual(c.execute("SELECT readiness_status,declaration_status,effective_status FROM symbol_declaration_status WHERE mangled='b'").fetchone(),
                             ('pending', 'return_type_unresolved', 'return_type_unresolved'))
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute('DELETE FROM declaration_assessments')
            original['validation_sha256'] = 'new-proof'
            c.execute("UPDATE records SET metadata=? WHERE mangled='b'", (json.dumps(original),))
            self.assertEqual(c.execute("SELECT declaration_status,effective_status FROM symbol_declaration_status WHERE mangled='b'").fetchone(), ('needs_review','pending'))
            c.execute("UPDATE records SET status='ready',ordinal=99 WHERE mangled='b'")
            self.assertEqual(c.execute("SELECT declaration_status,effective_status FROM symbol_declaration_status WHERE mangled='b'").fetchone(), ('not_pending','ready'))

    def test_assessment_is_idempotent_and_excludes_ready_and_lifecycle(self):
        import declaration_status as ds
        from unittest.mock import patch
        audit = self.root/'audit.json'
        body = {'evidence': {}, 'per_unique_name': {}}
        for name in ('a', 'b'):
            body['per_unique_name'][name] = dict(method_kind='ordinary_method',
                decision='independent_original_declaration_missing',
                identities=[{'original_elf_sha256':'elf'}], portable_return='int',
                concrete_missing_evidence='Original typed evidence absent')
        body['per_unique_name']['ctor'] = dict(method_kind='constructor', decision='active_owner_lifecycle_completion')
        audit.write_text(json.dumps(body))
        # Fixture library has the same relative name as the actual repository.
        root = self.lib.parent
        with patch.object(ds, 'ROOT', root):
            # Existing workflow fixtures call the library "lib"; expose its
            # real path via the expected repository layout without copying it.
            (root/'uc-library').symlink_to(self.lib, target_is_directory=True)
            before = registry.digest(self.db)
            self.assertEqual(ds.assess(self.db,audit)['identities'],1)
            self.assertEqual(registry.digest(self.db),before)
            self.assertEqual(ds.assess(self.db,audit,True)['identities'],1)
            self.assertEqual(ds.assess(self.db,audit,True)['identities'],0)
            self.assertEqual(ds.summary(self.db),[{'declaration_status':'return_type_unresolved','identities':1,'names':1}])

    def test_migration_failure_rolls_back_view_and_assessment_table(self):
        db = self.root/'legacy-declarations'
        import workflow
        workflow.working_copy(self.root/'baseline',db)
        with registry.connect(db) as c:
            before = schema.fingerprint(c)
        with self.assertRaises(RuntimeError):
            schema.upgrade(db,self.root/'declarations-backup',True,fail_after='0004_declaration_status')
        with registry.connect(db) as c:
            self.assertEqual(schema.fingerprint(c),before)
            self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='symbol_declaration_status'").fetchone())


if __name__ == '__main__':
    unittest.main()
