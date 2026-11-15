"""Selection comes from current catalog/history and excludes unavailable work."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('measure_preparation', ROOT/'dependency-graph/measure_context_preparation.py')
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)


class SelectionTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT/'temp/test-work/preparation-selection'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'dependency-graph').mkdir()
        folder = self.root/'uc-library/validation/registry-sqlite'
        folder.mkdir(parents=True)
        (folder/'ACTIVE.json').write_text(json.dumps({'database':{'absolute_path':str(self.root/'registry.sqlite')}}))
        (self.root/'dependency-graph/DEDUP_ACTIVE.json').write_text(json.dumps({'database':'work.sqlite','generation':'generation'}))
        (self.root/'dependency-graph/NATIVE_ACTIVE.json').write_text(json.dumps({'database':'native.sqlite','sha256':'native'}))
        with sqlite3.connect(self.root/'registry.sqlite') as c:
            c.executescript('''CREATE TABLE catalog_symbols(anchor,elf,mangled,demangled,address,size,kind);
                CREATE TABLE catalog_tasks(anchor,state,notes,revision);
                CREATE TABLE records(elf,mangled);''')
            for i in range(8):
                c.execute('INSERT INTO catalog_symbols VALUES(?,?,?,?,?,?,?)',
                          (str(i),'a'*64,f'_Zsymbol{i}',f'Presonus::Thing::method{i}()',i*4,4,'STT_FUNC'))
                c.execute('INSERT INTO catalog_tasks VALUES(?,?,?,?)',(str(i),'todo','',0))
        with sqlite3.connect(self.root/'work.sqlite') as c:
            c.executescript('''CREATE TABLE reconstruction_work_items(id,status,work_kind);
                CREATE TABLE work_item_members(work_item_id,occurrence_id);
                CREATE TABLE symbol_occurrences(id,native_id,catalog_anchor,strategy);
                CREATE TABLE work_claims(work_item_id,state);
                CREATE TABLE carryover_reservations(occurrence_id);''')
            for i in range(8):
                c.execute('INSERT INTO reconstruction_work_items VALUES(?,?,?)',(str(i),'todo','reconstruct'))
                c.execute('INSERT INTO work_item_members VALUES(?,?)',(str(i),str(i)))
                c.execute('INSERT INTO symbol_occurrences VALUES(?,?,?,?)',(str(i),str(i),str(i),'native'))
            c.execute('INSERT INTO work_claims VALUES("0","active")')
            c.execute('INSERT INTO carryover_reservations VALUES("1")')
            c.execute('UPDATE reconstruction_work_items SET status="completed" WHERE id="2"')
        with sqlite3.connect(self.root/'registry.sqlite') as c:
            c.execute('UPDATE catalog_tasks SET notes="Needs review" WHERE anchor="3"')
            c.execute('INSERT INTO records VALUES(?,?)',('a'*64,'_Zsymbol4'))
            c.execute('UPDATE catalog_tasks SET state="blocked" WHERE anchor="5"')
        with sqlite3.connect(self.root/'native.sqlite') as c:
            c.execute('CREATE TABLE bodies(id,payload)')
            c.executemany('INSERT INTO bodies VALUES(?,?)',[(str(i),'{"instructions":[{"mnemonic":"bx"}]}') for i in range(8)])
        self.out = self.root/'temp/recovery-work/measurement'
        self.out.mkdir(parents=True)

    def test_claims_reservations_history_and_compiled_records_excluded(self):
        with patch.object(measure,'ROOT',self.root):
            manifest = measure.select_audit(self.out,self.out/'prepared',1,2)
        value = json.loads(manifest.read_text())
        tasks = [json.loads((self.root/p).read_text()) for p in value['tasks']]
        self.assertEqual({t['targets'][0]['anchor'] for t in tasks},{'6','7'})
        self.assertTrue(all(t['mode']=='audit' and not t['owned_files'] for t in tasks))
        self.assertEqual(len(value['groups']),1)
        self.assertFalse((self.out/'prepared').exists())


if __name__=='__main__':
    unittest.main()
