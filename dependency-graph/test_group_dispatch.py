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

    def small_fixture(self):
        g,e,r=self.fixture()
        g=g[:2]
        for group,count in zip(g,(1,3)):
            group['packets']=group['packets'][:count]
            group['execution_order']=group['packets'][:]
        paths={p for group in g for p in group['packets']}
        return g,{p:v for p,v in e.items() if p in paths},{p:v for p,v in r.items() if p in paths}

    def test_explicit_smaller_unequal_groups(self):
        g,e,r=self.small_fixture()
        self.assertEqual(len(check_groups(g,e,r,allow_smaller=True)),4)
        with self.assertRaisesRegex(ContextError,'ten'):check_groups(g,e,r)

    def test_smaller_retains_every_negative_gate(self):
        for mutation in ('generation','empty','work','overlap','original','extra'):
            with self.subTest(mutation=mutation):
                g,e,r=self.small_fixture()
                if mutation=='generation':e['p1_0']['generation_sha256']='other'
                if mutation=='empty':e['p1_0']['state']='selected'
                if mutation=='work':e['p1_0']['work_binding']['work_item_id']='p0_0'
                if mutation=='overlap':e['p1_0']['selected_file_sha256']['uc-library/src/0.cpp']='hash'
                if mutation=='original':e['p1_0']['work_binding']['covered_occurrences']*=2
                if mutation=='extra':e['outside']=e['p1_0']
                with self.assertRaises(ContextError):check_groups(g,e,r,allow_smaller=True)

    def test_smaller_cannot_be_empty(self):
        with self.assertRaises(ContextError):check_groups([],{}, {},allow_smaller=True)
        g,e,r=self.small_fixture();g[0]['packets']=[]
        with self.assertRaises(ContextError):check_groups(g,e,r,allow_smaller=True)

    def production_fixture(self):
        g,e,r=self.small_fixture()
        for index,(path,entry) in enumerate(e.items()):
            targets=entry['work_binding']['covered_occurrences']
            if index == 0:
                targets.append({'elf_sha256':'elf','original_mangled':'co-covered'})
            for offset,t in enumerate(targets):
                t.update(original_address=100+index*16+offset*4,original_size=4)
            entry['work_binding'].update(work_kind='reconstruct',equivalence_decision_id='verified-decision',
                                         verification_scope='shared_portable_implementation')
            r[path].update(mode='reconstruct',originals=[{'original':{'elf':t['elf_sha256'],
                'mangled':t['original_mangled'],'address':t['original_address'],'size':t['original_size']}} for t in targets])
        return g,e,r

    def test_production_preserves_all_originals_without_changing_trial_gate(self):
        g,e,r=self.production_fixture()
        self.assertEqual(len(check_groups(g,e,r,allow_smaller=True,production_continuation='Close existing lifecycle targets')),4)
        with self.assertRaisesRegex(ContextError,'expands'):
            check_groups(g,e,r,allow_smaller=True)

    def test_production_rejects_incomplete_or_unverified_original_coverage(self):
        for mutation in ('missing','extra','range','malformed','duplicate','unverified','generation','overlap','empty','work'):
            with self.subTest(mutation=mutation):
                g,e,r=self.production_fixture()
                if mutation=='missing':r['p0_0']['originals'].pop()
                if mutation=='extra':r['p0_0']['originals'].append({'original':{'elf':'elf','mangled':'extra','address':99,'size':4}})
                if mutation=='range':r['p0_0']['originals'][0]['original']['size']=8
                if mutation=='malformed':e['p0_0']['work_binding']['covered_occurrences'][0].pop('original_address')
                if mutation=='duplicate':e['p0_0']['work_binding']['covered_occurrences']*=2
                if mutation=='unverified':e['p0_0']['work_binding']['verification_scope']='unresolved'
                if mutation=='generation':e['p1_0']['generation_sha256']='other'
                if mutation=='overlap':e['p1_0']['selected_file_sha256']['uc-library/src/0.cpp']='hash'
                if mutation=='empty':e['p0_0']['state']='selected'
                if mutation=='work':e['p1_0']['work_binding']['work_item_id']='p0_0'
                with self.assertRaises(ContextError):
                    check_groups(g,e,r,allow_smaller=True,production_continuation='Close existing lifecycle targets')

    def test_production_requires_explicit_bounded_scope(self):
        g,e,r=self.production_fixture()
        for scope in ('',True,{}):
            with self.assertRaises(ContextError):
                check_groups(g,e,r,allow_smaller=True,production_continuation=scope)
        with self.assertRaises(ContextError):
            check_groups(g,e,r,production_continuation='Close existing targets')

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


    def test_twenty_packets_exact200(self):
        g,e,r=self.fixture(20);self.assertEqual(len(check_groups(g,e,r,20)),200)

    def test_twenty_retains_negative_gates(self):
        for mutation in ('generation','empty','work','overlap','original','identity','order','coverage','waves'):
            with self.subTest(mutation=mutation):
                g,e,r=self.fixture(20)
                if mutation=='generation':e['p1_0']['generation_sha256']='other'
                if mutation=='empty':e['p1_0']['state']='selected'
                if mutation=='work':e['p1_0']['work_binding']['work_item_id']='p0_0'
                if mutation=='overlap':e['p1_0']['selected_file_sha256']['uc-library/src/0.cpp']='hash'
                if mutation=='original':e['p1_0']['work_binding']['covered_occurrences']*=2
                if mutation=='identity':e['p1_0']['work_binding']['covered_occurrences']=e['p0_0']['work_binding']['covered_occurrences']
                if mutation=='order':g[0]['execution_order']=g[0]['execution_order'][:-1]
                if mutation=='coverage':g[0]['packets']=g[0]['packets'][:-1]
                if mutation=='waves':g=g[:5]
                with self.assertRaises(ContextError):check_groups(g,e,r,20)

    def test_group_sizes_do_not_silently_mix(self):
        for expected,actual in ((20,10),(10,20),(5,20),(20,5)):
            g,e,r=self.fixture(actual)
            with self.assertRaises(ContextError):check_groups(g,e,r,expected)

    def test_flexible200_eight_workers25(self):
        g,e,r=self.fixture(25); g=g[:8]
        paths={p for group in g for p in group['packets']}
        e={p:v for p,v in e.items() if p in paths};r={p:v for p,v in r.items() if p in paths}
        self.assertEqual(len(check_groups(g,e,r,flexible_total=200)),200)
        g[0]['packets'].pop()
        with self.assertRaises(ContextError):check_groups(g,e,r,flexible_total=200)

    def test_flexible_retains_negative_gates(self):
        for mutation in ('generation','empty','work','overlap','identity','order','oversize','small','duplicate'):
            with self.subTest(mutation=mutation):
                g,e,r=self.fixture(20)
                if mutation=='generation':e['p1_0']['generation_sha256']='other'
                if mutation=='empty':e['p1_0']['state']='selected'
                if mutation=='work':e['p1_0']['work_binding']['work_item_id']='p0_0'
                if mutation=='overlap':e['p1_0']['selected_file_sha256']['uc-library/src/0.cpp']='hash'
                if mutation=='identity':e['p1_0']['work_binding']['covered_occurrences']=e['p0_0']['work_binding']['covered_occurrences']
                if mutation=='order':g[0]['execution_order']=[]
                if mutation=='oversize':g[0]['packets']+=['extra']*6
                if mutation=='small':g.pop()
                if mutation=='duplicate':g[0]['packets'].append(g[0]['packets'][0]);g[0]['execution_order']=g[0]['packets'][:]
                with self.assertRaises(ContextError):check_groups(g,e,r,flexible_total=200)


if __name__=='__main__':unittest.main()
