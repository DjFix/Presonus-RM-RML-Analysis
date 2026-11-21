import json
import os
import pathlib
import tempfile
import unittest
from snapshot_runtime import immutable_mounts
from context_runtime import ContextError, sha

class MetadataClosure(unittest.TestCase):
    def setUp(self):
        scratch=pathlib.Path(__file__).resolve().parents[1]/'temp/test-work'
        scratch.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=scratch);self.addCleanup(self.tmp.cleanup)
        self.root=pathlib.Path(self.tmp.name).resolve()
        self.prior=self.root/'temp/recovery-work/prior';self.prior.mkdir(parents=True)
        self.out=self.root/'temp/recovery-work/new';self.out.mkdir()
        self.metadata={}
        for key in ('state','report','receipt'):
            p=self.root/('evidence/'+key+'.json');p.parent.mkdir(exist_ok=True);p.write_text('{}')
            self.metadata[key]={'path':str(p.relative_to(self.root)),'sha256':sha(p)}
        self.origin=self.root/'temp/recovery-work/dependency-graph/refresh/1'
        self.origin.mkdir(parents=True)
        self.manifest=self.prior/'SNAPSHOT.json'
        self.manifest.write_text(json.dumps({'version':1,'references':{'leaf':{'kind':'compiler_observation','target':str(self.root/'temp/recovery-work/dependency-graph/refresh/1/observations/o/ast.json'),'provenance':self.metadata}}}))
        self.snapshot={'mounts':[],'references':{},'reuse':{'batch':str(self.prior.relative_to(self.root)),'manifest_sha256':sha(self.manifest)}}
    def test_ancestor_metadata_mounted_exactly(self):
        mounts=immutable_mounts(self.root,self.out,self.snapshot)
        self.assertIn((self.origin,self.origin),mounts)
        for ref in self.metadata.values():
            p=self.root/ref['path'];self.assertTrue(p.is_file())
            self.assertFalse(any(p.is_relative_to(dst) and src != dst for src,dst in mounts))
    def test_inherited_report_not_masked_by_snapshot_directory(self):
        prefix = 'temp/recovery-work/dependency-graph/refresh'
        report_dir = self.root / prefix / '2'
        report_dir.mkdir()
        report = report_dir / 'refresh-report.json'
        report.write_text('{}')
        metadata = dict(self.metadata)
        metadata['report'] = {'path': str(report.relative_to(self.root)), 'sha256': sha(report)}
        old = json.loads(self.manifest.read_text())
        old['references']['leaf']['provenance'] = metadata
        self.manifest.write_text(json.dumps(old))
        self.snapshot['reuse']['manifest_sha256'] = sha(self.manifest)
        self.snapshot['mounts'] = [prefix]
        overlay = self.out / 'snapshot' / prefix / '2'
        (overlay / 'observations').mkdir(parents=True)
        (report_dir / 'observations').mkdir()
        mounts = immutable_mounts(self.root, self.out, self.snapshot)
        self.assertNotIn((overlay, report_dir), mounts)
        self.assertIn((overlay / 'observations', report_dir / 'observations'), mounts)
        self.assertFalse(any(report.is_relative_to(dst) and src != dst for src, dst in mounts))

    def test_file_mount_alias_leaves_inherited_reference_inode_visible(self):
        target = self.prior / 'snapshot' / 'original'
        target.parent.mkdir()
        target.write_text('immutable bytes')
        alias = self.root / 'historical-alias'
        alias.symlink_to(target)
        source = self.out / 'snapshot' / alias.name
        source.parent.mkdir()
        source.write_text(target.read_text())
        self.snapshot['references']['alias-origin'] = {'target': str(target)}
        self.snapshot['mounts'] = [alias.name]
        self.snapshot['files'] = {alias.name: sha(source)}
        self.assertEqual(immutable_mounts(self.root, self.out, self.snapshot),
                         [(self.origin, self.origin)])
        self.assertTrue(os.path.samefile(alias, target))
        self.snapshot['files'][alias.name] = '0' * 64
        with self.assertRaisesRegex(ContextError, 'mount alias changed'):
            immutable_mounts(self.root, self.out, self.snapshot)

    def test_changed_metadata_rejected(self):
        (self.root/self.metadata['report']['path']).write_text('changed')
        with self.assertRaises(ContextError):immutable_mounts(self.root,self.out,self.snapshot)
    def test_changed_lineage_rejected(self):
        self.manifest.write_text('{}')
        with self.assertRaises(ContextError):immutable_mounts(self.root,self.out,self.snapshot)
    def test_missing_metadata_rejected(self):
        (self.root/self.metadata['report']['path']).unlink()
        with self.assertRaises(ContextError):immutable_mounts(self.root,self.out,self.snapshot)
    def test_symlink_metadata_rejected(self):
        p=self.root/self.metadata['report']['path'];other=p.with_suffix('.old');p.rename(other);p.symlink_to(other)
        with self.assertRaises(ContextError):immutable_mounts(self.root,self.out,self.snapshot)
    def test_hardlink_metadata_rejected(self):
        p=self.root/self.metadata['report']['path'];os.link(p,p.with_suffix('.other'))
        with self.assertRaises(ContextError):immutable_mounts(self.root,self.out,self.snapshot)

if __name__=='__main__':unittest.main()
