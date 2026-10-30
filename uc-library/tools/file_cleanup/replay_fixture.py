#!/usr/bin/env python3
"""Replay retained app expectations against native source only; never executes ELF."""
import argparse
from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import sys
import uuid
from differential import Bridge,prepare,snapshot,encode,decode

def normalize(trace,root):
    result=[]
    for line in trace:
        kind,path,status=line.split()
        relative=str(Path(decode(path)).relative_to(root))
        result.append(kind+' '+encode(relative)+' '+status)
    return sorted(result)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository',type=Path,required=True);p.add_argument('--bridge',type=Path,required=True)
    p.add_argument('--fixture',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    p.add_argument('--report',type=Path)
    a=p.parse_args();repo=a.repository.resolve();parent=a.work.resolve()
    assert os.geteuid()!=0 and parent.is_relative_to(repo/'temp')
    parent.mkdir(parents=True,exist_ok=True)
    work=parent/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-'+uuid.uuid4().hex[:8])
    work.mkdir(exist_ok=False);owned=work/'owned';owned.mkdir();logs=work/'logs';logs.mkdir()
    fixture=json.loads(a.fixture.read_text());assert fixture['original_core_binary_executed'] is False
    bridge=Bridge(a.bridge.resolve(),owned,logs);count=0
    try:
        for row in fixture['cases']:
            case=row['input'];root=owned/f'case-{count:03d}'
            prepare(root,case);bridge.ask('reset');bridge.ask('trace_begin');bridge.ask('native_new '+encode(str(root)))
            added=[int(bridge.ask('native_add_file '+encode(s))) for s in case['files']]+[int(bridge.ask('native_add_directory '+encode(s))) for s in case['directories']]
            actual=dict(result=int(bridge.ask('native_cleanup')),add_results=added)
            bridge.ask('native_destroy');fs,arrays=bridge.trace()
            actual.update(filesystem_trace=normalize(fs,root),array_deallocation_trace=arrays,tree=snapshot(root,case))
            assert actual==row['expected'],dict(index=count,input=case,actual=actual,expected=row['expected'])
            count+=1
    finally:bridge.close()
    assert count==72
    result=dict(passed=True,cases=count,original_elf_executed=False,fixture_sha256=hashlib.sha256(a.fixture.read_bytes()).hexdigest(),bridge_sha256=hashlib.sha256(a.bridge.read_bytes()).hexdigest())
    (work/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    if a.report:
        report=a.report.resolve();assert report.is_relative_to(repo) and not report.exists();report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(result,indent=2)+'\n')
    print(f'passed {count} retained FileCleanup lifecycle cases; native source only')
if __name__=='__main__':main()
