"""Regression for exact legacy declaration-note fallback; no firmware execution."""
import unittest
import registry as r
import workflow as w
import test_workflow as fixtures

class UncertaintyTests(unittest.TestCase):
    setUp=fixtures.WorkflowTests.setUp
    request=fixtures.WorkflowTests.request
    def test_proof_fallback_and_entry_method_notes_are_preserved(self):
        proof={'cpp_differential_passed':True,'compiled_mangled_names_matched':True,'mangled_names':['b'],'original_elf_sha256':'elf','return_declaration_choices':['Unencoded fixture return choice']}
        sha=self.put('proof.json',proof)
        entry=dict(self.entries['b'],portable_ready=True,validation_sha256=sha)
        body=self.request({'kind':'classify','target':'ready','entry':entry,'previous_validation_sha256':self.proof},'uncertainty-proof')
        w.operate(self.db,self.lib,body,False)
        with r.connect(self.db) as c:
            row=c.execute('SELECT * FROM records WHERE mangled="b"').fetchone()
            self.assertEqual(r.restored(c,row)['declaration_uncertainties'],proof['return_declaration_choices'])
        entry['method_declaration_uncertainties']=['Explicit method note wins']
        body=self.request({'kind':'classify','target':'ready','entry':entry,'previous_validation_sha256':sha},'uncertainty-entry')
        body['operations'][0]['expected_revision']=1
        w.operate(self.db,self.lib,body,False)
        with r.connect(self.db) as c:
            row=c.execute('SELECT * FROM records WHERE mangled="b"').fetchone()
            self.assertEqual(r.restored(c,row)['declaration_uncertainties'],entry['method_declaration_uncertainties'])

if __name__=='__main__':unittest.main()
