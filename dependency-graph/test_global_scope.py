import unittest
from context_runtime import ContextError, validate_original_scope, validate_task


class GlobalScopeTests(unittest.TestCase):
    def test_cpp_namespace_gate_unchanged(self):
        target={'mangled':'_ZN8Presonus3Dsp3fooEv','demangled':'Presonus::Dsp::foo()'}
        validate_original_scope({'namespace':'Presonus::Dsp'},target)
        with self.assertRaises(ContextError):validate_original_scope({'namespace':'Presonus::Other'},target)

    def test_global_requires_explicit_marker(self):
        target={'mangled':'getSharedLink','demangled':'getSharedLink'}
        with self.assertRaises(ContextError):validate_original_scope({'namespace':'global'},target)
        validate_original_scope({'namespace':'::','linkage_scope':'global_elf'},target)

    def test_global_cannot_admit_cpp_scope_or_mangling(self):
        task={'namespace':'::','linkage_scope':'global_elf'}
        for target in ({'mangled':'_Z3foov','demangled':'foo()'},
                       {'mangled':'plain','demangled':'Presonus::Dsp::plain()'}):
            with self.assertRaises(ContextError):validate_original_scope(task,target)

    def test_task_cannot_use_implicit_global_namespace(self):
        task={'task_id':'global_test','objective':'test','namespace':'::','mode':'reconstruct',
              'owned_files':['uc-library/src/test.cpp'],'targets':[{'original_elf_sha256':'a'*64,'mangled':'plain'}]}
        with self.assertRaises(ContextError):validate_task(task)
        validate_task({**task,'linkage_scope':'global_elf'})


if __name__=='__main__':unittest.main()
