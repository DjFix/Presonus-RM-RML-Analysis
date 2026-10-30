#!/usr/bin/env python3
"""Replay retained identity cases against native source only; no original ELF."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
import uuid
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repository',type=Path,required=True);p.add_argument('--bridge',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--report',type=Path)
a=p.parse_args();repo=a.repository.resolve();parent=a.work.resolve();assert os.geteuid()!=0 and parent.is_relative_to(repo/'temp');sys.path.insert(0,str(repo/'uc-library/tools/file_cleanup'));from differential import Bridge,sha
parent.mkdir(parents=True,exist_ok=True);work=parent/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-'+uuid.uuid4().hex[:8]);work.mkdir();owned=work/'owned';owned.mkdir();logs=work/'logs';logs.mkdir();fixture=json.loads(a.fixture.read_text());assert not fixture['original_core_binary_executed'];bridge=Bridge(a.bridge.resolve(),owned,logs);results=[]
try:
    for row in fixture['cases']:
        bridge.ask('reset');actual=dict(value=int(bridge.ask(f"native {row['method']} {row['serial']}")),trace=bridge.ask('trace'));result=dict(serial=row['serial'],method=row['method'],actual=actual,passed=actual==row['expected'] and actual['value']==row['arithmetic_value']);results.append(result);assert result['passed'],dict(input=row,actual=result)
finally:bridge.close()
assert len(results)==fixture['case_count']
(work/'results.json').write_text(json.dumps(results,indent=2)+'\n');proof=dict(passed=True,cases=len(results),fixture_sha256=sha(a.fixture),bridge_sha256=sha(a.bridge),original_elf_executed=False,results_sha256=sha(work/'results.json'))
(work/'validation.json').write_text(json.dumps(proof,indent=2)+'\n')
if a.report:
    path=a.report.resolve();assert path.is_relative_to(repo) and not path.exists();path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(proof,indent=2)+'\n')
print('passed',len(results),'retained native identity cases')
