#!/usr/bin/env python3
"""Native-only retained serial fixtures; no original ELF execution."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repository',type=Path,required=True);p.add_argument('--bridge',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--report',type=Path)
a=p.parse_args();repo=a.repository.resolve();parent=a.work.resolve();assert os.geteuid()!=0 and parent.is_relative_to(repo/'temp')
library=repo/'uc-library';sys.path.insert(0,str(library/'tools/file_cleanup'));from differential import Bridge,sha
parent.mkdir(parents=True,exist_ok=True);work=parent/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-'+uuid.uuid4().hex[:8]);work.mkdir();owned=work/'owned';owned.mkdir();logs=work/'logs';logs.mkdir()
fixture=json.loads(a.fixture.read_text());assert not fixture['original_core_binary_executed'];bridge=Bridge(a.bridge.resolve(),owned,logs);rows=[]
try:
    for index,row in enumerate(fixture['cases']):
        case=row['input'];name=f'case-{index:04d}';path=owned/name
        if case['content'] is not None:path.write_bytes(bytes.fromhex(case['content']));path.chmod(case['mode'])
        bridge.ask('use '+name);actual=int(bridge.ask('native '+str(case['seed'])));trace=bridge.ask('trace')
        result=dict(index=index,passed=actual==row['expected'] and trace==row['expected_trace'],actual=actual,trace=trace)
        rows.append(result)
        if path.exists():path.chmod(0o600)
        assert result['passed'],dict(input=case,expected=row,actual=result)
finally:bridge.close()
assert len(rows)==755
(work/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
proof=dict(passed=True,cases=len(rows),fixture_sha256=sha(a.fixture),bridge_sha256=sha(a.bridge),original_elf_executed=False,results_sha256=sha(work/'results.json'))
(work/'validation.json').write_text(json.dumps(proof,indent=2)+'\n')
if a.report:
    path=a.report.resolve();assert path.is_relative_to(repo) and not path.exists();path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(proof,indent=2)+'\n')
print('passed',len(rows),'retained native serial cases')
