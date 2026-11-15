import base64
import hashlib
import json
import unittest
import zlib
from native_candidate_ownership import pack_guard, unpack_guard, canonical, canonical_matches
from context_runtime import ContextError

def authenticate(packed,envelope):
    raw=canonical(packed).encode();envelope=dict(envelope)
    envelope.update(data=base64.b64encode(zlib.compress(raw)).decode(),payload_bytes=len(raw),payload_sha256=hashlib.sha256(raw).hexdigest())
    return envelope

class CodecV2(unittest.TestCase):
    def setUp(self):
        self.seal={'version':1,'sources':[{'owners':['α','b','α'],'properties':{'id':'one'}},{'owners':['b','α'],'properties':{'id':'two'}}]}
    def test_v2_exact_order_duplicates(self):
        p=pack_guard(self.seal)
        self.assertEqual(p['guard_codec'],'owner-atoms-zlib-base64-v2')
        self.assertEqual(canonical(unpack_guard(p)),canonical(self.seal))
        self.assertTrue(canonical_matches(canonical(p),self.seal))
    def test_legacy_v1_codec_still_decodes(self):
        p=pack_guard(self.seal);d=json.loads(zlib.decompress(base64.b64decode(p['data'])))
        d['owner_lists']=[[d['owner_atoms'][i] for i in row] for row in d['owner_lists']]
        del d['owner_atoms'];p['guard_codec']='owner-lists-zlib-base64-v1';p=authenticate(d,p)
        self.assertEqual(canonical(unpack_guard(p)),canonical(self.seal))
        self.assertTrue(canonical_matches(canonical(p),self.seal))
    def test_atom_reference_wrong_type_or_bounds(self):
        for bad in [True,-1,2**40,'0',None]:
            p=pack_guard(self.seal);d=json.loads(zlib.decompress(base64.b64decode(p['data'])))
            d['owner_lists'][0][0]=bad
            with self.assertRaises(ContextError):unpack_guard(authenticate(d,p))
    def test_atom_type_rejected(self):
        p=pack_guard(self.seal);d=json.loads(zlib.decompress(base64.b64decode(p['data'])))
        d['owner_atoms'][0]=False
        with self.assertRaises(ContextError):unpack_guard(authenticate(d,p))
    def test_expansion_still_prechecked(self):
        p=pack_guard(self.seal);p['logical_bytes']=1
        with self.assertRaises(ContextError):unpack_guard(p)

class CheckpointCodecCompatibility(unittest.TestCase):
    def test_actual_reader_validates_legacy_and_compact_checkpoints(self):
        from native_candidate_ownership import OWNER, digest, checkpoint_id, read_checkpoint
        seal = {'version': 1, 'sources': [], 'native': {'sha256': 'native'},
                'expected': [], 'native_nodes': {}, 'affected_ids': [], 'native_inputs': [],
                'scope': 'affected_current_function_candidate_completeness'}
        seal['seal_sha256'] = digest(seal)
        identity = checkpoint_id('delta', seal['seal_sha256'], 'native')
        props = {'id': identity, 'contract_version': 1, 'owner': OWNER,
                 'state': 'verified', 'source_delta_sha256': 'delta',
                 'seal_sha256': seal['seal_sha256'], 'native_generation': 'native',
                 'before_json': '[]', 'after_json': '[]',
                 'orphan_before_json': '[]', 'orphan_after_json': '[]',
                 'journal_sha256': digest({'before': [], 'after': [],
                                          'orphan_before': [], 'orphan_after': []})}
        class Session:
            def run(self, query, **params):
                return [{'p': props}]
        for stored in (seal, pack_guard(seal)):
            props['seal_json'] = canonical(stored)
            self.assertEqual(read_checkpoint(Session(), identity, include_seal=True)[3], seal)
        altered = dict(seal, native={'sha256': 'different'})
        props['seal_json'] = canonical(pack_guard(altered))
        with self.assertRaises(ContextError):
            read_checkpoint(Session(), identity, include_seal=True)

if __name__=='__main__':unittest.main()
