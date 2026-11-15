"""Fresh capture equivalence preserves old IDs only for unchanged semantic input."""
import ast
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from code_identity import VERSION, context_descriptor
from unchanged_observations import ObservationEquivalence


class ObservationEquivalenceTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / 'temp/test-work'
        scratch.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='unchanged-captures-', dir=scratch)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / 'example.cpp'
        self.source.write_text('int f() { return 1; }\n')
        self.v = ObservationEquivalence(self.root)
        self.row = {'directory': str(self.root), 'file': str(self.source),
                    'arguments': ['c++', '-c', str(self.source), '-o', 'example.o']}
        self.ast = {'passed': True, 'parse_clean': True, 'recovery': None,
                    'source': 'example.cpp', 'identity_version': VERSION,
                    'input_sha256': {str(self.source): self.v.sha(self.source)},
                    'external_inputs': [], 'seconds': 1,
                    'nodes': {'tu:old': {'kind': 'TranslationUnit', 'label': 'example.cpp',
                              'metadata': {'compile_command': context_descriptor(self.root, self.row)}}},
                    'edges': [], 'unresolved': [], 'diagnostics': []}
        self.gcc = {'source': str(self.source), 'source_sha256': self.v.sha(self.source),
                    'returncode': 0, 'seconds': 1, 'symbols': {'1': {'name': 'f', 'calls': []}}}
        self.old = self.write_pair('old', self.ast, self.gcc)
        self.new = self.write_pair('new', dict(self.ast, seconds=9), dict(self.gcc, seconds=8))
        self.previous = dict(self.old, command=self.row, inputs=self.ast['input_sha256'], external_inputs=[])

    def write_pair(self, name, ast, gcc):
        folder = self.root / name
        folder.mkdir(exist_ok=True)
        scratch = folder / 'scratch'
        scratch.mkdir(exist_ok=True)
        dump = scratch / 'unit.cgraph'
        dump.write_text('different execution dump ' + name)
        ap, gp = folder / 'ast.json', folder / '0000.json'
        argv = self.row['arguments'][:-1] + [str(scratch / 'unit.o'), '-fdump-ipa-cgraph=' + str(dump)]
        gcc = dict(gcc, scratch=str(scratch), dump=str(dump), argv=argv, dump_sha256=self.v.sha(dump))
        gp.write_text(json.dumps(gcc))
        ast = copy.deepcopy(ast)
        if ast.get('recovery'):
            ast['recovery'].update(gcc_validation=str(gp), sha256=self.v.sha(gp))
        ap.write_text(json.dumps(ast))
        return {'ast': str(ap), 'gcc': str(gp), 'ast_sha256': self.v.sha(ap), 'gcc_sha256': self.v.sha(gp)}

    def check(self):
        return self.v.check('app:one', self.row, self.previous, self.new['ast'], self.new['gcc'])

    def mutate(self, kind, update):
        path = Path(self.new[kind]); data = json.loads(path.read_text()); update(data)
        path.write_text(json.dumps(data))

    def test_only_capture_path_timing_dump_differences_keep_exact_old_binding(self):
        self.assertTrue(self.check())
        receipt = self.v.receipt['eligible'][0]
        self.assertEqual(receipt['retained']['gcc_sha256'], self.old['gcc_sha256'])
        self.assertNotEqual(receipt['fresh']['gcc_sha256'], self.old['gcc_sha256'])

    def test_semantic_ast_changes_reject(self):
        self.mutate('ast', lambda data: data.update(diagnostics=['new warning']))
        self.assertFalse(self.check())

    def test_gcc_symbols_changes_reject(self):
        self.mutate('gcc', lambda data: data.update(symbols={'2': {'name': 'changed'}}))
        self.assertFalse(self.check())

    def test_source_change_rejects_even_when_both_captures_agree(self):
        self.source.write_text('int f() { return 2; }\n')
        self.assertFalse(self.check())

    def test_current_command_change_rejects(self):
        self.previous['command'] = dict(self.row, arguments=self.row['arguments'] + ['-DOLD=1'])
        self.assertFalse(self.check())

    def test_old_capture_tamper_rejects(self):
        path = Path(self.old['gcc']); path.write_text(path.read_text() + ' ')
        self.assertFalse(self.check())

    def test_external_inventory_change_rejects(self):
        self.mutate('ast', lambda data: data.update(external_inputs=['/usr/include/new.h']))
        self.assertFalse(self.check())

    def test_capture_actual_replay_command_change_rejects(self):
        self.mutate('gcc', lambda data: data['argv'].append('-DUNRECORDED=1'))
        self.assertFalse(self.check())

    def test_verified_recovery_pair_paths_are_equivalent_but_reason_is_semantic(self):
        ast = dict(self.ast, parse_clean=False, recovery={'reason': 'known provider diagnostics'})
        self.old = self.write_pair('old', ast, self.gcc)
        self.new = self.write_pair('new', ast, self.gcc)
        self.previous.update(self.old)
        self.assertTrue(self.check())
        self.mutate('ast', lambda data: data['recovery'].update(reason='different'))
        self.assertFalse(self.check())

    def test_retained_capture_mutation_after_check_rejects_before_seal(self):
        self.assertTrue(self.check())
        path = Path(self.old['ast'])
        path.write_text(path.read_text() + ' ')
        with self.assertRaisesRegex(ValueError, 'changed before publication'):
            self.v.verify_retained()

    def test_stage_skips_facts_and_mutations_for_equivalent_owner(self):
        # Execute the maintained stage function without publisher-only neo4j.
        tree = ast.parse((Path(__file__).parent / 'refresh_publish.py').read_text())
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == '_stage_compact')
        stop = RuntimeError('stop before build fact staging')
        facts = Mock(side_effect=AssertionError('unchanged owner must not regenerate facts'))
        scope = {'ROOT': self.root, 'json': json, 'clean_catalog': lambda c, p: None,
                 'facts': facts, 'build_facts': Mock(side_effect=stop)}
        exec(compile(ast.Module(body=[function], type_ignores=[]), 'refresh_publish.py', 'exec'), scope)
        c = Mock()
        c.execute.side_effect = lambda query, *args: Mock(fetchone=lambda: (
            (json.dumps(self.previous),) if query.startswith('SELECT payload FROM units') else None))
        out = self.root / 'stage'
        (out / 'observations').mkdir(parents=True)
        (out / 'observations/app-one').symlink_to(Path(self.new['ast']).parent, target_is_directory=True)
        update = Mock()
        with patch('incremental_stage.IncrementalStage', return_value=update):
            with self.assertRaisesRegex(RuntimeError, 'stop before build fact staging'):
                scope['_stage_compact'](c, out, Mock(), {'removed_units': []},
                                        [('app:one', self.row)], Mock())
        facts.assert_not_called()
        update.replace_unit.assert_not_called()
        receipt = json.loads((out / 'unchanged-observations.json').read_text())
        self.assertEqual(len(receipt['eligible']), 1)
        failure = json.loads((out / 'stage-failure.json').read_text())
        self.assertEqual(failure['phase'], 'build_facts')
        self.assertEqual(failure['owner'], '@build')
        self.assertEqual(failure['processed_units'], 1)
        self.assertEqual(failure['retained_units'], 1)
        progress = [json.loads(line) for line in (out / 'stage-progress.jsonl').read_text().splitlines()]
        self.assertEqual([record['phase'] for record in progress],
                         ['selected_owner', 'retained', 'build_facts'])
        self.mutate('ast', lambda data: data.update(diagnostics=['new warning']))
        failed_out = self.root / 'stage-owner-failure'
        (failed_out / 'observations').mkdir(parents=True)
        (failed_out / 'observations/app-one').symlink_to(Path(self.new['ast']).parent, target_is_directory=True)
        scope['facts'] = Mock(return_value=({}, []))
        update.replace_unit.side_effect = RuntimeError('journal estimate exceeds routine budget')
        with patch('incremental_stage.IncrementalStage', return_value=update):
            with self.assertRaisesRegex(RuntimeError, 'journal estimate exceeds'):
                scope['_stage_compact'](c, failed_out, Mock(), {'removed_units': []},
                                        [('app:one', self.row)], Mock())
        failure = json.loads((failed_out / 'stage-failure.json').read_text())
        self.assertEqual(failure['owner'], 'app:one')
        self.assertEqual(failure['phase'], 'replace_unit')
        self.assertEqual(failure['processed_units'], 0)
        partial = json.loads((failed_out / 'unchanged-observations.json').read_text())
        self.assertEqual(len(partial['rejected']), 1)
        self.assertIn('semantic fields differ', partial['rejected'][0]['reason'])

    def test_gcc_dump_tamper_rejects(self):
        data = json.loads(Path(self.new['gcc']).read_text())
        Path(data['dump']).write_text('tampered dump')
        self.assertFalse(self.check())


if __name__ == '__main__':
    unittest.main()
