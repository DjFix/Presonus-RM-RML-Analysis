import copy
import unittest
from group_dispatch import check_groups
from context_runtime import ContextError


class GroupDispatchTests(unittest.TestCase):
    def fixture(self, count=5):
        groups=[];entries={};requests={}
        for i in range(10):
            paths=[f'p{i}_{j}' for j in range(count)]
            groups.append({'task_name':f'worker{i}','packets':paths,'scope_reason':'connected class scope','execution_order':paths[:]})
            for p in paths:
                entries[p]={'task_id':p,'generation_sha256':'generation','state':'dispatch_ready','selected_file_sha256':{},'work_binding':{'work_item_id':p,'covered_occurrences':[{'elf_sha256':'elf','original_mangled':p}]}}
                requests[p]={'owned_files':[f'uc-library/src/{i}.cpp']}
        return groups,entries,requests

    def test_valid_intra_group_ownership(self):
        g,e,r=self.fixture();self.assertEqual(len(check_groups(g,e,r)),50)

    def test_inter_group_overlap(self):
        g,e,r=self.fixture();e['p1_0']['selected_file_sha256']['uc-library/src/0.cpp']='hash'
        with self.assertRaisesRegex(ContextError,'overlap'):check_groups(g,e,r)

    def test_mixed_generations(self):
        g,e,r=self.fixture();e['p1_0']['generation_sha256']='other'
        with self.assertRaisesRegex(ContextError,'Mixed'):check_groups(g,e,r)

    def test_empty_context(self):
        g,e,r=self.fixture();e['p1_0']['state']='selected'
        with self.assertRaisesRegex(ContextError,'Empty'):check_groups(g,e,r)

    def test_duplicate_work(self):
        g,e,r=self.fixture();e['p1_0']['work_binding']['work_item_id']='p0_0'
        with self.assertRaisesRegex(ContextError,'Duplicate unique'):check_groups(g,e,r)

    def test_expanded_original_count(self):
        g,e,r=self.fixture();e['p1_0']['work_binding']['covered_occurrences']*=2
        with self.assertRaisesRegex(ContextError,'expands'):check_groups(g,e,r)

    def test_no_waves(self):
        g,e,r=self.fixture()
        with self.assertRaisesRegex(ContextError,'ten'):check_groups(g[:3],e,r)

    def test_ten_packets(self):
        g,e,r=self.fixture(10);self.assertEqual(len(check_groups(g,e,r,10)),100)

    def test_ten_rejects_five(self):
        g,e,r=self.fixture()
        with self.assertRaises(ContextError):check_groups(g,e,r,10)

    def test_five_rejects_ten(self):
        g,e,r=self.fixture(10)
        with self.assertRaises(ContextError):check_groups(g,e,r)

    def test_ten_negative_gates(self):
        for mutation in ('generation','empty','work','overlap','original'):
            with self.subTest(mutation=mutation):
                g,e,r=self.fixture(10)
                if mutation=='generation':e['p1_0']['generation_sha256']='other'
                if mutation=='empty':e['p1_0']['state']='selected'
                if mutation=='work':e['p1_0']['work_binding']['work_item_id']='p0_0'
                if mutation=='overlap':e['p1_0']['selected_file_sha256']['uc-library/src/0.cpp']='hash'
                if mutation=='original':e['p1_0']['work_binding']['covered_occurrences']*=2
                with self.assertRaises(ContextError):check_groups(g,e,r,10)


if __name__=='__main__':unittest.main()
