"""Fixture tests run entirely in project-local temporary directories."""
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import registry as r

ROOT = pathlib.Path(__file__).resolve().parents[3]

class RegistryTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / 'temp' / 'registry-tests'
        base.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.paths = {}
        for status, name in [('ready','a'), ('pending','b')]:
            self.paths[status] = self.root / (status+'.json')
            self.paths[status].write_text(json.dumps({'functions': [
                {'mangled': name, 'original_elf_sha256':'elf', 'sources': {'p':'hash1'},
                 'repository_sources': {'p':'hash2'}, 'domain':['bounded',None], 'validation':'proof'}],
                 'unknown': {'preserved':[True,3,None]}}))
    def build(self):
        r.capture(self.paths,self.root/'snapshots')
        return r.import_snapshots(self.root/'snapshots',self.root/'db')
    def test_roundtrip_reverse_integrity_and_readonly(self):
        report=self.build()
        self.assertEqual(report['counts'],{'ready':1,'pending':1})
        self.assertEqual(report['source_sets'],2)
        with r.connect(self.root/'db') as c:
            self.assertEqual(r.validate(c,self.root/'snapshots')['integrity'],'ok')
            self.assertEqual(c.execute('SELECT count(*) FROM source_versions WHERE path=?',('p',)).fetchone()[0],2)
            self.assertEqual(c.execute('SELECT count(DISTINCT x.record_id) FROM record_sets x JOIN source_members m ON m.set_id=x.set_id JOIN source_versions v ON v.id=m.version_id WHERE v.path=? AND v.digest_json=?',('p',r.encode('hash2'))).fetchone()[0],2)
            r.export(c,'ready',self.root/'export.json')
            self.assertEqual(json.loads((self.root/'export.json').read_text()),json.loads(self.paths['ready'].read_text()))
            with self.assertRaises(Exception): c.execute('DELETE FROM records')
    def test_disjointness(self):
        d=json.loads(self.paths['pending'].read_text()); d['functions'][0]['mangled']='a'
        self.paths['pending'].write_text(json.dumps(d))
        with self.assertRaises(Exception): self.build()
    def test_capture_change_rejected(self):
        real=r.digest; calls=0
        def changed(p):
            nonlocal calls
            calls+=1
            return 'changed' if calls==6 else real(p)
        with patch.object(r,'digest',changed):
            with self.assertRaises(RuntimeError): r.capture(self.paths,self.root/'snapshots')
        self.assertFalse((self.root/'snapshots'/'capture.json').exists())
    def test_expected_producer_pair_guard(self):
        expected=self.root/'producer.json'
        expected.write_text(json.dumps({p.name:r.digest(p) for p in self.paths.values()}))
        manifest=r.capture(self.paths,self.root/'snapshots',expected)
        self.assertEqual(manifest['expected_producer_manifest']['sha256'],r.digest(expected))
        wrong=self.root/'wrong.json';wrong.write_text('{}')
        with self.assertRaises(ValueError):r.capture(self.paths,self.root/'rejected',wrong)

    def test_tampered_snapshot_rejected(self):
        r.capture(self.paths,self.root/'snapshots')
        p=self.root/'snapshots'/'ready.json'; p.chmod(0o644); p.write_text('{}')
        with self.assertRaises(ValueError): r.import_snapshots(self.root/'snapshots',self.root/'db')

if __name__ == '__main__': unittest.main()
