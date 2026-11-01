import json
import os
import pathlib
import unittest
import uuid

from context_runtime import ContextError, fingerprint, guard, inside, inventory, sha, validate_task

ROOT=pathlib.Path(__file__).resolve().parents[1]


class ContextRuntimeTests(unittest.TestCase):
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
