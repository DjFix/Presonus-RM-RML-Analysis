"""Admission CLI safety regression tests; synthetic proofs are not firmware evidence."""
import contextlib
import hashlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adapter
import registry as reg
import schema
import workflow

spec = importlib.util.spec_from_file_location('merger_under_test', HERE.parent/'merge_readiness.py')
merger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merger)


class MergerTests(unittest.TestCase):
    def setUp(self):
        scratch = HERE.parents[2]/'temp/test-work/registry-merger'
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.lib = self.root/'library'
        self.lib.mkdir()
        self.source = self.lib/'src/example.cpp'
        self.source.parent.mkdir()
        self.source.write_text('int foo() { return 1; }\n')
        self.source_hash = reg.digest(self.source)
        self.write('validation/formatting.json', {'format_check_passed':True, 'files':{'src/example.cpp':self.source_hash}})
        self.write('validation/integration.json', {'ctest_passed':True, 'files':{'src/example.cpp':self.source_hash}})
        self.elf = 'a'*64
        for role in ('client', 'server'):
            self.write('recovered-all/'+role+'/manifest.json', {'sha256':self.elf if role=='client' else 'b'*64})
            self.write('recovered-all/'+role+'/symbols.json', [dict(kind='STT_FUNC',section=1,size=4,address=i,mangled=n) for i,n in [(100,'_Z3foov'),(104,'_Z3barv')]] if role=='client' else [])
        self.write('proof.json', {'cpp_differential_passed':True,'compiled_mangled_names_matched':True,'mangled_names':['_Z3foov'],'portable_ready':True})
        self.entry = dict(original_elf_sha256=self.elf,mangled='_Z3foov',original_address=100,
                          portable_ready=True,domain='Synthetic integer return fixture',
                          validation='proof.json',validation_sha256=reg.digest(self.lib/'proof.json'),
                          sources={'src/example.cpp':self.source_hash},original_function_verified=False,
                          hardware_verified=False,declaration_uncertainties=[],
                          formatting_reference='validation/formatting.json',
                          formatting_sha256=reg.digest(self.lib/'validation/formatting.json'))
        self.write('validation/ready-functions.json', {'functions':[self.entry],'integration_reference':'validation/integration.json','original_full_verification':False})
        self.write('validation/compiled-functions.json', {'functions':[]})
        snapshots = self.root/'snapshots'
        reg.capture({'ready':self.lib/'validation/ready-functions.json','pending':self.lib/'validation/compiled-functions.json'}, snapshots)
        baseline = self.root/'baseline.sqlite'
        reg.import_snapshots(snapshots, baseline)
        self.db = self.root/'working.sqlite'
        workflow.working_copy(baseline, self.db)
        schema.upgrade(self.db, self.root/'before-migration.sqlite', apply=True)
        self.write('validation/registry-sqlite/ACTIVE.json', {'database':{'absolute_path':str(self.db)}})
        # Consumers must never read or overwrite these retired JSON ledgers.
        for name in ('ready-functions.json','compiled-functions.json'):
            (self.lib/'validation'/name).write_text('retired JSON must remain untouched\n')

    def write(self, relative, value):
        path = self.lib/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value)+'\n')

    def run_merger(self, *args):
        with patch.object(sys,'argv',['merge_readiness.py','--library',str(self.lib),*args]), contextlib.redirect_stdout(io.StringIO()) as output:
            merger.main()
        return json.loads(output.getvalue())

    def legacy_bytes(self):
        return [(self.lib/'validation'/name).read_bytes() for name in ('ready-functions.json','compiled-functions.json')]

    def test_default_sqlite_noop_preserves_json_and_database(self):
        old = self.legacy_bytes()
        before = reg.digest(self.db)
        self.assertEqual(self.run_merger('--dry-run')['portable_ready_entries'],1)
        self.assertEqual(reg.digest(self.db),before)
        result = self.run_merger()
        self.assertEqual(result['sqlite_commit']['changed'],0)
        self.assertEqual(reg.digest(self.db),before)
        self.assertEqual(self.legacy_bytes(),old)

    def test_pending_admission_and_guarded_demotion(self):
        pending = dict(self.entry,portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True)
        self.write('pending.json', {'functions':[pending]})
        before = reg.digest(self.db)
        with self.assertRaises(AssertionError):
            self.run_merger('--pending','pending.json')
        self.assertEqual(reg.digest(self.db),before)
        self.write('demote.json', {'demotions':[dict(original_elf_sha256=self.elf,mangled='_Z3foov',previous_validation_sha256=self.entry['validation_sha256'],reason='Synthetic declaration uncertainty')]})
        result = self.run_merger('--pending','pending.json','--demote','demote.json')
        self.assertEqual(result['sqlite_commit']['changed'],1)
        with adapter.snapshot(self.lib) as current:
            self.assertEqual(len(current.ready['functions']),0)
            self.assertEqual(len(current.pending['functions']),1)
            row = current.c.execute('SELECT bindings FROM journal').fetchone()
            self.assertIn('demote.json',row[0])

    def test_stale_source_fails_both_modes_without_removal(self):
        before = reg.digest(self.db)
        self.source.write_text('int foo() { return 22; }\n')
        for args in (('--dry-run',),()):
            with self.assertRaises(AssertionError):
                self.run_merger(*args)
            self.assertEqual(reg.digest(self.db),before)

    def test_cached_file_and_symlink_changes_fail_final_guard(self):
        cache = merger.ValidationCache()
        cache.sha(self.source)
        self.source.write_text('changed length\n')
        with self.assertRaises(AssertionError):
            cache.unchanged()
        alternate = self.source.with_name('alternate.cpp')
        alternate.write_text('other\n')
        link = self.source.with_name('link.cpp')
        link.symlink_to(self.source)
        cache = merger.ValidationCache()
        cache.sha(link)
        link.unlink()
        link.symlink_to(alternate)
        with self.assertRaises(AssertionError):
            cache.unchanged()


    def two_record_fragment(self, shared_name='src/example.cpp'):
        self.write('two-proof.json', {'cpp_differential_passed': True,
            'compiled_mangled_names_matched': True,
            'mangled_names': ['_Z3foov', '_Z3barv'], 'portable_ready': True})
        first = dict(self.entry, validation='two-proof.json',
            validation_sha256=reg.digest(self.lib/'two-proof.json'),
            sources={shared_name: self.source_hash})
        second = dict(first, mangled='_Z3barv', original_address=104,
                      sources=dict(first['sources']))
        self.write('two.json', {'functions': [first, second]})
        return first, second

    def test_shared_binding_across_distinct_maps_checks_path_once(self):
        self.two_record_fragment()
        checked = self.source.resolve()
        calls = []
        original = pathlib.Path.is_file
        def observe(path):
            if path == checked:
                calls.append(path)
            return original(path)
        with patch.object(pathlib.Path, 'is_file', observe):
            result = self.run_merger('--fragment', 'two.json', '--dry-run')
        self.assertEqual(result['portable_ready_entries'], 2)
        self.assertEqual(len(calls), 1)

    def test_shared_path_with_different_digest_is_not_reused(self):
        first, second = self.two_record_fragment()
        second['sources']['src/example.cpp'] = '0'*64
        self.write('two.json', {'functions': [first, second]})
        before = reg.digest(self.db)
        for options in [('--dry-run',), ()]:
            with self.assertRaisesRegex(AssertionError, 'stale source seal'):
                self.run_merger('--fragment', 'two.json', *options)
            self.assertEqual(reg.digest(self.db), before)

    def test_new_binding_still_requires_formatting(self):
        first, second = self.two_record_fragment()
        extra = self.lib/'src/unformatted.cpp'
        extra.write_text('int extra() { return 0; }\n')
        second['sources']['src/unformatted.cpp'] = reg.digest(extra)
        self.write('two.json', {'functions': [first, second]})
        with self.assertRaisesRegex(AssertionError, 'source not format-checked'):
            self.run_merger('--fragment', 'two.json', '--dry-run')

    def test_binding_cache_does_not_survive_an_invocation(self):
        first, second = self.two_record_fragment()
        extra = self.lib/'extra.txt'
        extra.write_text('unchanged\n')
        for row in (first, second):
            row['sources']['extra.txt'] = reg.digest(extra)
        self.write('two.json', {'functions': [first, second]})
        self.run_merger('--fragment', 'two.json', '--dry-run')
        extra.write_text('changed between independent operations\n')
        with self.assertRaisesRegex(AssertionError, 'stale source seal'):
            self.run_merger('--fragment', 'two.json', '--dry-run')

    def test_repeated_binding_hit_keeps_final_file_race_guard(self):
        self.two_record_fragment()
        before = reg.digest(self.db)
        original = merger.proof_covers
        def mutate(proof, entry):
            if entry['mangled'] == '_Z3barv':
                self.source.write_text('changed after first binding check\n')
            return original(proof, entry)
        with patch.object(merger, 'proof_covers', mutate):
            with self.assertRaisesRegex(AssertionError, 'evidence changed after validation'):
                self.run_merger('--fragment', 'two.json')
        self.assertEqual(reg.digest(self.db), before)

    def test_repeated_binding_hit_keeps_final_symlink_race_guard(self):
        alias = self.lib/'src/alias.cpp'
        alternate = self.lib/'src/same-content.cpp'
        alternate.write_bytes(self.source.read_bytes())
        alias.symlink_to(self.source.name)
        self.write('validation/formatting.json', {'format_check_passed': True,
            'files': {'src/example.cpp': self.source_hash, 'src/alias.cpp': self.source_hash}})
        self.two_record_fragment('src/alias.cpp')
        before = reg.digest(self.db)
        original = merger.proof_covers
        def retarget(proof, entry):
            if entry['mangled'] == '_Z3barv':
                alias.unlink()
                alias.symlink_to(alternate.name)
            return original(proof, entry)
        with patch.object(merger, 'proof_covers', retarget):
            with self.assertRaisesRegex(AssertionError, 'evidence path changed'):
                self.run_merger('--fragment', 'two.json')
        self.assertEqual(reg.digest(self.db), before)


if __name__ == '__main__':
    unittest.main()
