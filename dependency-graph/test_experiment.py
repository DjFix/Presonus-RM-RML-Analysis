import sqlite3
import unittest

from experiment import dependencies, impact
from graph_query import impact as portable_impact


class ExperimentTests(unittest.TestCase):
    def test_make_escaping(self):
        text = 'a.o: a.cpp dir/a\\ b.hpp ' + '\\' + '\n c.hpp\n'
        self.assertEqual(dependencies(text),
                         (['a.o'], ['a.cpp', 'dir/a b.hpp', 'c.hpp']))

    def test_cycle_and_edge_domains(self):
        c = sqlite3.connect(':memory:')
        c.executescript('''CREATE TABLE nodes(id,kind,label);
          CREATE TABLE edges(src,dst,kind);
          INSERT INTO nodes VALUES('h','file','h'),('o','object','o'),
          ('a','archive','a'),('s','symbol','s');
          INSERT INTO edges VALUES('o','h','code'),('a','o','code'),
          ('o','a','code'),('s','h','proof');''')
        self.assertEqual({r[0] for r in impact(c, 'h', ('code',))}, {'h', 'o', 'a'})
        self.assertEqual({r[0] for r in impact(c, 'h', ('proof',))}, {'h', 's'})
        self.assertEqual(impact(c, 'h', ('code',)), portable_impact(c, 'h', ('code',)))


if __name__ == '__main__':
    unittest.main()
