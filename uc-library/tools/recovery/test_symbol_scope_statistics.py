import unittest
from symbol_scope_statistics import scope_parts, memberships, GLOBAL, UNKNOWN
from symbol_statistics import aggregate
from test_symbol_statistics import row


class ScopeTests(unittest.TestCase):
    def test_nested_and_template_scopes(self):
        self.assertEqual(scope_parts('Presonus::UC::Queue::push(Core::Buffer const&)', '_ZNx'),
                         ('Presonus','UC','Queue'))
        self.assertEqual(scope_parts('void Presonus::Map<Core::Key, Core::Value>::put<int>(int)', '_ZNx'),
                         ('Presonus','Map<Core::Key, Core::Value>'))
        self.assertEqual(scope_parts('std::string Presonus::C::get() const','_ZNx'),('Presonus','C'))

    def test_operators_thunks_and_anonymous(self):
        for name in ('Presonus::C::operator()(int)', 'Presonus::C::operator<<(int)',
                     'Presonus::C::operator Core::Value()',
                     'non-virtual thunk to Presonus::C::~C()'):
            self.assertEqual(scope_parts(name, '_ZNx'), ('Presonus','C'))
        self.assertEqual(scope_parts('(anonymous namespace)::C::f()', '_ZNx'),
                         ('(anonymous namespace)','C'))

    def test_global_unknown_and_conflict(self):
        self.assertEqual(scope_parts('png_read_info','png_read_info'),(GLOBAL,))
        self.assertEqual(scope_parts('_ZNbad','_ZNbad'),(UNKNOWN,))
        self.assertEqual(memberships([('x','A::f()'),('x','B::f()')])['x'],[UNKNOWN])

    def test_rollups_preserve_all_role_readiness_and_vendor_exclusion(self):
        rows = [row('a','f','ready'),row('b','f'),row('a','g','pending'),
                row('a','png')]
        scopes = memberships([('f','N::C::f()'),('g','N::D::g()'),('png','png')])
        report = aggregate(rows,[('a','png',1,'libpng')], scopes)
        unique = {r['scope']:r for r in report['scope_trees'][-1]['rows']}
        self.assertEqual(unique['N']['remaining'],1)
        self.assertEqual(unique['N']['partial'],1)
        self.assertEqual(unique['N']['pending'],1)
        self.assertEqual(unique[GLOBAL]['libpng'],1)
        self.assertEqual(unique['N']['total'],unique['N::C']['total']+unique['N::D']['total'])
        self.assertEqual(unique['N']['total']+unique[GLOBAL]['total'],report['unique_names'][-1]['total'])


if __name__ == '__main__':
    unittest.main()
