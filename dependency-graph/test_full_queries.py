import sqlite3
import unittest

from full_queries import QUERIES, sql_closure
from gcc_source_graph import parse_dump


class FullQueryTests(unittest.TestCase):
    def test_cycles_aliases_and_provenance_are_separate(self):
        c = sqlite3.connect(':memory:')
        c.executescript('''CREATE TABLE edges(src,dst,kind,evidence);
          INSERT INTO edges VALUES ('a','b','CALLS',''),('b','c','ALIAS_OF',''),
          ('c','a','GCC_CALLS',''),('a','field','USES_DATA',''),
          ('field','type','HAS_TYPE',''),('a','unrelated','proof_binding',''),
          ('test','tu','HAS_TEST_TU',''),('tu','caller','DEFINES_FUNCTION',''),
          ('caller','a','CALLS','');''')
        self.assertEqual(sql_closure(c, 'a'), {'a','b','c'})
        self.assertEqual(sql_closure(c, 'a', context=True), {'a','b','c','field','type'})
        self.assertEqual({r[0] for r in c.execute(QUERIES['tests'].sql, {'seed':'a'})}, {'test'})

    def test_real_gcc13_format_and_abi_alias(self):
        text = '''Initial Symbol table:
_ZN4TypeC1Ev/7 (Type::Type())
  Type: function definition analyzed alias cpp_implicit_alias
  References: _ZN4TypeC2Ev/8 (alias)
  Calls:
_ZN4TypeC2Ev/8 (Type::Type())
  Type: function definition analyzed
  Calls: helper/9
helper/9 (void helper())
  Type: function
Removing unused symbols:
'''
        records = parse_dump(text)
        self.assertEqual(records['7']['references'], [('_ZN4TypeC2Ev','8')])
        self.assertEqual(records['8']['calls'], [('helper','9')])
        self.assertEqual(records['7']['name'], '_ZN4TypeC1Ev')


if __name__ == '__main__':
    unittest.main()
