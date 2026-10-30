#!/usr/bin/env python3
"""Control-flow tests for exporter safety; fake CFGs, no firmware decompilation."""
import argparse
import ast
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('repository',type=Path)
    a=p.parse_args();repository=a.repository.resolve();library=repository/'uc-library'
    temporary=repository/'temp/extraction-verification'/f'selftest-{os.getpid()}'
    temporary.mkdir(parents=True)
    checks=[]
    fake='''from types import SimpleNamespace
import json,os,time
from pathlib import Path
__version__='selftest-fake'
class Cache:
    def discard(self,key): pass
class Analyses:
    def __init__(self):self.kb=SimpleNamespace(functions={a:SimpleNamespace(addr=a) for a in (4096,4352,4608,4864)},decompilations=Cache())
    def CFGFast(self,**kw):
        time.sleep(float(os.environ.get('SELFTEST_CFG_SLEEP','0')))
        if os.environ.get('SELFTEST_STOP_AFTER_CFG'):Path('stop.flag').touch()
        return SimpleNamespace(kb=self.kb,model=object())
    def Decompiler(self,function,**kw):
        assert kw['use_cache'] is False and kw['update_cache'] is False
        if os.environ.get('SELFTEST_STOP_AFTER_FUNCTION'):Path('stop.flag').touch()
        with Path('calls.jsonl').open('a') as f:f.write(json.dumps({'address':function.addr,'use_cache':kw['use_cache'],'update_cache':kw['update_cache']})+'\\n')
        return SimpleNamespace(codegen=SimpleNamespace(text='int test_only_'+str(function.addr)+'() { return 0; }'))
class Project:
    def __init__(self,*a,**kw):self.analyses=Analyses();self.kb=self.analyses.kb
'''
    def fixture(name):
        repo=temporary/name;tools=repo/'uc-library/tools';root=repo/'uc-library/recovered-all/server';prior=repo/'uc-library/recovered/server'
        tools.mkdir(parents=True);(root/'pseudocode').mkdir(parents=True);(prior/'pseudocode').mkdir(parents=True)
        for filename in ('decompile_uc.py','extraction_verify_bounded.py'):shutil.copyfile(library/'tools'/filename,tools/filename)
        (tools/'angr.py').write_text(fake)
        data=b'fixture-only source, not a firmware ELF';(repo/'input.bin').write_bytes(data)
        manifest={'path':'input.bin','sha256':hashlib.sha256(data).hexdigest()}
        for folder in (root,prior):(folder/'manifest.json').write_text(json.dumps(manifest))
        (root/'analysis-input.json').write_text(json.dumps({'sha256':manifest['sha256']}))
        (prior.parent/'audit.json').write_text(json.dumps({'roles':{'server':{'sha256':manifest['sha256']}}}))
        symbols=[dict(mangled=f'fixture_{addr}',demangled=f'fixture_{addr}()',address=addr,size=16,kind='STT_FUNC',section=1) for addr in (4096,4352,4608,4864)]
        symbols.append(dict(symbols[-1],mangled='fixture_alias',size=12))
        (root/'symbols.json').write_text(json.dumps(symbols))
        text=lambda addr:'// UNVALIDATED DECOMPILER OUTPUT. TEST ONLY.\n//'+('x'*100)+f'\n// Symbol fixture_{addr} address=0x{addr:x}\nint dummy(){{return 0;}}\n'
        (root/'pseudocode/00001000.cpp.txt').write_text(text(4096))
        (root/'decompilation.json').write_text(json.dumps([dict(address=4096,status='exported',mangled='fixture_4096')]))
        (prior/'pseudocode/00001100.cpp.txt').write_text(text(4352))
        (prior/'decompilation.json').write_text(json.dumps([dict(address=4352,status='exported',mangled='fixture_4352')]))
        (root/'pseudocode/00001100.cpp.txt').write_text(text(4352))
        (root/'pseudocode/00001200.cpp.txt').write_bytes(b'// UNVALIDATED truncated test-only output')
        return repo,root
    def command(repo,*extra):return [sys.executable,'uc-library/tools/decompile_uc.py','.', 'server','--recovery','uc-library/recovered-all','--reuse-from','uc-library/recovered','--batch-size','1',*extra]
    def run(repo,*extra,success=True,environment=None):
        completed=subprocess.run(command(repo,*extra),cwd=repo,text=True,capture_output=True,env=environment)
        assert (completed.returncode==0)==success,(completed.stdout,completed.stderr)
        return completed
    repo,root=fixture('main')
    before=(root/'decompilation.json').read_bytes()
    plan=run(repo,'--plan-only')
    first=json.loads(plan.stdout.splitlines()[0])
    assert first['trusted_existing']==2 and first['pending_attempts']==2 and len(first['untrusted_files'])==1
    assert before==(root/'decompilation.json').read_bytes() and not (root/'trusted-exports.json').exists() and not (repo/'calls.jsonl').exists()
    checks.append('plan-only does not import angr or mutate recovery')
    run(repo,'--max-rss-mb','0','--min-available-mb','0','--quarantine-untrusted')
    state=json.loads((root/'run-state.json').read_text());assert state['state']=='partial' and state['reason']=='batch-limit'
    saved=list((repo/'temp/extraction-verification/quarantine').rglob('00001200.cpp.txt'))
    assert len(saved)==1 and saved[0].read_bytes()==b'// UNVALIDATED truncated test-only output'
    assert [json.loads(line)['address'] for line in (repo/'calls.jsonl').read_text().splitlines()]==[4608]
    checks.append('untrusted cache quarantined; exactly one new attempt; prior exports reused')
    run(repo,'--max-rss-mb','0','--min-available-mb','0')
    state=json.loads((root/'run-state.json').read_text());assert state['state']=='complete' and state['processed']==4
    entries=json.loads((root/'decompilation.json').read_text());assert len(next(e for e in entries if e['address']==4864)['aliases'])==2
    assert not list(root.rglob('*.new'))
    checks.append('second batch resumes remaining address, preserves aliases and seals atomic state')
    (root/'pseudocode/00001000.cpp.txt').write_text('tampered')
    assert 'sealed cache file changed' in run(repo,'--plan-only',success=False).stderr
    checks.append('sealed output tampering is rejected')
    stop_repo,stop_root=fixture('stop-before')
    (stop_repo/'stop.flag').touch()
    run(stop_repo,'--stop-file','stop.flag','--max-rss-mb','0','--min-available-mb','0')
    stopped=json.loads((stop_root/'run-state.json').read_text())
    assert stopped['state']=='stopped' and stopped['reason']=='stop-file' and not (stop_repo/'calls.jsonl').exists()
    checks.append('existing stop marker checkpoints before angr/CFG')
    after_repo,after_root=fixture('stop-after-cfg')
    run(after_repo,'--stop-file','stop.flag','--max-rss-mb','0','--min-available-mb','0',environment=dict(os.environ,SELFTEST_STOP_AFTER_CFG='1'))
    assert json.loads((after_root/'run-state.json').read_text())['state']=='stopped' and not (after_repo/'calls.jsonl').exists()
    checks.append('stop arriving during CFG is honored before decompilation')
    between_repo,between_root=fixture('stop-after-function')
    run(between_repo,'--stop-file','stop.flag','--max-rss-mb','0','--min-available-mb','0','--batch-size','4',environment=dict(os.environ,SELFTEST_STOP_AFTER_FUNCTION='1'))
    stopped=json.loads((between_root/'run-state.json').read_text())
    assert stopped['state']=='stopped' and stopped['new_attempts']==1 and stopped['pending_unique']==1
    assert len((between_repo/'calls.jsonl').read_text().splitlines())==1
    checks.append('stop completes/seals the current function then releases the worker')
    global_repo,global_root=fixture('global-lock')
    lock_path=global_repo/'temp/extraction-verification/decompiler.global.lock'
    lock_path.parent.mkdir(parents=True,exist_ok=True)
    with lock_path.open('a+') as held:
        fcntl.flock(held.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        blocked=run(global_repo,'--max-rss-mb','0','--min-available-mb','0',success=False)
        assert 'project-wide heavy-analysis lock' in blocked.stderr
        assert not (global_repo/'calls.jsonl').exists()
    checks.append('project-wide heavy-analysis lock blocks a concurrent role')
    if Path('/proc/meminfo').exists():
        low_repo,low_root=fixture('low-memory')
        run(low_repo,'--max-rss-mb','0','--min-available-mb','99999999')
        assert json.loads((low_root/'run-state.json').read_text())['reason']=='low-available-memory'
        assert not (low_repo/'calls.jsonl').exists()
        checks.append('low-memory guard checkpoints before angr/CFG')
    lock_repo,lock_root=fixture('live-worker')
    environment=dict(os.environ,SELFTEST_CFG_SLEEP='2')
    first_worker=subprocess.Popen(command(lock_repo,'--max-rss-mb','0','--min-available-mb','0'),cwd=lock_repo,env=environment,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    for attempt in range(100):
        if (lock_root/'run-state.json').exists() and json.loads((lock_root/'run-state.json').read_text())['state']=='cfg':break
        time.sleep(.02)
    second=run(lock_repo,'--max-rss-mb','0','--min-available-mb','0',success=False)
    stdout,stderr=first_worker.communicate(timeout=10)
    assert first_worker.returncode==0 and ('existing worker owns' in second.stderr or 'project-wide heavy-analysis lock' in second.stderr),(stdout,stderr,second.stderr)
    checks.append('duplicate live recovery worker is refused')
    spec=importlib.util.find_spec('angr')
    if spec is not None:
        package=Path(spec.origin).parent
        path=package/'analyses/decompiler/decompiler.py';tree=ast.parse(path.read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Decompiler')
        constructor=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
        names={n.arg for n in constructor.args.args+constructor.args.kwonlyargs}
        assert {'use_cache','update_cache'}<=names
        path=package/'knowledge_plugins/structured_code.py';tree=ast.parse(path.read_text())
        manager=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='StructuredCodeManager')
        assert any(isinstance(n,ast.FunctionDef) and n.name=='discard' for n in manager.body)
        checks.append('installed angr source exposes no-cache options and discard API')
    report={'test_kind':'exporter control-flow safety tests with fake CFG, not firmware behavioral verification',
            'checks':checks,'passed':True,'fixture_directory':str(temporary)}
    destination=library/'validation/extraction-verification';destination.mkdir(parents=True,exist_ok=True)
    (destination/'selftest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
