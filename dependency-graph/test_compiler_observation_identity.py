"""GCC serials identify records only within an exact compiler capture."""
import hashlib
import json
import pathlib
import unittest
import uuid

from code_identity import context_id
from refresh_facts import connect, facts, merged_node

ROOT = pathlib.Path(__file__).resolve().parents[1]


class CompilerObservationIdentityTests(unittest.TestCase):
    def setUp(self):
        self.out = ROOT / 'temp/test-work/compiler-observation-identity' / uuid.uuid4().hex
        self.out.mkdir(parents=True)
        self.row = {'directory': str(self.out), 'file': str(self.out / 'unit.cpp'),
                    'arguments': ['c++', '-c', 'unit.cpp', '-o', 'unit.o']}
        self.ast = self.out / 'ast.json'
        self.ast.write_text(json.dumps({'passed': True, 'nodes': {
            'old-tu': {'kind': 'TranslationUnit', 'label': 'unit', 'metadata': {}},
            'function:_Z5namedv': {'kind': 'Function', 'label': 'named',
                                   'metadata': {'mangled': '_Z5namedv'}}}, 'edges': []}))

    def capture(self, kind, filename):
        records = {
            '7': {'name': '<unnamed>', 'demangled': kind, 'type': kind,
                  'definition': True, 'calls': [('_Z5namedv', '8'), ('external_named', '98'), ('<unknown>', '99')],
                  'references': [], 'indirect': ['unknown target']},
            '8': {'name': '_Z5namedv', 'demangled': 'named()', 'type': 'function',
                  'definition': True, 'calls': [], 'references': [('<unnamed>', '7')],
                  'indirect': []}}
        path = self.out / filename
        path.write_text(json.dumps({'returncode': 0, 'symbols': records}))
        return path

    def test_capture_scopes_serials_and_incident_edges_but_not_named_or_ast_nodes(self):
        first = self.capture('function', 'first.json')
        second = self.capture('variable', 'second.json')
        duplicate = self.out / 'duplicate.json'
        duplicate.write_bytes(first.read_bytes())
        results = [facts(ROOT, 'owner', self.row, self.ast, path, {})
                   for path in (first, second, duplicate)]
        self.assertEqual(results[0], results[2])
        scoped = []
        for path, (nodes, edges), kind in zip((first, second), results, ('Function', 'Data')):
            scope = context_id(ROOT, self.row) + ':' + hashlib.sha256(path.read_bytes()).hexdigest()
            record = 'compiler:' + scope + ':7'
            unresolved = 'unresolved:gcc:' + scope + ':7:0'
            unknown = 'compiler:' + scope + ':99'
            self.assertEqual(nodes[record]['kind'], kind)
            self.assertEqual(nodes['function:_Z5namedv']['kind'], 'Function')
            self.assertEqual(nodes['function:external_named']['metadata']['mangled'], 'external_named')
            self.assertIn('tu:' + context_id(ROOT, self.row), nodes)
            triples = {(src, dst, relation) for src, dst, relation, _ in edges}
            self.assertIn((record, 'function:_Z5namedv', 'GCC_CALLS'), triples)
            self.assertIn(('function:_Z5namedv', record, 'GCC_REFERENCES'), triples)
            self.assertIn((record, unknown, 'GCC_CALLS'), triples)
            self.assertIn((record, unresolved, 'GCC_UNRESOLVED'), triples)
            scoped.append({record, unresolved, unknown})
        self.assertTrue(scoped[0].isdisjoint(scoped[1]))
        self.assertTrue(scoped[0].isdisjoint(results[1][0]))
        self.assertTrue(scoped[1].isdisjoint(results[0][0]))


    def test_same_kind_serial_reuse_is_scoped_to_exact_capture(self):
        first = self.capture('function', 'same-kind-first.json')
        second = self.capture('function', 'same-kind-second.json')
        payload = json.loads(second.read_text())
        payload['symbols']['7']['demangled'] = 'another unnamed function'
        second.write_text(json.dumps(payload))
        duplicate = self.out / 'same-kind-duplicate.json'
        duplicate.write_bytes(second.read_bytes())
        results = [facts(ROOT, 'owner', self.row, self.ast, path, {})
                   for path in (first, second, duplicate)]
        self.assertEqual(results[1], results[2])
        first_ids = {key for key in results[0][0] if key.startswith('compiler:')}
        second_ids = {key for key in results[1][0] if key.startswith('compiler:')}
        self.assertTrue(first_ids)
        self.assertTrue(second_ids)
        self.assertTrue(first_ids.isdisjoint(second_ids))
        for nodes, edges in results[:2]:
            source = next(key for key, value in nodes.items()
                          if key.startswith('compiler:') and value['label'] in
                          ('function', 'another unnamed function'))
            self.assertTrue(any(src == source and kind == 'GCC_UNRESOLVED'
                                for src, _, kind, _ in edges))

    def test_merge_rejects_heterogeneous_kinds_independent_of_owner_order(self):
        from compact_facts import CompactFacts
        with connect(self.out / 'facts.sqlite') as connection:
            for index, kinds in enumerate((('Function', 'Data'), ('Data', 'Function'))):
                key = 'collision:' + str(index)
                store = CompactFacts(connection)
                store.replace_owner('a', {key: dict(kind=kinds[0], label='a', metadata={})}, [])
                with self.assertRaises(ValueError):
                    store.replace_owner('z', {key: dict(kind=kinds[1], label='z', metadata={})}, [])
                self.assertEqual(merged_node(connection, key)['kind'], kinds[0])
            self.assertIsNone(merged_node(connection, 'absent'))

if __name__ == '__main__':
    unittest.main()
