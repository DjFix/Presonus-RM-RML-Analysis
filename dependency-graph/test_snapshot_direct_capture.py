"""Synthetic completed compiler captures; no firmware/readiness claims."""
import importlib.util
import json
from pathlib import Path
import unittest

from context_runtime import fingerprint, sha
import test_reuse_observations as reuse_fixture

import snapshot_observations as module


class DirectCaptureTests(unittest.TestCase):
    def setUp(self):
        fixture=reuse_fixture.ObservationReuseTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture=fixture
        self.root=fixture.root
        origin=self.root/'temp/recovery-work/dependency-graph/refresh/123'
        origin.parent.mkdir(parents=True)
        old=fixture.source
        old.rename(origin)
        for path in origin.rglob('*.json'):
            path.write_text(path.read_text().replace(str(old),str(origin)))
        self.origin=origin
        self.leaf=origin/'observations/app-unit/ast.json'
        self.relative=str(self.leaf.relative_to(self.root))
        report=origin/'refresh-report.json'
        report.write_text(json.dumps({'source_graph_refresh':True,'producer_sha256':fixture.plan['producer_sha256']}))
        state=self.root/'dependency-graph/state.json'
        self.state={'files':{},'reports':{str(report.relative_to(self.root)):sha(report)}}
        for path in (self.leaf,self.leaf.with_name('0000.json')):
            self.state['files'][str(path.relative_to(self.root))]={'sha256':sha(path),'fingerprint':fingerprint(path)}
        state.write_text(json.dumps(self.state))
        active=self.root/'dependency-graph/ACTIVE.json'
        active.write_text(json.dumps({'state':str(state.relative_to(self.root)),'state_sha256':sha(state)}))
        self.files={'dependency-graph/ACTIVE.json':sha(active),str(state.relative_to(self.root)):sha(state)}

    def candidate(self):
        return module.candidate(self.root,self.relative,sha(self.leaf),self.files,{})

    def test_direct_capture_reference_without_payload_copy(self):
        before=sha(self.leaf)
        leaf,record=self.candidate()
        self.assertEqual(leaf,self.leaf)
        self.assertEqual(record['kind'],'registered_capture')
        self.assertEqual(sha(leaf),before)
        self.assertEqual(module.validate_record(self.root,self.relative,before,record,{},payload_hash=False),leaf)

    def test_changed_current_compiler_input_rejected_at_capture(self):
        self.fixture.header.write_text('// changed\n')
        with self.assertRaisesRegex(ValueError,'changed'):
            self.candidate()

    def test_changed_payload_rejected_even_in_runtime_stat_mode(self):
        leaf,record=self.candidate()
        expected=sha(leaf)
        leaf.write_text(leaf.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'fingerprint changed'):
            module.validate_record(self.root,self.relative,expected,record,{},payload_hash=False)

    def test_changed_metadata_rejected(self):
        leaf,record=self.candidate()
        path=self.origin/'extract.json'
        path.write_text('{"returncode":1}')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):
            module.validate_record(self.root,self.relative,sha(leaf),record,{})


if __name__=='__main__':unittest.main()
