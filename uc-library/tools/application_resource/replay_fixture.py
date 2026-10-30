#!/usr/bin/env python3
"""Native-only replay of retained ResourceLibrary state/ownership fixtures."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
import uuid
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repository',type=Path,required=True);p.add_argument('--bridge',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--report',type=Path)
a=p.parse_args();repo=a.repository.resolve();parent=a.work.resolve();assert os.geteuid()!=0 and parent.is_relative_to(repo/'temp');sys.path.insert(0,str(repo/'uc-library/tools/file_cleanup'));from differential import Bridge,sha
def token(value):return 'NULL' if value is None else value or '-'
def native(bridge,case,constructor,destructor):
    bridge.ask('reset');bridge.ask('native_new '+constructor);states=[bridge.ask('native_info')];metadata=[]
    for operation in case['add']:
        if operation['kind']=='null':bridge.ask('native_add 0')
        else:
            name,version,image,size,compressed=operation['metadata'];values=token(name)+' '+f'{version} {image} {size} {compressed}'
            if operation['kind']=='raw':value=int(bridge.ask('native_add_raw '+values))
            else:
                value=int(bridge.ask('bundle_new'));bridge.ask('bundle_set '+str(value)+' '+values);bridge.ask('native_add '+str(value))
            metadata.append(bridge.ask('bundle_info '+str(value)))
        states.append(bridge.ask('native_info'))
    queries=[[int(bridge.ask('native_get '+token(name))),int(bridge.ask('native_version '+token(name)))] for name in case['queries']]
    bridge.ask('native_destroy '+destructor)
    return dict(states=states,metadata=metadata,queries=queries,deallocation=bridge.ask('trace'))
parent.mkdir(parents=True,exist_ok=True);work=parent/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-'+uuid.uuid4().hex[:8]);work.mkdir();owned=work/'owned';owned.mkdir();logs=work/'logs';logs.mkdir();fixture=json.loads(a.fixture.read_text());assert not fixture['original_core_binary_executed'];bridge=Bridge(a.bridge.resolve(),owned,logs);results=[]
try:
    for row in fixture['cases']:
        actual=native(bridge,row['input'],row['constructor'],row['destructor']);result=dict(role=row['role'],index=row['index'],constructor=row['constructor'],destructor=row['destructor'],actual=actual,passed=actual==row['expected']);results.append(result);assert result['passed'],dict(input=row,actual=result)
finally:bridge.close()
assert len(results)==352
(work/'results.json').write_text(json.dumps(results,indent=2)+'\n');proof=dict(passed=True,cases=len(results),fixture_sha256=sha(a.fixture),bridge_sha256=sha(a.bridge),original_elf_executed=False,results_sha256=sha(work/'results.json'))
(work/'validation.json').write_text(json.dumps(proof,indent=2)+'\n')
if a.report:
    path=a.report.resolve();assert path.is_relative_to(repo) and not path.exists();path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(proof,indent=2)+'\n')
print('passed',len(results),'retained native registration cases')
