import pathlib
import sqlite3
import unittest
import registry as r
import schema
import workflow as w
import test_workflow as fixtures

class SchemaTests(unittest.TestCase):
    setUp=fixtures.WorkflowTests.setUp
    def legacy(self):
        db=self.root/'legacy';w.working_copy(self.root/'baseline',db)
        c=sqlite3.connect(db)
        c.execute("UPDATE work_state SET assignment='preserved-owner',revision=7 WHERE record_id=1")
        c.execute("INSERT INTO requests VALUES ('old','digest','{}')")
        c.execute("INSERT INTO stages VALUES (1,'compiled','proof','sha','bounded')")
        c.execute("INSERT INTO evidence_checks VALUES ('old','source','sha','[]')")
        c.execute("INSERT INTO journal VALUES (1,'old',1,'actor','time','reason',6,7,'{}','{}','{}')")
        c.commit();c.close();return db
    def test_explicit_adoption_preserves_rows_triggers_indexes_and_backup(self):
        db=self.legacy()
        with r.connect(db) as c:before=schema.fingerprint(c)
        old=r.digest(db);plan=schema.upgrade(db);self.assertEqual(old,r.digest(db));self.assertEqual(len(plan['steps']),2)
        report=schema.upgrade(db,self.root/'backup',True)
        with r.connect(db) as c:
            schema.require_current(c);after=schema.fingerprint(c,set(before)-{'_objects'})
        for name,value in before.items():
            if name!='_objects':self.assertEqual(after[name],value)
        self.assertTrue(set(before['_objects'])<=set(after['_objects']))
        with r.connect(self.root/'backup') as c:self.assertEqual(schema.fingerprint(c),before)
        self.assertEqual(schema.upgrade(db,apply=True)['steps'],[])
        self.assertTrue(report['applied'])
    def test_failed_upgrade_rolls_back_ddl_data_and_version(self):
        db=self.legacy()
        with r.connect(db) as c:before=schema.fingerprint(c)
        with self.assertRaises(RuntimeError):schema.upgrade(db,self.root/'failed-backup',True,fail_after='0001_adopt')
        with r.connect(db) as c:self.assertEqual(schema.fingerprint(c),before)
        self.assertTrue((self.root/'failed-backup').exists())
    def test_existing_adoption_revision_upgrades_without_history_loss(self):
        db=self.legacy()
        schema.upgrade(db,self.root/'initial-backup',True)
        c=sqlite3.connect(db)
        for name in ('workflow_assignment_lookup','workflow_blocker_lookup','workflow_stage_lookup'):
            c.execute('DROP INDEX '+name)
        # Construct the earlier supported revision as a test fixture only.
        c.execute('DROP TRIGGER migration_no_delete')
        c.execute("DELETE FROM migration_journal WHERE revision='0002_workflow_indexes'")
        c.execute("CREATE TRIGGER migration_no_delete BEFORE DELETE ON migration_journal BEGIN SELECT RAISE(ABORT,'append-only migration journal'); END")
        c.execute("UPDATE alembic_version SET version_num='0001_adopt'");c.commit();c.close()
        schema.upgrade(db,self.root/'revision1-backup',True)
        with r.connect(db) as c:
            self.assertEqual(schema.revision(c),schema.CURRENT)
            self.assertEqual(c.execute('SELECT revision FROM migration_journal ORDER BY sequence').fetchall()[0][0],'0001_adopt')
            self.assertEqual(c.execute('SELECT count(*) FROM migration_journal').fetchone()[0],2)

    def test_baseline_and_newer_or_ambiguous_marker_rejected(self):
        with self.assertRaises(ValueError):schema.upgrade(self.root/'baseline',self.root/'no-backup',True)
        c=sqlite3.connect(self.db);c.execute("UPDATE alembic_version SET version_num='9999_future'");c.commit();c.close()
        with self.assertRaises(ValueError):r.connect(self.db)
        db=self.legacy();c=sqlite3.connect(db);c.execute('INSERT INTO schema_info VALUES (99,0)');c.commit();c.close()
        with self.assertRaises(ValueError):r.connect(db)

if __name__=='__main__':unittest.main()
