"""Eligibility must check every original member and preserve independent work."""
import unittest
from rolling_selection import eligibility, classify_boundary


class EligibilityTest(unittest.TestCase):
    def setUp(self):
        self.a={'id':'a','catalog_anchor':'ca','elf_sha256':'ea','original_mangled':'ma','strategy':'reconstruct'}
        self.b={'id':'b','catalog_anchor':'cb','elf_sha256':'eb','original_mangled':'mb','strategy':'reconstruct'}
        self.catalog={key:{'state':'todo','notes':''} for key in ('ca','cb')}

    def check(self, members, **kwargs):
        values=dict(admitted=set(),active=set(),reserved=set(),compiled=set())
        values.update(kwargs)
        return eligibility(members,self.catalog,**values)

    def test_admission_of_nonrepresentative_member_blocks_duplicate_work(self):
        self.assertEqual(self.check([self.a,self.b],admitted={('eb','mb')}),['already_admitted'])

    def test_carryover_nonrepresentative_member_is_not_stolen(self):
        self.assertEqual(self.check([self.a,self.b],reserved={'b'}),['carryover_owner'])

    def test_canonical_implementation_without_admission_is_excluded(self):
        self.assertEqual(self.check([self.a],compiled={'ma'}),['canonical_compiled_symbol'])

    def test_parked_work_does_not_block_independent_replacement(self):
        self.catalog['ca']['state']='blocked'
        self.assertEqual(self.check([self.a]),['catalog_blocked'])
        self.assertEqual(self.check([self.b]),[])

    def test_history_requires_explicit_review_even_if_catalog_todo(self):
        self.catalog['ca']['notes']='prior unresolved receiver; retry when typed evidence changes'
        self.assertEqual(self.check([self.a]),['history_requires_review'])


class RuntimeRoutingTest(unittest.TestCase):
    def boundary(self, names, kind='ELF_CALLS'):
        return {'kind':kind,'available_originals':[],'target_names':names}

    def test_versioned_runtime_symbol_requires_real_binding(self):
        self.assertEqual(classify_boundary(self.boundary(['strlen@@GLIBC_2.4'])),
                         'runtime_provider_requires_binding')

    def test_unknown_aeabi_name_is_not_implicitly_available(self):
        self.assertEqual(classify_boundary(self.boundary(['__aeabi_invented'])),
                         'missing_application_or_unknown_dependency')

    def test_indirect_site_remains_explicit_review_even_with_runtime_candidate(self):
        self.assertEqual(classify_boundary(self.boundary(['strlen'], 'ARM_INDIRECT_REVIEW_CANDIDATE')),
                         'indirect_requires_explicit_review')


if __name__=='__main__':unittest.main()

