import json
import os
import pathlib
import unittest
import uuid

from context_runtime import ContextError, fingerprint, guard, inside, inventory, sha, validate_task, validate_original_scope

ROOT=pathlib.Path(__file__).resolve().parents[1]


class ContextRuntimeTests(unittest.TestCase):
    def test_mixed_cpp_scopes_require_exact_explicit_original_ranges(self):
        target = {'original_elf_sha256': 'a'*64, 'mangled': '_ZN8Presonus15IColorConverterD1Ev',
                  'address': 100, 'size': 28}
        original = {'elf': 'a'*64, 'mangled': target['mangled'], 'address': 100,
                    'size': 28, 'demangled': 'Presonus::IColorConverter::~IColorConverter()'}
        task = {'task_id': 'mixed_scope', 'objective': 'Compare exact destructor aliases',
                'namespace': 'MixerColorConverter', 'mode': 'research', 'owned_files': [],
                'targets': [target]}
        with self.assertRaisesRegex(ContextError, 'outside'):
            validate_original_scope(task, original)
        task['additional_original_scopes'] = [dict(target, namespace='Presonus::IColorConverter',
                                                  reason='Explicitly assigned base alias comparison')]
        validate_task(task)
        validate_original_scope(task, original)
        with self.assertRaisesRegex(ContextError, 'range'):
            validate_original_scope(task, dict(original, size=24))
        with self.assertRaisesRegex(ContextError, 'outside'):
            validate_original_scope(task, dict(original, elf='b'*64))
        with self.assertRaisesRegex(ContextError, 'outside'):
            validate_original_scope(task, dict(original, demangled='Unrelated::method()'))
        task['additional_original_scopes'].append(task['additional_original_scopes'][0])
        with self.assertRaisesRegex(ContextError, 'unique'):
            validate_task(task)

    def test_global_cpp_scope_is_per_function_not_an_unrestricted_namespace(self):
        target = {'original_elf_sha256': 'a'*64, 'mangled': '_Z4leafv', 'address': 120, 'size': 16}
        task = {'task_id': 'global_cpp', 'objective': 'Compare exact no-op group',
                'namespace': 'Example::Controller', 'mode': 'research', 'owned_files': [],
                'targets': [target], 'additional_original_scopes': [dict(target,
                    namespace='::', linkage_scope='global_cpp', reason='Exact global function member')]}
        validate_task(task)
        original = dict(elf='a'*64, mangled=target['mangled'], address=120,
                        size=16, demangled='leaf()')
        validate_original_scope(task, original)
        for name in ('Other::leaf()', 'vtable for Example'):
            with self.assertRaisesRegex(ContextError, 'outside'):
                validate_original_scope(task, dict(original, demangled=name))
        task['additional_original_scopes'][0]['namespace'] = '::Other'
        with self.assertRaisesRegex(ContextError, 'scope'):
            validate_task(task)

    def fixture(self):
        root=ROOT/'temp/test-work/context-gate'/uuid.uuid4().hex
        source=root/'uc-library/src/sample.cpp'
        source.parent.mkdir(parents=True)
        source.write_text('int sample() { return 1; }\n')
        state={'files':{'uc-library/src/sample.cpp':{'sha256':sha(source),'fingerprint':fingerprint(source)}},
               'source_inventory':inventory(root)}
        path=root/'state.json';path.write_text(json.dumps(state))
        return root,source,{'state':'state.json','state_sha256':sha(path)}

    def test_detects_changed_bytes_and_new_source(self):
        root,source,active=self.fixture()
        guard(root,active)
        source.write_text('int sample() { return 2; }\n')
        with self.assertRaisesRegex(ContextError,'stale'):guard(root,active)
        root,source,active=self.fixture()
        (source.parent/'new.cpp').write_text('int added;\n')
        with self.assertRaisesRegex(ContextError,'stale'):guard(root,active)

    def test_touch_with_identical_bytes_is_not_semantic_staleness(self):
        root,source,active=self.fixture()
        os.utime(source,ns=(source.stat().st_atime_ns,source.stat().st_mtime_ns+1000000))
        guard(root,active)

    def test_paths_and_ownership_fail_closed(self):
        with self.assertRaises(ContextError):inside(ROOT,'../escape')
        task={'task_id':'sample','objective':'reconstruct','namespace':'Presonus::Panel::ControlRegistrar',
              'mode':'reconstruct','owned_files':['uc-library/CMakeLists.txt'],
              'targets':[{'original_elf_sha256':'a'*64,'mangled':'_Zsample'}]}
        with self.assertRaisesRegex(ContextError,'Root'):validate_task(task)
        task['owned_files']=['uc-library/src/sample.cpp']
        task['unmapped_policy']='research'
        with self.assertRaisesRegex(ContextError,'research'):validate_task(task)
        task.pop('unmapped_policy')
        task['owned_files']=['uc-library/src/../CMakeLists.txt']
        with self.assertRaisesRegex(ContextError,'canonical'):validate_task(task)


if __name__=='__main__':unittest.main()
