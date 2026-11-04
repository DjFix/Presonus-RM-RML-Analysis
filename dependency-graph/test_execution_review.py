"""Isolated planning tests; no operational claims or readiness mutations."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import execution_review as gate


class ExecutionReviewTests(unittest.TestCase):
    def setUp(self):
        work = Path(__file__).resolve().parents[1] / 'temp/test-work'
        work.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=work)
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'dependency-graph').mkdir()
        self.database = self.root / 'native.sqlite'
        self.target = {'original_elf_sha256': 'a' * 64, 'mangled': '_ZN1AC1Ev', 'address': 100, 'size': 32}
        with sqlite3.connect(self.database) as c:
            c.executescript('CREATE TABLE nodes(id,metadata); CREATE TABLE edges(src,dst,kind,site); CREATE TABLE bodies(id,payload);')
            c.execute('INSERT INTO nodes VALUES(?,?)', ('source', json.dumps(dict(elf_sha256='a'*64,mangled=self.target['mangled'],address=100,size=32))))
            c.executemany('INSERT INTO edges VALUES(?,?,?,?)', [('source','base','ELF_CALLS',100),('source','helper','ELF_TAIL_BRANCH',104),('source','bridge','ELF_NAME_CORRESPONDENCE',108)])
            instructions = [dict(address=112,mnemonic='ldr',operands='pc, [r3, #0x58]'),dict(address=116,mnemonic='bx',operands='lr'),dict(address=120,mnemonic='ldm',operands='sp, {r4, sp, pc}')]
            c.execute('INSERT INTO bodies VALUES(?,?)', ('source',json.dumps({'instructions':instructions})))
        digest = hashlib.sha256(self.database.read_bytes()).hexdigest()
        (self.root/'dependency-graph/NATIVE_ACTIVE.json').write_text(json.dumps({'database':'native.sqlite','sha256':digest}))
        self.evidence = {'path':'native.sqlite','sha256':digest,'kind':'native_observation','scope':'Synthetic isolated execution-boundary fixture'}
        with sqlite3.connect(self.database) as c:
            c.row_factory = sqlite3.Row
            self.observed = gate.collect(c,[self.target])
        entries = [dict(key=k,kind='dependency',dependency_index=0,reason='Explicit provider scope to review',evidence=[self.evidence]) for k in self.observed]
        self.review = {'dependencies':[{'kind':'unresolved'}],'execution_boundary_review':{'native_sha256':digest,'observations':entries}}
        self.task = {'targets':[self.target]}

    def test_actual_call_tail_and_indirect_are_distinct(self):
        self.assertEqual({x['kind'] for x in self.observed.values()}, {'ELF_CALLS','ELF_TAIL_BRANCH','ARM_INDIRECT_REVIEW_CANDIDATE'})
        self.assertEqual(gate.validate(self.root,self.task,self.review)['observations'],3)

    def test_missing_or_duplicate_observations_fail(self):
        for entries in (self.review['execution_boundary_review']['observations'][:-1],self.review['execution_boundary_review']['observations']*2):
            review=copy.deepcopy(self.review);review['execution_boundary_review']['observations']=entries
            with self.assertRaisesRegex(ValueError,'exact direct/tail'):
                gate.validate(self.root,self.task,review)

    def test_proven_tail_cannot_be_dismissed_as_local_jump(self):
        review=copy.deepcopy(self.review)
        for entry in review['execution_boundary_review']['observations']:
            if self.observed[entry['key']]['kind']=='ELF_TAIL_BRANCH':entry['kind']='local_control_flow'
        with self.assertRaisesRegex(ValueError,'cannot be dismissed'):
            gate.validate(self.root,self.task,review)

    def test_unknown_dependency_or_native_generation_fail(self):
        review=copy.deepcopy(self.review);review['execution_boundary_review']['observations'][0]['dependency_index']=9
        with self.assertRaisesRegex(ValueError,'actual reviewed dependency'):
            gate.validate(self.root,self.task,review)
        review=copy.deepcopy(self.review);review['execution_boundary_review']['native_sha256']='b'*64
        with self.assertRaisesRegex(ValueError,'generation changed'):
            gate.validate(self.root,self.task,review)

    def test_arm_calls_and_returns(self):
        for mnemonic,operands,expected in [('blx','r3',True),('blx','lr',True),('bxne','r2',True),('bx','lr',False),('mov','pc, lr',False),('ldrne','pc, [r3]',True),('mov','lr, pc',False),('ldm','r0, {r1, pc}',True)]:
            self.assertEqual(bool(gate.indirect_candidate({'mnemonic':mnemonic,'operands':operands})),expected,(mnemonic,operands))

    def test_prospective_request_preserves_dependency_and_coverage_gates(self):
        from reconstruction_contract import validate_request
        task = dict(self.task, mode='reconstruct', owned_files=[])
        review = copy.deepcopy(self.review)
        review.update(version=1, reviewer='isolated-test', targets=task['targets'],
                      owned_files=[], domain='Synthetic planning only')
        review['requirements'] = {
            name: {'status': 'not_required', 'reason': 'Synthetic contract fixture',
                   'evidence': [self.evidence]}
            for name in ('declarations', 'state', 'lifecycle', 'providers')}
        review['dependencies'][0].update(name='missing-provider', evidence=[self.evidence])

        def bind():
            path = self.root / 'review.json'
            path.write_text(json.dumps(review))
            task['reconstruction_contract'] = {
                'path': 'review.json', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

        bind()
        with self.assertRaisesRegex(ValueError, 'prepare_dependencies_first'):
            validate_request(self.root, task)
        source = self.root / 'provider.cpp'
        source.write_text('void synthetic_provider() {}\n')
        review['dependencies'][0] = {
            'kind': 'existing_implementation', 'binding_domain': 'Synthetic fixture only',
            'evidence': [{'path': 'provider.cpp',
                          'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                          'kind': 'cpp_implementation', 'scope': 'Synthetic provider fixture'}]}
        bind()
        self.assertTrue(validate_request(self.root, task)['dispatch_reconstruction'])
        review['execution_boundary_review']['observations'].pop()
        bind()
        with self.assertRaisesRegex(ValueError, 'exact direct/tail'):
            validate_request(self.root, task)


if __name__=='__main__':
    unittest.main()
