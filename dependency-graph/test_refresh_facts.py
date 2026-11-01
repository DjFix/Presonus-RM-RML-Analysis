import json
import pathlib
import unittest
import uuid

from refresh_facts import connect, external_dependencies, merged_node, replace, requires_reconfigure, stale_units

ROOT = pathlib.Path(__file__).resolve().parents[1]


class RefreshFactsTests(unittest.TestCase):
    def setUp(self):
        self.out = ROOT / 'temp/test-work/refresh-facts' / uuid.uuid4().hex
        self.out.mkdir(parents=True)
        self.c = connect(self.out / 'facts.sqlite')
        self.evidence = self.out / 'evidence.json'; self.evidence.write_text('{}')

    def tearDown(self): self.c.close()

    def put(self, owner, edges, definition=True):
        nodes = {'fn': {'kind': 'Function', 'label': 'fn', 'metadata': {'source_definition': definition}}}
        replace(self.c, owner, {'file': owner + '.cpp'}, nodes, edges,
                {'shared.hpp': 'sha', owner + '.cpp': 'sha'}, self.evidence, self.evidence)

    def test_header_and_configuration_invalidation(self):
        self.put('a', []); self.put('b', [])
        rows = [('a', {'file': 'a.cpp'}), ('b', {'file': 'b.cpp'})]
        self.assertEqual(stale_units(self.c, rows, ['a.cpp']), ({'a'}, set()))
        self.assertEqual(stale_units(self.c, rows, ['shared.hpp']), ({'a', 'b'}, set()))
        self.assertEqual(stale_units(self.c, rows, [], True), ({'a', 'b'}, set()))
        self.assertEqual(stale_units(self.c, rows[:1], []), (set(), {'b'}))
        self.assertEqual(stale_units(self.c, [('a', {'file': 'new.cpp'})], []), ({'a'}, {'b'}))

    def test_last_contributor_removal_and_definition_demotion(self):
        edge = ('fn', 'callee', 'CALLS', 'site')
        self.put('a', [edge]); self.put('b', [edge], False)
        self.put('a', [], False)
        self.assertEqual(self.c.execute('SELECT count(*) FROM edge_facts').fetchone()[0], 1)
        self.assertFalse(json.loads(merged_node(self.c, 'fn')['metadata'])['source_definition'])
        self.put('b', [], False)
        self.assertEqual(self.c.execute('SELECT count(*) FROM edge_facts').fetchone()[0], 0)

    def test_rollback_preserves_previous_generation(self):
        self.put('a', [('fn', 'callee', 'CALLS', 'site')]); self.c.commit()
        self.put('a', []); self.c.rollback()
        self.assertEqual(self.c.execute('SELECT count(*) FROM edge_facts').fetchone()[0], 1)

    def test_optional_header_and_build_inventory_are_not_leaves(self):
        self.assertFalse(requires_reconfigure(['old.cpp', 'shared.hpp'], []))
        self.assertTrue(requires_reconfigure(['new.hpp'], ['new.hpp']))
        self.assertTrue(requires_reconfigure(['CMakeLists.txt'], []))
        self.assertTrue(requires_reconfigure([], ['new.cpp']))

    def test_external_includes_retained_without_claiming_source_hashes(self):
        (self.out / 'unit.o.d').write_text('unit.o: source.cpp /usr/include/stdio.h\n')
        row = {'directory': str(self.out), 'arguments': ['c++', '-c', 'source.cpp', '-o', 'unit.o']}
        self.assertEqual(external_dependencies(ROOT, row), ['/usr/include/stdio.h'])
