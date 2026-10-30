#!/usr/bin/env python3
"""Native-only retained FirmwareBundle stream replay; no original ELF execution."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
import uuid
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repository',type=Path,required=True);p.add_argument('--bridge',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--report',type=Path)
a=p.parse_args();repo=a.repository.resolve();parent=a.work.resolve();assert os.geteuid()!=0 and parent.is_relative_to(repo/'temp');sys.path.insert(0,str(repo/'uc-library/tools/file_cleanup'));from differential import Bridge,sha
def native(bridge,case):
    bridge.ask('begin '+(case['payload'] or '-')+' '+f"{case['declared_size']} {case['compressed']} {case['null_input']} {case['fault_init']}");results=[]
    for action in case['actions']:
        if action[0]=='read':
            response=bridge.ask(f'native_read {action[1]} {action[2]}').split();results.append([int(response[0]),response[2]])
        else:results.append([int(bridge.ask('native_'+action[0]))])
    trace=bridge.ask('trace');cleanup=int(bridge.ask('cleanup'));return dict(results=results,trace=trace,fixture_cleanup_live_contexts=cleanup)
parent.mkdir(parents=True,exist_ok=True);work=parent/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-'+uuid.uuid4().hex[:8]);work.mkdir();owned=work/'owned';owned.mkdir();logs=work/'logs';logs.mkdir();fixture=json.loads(a.fixture.read_text());assert not fixture['original_zlib_binary_executed'];bridge=Bridge(a.bridge.resolve(),owned,logs);rows=[]
try:
    info=bridge.ask('info').split();assert info==fixture['native_zlib_info']
    for row in fixture['cases']:
        actual=native(bridge,row['input']);result=dict(role=row['role'],index=row['index'],actual=actual,passed=actual==row['expected']);rows.append(result);assert result['passed'],dict(input=row,actual=result)
finally:bridge.close()
assert len(rows)==238
(work/'results.json').write_text(json.dumps(rows,indent=2)+'\n');proof=dict(passed=True,cases=len(rows),fixture_sha256=sha(a.fixture),bridge_sha256=sha(a.bridge),original_elf_executed=False,results_sha256=sha(work/'results.json'),native_zlib_info=info)
(work/'validation.json').write_text(json.dumps(proof,indent=2)+'\n')
if a.report:
    path=a.report.resolve();assert path.is_relative_to(repo) and not path.exists();path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(proof,indent=2)+'\n')
print('passed',len(rows),'retained native stream cases')
