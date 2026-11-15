"""Tiny finished-capture fixtures, always beneath project temp/test-work."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from code_identity import VERSION, context_descriptor
from reuse_observations import reuse_verified


class ObservationReuseTests(unittest.TestCase):
    def setUp(self):
        project = Path(__file__).resolve().parents[1]
        base = project / 'temp/test-work'
        base.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='verified-observation-', dir=base)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        producer_dir = self.root / 'dependency-graph'
        producer_dir.mkdir()
        for name in ('refresh_extract', 'full_source_graph', 'gcc_source_graph',
                     'code_identity', 'context_runtime', 'context_resources'):
            shutil.copyfile(project / 'dependency-graph' / (name + '.py'), producer_dir / (name + '.py'))
        self.source = self.root / 'source-capture'
        self.dest = self.root / 'new-capture'
        self.owner = 'app:unit'
        self.directory = self.source / 'observations/app-unit'
        self.scratch = self.directory / 'scratch/0000'
        self.scratch.mkdir(parents=True)
        self.cpp = self.root / 'unit.cpp'
        self.cpp.write_text('int unit() { return 1; }\n')
        self.header = self.root / 'unit.hpp'
        self.header.write_text('#pragma once\n')
        self.row = {'file': str(self.cpp), 'directory': str(self.root),
                    'arguments': ['c++', '-c', str(self.cpp), '-o', 'unit.o']}
        self.dump = self.scratch / 'unit.cgraph'
        self.dump.write_text('original parsed GCC dump\n')
        self.ast_path = self.directory / 'ast.json'
        self.gcc_path = self.directory / '0000.json'
        self.ast = {'passed': True, 'parse_clean': True, 'recovery': None,
                    'identity_version': VERSION, 'source': 'unit.cpp',
                    'input_sha256': {str(self.cpp): self.sha(self.cpp), str(self.header): self.sha(self.header)},
                    'nodes': {'tu:unit': {'kind': 'TranslationUnit', 'metadata': {
                        'compile_command': context_descriptor(self.root, self.row)}}}}
        self.gcc = {'source': str(self.cpp), 'returncode': 0,
                    'source_sha256': self.sha(self.cpp), 'symbols': {'unit': {}},
                    'scratch': str(self.scratch), 'dump': str(self.dump),
                    'dump_sha256': self.sha(self.dump),
                    'argv': ['c++', '-c', str(self.cpp), '-o', str(self.scratch / 'unit.o'),
                             '-fdump-ipa-cgraph=' + str(self.dump)]}
        self.write(self.ast_path, self.ast)
        self.write(self.gcc_path, self.gcc)
        self.producers = {'dependency-graph/' + p.name: self.sha(p) for p in producer_dir.glob('*.py')}
        self.plan = {'identity_version': VERSION, 'producer_sha256': dict(self.producers)}
        self.write(self.source / 'plan.json', self.plan)
        self.write(self.source / 'units.json', [[self.owner, self.row]])
        self.extract = {'returncode': 0, 'argv': ['python', str(producer_dir / 'refresh_extract.py'), str(self.source)]}
        self.write(self.source / 'extract.json', self.extract)
        self.bindings = {'producers': dict(self.producers), 'source_metadata': {
            name: self.sha(self.source / name) for name in ('plan.json', 'units.json', 'extract.json')}}

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value) + '\n')

    def reuse(self, row=None, source=None):
        return reuse_verified(self.root, source or self.source, self.dest,
                              [(self.owner, row or self.row)], self.bindings)

    def rejected(self, result):
        self.assertEqual(result['eligible'], [])
        self.assertEqual(len(result['rejected']), 1)
        self.assertFalse((self.dest / 'observations/app-unit').exists())
        return result['rejected'][0]['reason']

    def test_valid_capture_creates_only_reference_and_preserves_original_bytes(self):
        before = {str(p): self.sha(p) for p in self.source.rglob('*') if p.is_file()}
        result = self.reuse()
        self.assertEqual(result['rejected'], [])
        entry, = result['eligible']
        link = self.dest / 'observations/app-unit'
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), self.directory)
        self.assertEqual(entry['ast_sha256'], self.sha(self.ast_path))
        self.assertEqual(entry['gcc_sha256'], self.sha(self.gcc_path))
        self.assertFalse(entry['historical_pair_seal_present'])
        self.assertFalse(result['graph_freshness_claimed'])
        self.assertEqual(before, {str(p): self.sha(p) for p in self.source.rglob('*') if p.is_file()})
        self.assertEqual(set(self.dest.iterdir()), {self.dest / 'observations'})

    def test_source_or_header_changed_rejects(self):
        self.header.write_text('// changed include\n')
        self.assertIn('changed', self.rejected(self.reuse()))

    def test_extraction_producer_changed_rejects(self):
        path = self.root / 'dependency-graph/code_identity.py'
        path.write_text(path.read_text() + '\n# changed compiler identity\n')
        self.assertIn('producer', self.rejected(self.reuse()))

    def test_staging_producer_change_is_allowed(self):
        self.plan['producer_sha256']['dependency-graph/refresh_facts.py'] = 'old staging hash'
        self.write(self.source / 'plan.json', self.plan)
        self.bindings['source_metadata']['plan.json'] = self.sha(self.source / 'plan.json')
        self.bindings['producers']['dependency-graph/refresh_facts.py'] = 'new staging hash'
        self.assertEqual(len(self.reuse()['eligible']), 1)

    def test_missing_gcc_rejects(self):
        self.gcc_path.unlink()
        self.assertIn('missing', self.rejected(self.reuse()))

    def test_compile_command_mismatch_rejects(self):
        row = dict(self.row, arguments=self.row['arguments'] + ['-DCHANGED=1'])
        self.assertIn('compile command', self.rejected(self.reuse(row=row)))

    def test_source_output_traversal_rejects(self):
        self.assertIn('traversal', self.rejected(self.reuse(source=self.root / '..' / 'other')))

    def test_symlinked_source_output_rejects(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.source, target_is_directory=True)
        self.assertIn('alias', self.rejected(self.reuse(source=alias)))

    def test_metadata_mutation_without_original_binding_rejects(self):
        self.plan['extra'] = 'not the retained metadata'
        self.write(self.source / 'plan.json', self.plan)
        self.assertIn('metadata binding', self.rejected(self.reuse()))

    def test_capture_failure_rejects(self):
        self.extract['returncode'] = 1
        self.write(self.source / 'extract.json', self.extract)
        self.bindings['source_metadata']['extract.json'] = self.sha(self.source / 'extract.json')
        self.assertIn('successfully', self.rejected(self.reuse()))

    def test_pair_recovery_binding_is_checked(self):
        self.ast.update(parse_clean=False, recovery={'kind': 'captured GCC recovery',
                        'gcc_validation': str(self.gcc_path), 'sha256': '0' * 64})
        self.write(self.ast_path, self.ast)
        self.assertIn('pair hash', self.rejected(self.reuse()))

    def test_valid_pair_recovery_retains_original_hash(self):
        self.ast.update(parse_clean=False, recovery={'kind': 'captured GCC recovery',
                        'gcc_validation': str(self.gcc_path), 'sha256': self.sha(self.gcc_path)})
        self.write(self.ast_path, self.ast)
        result = self.reuse()
        self.assertEqual(result['rejected'], [])
        self.assertTrue(result['eligible'][0]['historical_pair_seal_present'])

    def test_gcc_dump_or_argv_mismatch_rejects(self):
        self.gcc['argv'].append('-DUNBOUND=1')
        self.write(self.gcc_path, self.gcc)
        self.assertIn('compile command', self.rejected(self.reuse()))

    def test_owner_traversal_rejects(self):
        result = reuse_verified(self.root, self.source, self.dest,
                                [('../outside', self.row)], self.bindings)
        self.rejected(result)

    def test_existing_destination_not_overwritten(self):
        first = self.reuse()
        self.assertEqual(len(first['eligible']), 1)
        second = self.reuse()
        self.assertEqual(second['eligible'], [])
        self.assertIn('already exists', second['rejected'][0]['reason'])
        self.assertTrue((self.dest / 'observations/app-unit').is_symlink())


if __name__ == '__main__':
    unittest.main()
