"""Exercise transitive stale dependency detection with real compiler-generated depfiles."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from sqlite_dependency_gate import digest, hydrate, inspect


class DependencyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.root=Path(self.temp.name)
        self.canonical=self.root/'canonical'
        self.workspace=self.root/'worker'
        self.header='uc-library/include/presonus/Book.hpp'
        self.parent='uc-library/include/presonus/Owner.hpp'
        self.production='uc-library/src/Owner.cpp'
        self.replay='uc-library/tests/recovery/sqlite_owner/Replay.cpp'
        for root in (self.canonical,self.workspace):
            for p in (self.header,self.parent,self.production,self.replay):
                (root/p).parent.mkdir(parents=True,exist_ok=True)
            (root/self.header).write_text('#define BOOK_VALUE 1\n')
            (root/self.parent).write_text('#include "Book.hpp"\n')
            (root/self.production).write_text('#include "presonus/Owner.hpp"\nint owner() { return BOOK_VALUE; }\n')
            (root/self.replay).write_text('#include "presonus/Owner.hpp"\nint replay() { return BOOK_VALUE; }\n')
        self.build=self.workspace/'temp/recovery-work/build'
        self.build.mkdir(parents=True)
        self.requirements=[
            {'kind':'ctest','role':'client','source':self.replay},
            {'kind':'installed_role','role':'client','source':self.production},
        ]
        self.scope={'version':1,'required_units':self.requirements}
        self.proof={'version':1,'units':self.compile()}

    def tearDown(self):
        self.temp.cleanup()

    def reference(self,path):
        return {'path':str(path.relative_to(self.workspace)),'sha256':digest(path)}

    def compile(self):
        output=[]
        for row in self.requirements:
            source=self.workspace/row['source']
            obj=self.build/(source.name+'.o')
            dep=self.build/(source.name+'.o.d')
            subprocess.run(['/usr/bin/c++','-I',str(self.workspace/'uc-library/include'),
                '-MMD','-MF',str(dep),'-c',str(source),'-o',str(obj)],cwd=self.build,check=True)
            unit={**row,'directory':str(self.build.relative_to(self.workspace)),
                  'object':self.reference(obj),'depfile':self.reference(dep)}
            if row['kind']=='installed_role':
                archive=self.build/'librole.a'
                subprocess.run(['/usr/bin/ar','rcs',str(archive),str(obj)],cwd=self.build,check=True)
                unit['archive']=self.reference(archive)
            output.append(unit)
        return output

    def test_stale_transitive_header_blocks_both_proofs(self):
        (self.canonical/self.header).write_text('#define BOOK_VALUE 2\n')
        report=inspect(self.canonical,self.workspace,self.proof,self.scope)
        self.assertFalse(report['passed'])
        self.assertEqual(set(report['drift']),{self.header})
        self.assertEqual({s['kind'] for s in report['drift'][self.header]['scopes']},
                         {'ctest','installed_role'})
        self.assertTrue(report['requires_fresh_compile_and_replay_after_hydration'])

    def test_hydration_preserves_old_file_and_requires_new_objects(self):
        old=digest(self.workspace/self.header)
        (self.canonical/self.header).write_text('#define BOOK_VALUE 2\n')
        report=inspect(self.canonical,self.workspace,self.proof,self.scope)
        archive=self.workspace/'temp/recovery-work/hydration'
        result=hydrate(self.canonical,self.workspace,report,archive)
        self.assertTrue(result['replay_required'])
        self.assertEqual(digest(archive/'predecessors'/self.header),old)
        with self.assertRaisesRegex(ValueError,'newer than compiled object'):
            inspect(self.canonical,self.workspace,self.proof,self.scope)
        self.proof['units']=self.compile()
        self.assertTrue(inspect(self.canonical,self.workspace,self.proof,self.scope)['passed'])

    def test_own_artifact_requires_exact_approved_receipt(self):
        (self.canonical/self.production).write_text('int owner() { return 42; }\n')
        self.scope['owned_artifact_hashes']={self.production:digest(self.workspace/self.production)}
        self.assertTrue(inspect(self.canonical,self.workspace,self.proof,self.scope)['passed'])
        self.scope['owned_artifact_hashes'][self.production]='0'*64
        with self.assertRaisesRegex(ValueError,'Approved artifact changed'):
            inspect(self.canonical,self.workspace,self.proof,self.scope)

    def test_deny_incomplete_installed_role(self):
        self.proof['units'].pop()
        with self.assertRaisesRegex(ValueError,'Missing required'):
            inspect(self.canonical,self.workspace,self.proof,self.scope)


if __name__=='__main__':
    unittest.main()
