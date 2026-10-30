"""Catalog identity/transaction tests; every scratch file is project local."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import catalog
import registry as reg
import workflow
import schema

ROOT = Path(__file__).resolve().parents[3]

class CatalogTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT/'temp/registry-catalog-tests'; scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.temp.name); self.lib = self.root/'library'; self.lib.mkdir()
        self.db = self.root/'working.sqlite'
        baseline = self.root/'baseline.sqlite'
        paths = {}
        for status in ('ready', 'pending'):
            path = self.root/(status+'.json')
            path.write_text(json.dumps({'functions': [] if status == 'ready' else [{'original_elf_sha256': 'a'*64, 'mangled': 'sentinel'}]}))
            paths[status] = path
        reg.capture(paths, self.root/'snapshots')
        reg.import_snapshots(self.root/'snapshots', baseline)
        workflow.working_copy(baseline, self.db)
        schema.upgrade(self.db, self.root/'pre-migration.sqlite', apply=True)
        roles = {}
        for role, elf in [('client', 'a'*64), ('server', 'b'*64)]:
            rows = [dict(mangled='_ZN8Presonus1fEPN4Core1AE', demangled='Presonus::f(Core::A*)', address=64,size=4,section=12,kind='STT_FUNC',binding='STB_GLOBAL'),
                    dict(mangled='alias',demangled='alias',address=64,size=4,section=12,kind='STT_FUNC',binding='STB_WEAK'),
                    dict(mangled='data',demangled='data',address=80,size=4,section=24,kind='STT_OBJECT',binding='STB_LOCAL',storage='zero-initialized NOBITS; no file bytes'),
                    dict(mangled='_ZN4Core1fEv',demangled='Core::f()',address=0,size=0,section='SHN_UNDEF',kind='STT_FUNC',binding='STB_GLOBAL')]
            more = copy.deepcopy(rows); more[3]['upstream_body_available']=True
            roles[role]={'summary':{'sha256':elf,'label':role+' firmware'},'symbols':more}
            dest=self.lib/'recovered-all'/role; dest.mkdir(parents=True)
            for name,data in [('manifest.json',{'sha256':elf}),('all-symbols.json',rows),('symbols.json',rows[:3])]: (dest/name).write_text(json.dumps(data))
        (self.lib/'tracking').mkdir(); (self.lib/'tracking/coverage.json').write_text(json.dumps({'roles':roles}))
    def tearDown(self): self.temp.cleanup()
    def init(self): return catalog.import_catalog(self.db,self.lib,False)
    def payload(self, rows=None):
        rows=rows or catalog.query(self.db,role='client')
        return {'request_id':'request1','actor':'tester','operations':[{'anchor':rows[0]['anchor'],'expected_revision':0,'state':'done','notes':'task only','reason':'bounded task complete'}]}
    def test_import_query_and_aliases(self):
        result=self.init(); self.assertEqual(result['symbols'],8); self.assertEqual(result['raw_rows'],22)
        rows=catalog.query(self.db,role='client',name='Presonus',raw=True)
        self.assertEqual(rows[0]['policy'],'application-or-other'); self.assertEqual(len(rows[0]['aliases']),1)
        self.assertEqual(len(catalog.query(self.db,policy='core-source-provided')),2)
        self.assertTrue(catalog.query(self.db,name='data')[0]['NOBITS'])
        self.assertTrue(catalog.query(self.db,name='Core::f')[0]['zero_size'])
        self.assertEqual(len(catalog.query(self.db,source='recovered-all/client/symbols.json')),3)
        with self.assertRaises(ValueError): self.init()
    def test_import_dryrun_rollback(self):
        catalog.import_catalog(self.db,self.lib,True)
        with sqlite3.connect(self.db) as c:self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='catalog_info'").fetchone())
    def test_atomic_idempotent_revisions_and_no_readiness(self):
        self.init();p=self.payload();catalog.operate(self.db,p,True)
        self.assertTrue(all(x['revision']==0 for x in catalog.query(self.db)))
        catalog.operate(self.db,p,False);self.assertTrue(catalog.operate(self.db,p,False)['idempotent_replay'])
        q=copy.deepcopy(p);q['actor']='other'
        with self.assertRaises(ValueError):catalog.operate(self.db,q,False)
        q=copy.deepcopy(p);q['request_id']='stale'
        with self.assertRaises(ValueError):catalog.operate(self.db,q,False)
        with sqlite3.connect(self.db) as c:
            self.assertEqual(c.execute('SELECT status FROM records').fetchone()[0],'pending')
            self.assertEqual(c.execute('SELECT count(*) FROM catalog_journal').fetchone()[0],1)
            with self.assertRaises(sqlite3.IntegrityError):c.execute('DELETE FROM catalog_journal')
    def test_compensating_rollback_preserves_journal(self):
        self.init(); p=self.payload(); catalog.operate(self.db,p,False)
        self.assertEqual(len(catalog.query(self.db,state='done')),1)
        catalog.rollback_request(self.db,'request1','undo1','tester','restore task',False)
        self.assertEqual(len(catalog.query(self.db,state='done')),0)
        with sqlite3.connect(self.db) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM catalog_journal').fetchone()[0],2)
        with self.assertRaises(ValueError):catalog.rollback_request(self.db,'request1','undo2','tester','stale undo',False)

    def test_legacy_catalog_migration_preserves_history_and_rolls_back_failure(self):
        self.init(); request=self.payload(); catalog.operate(self.db,request,False)
        legacy=self.root/'legacy-working.sqlite'
        workflow.working_copy(self.root/'baseline.sqlite',legacy)
        with sqlite3.connect(legacy) as dest, sqlite3.connect(self.db) as source:
            dest.executescript(catalog.SCHEMA)
            for table in catalog.models.TABLES:
                rows=source.execute('SELECT * FROM '+table.name).fetchall()
                if rows:
                    dest.executemany('INSERT INTO '+table.name+' VALUES('+','.join('?' for _ in rows[0])+')',rows)
        with sqlite3.connect(legacy) as c:
            before=schema.fingerprint(c)
        self.assertEqual(len(catalog.query(legacy,state='done')),1)
        with self.assertRaises(ValueError):catalog.operate(legacy,self.payload(),False)
        with self.assertRaises(RuntimeError):
            schema.upgrade(legacy,self.root/'failed-upgrade-backup.sqlite',apply=True,fail_after='0001_adopt')
        with sqlite3.connect(legacy) as c:self.assertEqual(schema.fingerprint(c),before)
        schema.upgrade(legacy,self.root/'successful-upgrade-backup.sqlite',apply=True)
        with sqlite3.connect(legacy) as c:
            after=schema.fingerprint(c)
            for name in before:
                if name != '_objects':self.assertEqual(after[name],before[name])
            old_triggers=[x for x in before['_objects'] if x[0]=='trigger']
            self.assertTrue(all(x in after['_objects'] for x in old_triggers))
        self.assertTrue(catalog.operate(legacy,request,False)['idempotent_replay'])
        catalog.rollback_request(legacy,'request1','undo-after-migration','tester','preserve history',False)
        with sqlite3.connect(legacy) as c:self.assertEqual(c.execute('SELECT count(*) FROM catalog_journal').fetchone()[0],2)

    def test_bad_second_operation_rolls_back_batch(self):
        self.init();p=self.payload();p['operations'].append({'anchor':'missing','expected_revision':0,'state':'done','reason':'bad'})
        with self.assertRaises(ValueError):catalog.operate(self.db,p,False)
        self.assertTrue(all(x['revision']==0 for x in catalog.query(self.db)))
        with sqlite3.connect(self.db) as c:self.assertEqual(c.execute('SELECT count(*) FROM catalog_requests').fetchone()[0],0)

if __name__=='__main__':unittest.main()
