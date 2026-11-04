"""Isolated ranking tests; never acquire/release operational work claims."""
import copy
import json
import pathlib
import sqlite3
import unittest

import ranking as r


def database():
    c = sqlite3.connect(':memory:'); c.row_factory = sqlite3.Row
    c.executescript(r.SCHEMA)
    c.execute('INSERT INTO meta VALUES(?,?)', ('policy', r.POLICY.read_text()))
    c.execute('INSERT INTO meta VALUES(?,?)', ('provenance', '{"scope":"synthetic isolated test"}'))
    for name in ('a', 'b', 'c'):
        f = {k: r.feature(v) for k, v in {'instruction_count': 3, 'basic_blocks': 1, 'conditional_branches': 0, 'cfg_complete': True}.items()}
        c.execute('INSERT INTO items VALUES(?,?,?,?,?,?,?)', (name, 'function_reconstruction', 'reconstruct', 'Example', '[]', r.packed(f), name))
        c.execute('INSERT INTO states VALUES(?,?,?,?)', (name, 'remaining', 0, 'baseline'))
    c.execute('INSERT INTO requirements VALUES(?,?,?,?,?,?)', ('ab', 'a', 'b', 'callable_behavior', '{}', 0))
    c.execute('INSERT INTO requirements VALUES(?,?,?,?,?,?)', ('bc', 'b', 'c', 'callable_behavior', '{}', 0))
    r.reevaluate(c); c.commit()
    return c


def rows(c):
    return [tuple(x) for x in c.execute('SELECT * FROM evaluations ORDER BY id')]


