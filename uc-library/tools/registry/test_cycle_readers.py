"""Consumer-gate fixtures only: no native or hardware validation is claimed."""
import ast
import hashlib
import json
import pathlib
import runpy
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import registry as r
import test_workflow as fixtures

PROJECT=pathlib.Path(__file__).resolve().parents[3]
TOOLS=PROJECT/'uc-library/tools'

class CycleReaderTests(unittest.TestCase):
    def setUp(self):
        fixtures.WorkflowTests.setUp(self)
        previous=self.lib
        self.lib=self.root/'uc-library'
        previous.rename(self.lib)
    def command(self,name,*args,passed=True):
        p=subprocess.run([str(PROJECT/'uc-library/.venv/bin/python'),str(TOOLS/name),*map(str,args)],capture_output=True,text=True)
        self.assertEqual(p.returncode==0,passed,p.stdout+p.stderr)
        return p
    def coverage(self):
        rows=[{'kind':'STT_FUNC','defined':True,'size':4,'address':i*4,'section':1,'mangled':name,'demangled':'Presonus::Panel::BlinkLEDControl::fixture()','work_deferred':False} for i,name in enumerate(('a','b'))]
        self.put('tracking/coverage.json',{'roles':{'client':{'summary':{'sha256':'elf','portable_reconstructions_ready':1,'compiled_declaration_pending_entries':1},'symbols':rows}}})
        self.put('recovered-all/client/manifest.json',{'sha256':'elf','path':'fixture-only.elf'})
    def test_hal_reader_missing_legacy_json_and_stale_source_status(self):
        self.coverage();out=self.root/'hal';markdown=self.root/'HAL.md'
        self.command('recovery/generate_hal_symbol_tracking.py','--repository',self.root,'--registry-db',self.db,'--output-dir',out,'--markdown',markdown)
        value=json.loads((out/'hal-priority-symbols.json').read_text())
        self.assertEqual([v['status'] for v in value['symbols']],['ready-ledger','declaration-pending'])
        self.assertTrue(all(v['source_bindings_current'] for v in value['symbols']))
        (self.lib/'t.cpp').write_text('changed fixture source')
        self.command('recovery/generate_hal_symbol_tracking.py','--repository',self.root,'--registry-db',self.db,'--output-dir',out,'--markdown',markdown)
        value=json.loads((out/'hal-priority-symbols.json').read_text())
        self.assertTrue(all(v['status'].endswith('active-refresh-pending') for v in value['symbols']))
    def test_full_checkpoint_audit_preserves_gates_without_json_ledgers(self):
        self.coverage();(self.lib/'SYMBOLS.md').write_text('fixture only')
        (self.lib/'tools').mkdir(exist_ok=True);shutil.copyfile(TOOLS/'merge_readiness.py',self.lib/'tools/merge_readiness.py')
        integration={'platform':'linux','ctest_passed':True,'test_suites':321,'files':self.sources,'logs':{}}
        self.put('validation/integration.json',integration);self.put('validation/integration-linux.json',integration)
        for script in ('audit_recovery_checkpoint.py','audit_fader_queue_router_checkpoint.py'):
            out=self.root/(script+'.json')
            self.command('recovery/'+script,'--repository',self.root,'--registry-db',self.db,'--ready',1,'--pending',1,'--mangles',1,'--suites',321,'--phase','fixture','--output',out)
            result=json.loads(out.read_text());self.assertTrue(result['passed']);self.assertIn('registry_source',result)
            self.assertNotIn('ready_sha256',result)
        (self.lib/'t.cpp').write_text('changed fixture source')
        self.command('recovery/audit_fader_queue_router_checkpoint.py','--repository',self.root,'--registry-db',self.db,'--ready',1,'--pending',1,'--mangles',1,'--suites',321,'--phase','fixture','--output',self.root/'rejected.json',passed=False)
    def test_counter_fixed_workload_policy_without_json_ledgers(self):
        policy=PROJECT/'uc-library/candidates/unique-workload-audit/validation/unique-02/validation.json'
        destination=self.lib/'candidates/unique-workload-audit/validation/unique-02/validation.json';destination.parent.mkdir(parents=True);shutil.copyfile(policy,destination)
        names=['a','b']+['fixture_'+str(i) for i in range(10171)]
        self.put('tracking/coverage.json',{'roles':{'client':{'summary':{'sha256':'elf'},'symbols':[{'kind':'STT_FUNC','defined':True,'size':4,'mangled':n,'work_deferred':False} for n in names]}}})
        out=self.root/'counts.json';self.command('recovery/count_current_unique.py','--repository',self.root,'--registry-db',self.db,'--output',out)
        result=json.loads(out.read_text());self.assertEqual(result['unique_total'],10173);self.assertEqual(result['complete_all_roles'],1);self.assertEqual(result['per_elf_pending'],1)
        self.assertIn('registry_source',result)
        self.command('recovery/count_current_unique.py','--repository',self.root,'--registry-db',self.db,'--output',out,passed=False)
    def test_installed_audit_original_mangles_and_missing_symbol_failure(self):
        header=self.lib/'include/presonus/fixture.hpp';header.parent.mkdir(parents=True);header.write_text('// fixture only\n')
        self.put('validation/integration.json',{'files':{'include/presonus/fixture.hpp':r.digest(header)}})
        prefix=self.root/'install';(prefix/'include/presonus').mkdir(parents=True);shutil.copyfile(header,prefix/'include/presonus/fixture.hpp');(prefix/'lib').mkdir();(prefix/'lib/libpresonus_uc.a').write_bytes(b'synthetic archive fixture')
        out=self.root/'install.json';argv=['audit_install.py','--library',str(self.lib),'--registry-db',str(self.db),'--prefix',str(prefix),'--nm','/fixture/nm','--output',str(out)]
        with patch.object(sys,'argv',argv),patch('subprocess.run',return_value=subprocess.CompletedProcess([],0,'0000 T a\n','')):
            runpy.run_path(str(TOOLS/'audit_install.py'),run_name='__main__')
        self.assertTrue(json.loads(out.read_text())['compiled_mangles_matched'])
        with patch.object(sys,'argv',argv),patch('subprocess.run',return_value=subprocess.CompletedProcess([],0,'','')):
            with self.assertRaises(SystemExit):runpy.run_path(str(TOOLS/'audit_install.py'),run_name='__main__')
    def test_actual_role_all_42_assertions_unchanged_including_rtti_policy(self):
        text=(TOOLS/'recovery/audit_role_build_basic_activity.py').read_text();tree=ast.parse(text)
        assertions=[ast.dump(n,include_attributes=False) for n in ast.walk(tree) if isinstance(n,ast.Assert)]
        self.assertEqual(len(assertions),42)
        self.assertEqual(hashlib.sha256(json.dumps(assertions).encode()).hexdigest(),'ba476ee2fc8fb6d62b2399b1e904d277723ebf3872a009b88e318cdc3e676874')
        self.assertNotIn('ready-functions.json',text)

if __name__=='__main__':unittest.main()
