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


if __name__ == '__main__':
    unittest.main()