class RankingTests(unittest.TestCase):
    def test_execution_requirements_include_tails_without_behavior_credit(self):
        c = database()
        c.execute('DELETE FROM requirements')
        native = sqlite3.connect(':memory:')
        native.row_factory = sqlite3.Row
        native.executescript('''CREATE TABLE edges(src,dst,kind,site);
            CREATE TABLE symbol_resolution(symbol_id,strategy,evidence_json);''')
        native.executemany('INSERT INTO edges VALUES(?,?,?,?)', [
            ('na', 'nb', 'ELF_CALLS', 4),
            ('na', 'nc', 'ELF_TAIL_BRANCH', 8),
            ('na', 'unmapped', 'ELF_TAIL_BRANCH', 12),
            ('nb', 'nc', 'ELF_NAME_CORRESPONDENCE', 16)])
        mapping = {'na': {'a'}, 'nb': {'b'}, 'nc': {'c'}}
        r.add_execution_requirements(c, native, {'nb': {'instructions': [1]},
                                               'nc': {'instructions': [1]}}, mapping)
        behavior = list(c.execute("SELECT * FROM requirements WHERE scope='callable_behavior'"))
        self.assertEqual({(x['consumer'], x['target']) for x in behavior},
                         {('a', 'b'), ('a', 'c'), ('a', 'unmapped')})
        self.assertTrue(all(x['satisfied'] == 0 for x in behavior))
        contexts = {x['target']: x['satisfied'] for x in c.execute(
            "SELECT * FROM requirements WHERE scope='callee_context'")}
        self.assertEqual(contexts, {'b': 1, 'c': 1, 'unmapped': 0})
        # Replaying the same immutable observations must not duplicate requirements.
        r.add_execution_requirements(c, native, {}, mapping)
        self.assertEqual(c.execute('SELECT count(*) FROM requirements').fetchone()[0], 6)

    def test_unknown_is_not_zero(self):
        self.assertEqual(r.grade(r.feature(None, 'unknown'), [0, 2, 8]), 4)
        self.assertEqual(r.grade(r.feature(0, 'partial'), [0, 2, 8]), 4)
        self.assertEqual(r.grade(r.feature(0), [0, 2, 8]), 0)

    def test_claim_complete_does_not_satisfy_call(self):
        c = database()
        r.event(c, {'id': 'done', 'changes': [{'item': 'b', 'expected_revision': 'baseline', 'canonical': 'completed'}]})
        self.assertEqual(c.execute("SELECT satisfied FROM requirements WHERE id='ab'").fetchone()[0], 0)
        self.assertEqual(c.execute("SELECT queue FROM evaluations WHERE id='a'").fetchone()[0], 'reconstruction_eligible')

    def test_events_idempotent_and_revisions_guarded(self):
        c = database()
        payload = {'id': 'claim', 'changes': [{'item': 'b', 'expected_revision': 'baseline', 'claimed': 1}]}
        first = r.event(c, payload)
        self.assertEqual(first, r.event(c, payload))
        with self.assertRaisesRegex(ValueError, 'reused'):
            r.event(c, {**payload, 'changes': []})
        with self.assertRaisesRegex(ValueError, 'stale'):
            r.event(c, {'id': 'stale', 'changes': [{'item': 'b', 'expected_revision': 'baseline', 'claimed': 0}]})

    def test_incremental_equals_full_all_fields(self):
        for canonical, claimed in [('completed', 0), ('remaining', 1), ('pending', 0), ('remaining', 0)]:
            c = database()
            r.event(c, {'id': 'event', 'changes': [{'item': 'b', 'expected_revision': 'baseline', 'canonical': canonical, 'claimed': claimed}]})
            incremental = rows(c)
            c.execute('DELETE FROM evaluations')
            r.reevaluate(c)
            self.assertEqual(incremental, rows(c))

    def test_cycles_never_self_satisfy(self):
        c = database()
        c.execute('INSERT INTO requirements VALUES(?,?,?,?,?,?)', ('ba', 'b', 'a', 'callable_behavior', '{}', 0))
        r.reevaluate(c)
        self.assertEqual(c.execute('SELECT count(*) FROM requirements WHERE satisfied=0').fetchone()[0], 3)
        self.assertEqual(r.reevaluate(c)['changed'], [])
        self.assertEqual(sorted(r.scc({'a': {'b'}, 'b': {'a'}, 'c': set()})), [['a', 'b'], ['c']])

    def test_provider_and_existing_exclusions(self):
        c = database()
        c.execute("UPDATE items SET original_kind='provider_binding' WHERE id='c'")
        c.execute("UPDATE states SET canonical='pending' WHERE id='a'")
        r.reevaluate(c)
        self.assertEqual(c.execute("SELECT queue FROM evaluations WHERE id='c'").fetchone()[0], 'provider_work')
        self.assertEqual(c.execute("SELECT queue FROM evaluations WHERE id='a'").fetchone()[0], 'completed')

    def test_empty_partial_cfg_and_pc_write(self):
        self.assertFalse(r.cfg({})['cfg_complete']['value'])
        body = {'instructions': [{'address': 0x1000, 'bytes': '000090e5', 'mnemonic': 'ldr', 'operands': 'r0, [r0]'},
                                 {'address': 0x1004, 'bytes': '00f090e5', 'mnemonic': 'ldr', 'operands': 'pc, [r0]'}]}
        f = r.cfg(body)
        self.assertFalse(f['cfg_complete']['value'])
        self.assertEqual(f['register_provenance']['state'], 'partial')

    def test_redefined_r0_is_not_this(self):
        f = r.cfg({'instructions': [{'address': 4096, 'bytes': '0000a0e3', 'mnemonic': 'mov', 'operands': 'r0, #0'},
                                  {'address': 4100, 'bytes': '001090e5', 'mnemonic': 'ldr', 'operands': 'r1, [r0]'},
                                  {'address': 4104, 'bytes': '1eff2fe1', 'mnemonic': 'bx', 'operands': 'lr'}]})
        self.assertEqual(f['memory_reads']['value'][0]['base_origin']['kind'], 'constant')
        self.assertEqual(f['proven_data_accesses']['value'][0]['address'], 0)

    def test_literal_is_dependency_only_when_consumed(self):
        body = {'literal_values': {'4096': {'cell_address': 4112, 'value': 32768}},
                'instructions': [{'address': 4096, 'bytes': '08009fe5', 'mnemonic': 'ldr', 'operands': 'r0, [pc, #8]'},
                                 {'address': 4100, 'bytes': '041090e5', 'mnemonic': 'ldr', 'operands': 'r1, [r0, #4]'},
                                 {'address': 4104, 'bytes': '1eff2fe1', 'mnemonic': 'bx', 'operands': 'lr'}]}
        self.assertEqual(r.cfg(body)['proven_data_accesses']['value'][0]['address'], 32772)
        body['instructions'].pop(1)
        self.assertEqual(r.cfg(body)['proven_data_accesses']['value'], [])

    def test_missing_context_blocks_even_if_behavior_attested(self):
        c = database()
        c.execute('INSERT INTO requirements VALUES(?,?,?,?,?,?)', ('ctx', 'a', 'b', 'callee_context', '{}', 0))
        c.execute("UPDATE requirements SET satisfied=1 WHERE id='ab'")
        r.reevaluate(c)
        self.assertEqual(c.execute("SELECT queue FROM evaluations WHERE id='a'").fetchone()[0], 'research_required')

    def test_register_arithmetic_leaf_cfg(self):
        f = r.cfg({'instructions': [{'address': 4096, 'bytes': '010080e0', 'mnemonic': 'add', 'operands': 'r0, r0, r1'},
                                  {'address': 4100, 'bytes': '1eff2fe1', 'mnemonic': 'bx', 'operands': 'lr'}]})
        self.assertTrue(f['cfg_complete']['value'])
        self.assertEqual(f['instruction_count']['value'], 2)

    def test_tie_break_and_no_leaf_quota_fill(self):
        c = database()
        result = r.plan(c)
        self.assertEqual(result['status'], 'blocked')
        self.assertFalse(result['spawn_authorized'])
        self.assertEqual(result['symbol_deficit'], 98)
        self.assertTrue(any('leaves excluded' in x['reason'] for x in result['skipped']))

    def test_global_helpers_are_not_reported_as_a_class_group(self):
        c=database()
        for i in range(10):
            name='global'+str(i)
            c.execute("INSERT INTO items SELECT ?,kind,original_kind,'',identities,features,feature_hash FROM items WHERE id='a'",(name,))
            c.execute('INSERT INTO states VALUES(?,?,?,?)',(name,'remaining',0,'baseline'))
            c.execute('INSERT INTO requirements VALUES(?,?,?,?,?,?)',(name+'call',name,'b','callable_behavior','{}',0))
        r.reevaluate(c)
        self.assertEqual(r.plan(c)['namespace_groups_with_ten'],0)
        self.assertEqual(r.plan(c,20)['namespace_groups_with_required_count'],0)

    def test_twenty_plan_deficit_is200_and_never_fills_with_leaves(self):
        c=database();result=r.plan(c,20)
        self.assertEqual(result['required_symbols'],200)
        self.assertEqual(result['packets_per_worker'],20)
        self.assertEqual(result['symbol_deficit'],198)
        self.assertEqual(result['status'],'blocked')
        self.assertFalse(result['spawn_authorized'])
        with self.assertRaises(ValueError):r.plan(c,19)

    def test_atomic_event_rollback(self):
        c = database(); before = rows(c)
        with self.assertRaises(ValueError):
            r.event(c, {'id': 'bad', 'changes': [{'item': 'b', 'expected_revision': 'baseline', 'claimed': 1},
                                              {'item': 'a', 'expected_revision': 'wrong'}]})
        self.assertEqual(before, rows(c))
        self.assertEqual(c.execute("SELECT claimed FROM states WHERE id='b'").fetchone()[0], 0)

    def test_scoped_evidence_corruption_rejected(self):
        c = database()
        with self.assertRaisesRegex(ValueError, 'evidence changed'):
            r.event(c, {'id': 'scope', 'changes': [{'item': 'b', 'expected_revision': 'baseline', 'requirements': [
                {'id': 'ab', 'satisfied': True, 'evidence': {'path': 'AGENTS.md', 'sha256': '0'*64, 'domain': 'test'}}]}]})
        self.assertEqual(c.execute("SELECT satisfied FROM requirements WHERE id='ab'").fetchone()[0], 0)

    def test_scoped_binding_demotion_and_interpretation_events(self):
        for label, scope in [('provider_binding', 'callable_behavior'), ('data_interpretation', 'consumer_binding')]:
            c = database()
            c.execute("UPDATE requirements SET scope=? WHERE id='ab'", (scope,)); c.commit()
            evidence = {'path': 'AGENTS.md', 'sha256': r.digest(r.ROOT / 'AGENTS.md'), 'domain': 'synthetic attestation to test scope updates only; not production evidence'}
            r.event(c, {'id': label, 'changes': [{'item': 'b', 'expected_revision': 'baseline', 'requirements': [{'id': 'ab', 'satisfied': True, 'evidence': evidence}]}]})
            self.assertEqual(c.execute("SELECT satisfied FROM requirements WHERE id='ab'").fetchone()[0], 1)
            incremental = rows(c); c.execute('DELETE FROM evaluations'); r.reevaluate(c)
            self.assertEqual(incremental, rows(c))
            r.event(c, {'id': label+'-demote', 'changes': [{'item': 'b', 'expected_revision': label, 'requirements': [{'id': 'ab', 'satisfied': False, 'evidence': evidence}]}]})
            self.assertEqual(c.execute("SELECT satisfied FROM requirements WHERE id='ab'").fetchone()[0], 0)
            incremental = rows(c); c.execute('DELETE FROM evaluations'); r.reevaluate(c)
            self.assertEqual(incremental, rows(c))


if __name__ == '__main__':
    unittest.main()
