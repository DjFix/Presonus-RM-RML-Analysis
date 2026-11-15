import copy
import unittest
import zlib
import base64
import hashlib
import json
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from native_candidate_ownership import pack_guard as pack, unpack_guard as unpack, canonical as text_canonical, canonical_matches
from incremental_stage import delta_reserve
from context_runtime import ContextError
import sqlite3
import tempfile

def canonical(value):
    return text_canonical(value).encode()


class Codec(unittest.TestCase):
    def setUp(self):
        self.seal = {'version': 1, 'sources': [
            {'owners':['α','b','α'], 'properties':{'id':'a','flag':True,'value':None}},
            {'owners':['α','b','α'], 'properties':{'id':'b','n':1}},
            {'owners':[], 'properties':{'id':'c'}}], 'seal_sha256':'old logical seal unchanged'}
    def test_roundtrip_exact_order_types(self):
        self.assertEqual(canonical(unpack(pack(self.seal))), canonical(self.seal))
    def test_legacy(self):
        self.assertIs(unpack(self.seal), self.seal)
    def test_modified_compressed(self):
        p=pack(self.seal); p['data']='A'+p['data'][1:]
        with self.assertRaises(Exception): unpack(p)
    def test_truncated(self):
        p=pack(self.seal); p['data']=base64.b64encode(base64.b64decode(p['data'])[:-1]).decode()
        with self.assertRaises(ContextError): unpack(p)
    def test_trailing(self):
        p=pack(self.seal); p['data']=base64.b64encode(base64.b64decode(p['data'])+b'x').decode()
        with self.assertRaises(ContextError): unpack(p)
    def test_size_digest(self):
        for key,value in [('logical_bytes', True), ('payload_bytes', 0), ('logical_sha256', '0'*64), ('payload_sha256','0'*64)]:
            p=pack(self.seal);p[key]=value
            with self.assertRaises(ContextError): unpack(p)
    def test_bool_reference_rejected_even_authenticated(self):
        p=pack(self.seal);raw=json.loads(zlib.decompress(base64.b64decode(p['data'])))
        raw['seal']['sources'][0]['owners_ref']=False
        payload=canonical(raw);p.update(payload_bytes=len(payload),payload_sha256=hashlib.sha256(payload).hexdigest(),data=base64.b64encode(zlib.compress(payload)).decode())
        with self.assertRaises(ContextError):unpack(p)
    def test_expansion_preflight(self):
        p=pack(self.seal); p['logical_bytes']=1
        with self.assertRaises(ContextError):unpack(p)
    def test_modified_logical_payload_rejected(self):
        p=pack(self.seal);raw=json.loads(zlib.decompress(base64.b64decode(p['data'])))
        raw['seal']['sources'][0]['properties']['flag']=1
        payload=canonical(raw);p.update(payload_bytes=len(payload),payload_sha256=hashlib.sha256(payload).hexdigest(),data=base64.b64encode(zlib.compress(payload)).decode())
        with self.assertRaises(ContextError):unpack(p)

class MaintainedBoundaries(unittest.TestCase):
    def test_typed_codec_compare_and_legacy_spelling(self):
        seal={'version':1,'sources':[],'n':1}
        encoded=text_canonical(pack(seal))
        self.assertTrue(canonical_matches(encoded,seal))
        self.assertFalse(canonical_matches(encoded,dict(seal,n=True)))
        self.assertFalse(canonical_matches(encoded,dict(seal,n=1.0)))
        legacy={'version':1,'nested':{'guard_codec':'owner-lists-zlib-base64-v1'}}
        self.assertTrue(canonical_matches(text_canonical(legacy),legacy))
        self.assertFalse(canonical_matches(json.dumps(legacy,indent=2),legacy))

    def test_long_id_fresh_origin_keeps_conservative_cost(self):
        scratch=pathlib.Path(__file__).resolve().parents[1] / 'temp/test-work'
        scratch.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            db=sqlite3.connect(pathlib.Path(folder)/'delta.sqlite')
            try:
                db.execute('PRAGMA journal_mode=DELETE')
                db.execute('PRAGMA page_size=4096')
                db.execute('BEGIN')
                reserve=delta_reserve(db,['x'*16384],{'payload_bytes':100,'rows':1})
                self.assertIs(reserve['fresh_empty_delete_database'],True)
                self.assertEqual(reserve['storage_case'],'conservative_old_state')
                self.assertEqual(reserve['journal_estimate_bytes'],32768+200+128)
            finally: db.close()

if __name__ == '__main__': unittest.main()
