import copy
import hashlib
import json
import pathlib
import sys
import subprocess
import unittest
import uuid
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'dependency-graph'))
import reconstruction_contract as gate

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.root=ROOT/'temp/test-work/reconstruction-contract'/uuid.uuid4().hex
        self.root.mkdir(parents=True)
        (self.root/'native.json').write_text('Native body only; not a source-port contract')
        self.ref={'path':'native.json','sha256':hashlib.sha256((self.root/'native.json').read_bytes()).hexdigest(),'scope':'bounded native observations','kind':'native_observation'}
        self.task={'mode':'reconstruct','targets':[{'original_elf_sha256':'e'*64,'mangled':'_ZN1A1fEv','address':4,'size':8}],'owned_files':['uc-library/src/A.cpp']}
        (self.root/'class.hpp').write_text('struct A { void f(); };')
        self.cppref={'path':'class.hpp','sha256':hashlib.sha256((self.root/'class.hpp').read_bytes()).hexdigest(),'scope':'synthetic reviewed declaration','kind':'cpp_declaration'}
        self.implref=dict(self.cppref,kind='cpp_implementation')
        self.review={'version':1,'reviewer':'Root','targets':copy.deepcopy(self.task['targets']),'owned_files':self.task['owned_files'][:],'domain':'bounded source port; no original declaration/ABI claim','requirements':{name:{'status':'established','reason':'Reviewed specific source-port contract','evidence':[self.cppref if name in ('declarations','state') else self.implref]} for name in gate.SCOPES},'dependencies':[]}
    def test_native_body_alone_cannot_dispatch(self):
        with self.assertRaisesRegex(ValueError,'reviewed'):gate.validate_request(self.root,self.task)
    def test_native_only_plan_can_recover_all_missing_cpp_inside_scope(self):
        self.task['owned_files']=['uc-library/src/NewClass.cpp','uc-library/include/NewClass.hpp']
        self.review['owned_files']=self.task['owned_files'][:]
        for name in gate.SCOPES:
            self.review['requirements'][name].update(status='bounded_work',evidence=[self.ref],work={'objective':'Recover required interface/state or app helper from original instructions, not from names alone','oracle_plan':'Independent native execution and actual source-port/provider replay; unresolved ABI excluded','owned_files':self.task['owned_files'][:]})
        self.assertTrue(gate.evaluate(self.root,self.task,self.review)['dispatch_reconstruction'])

    def test_missing_base_routes_to_prerequisite(self):
        self.review['requirements']['lifecycle']['status']='missing'
        self.assertEqual(gate.evaluate(self.root,self.task,self.review)['disposition'],'prepare_dependencies_first')
    def test_bounded_unknown_is_allowed_inside_owned_scope(self):
        self.review['requirements']['state'].update(status='bounded_work',work={'objective':'Establish bounded state mapping','oracle_plan':'Execute original writes and compare portable poststate','owned_files':self.task['owned_files'][:]})
        self.assertTrue(gate.evaluate(self.root,self.task,self.review)['dispatch_reconstruction'])
    def test_unknown_cannot_hide_outside_ownership(self):
        self.review['requirements']['state'].update(status='bounded_work',work={'objective':'unknown','oracle_plan':'native','owned_files':['uc-library/src/Other.cpp']})
        with self.assertRaisesRegex(ValueError,'owned'):gate.evaluate(self.root,self.task,self.review)
    def test_dependency_must_be_included_and_owned(self):
        self.review['dependencies']=[{'kind':'included_work','work_item_id':'base','owned_files':self.task['owned_files'][:],'evidence':[self.ref]}]
        self.assertFalse(gate.evaluate(self.root,self.task,self.review)['dispatch_reconstruction'])
        self.assertTrue(gate.evaluate(self.root,self.task,self.review,['base'])['dispatch_reconstruction'])
    def test_existing_symbol_routes_to_audit_not_reconstruction(self):
        source=self.root/'A.cpp';source.write_text('class A { public: A(); void f(); }; A::A() {} void A::f() {}')
        obj=self.root/'A.o';subprocess.run(['/usr/bin/c++','-c',str(source),'-o',str(obj)],check=True)
        self.review['existing_compiled_result']={'artifact':{'path':'A.o','sha256':hashlib.sha256(obj.read_bytes()).hexdigest()},'source_bindings':[{'path':'A.cpp','sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'scope':'actual fixture compiler input','kind':'cpp_implementation'}],'evidence':[dict(self.ref,kind='compiled_symbol_audit')]}
        self.assertEqual(gate.evaluate(self.root,self.task,self.review)['disposition'],'review_existing_result')
        for variant in ('C1','C2'):
            task=copy.deepcopy(self.task);task['targets'][0]['mangled']='_ZN1A'+variant+'Ev'
            review=copy.deepcopy(self.review);review['targets']=copy.deepcopy(task['targets'])
            self.assertEqual(gate.evaluate(self.root,task,review)['disposition'],'review_existing_result')
        self.task['targets'][0]['mangled']='_ZN1A7missingEv';self.review['targets']=copy.deepcopy(self.task['targets'])
        with self.assertRaisesRegex(ValueError,'actual defined'):gate.evaluate(self.root,self.task,self.review)
    def test_stale_evidence_rejected(self):
        (self.root/'class.hpp').write_text('changed')
        with self.assertRaisesRegex(ValueError,'Stale'):gate.evaluate(self.root,self.task,self.review)
    def test_identity_and_ownership_exact(self):
        for key,value in [('size',9),('address',5),('mangled','other')]:
            with self.subTest(key=key):
                review=copy.deepcopy(self.review);review['targets'][0][key]=value
                with self.assertRaisesRegex(ValueError,'identity'):gate.evaluate(self.root,self.task,review)
        self.review['owned_files']=[]
        with self.assertRaisesRegex(ValueError,'ownership'):gate.evaluate(self.root,self.task,self.review)
    def test_native_evidence_cannot_masquerade_as_cpp_contract(self):
        self.review['requirements']['declarations']['evidence']=[self.ref]
        with self.assertRaisesRegex(ValueError,'Native context alone'):gate.evaluate(self.root,self.task,self.review)
    def test_hash_bound_request(self):
        p=self.root/'review.json';p.write_text(json.dumps(self.review));self.task['reconstruction_contract']={'path':'review.json','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        self.assertTrue(gate.validate_request(self.root,self.task)['dispatch_reconstruction'])

class RuntimeEntryTests(unittest.TestCase):
    def test_single_prepare_rejects_before_enrich_or_claim(self):
        import importlib.util
        from unittest import mock
        spec=importlib.util.spec_from_file_location('contract_selector_test',ROOT/'uc-library/tools/recovery/select_context.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        task={'mode':'reconstruct'}
        with mock.patch.object(module,'enrich') as enrich:
            with self.assertRaisesRegex(module.ContextError,'planning gate'):module.prepare_task(task)
            enrich.assert_not_called()


class DependencyGroupingTests(unittest.TestCase):
    def test_declared_prerequisite_must_be_actual_work_of_same_worker(self):
        from context_batch import check_dependency_inclusion
        from context_runtime import ContextError
        tasks=[{'task_id':'a','included_dependency_work':['base-work']},{'task_id':'b'}]
        split=[{'task_name':'one','packets':['packets/a']},{'task_name':'two','packets':['packets/b']}]
        with self.assertRaisesRegex(ContextError,'outside actual'):check_dependency_inclusion(tasks,['target-work','base-work'],split)
        together=[{'task_name':'one','packets':['packets/a','packets/b']}]
        check_dependency_inclusion(tasks,['target-work','base-work'],together)
        with self.assertRaisesRegex(ContextError,'outside actual'):check_dependency_inclusion(tasks,['target-work','unrelated-work'],together)

if __name__=='__main__':unittest.main()
