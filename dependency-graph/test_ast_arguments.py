"""Keep GCC code-generation flags from breaking otherwise valid AST capture."""
import copy
import pathlib
import unittest

from code_identity import context_id
from full_source_graph import arguments


class ArgumentsTest(unittest.TestCase):
    def test_negative_instrumentation_does_not_change_original_identity(self):
        root = pathlib.Path.cwd()
        row = {
            'directory': str(root),
            'file': str(root / 'probe.cpp'),
            'arguments': ['c++', '-DVALUE=1', '-fno-instrument-functions',
                          '-ffp-contract=off', '-fno-rtti', '-o', 'probe.o',
                          '-c', str(root / 'probe.cpp')],
        }
        original = copy.deepcopy(row)
        identity = context_id(root, row)
        self.assertEqual(arguments(row), ['-DVALUE=1', '-ffp-contract=off', '-fno-rtti'])
        self.assertEqual(row, original)
        self.assertEqual(context_id(root, row), identity)

    def test_positive_and_unknown_flags_are_not_silently_dropped(self):
        row = {'file': 'probe.cpp', 'command':
               'c++ -finstrument-functions -unknown-analysis-flag -c probe.cpp -o probe.o'}
        self.assertEqual(arguments(row), ['-finstrument-functions', '-unknown-analysis-flag'])


if __name__ == '__main__':
    unittest.main()
