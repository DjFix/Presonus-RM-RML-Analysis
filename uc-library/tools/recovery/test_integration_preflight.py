"""Regression cases from the real installation/input/RTTI failures; no builds."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents
            if (p / 'uc-library/tools/registry').is_dir())
sys.path.insert(0, str(ROOT / 'uc-library/tools/registry'))
import integration_preflight as checks
from audit_role_build_basic_activity import check_production_compile_contracts


class IntegrationPreflightTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / 'temp/test-work/integration-preflight-regressions'
        base.mkdir(parents=True, exist_ok=True)
        # Retain failed and successful fixtures as evidence; never use system tmp.
        self.work = Path(tempfile.mkdtemp(dir=base))
        self.lib = self.work / 'library'
        self.build = self.work / 'build'
        self.build.mkdir()
        for directory in ('src', 'include/presonus', 'tests/new', 'cmake', 'tools'):
            (self.lib / directory).mkdir(parents=True, exist_ok=True)
        (self.lib / 'CMakeLists.txt').write_text('# fixture\n')
        for role in ('common', 'cs18', 'rm'):
            (self.lib / ('src/' + role + '.cpp')).write_text('// source\n')
        (self.lib / 'cmake/ProductionSourceGroups.cmake').write_text(''.join(
            'set(PRESONUS_' + role + '_SOURCES\n src/' + role + '.cpp\n)\n'
            for role in ('common', 'cs18', 'rm')))
        (self.lib / 'include/presonus/New.hpp').write_text('#pragma once\n')
        (self.lib / 'include/presonus/Private.hpp').write_text('#pragma once\n')
        (self.lib / 'tests/new/driver.cpp').write_text('// driver\n')
        (self.lib / 'tests/new/fixtures.json').write_text('{}\n')
        (self.lib / 'tools/new.py').write_text('# producer\n')
        self.install('include/presonus/New.hpp')

    def install(self, name, destination='include/presonus'):
        (self.build / 'cmake_install.cmake').write_text(
            'file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/' + destination +
            '" TYPE FILE FILES "' + str(self.lib / name) + '")\n')

    def test_new_production_header_test_and_tool_inputs_are_automatic(self):
        names, groups, headers = checks.automatic_inputs(self.lib, self.build)
        self.assertTrue({'src/common.cpp', 'src/cs18.cpp', 'src/rm.cpp',
                         'include/presonus/New.hpp', 'tests/new/driver.cpp',
                         'tests/new/fixtures.json', 'tools/new.py'} <= names)
        self.assertEqual(len(groups), 3)
        self.assertEqual(headers, {'include/presonus/New.hpp'})

    def test_private_header_remains_guarded_without_becoming_public(self):
        names, _, _ = checks.automatic_inputs(self.lib, self.build)
        self.assertNotIn('include/presonus/Private.hpp', names)
        self.assertIn('include/presonus/Private.hpp', checks.snapshot(self.lib))

    def test_real_include_include_failure_is_early(self):
        self.install('include/include/presonus/New.hpp')
        with self.assertRaisesRegex(checks.PreflightError, 'include/include/presonus'):
            checks.installed_headers(self.lib, self.build)

    def test_missing_header(self):
        (self.lib / 'include/presonus/New.hpp').unlink()
        with self.assertRaisesRegex(checks.PreflightError, 'Missing installed header'):
            checks.installed_headers(self.lib, self.build)

    def test_duplicate_install_header(self):
        p = self.build / 'cmake_install.cmake'
        p.write_text(p.read_text() * 2)
        with self.assertRaisesRegex(checks.PreflightError, 'Duplicate installed'):
            checks.installed_headers(self.lib, self.build)

    def test_wrong_install_destination(self):
        self.install('include/presonus/New.hpp', 'include/wrong')
        with self.assertRaisesRegex(checks.PreflightError, 'Unexpected install destination'):
            checks.installed_headers(self.lib, self.build)

    def test_empty_install_plan_fails_closed(self):
        (self.build / 'cmake_install.cmake').write_text('# empty\n')
        with self.assertRaisesRegex(checks.PreflightError, 'No application headers'):
            checks.installed_headers(self.lib, self.build)

    def test_unclassified_cpp(self):
        (self.lib / 'src/forgotten.cpp').write_text('// missing partition\n')
        with self.assertRaisesRegex(checks.PreflightError, 'Unclassified'):
            checks.production_groups(self.lib)

    def test_duplicate_partition_cpp(self):
        p = self.lib / 'cmake/ProductionSourceGroups.cmake'
        p.write_text(p.read_text().replace('src/cs18.cpp', 'src/cs18.cpp src/common.cpp'))
        with self.assertRaisesRegex(checks.PreflightError, 'duplicated production'):
            checks.production_groups(self.lib)

    def test_changed_private_header_fails_source_guard(self):
        before = checks.snapshot(self.lib)
        (self.lib / 'include/presonus/Private.hpp').write_text('// changed\n')
        with self.assertRaisesRegex(checks.PreflightError, 'Private.hpp'):
            checks.verify_snapshot(self.lib, before)

    def test_added_source_fails_source_guard(self):
        before = checks.snapshot(self.lib)
        (self.lib / 'tools/late.py').write_text('# changed inputs\n')
        with self.assertRaisesRegex(checks.PreflightError, 'tools/late.py'):
            checks.verify_snapshot(self.lib, before)

    def test_actual_production_compile_contracts_still_pass(self):
        library = ROOT / 'uc-library'
        counts = check_production_compile_contracts(
            library, ROOT / 'temp/core-upstream/root-integration-01',
            checks.production_groups(library))
        self.assertTrue(counts)
        self.assertEqual(set(counts.values()), {1})

    def test_actual_slchannel_rtti_contract_cannot_be_skipped(self):
        library = ROOT / 'uc-library'
        rows = json.loads((ROOT / 'temp/core-upstream/root-integration-01/'
                           'compile_commands.json').read_text())
        changed = 0
        for row in rows:
            if row['file'].endswith('/src/Presonus/SLChannel.cpp'):
                self.assertIn('-fno-rtti', row['command'])
                row['command'] = row['command'].replace('-fno-rtti', '')
                changed += 1
        self.assertEqual(changed, 1)
        (self.build / 'compile_commands.json').write_text(json.dumps(rows))
        with self.assertRaisesRegex(AssertionError, 'SLChannel.cpp'):
            check_production_compile_contracts(
                library, self.build, checks.production_groups(library))

    def test_actual_install_plan_includes_all_five_new_headers(self):
        names = checks.installed_headers(ROOT / 'uc-library',
                    ROOT / 'temp/core-upstream/root-integration-01')
        self.assertTrue({'include/presonus/SLChannel.hpp',
                         'include/presonus/MixerClientComponentBase.hpp',
                         'include/presonus/IMainScreenPageController.hpp',
                         'include/presonus/MappablePageComponent.hpp',
                         'include/presonus/surface/PageParam.hpp'} <= names)


if __name__ == '__main__':
    unittest.main()
