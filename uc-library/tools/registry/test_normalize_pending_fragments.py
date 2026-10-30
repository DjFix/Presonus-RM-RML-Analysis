import copy
import json
import unittest
from unittest.mock import patch
import registry as reg
import normalize_pending_fragments as normal
import test_workflow as fixtures

class PendingNormalizerTests(unittest.TestCase):
    setUp=fixtures.WorkflowTests.setUp
    def test_canonical_behavior_is_not_replaced_by_old_membership(self):
        row=dict(self.entries['b'],validation='old-membership.json',validation_sha256='membership-sha',behavior_validation='proof.json',behavior_validation_sha256=self.proof,domain='Exact native domain',declaration_uncertainties=['Unencoded return remains pending'])
        membership=self.lib/'old-membership.json';membership.write_text(json.dumps({'functions':[row]}));row['validation_sha256']=reg.digest(membership)
        source=self.root/'canonical.json';source.write_text(json.dumps({'functions':[row]}));out=self.lib/'candidate/normalized.json'
        receipt=normal.normalize(self.lib,[source],[],out);raw=json.loads(out.read_text())['functions'][0]
        self.assertEqual(raw['validation'],'proof.json');after=normal.merged_entry(raw,str(out.relative_to(self.lib)),reg.digest(out))
        self.assertEqual(after['behavior_validation'],'proof.json');self.assertEqual(after['behavior_validation_sha256'],self.proof)
        self.assertEqual({k:v for k,v in after.items() if k not in ('validation','validation_sha256')},{k:v for k,v in row.items() if k not in ('validation','validation_sha256')})
        self.assertEqual(receipt['expected_canonical'][0]['expected_canonical_sha256'],normal.digest_value(after))
        self.assertEqual(raw['sources'],after['sources'])
    def test_absent_native_proof_stays_absent_and_raw_proof_is_retained(self):
        canonical=dict(self.entries['b'],validation='membership.json',validation_sha256='membership-only')
        raw=normal.normalize_entry(canonical,'canonical');self.assertNotIn('validation',raw)
        after=normal.merged_entry(raw,'new-outer.json','new-sha');self.assertNotIn('behavior_validation',after)
        fresh=dict(self.entries['b'],mangled='new-key');raw=normal.normalize_entry(fresh,'raw');after=normal.merged_entry(raw,'new-outer.json','new-sha')
        self.assertEqual(after['behavior_validation'],fresh['validation']);self.assertEqual(after['behavior_validation_sha256'],fresh['validation_sha256'])
    def test_shared_membership_hashed_once_and_dirty_native_proof_rejected(self):
        rows=[dict(self.entries['b'],mangled=name,validation='shared-membership.json',validation_sha256='pending-placeholder',behavior_validation='proof.json',behavior_validation_sha256=self.proof) for name in ('a','b')]
        membership=self.lib/'shared-membership.json';membership.write_text(json.dumps({'functions':rows}))
        for row in rows:row['validation_sha256']=reg.digest(membership)
        source=self.root/'shared-canonical.json';source.write_text(json.dumps({'functions':rows}))
        receipt=normal.normalize(self.lib,[source],[],self.lib/'shared-output.json')
        self.assertEqual(receipt['fresh_unique_files_hashed'],3)
        parent=normal.ValidationCache
        native=self.lib/'proof.json'
        class DirtyCache(parent):
            def unchanged(self):
                native.write_text('changed after fresh hash')
                super().unchanged()
        with patch.object(normal,'ValidationCache',DirtyCache):
            with self.assertRaises(AssertionError):normal.normalize(self.lib,[source],[],self.lib/'dirty-output.json')
        self.assertFalse((self.lib/'dirty-output.json').exists())

    def test_ambiguous_raw_and_duplicate_original_keys_rejected(self):
        row=dict(self.entries['b'],behavior_validation='native.json',behavior_validation_sha256='native-sha')
        with self.assertRaises(ValueError):normal.normalize_entry(row,'raw')
        source=self.root/'duplicate.json';source.write_text(json.dumps({'functions':[self.entries['b'],self.entries['b']]}))
        with self.assertRaises(ValueError):normal.normalize(self.lib,[],[source],self.lib/'rejected.json')

if __name__=='__main__':unittest.main()
