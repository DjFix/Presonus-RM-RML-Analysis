"""Source-bound namespace deferral tests; fake CFG only, no firmware execution."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,sys

root=Path.cwd();library=root/'uc-library';checks=[]
spec=importlib.util.spec_from_file_location('bounded',library/'tools/extraction_verify_bounded.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert 'angr' not in sys.modules
vectors={
 '_ZN4Core6VectorIiE6resizeEi':'Core',
 '_ZNK4Core6Buffer7getSizeEv':'Core',
 '_ZThn4_N4Core6Buffer4tickEv':'Core',
 '_ZTv0_n12_NK4Core6Buffer4tickEv':'Core',
 '_ZTch0_h4_N4Core6Buffer4tickEv':'Core',
 '_ZZN4Core6Buffer4tickEvEN5Local3runEv':'Core',
 '_ZN8Presonus2UC3fooERKN4Core2IO6BufferE':'Presonus',
 '_Z3fooPN4Core6BufferE':None,
 'plain_fixture':None}
for name,expected in vectors.items():assert m.owning_namespace(name)==expected,(name,m.owning_namespace(name),expected)
checks.append('stdlib-only import; owning scope handles templates, const, local names, adjusting/covariant thunks; parameter types do not exclude')
fixture=root/'temp/recovery-work/core-scope-selftest'/str(os.getpid());tools=fixture/'uc-library/tools';scope=fixture/'uc-library/recovered-all/server'
tools.mkdir(parents=True);(scope/'pseudocode').mkdir(parents=True)
for name in ['decompile_uc.py','extraction_verify_bounded.py']:shutil.copy2(library/'tools'/name,tools/name)
data=b'fake source fixture, not firmware';(fixture/'input.bin').write_bytes(data);sha=hashlib.sha256(data).hexdigest()
(scope/'manifest.json').write_text(json.dumps(dict(path='input.bin',sha256=sha)))
(scope/'analysis-input.json').write_text(json.dumps(dict(sha256=sha)))
names=[('_ZN4Core6Buffer4doneEv','Core::Buffer::done()'),('_ZN4Core6VectorIiE6resizeEi','Core::Vector<int>::resize(int)'),('_ZN8Presonus2UC3fooERKN4Core2IO6BufferE','Presonus::UC::foo(Core::IO::Buffer const&)'),('plain_fixture','plain_fixture()')]
symbols=[dict(address=4096+256*i,mangled=names[i][0],demangled=names[i][1],kind='STT_FUNC',section=1,size=16) for i in range(4)]
symbols.append(dict(symbols[-1],mangled='_ZThn4_N4Core6Buffer4tickEv',demangled='non-virtual thunk to Core::Buffer::tick()'))
(scope/'symbols.json').write_text(json.dumps(symbols))
cached=b'// UNVALIDATED fixture-only preserved old Core export\n'+b'x'*150
(scope/'pseudocode/00001000.cpp.txt').write_bytes(cached)
(scope/'decompilation.json').write_text(json.dumps([dict(address=4096,status='exported')]))
fake='''from types import SimpleNamespace
from pathlib import Path
__version__='core-scope-fake'
class Analyses:
 def CFGFast(self,**kw):
  assert kw['function_starts']==[4608],kw
  assert kw['regions']==[(4608,4624)],kw
  return SimpleNamespace(kb=SimpleNamespace(functions={4608:SimpleNamespace(addr=4608)}),model=None)
 def Decompiler(self,f,**kw):
  assert f.addr==4608
  Path('called.txt').write_text(str(f.addr))
  return SimpleNamespace(codegen=SimpleNamespace(text='void fake_eligible_only(){}'))
class Project:
 def __init__(self,*a,**kw):
  self.analyses=Analyses();self.kb=SimpleNamespace(decompilations=SimpleNamespace(discard=lambda *a:None))
'''
(tools/'angr.py').write_text(fake)
cmd=[sys.executable,str(tools/'decompile_uc.py'),str(fixture),'server','--recovery','uc-library/recovered-all','--defer-namespace','Core','--max-rss-mb','0','--min-available-mb','0']
p=subprocess.run(cmd+['--plan-only'],cwd=fixture,capture_output=True,text=True);assert p.returncode==0,p.stderr
plan=json.loads(p.stdout.splitlines()[0]);assert plan['pending_attempts']==1 and plan['deferred_unique']==3 and plan['deferred_pending_unique']==2
assert not (fixture/'called.txt').exists()
checks.append('plan defers every Core-owned address including mixed aliases; Presonus Core-parameter method eligible')
p=subprocess.run(cmd,cwd=fixture,capture_output=True,text=True);assert p.returncode==0,(p.stdout,p.stderr)
s=json.loads((scope/'run-state.json').read_text())
assert s['state']=='scope-complete' and s['scope_complete'] and not s['workload_processed_complete'] and not s['all_exports_present']
assert s['deferred_pending_unique']==2 and s['processed']==2 and s['exports']==2 and s['failed']==0 and s['new_attempts']==1
assert (scope/'pseudocode/00001000.cpp.txt').read_bytes()==cached
assert not (scope/'pseudocode/00001100.cpp.txt').exists() and not (scope/'pseudocode/00001300.cpp.txt').exists()
assert json.loads((scope/'deferred-scope.json').read_text())['source_sha256']==sha
checks.append('CFG starts/regions exclude Core; only eligible function exported; past Core export preserved; deferred not processed/failed/complete')
(fixture/'input.bin').write_bytes(b'changed source')
p=subprocess.run(cmd+['--plan-only'],cwd=fixture,capture_output=True,text=True)
assert p.returncode and 'source ELF changed' in p.stderr
checks.append('namespace deferral remains tied to exact source SHA')
report=dict(passed=True,checks=checks,fixture=str(fixture),test_kind='fake CFG control-flow only; no Core firmware execution')
out=library/'validation/extraction-verification/core-scope-selftest.json';out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
