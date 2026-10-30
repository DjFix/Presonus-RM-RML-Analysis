"""Tracker SQLite parity and evidence guards, using project-local fixtures."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent/'registry'))
import registry
import workflow
import schema
import generate_symbol_tracking as tracker
from merge_readiness import ValidationCache

ROOT=Path(__file__).resolve().parents[2]

class TrackerTests(unittest.TestCase):
    def setUp(self):
        root=ROOT/'temp/tracker-sqlite-tests';root.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=root);self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.lib=self.root/'library';self.lib.mkdir();self.inputs=self.root/'inputs';self.inputs.mkdir()
        self.put('s.cpp',b'int f(){return 1;}\n');config=b'BasedOnStyle: LLVM\n';self.put('.clang-format',config);self.put('test.log',b'PASS\n')
        self.put_json('validation/formatting.json',{'format_check_passed':True,'configuration_sha256':self.sha(config),'files':{'s.cpp':self.sha((self.lib/'s.cpp').read_bytes())}})
        self.put_json('validation/integration.json',{'ctest_passed':True,'files':{'s.cpp':self.sha((self.lib/'s.cpp').read_bytes())},'test_log':'test.log','test_log_sha256':self.sha(b'PASS\n')})
        self.docs={'ready':{'functions':[]},'pending':{'functions':[]}}
        for role,filename,raw in [('client','surface-13840.elf',b'12345678'),('server','mixer-13731.elf',b'abcdefgh')]:
            (self.inputs/filename).write_bytes(raw);elf=self.sha(raw)
            symbols=[]
            for i,mangled in enumerate(['_ZN8Presonus1fEv','_ZN8Presonus1gEv']):
                sym={'mangled':mangled,'demangled':'Presonus::'+('f' if i==0 else 'g')+'()','address':16+4*i,'size':4,'section':12,'kind':'STT_FUNC','binding':'STB_GLOBAL'};symbols.append(sym)
                self.put(f'recovered/{role}/machine-code/{16+4*i:08x}.bin',raw[4*i:4*i+4])
                proof={'cpp_differential_passed':True,'compiled_mangled_names_matched':True,'functions':[{'mangled':mangled,'original_elf_sha256':elf,'cpp_compiled':True,'mangling_namespace_checked':True}]}
                proofpath=f'{role}-{i}.json';self.put_json(proofpath,proof)
                row={'original_elf_sha256':elf,'mangled':mangled,'validation':proofpath,'validation_sha256':registry.digest(self.lib/proofpath),'sources':{'s.cpp':registry.digest(self.lib/'s.cpp')},'domain':'fixture','portable_ready':i==0,'cpp_compiled':True,'mangling_namespace_checked':True}
                self.docs['ready' if i==0 else 'pending']['functions'].append(row)
            symbols.append({'mangled':'data','demangled':'data','address':80,'size':4,'section':24,'kind':'STT_OBJECT','binding':'STB_LOCAL'})
            self.put_json(f'recovered/{role}/manifest.json',{'path':filename,'sha256':elf})
            self.put_json(f'recovered/{role}/all-symbols.json',symbols)
            extracted=[dict(x,file_offset=i*4,sha256=self.sha(raw[i*4:i*4+4])) for i,x in enumerate(symbols[:2])]+[dict(symbols[2],storage='zero-initialized NOBITS; no file bytes')]
            self.put_json(f'recovered/{role}/symbols.json',extracted)
        paths={}
        for status,doc in self.docs.items():
            p=self.root/(status+'.json');p.write_text(json.dumps(doc));paths[status]=p
        registry.capture(paths,self.root/'snapshots');self.baseline=self.root/'baseline.sqlite';registry.import_snapshots(self.root/'snapshots',self.baseline)
        self.db=self.root/'working.sqlite';workflow.working_copy(self.baseline,self.db);schema.upgrade(self.db,self.root/'pre-upgrade.sqlite',True)
    @staticmethod
    def sha(raw):return hashlib.sha256(raw).hexdigest()
    def put(self,name,raw):
        p=self.lib/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    def put_json(self,name,data):self.put(name,json.dumps(data).encode())
    def generate(self,output,docs=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return tracker.main(['--library',str(self.lib),'--inputs',str(self.inputs),'--registry-db',str(self.db),'--output-root',str(output)],registry_data=docs)
    def test_sqlite_matches_json_documents_and_does_not_read_retired_ledgers(self):
        expected=self.generate(self.root/'json-output',self.docs)
        # If a retired JSON ledger is consulted, parsing must fail.
        self.put('validation/ready-functions.json',b'not json');self.put('validation/compiled-functions.json',b'not json')
        actual=self.generate(self.root/'sqlite-output')
        self.assertEqual(actual,expected)
        a=self.root/'json-output';b=self.root/'sqlite-output'
        self.assertEqual({str(p.relative_to(a)):p.read_bytes() for p in a.rglob('*') if p.is_file()}, {str(p.relative_to(b)):p.read_bytes() for p in b.rglob('*') if p.is_file()})
        self.assertEqual(actual['roles']['client']['summary']['portable_reconstructions_ready'],1)
        self.assertEqual(actual['roles']['client']['summary']['compiled_declaration_pending_entries'],1)
    def test_dirty_source_rejects_readiness_and_pending(self):
        self.put('s.cpp',b'changed')
        result=self.generate(self.root/'dirty')
        self.assertEqual(result['roles']['client']['summary']['portable_reconstructions_ready'],0)
        self.assertEqual(result['roles']['client']['summary']['compiled_declaration_pending_entries'],0)
    def test_proof_hash_and_repository_boundary_guards_remain(self):
        self.put('client-0.json',b'{"cpp_differential_passed":true}')
        result=self.generate(self.root/'bad-proof')
        self.assertEqual(result['roles']['client']['summary']['portable_reconstructions_ready'],0)
        import copy
        invalid=copy.deepcopy(self.docs)
        invalid['ready']['functions'][1]['repository_sources']={'../outside.cpp':'untrusted'}
        result=self.generate(self.root/'bad-repository',invalid)
        self.assertEqual(result['roles']['server']['summary']['portable_reconstructions_ready'],0)

    def test_export_range_and_proof_guards_remain(self):
        self.put('recovered/client/machine-code/00000010.bin',b'wrong')
        with self.assertRaisesRegex(AssertionError,'exported bytes differ'):self.generate(self.root/'bad-export')
    def test_cache_detects_dirty_file_and_retargeted_symlink(self):
        first=self.root/'first';second=self.root/'second';link=self.root/'link';first.write_bytes(b'one');second.write_bytes(b'two');link.symlink_to(first)
        cache=ValidationCache();cache.sha(link);link.unlink();link.symlink_to(second)
        with self.assertRaisesRegex(AssertionError,'path changed'):cache.unchanged()
        cache=ValidationCache();cache.sha(first);first.write_bytes(b'new longer bytes')
        with self.assertRaisesRegex(AssertionError,'changed after validation'):cache.unchanged()

if __name__=='__main__':unittest.main()
