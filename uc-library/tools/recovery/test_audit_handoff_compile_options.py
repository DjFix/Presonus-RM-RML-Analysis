"""Regression: flag->owned-files declarations must survive production staging."""
import unittest
from audit_handoff_compile_options import audit, handoff_task

ROOT = '/project'
A = 'uc-library/src/A.cpp'
B = 'uc-library/src/B.cpp'


def task(build):
    return {'build': build, 'plan': {'files': [{'path': A}, {'path': B}]},
            'canonical_registration': {'primary_source': A}}


def unit(source, *flags, role='common', arguments=True):
    argv = ['c++', '-O2', *flags, '-c', ROOT + '/' + source,
            '-o', 'CMakeFiles/presonus_' + role + '_objects.dir/' + source + '.o']
    row = {'file': ROOT + '/' + source, 'directory': ROOT}
    row['arguments' if arguments else 'command'] = argv if arguments else ' '.join(argv)
    return row


class HandoffCompileOptionsTest(unittest.TestCase):
    def test_old_loss_of_flag_to_paths_is_rejected(self):
        tasks = [task({'scoped_production_compile_options':
                       {'-fno-sized-deallocation': [A, B]}})]
        report = audit(tasks, [unit(A), unit(B)], ROOT)
        self.assertFalse(report['passed'])
        self.assertEqual(len(report['errors']), 2)
        self.assertIn('-fno-sized-deallocation', report['errors'][0])
        self.assertTrue(audit(tasks, [unit(A, '-fno-sized-deallocation'),
                                     unit(B, '-fno-sized-deallocation')], ROOT)['passed'])

    def test_both_real_schemas_and_shell_command(self):
        tasks = [task({'production_compile_options': {A: ['-ffp-contract=off']},
                       'scoped_production_compile_options': {'-fno-sized-deallocation': [B]},
                       'compile_options': {'test': ['-DTEST_ONLY']}})]
        self.assertTrue(audit(tasks, [unit(A, '-ffp-contract=off', arguments=False),
                                     unit(B, '-fno-sized-deallocation')], ROOT)['passed'])

    def test_required_flag_overridden_later_is_rejected(self):
        tasks = [task({'production_compile_options': {A: ['-fno-rtti', '-ffp-contract=off']}})]
        report = audit(tasks, [unit(A, '-fno-rtti', '-frtti', '-ffp-contract=off', '-ffp-contract=fast')], ROOT)
        self.assertEqual(len(report['errors']), 2)

    def test_scope_leak_is_new_against_comparable_baseline(self):
        tasks = [task({'production_compile_options': {A: ['-fno-sized-deallocation']}})]
        current = [unit(A, '-fno-sized-deallocation'), unit(B, '-fno-sized-deallocation')]
        report = audit(tasks, current, ROOT, baseline=[unit(A), unit(B)])
        self.assertFalse(report['passed'])
        self.assertEqual(report['scope_leak_audit']['new_out_of_scope_flags'],
                         [{'source': B, 'flag': '-fno-sized-deallocation'}])
        self.assertTrue(audit(tasks, current, ROOT, baseline=current)['passed'])

    def test_no_baseline_does_not_claim_no_leaks(self):
        tasks = [task({'production_compile_options': {A: ['-fno-rtti']}})]
        report = audit(tasks, [unit(A, '-fno-rtti'), unit(B)], ROOT)
        self.assertFalse(report['scope_leak_audit']['baseline_available'])
        report = audit(tasks, [unit(A, '-fno-rtti'), unit(B)], ROOT, baseline=[unit(A)])
        self.assertEqual(report['scope_leak_audit']['sources_without_baseline'], [B])

    def test_unowned_scoped_source_and_duplicate_compile_reject(self):
        with self.assertRaisesRegex(ValueError, 'unowned'):
            audit([task({'scoped_production_compile_options': {'-fno-rtti': ['src/C.cpp']}})], [], ROOT)
        with self.assertRaisesRegex(ValueError, 'more than once'):
            audit([task({})], [unit(A), unit(A, role='rm')], ROOT)

    def test_response_file_does_not_establish_effective_flags(self):
        tasks = [task({'production_compile_options': {A: ['-fno-rtti']}})]
        self.assertFalse(audit(tasks, [unit(A, '-fno-rtti', '@unknown.rsp')], ROOT)['passed'])

    def test_raw_handoff_and_primary_list(self):
        h = {'task_id': 'one', 'artifacts': [{'kind': 'source', 'path': A}],
             'build_integration': {'production_sources': [A],
                                   'production_compile_options': ['-fno-rtti']}}
        self.assertTrue(audit([handoff_task(h)], [unit(A, '-fno-rtti')], ROOT)['passed'])
        h['build_integration']['production_sources'] = {A: 'rm'}
        self.assertTrue(audit([handoff_task(h)], [unit(A, '-fno-rtti')], ROOT)['passed'])


if __name__ == '__main__':
    unittest.main()
