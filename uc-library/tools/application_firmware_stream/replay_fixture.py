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
def expected_with_codec_version(expected, old_version, current_version):
    tokens=expected['trace'].split()
    assert int(tokens[0])==len(tokens)-2
    changes=0
    for index in range(1,len(tokens)-1):
        fields=bytes.fromhex(tokens[index]).decode('ascii').split()
        if fields[0]=='init':
            assert len(fields)==7 and fields[2]==old_version,fields
            fields[2]=current_version
            tokens[index]=' '.join(fields).encode('ascii').hex()
            changes+=1
    return {**expected,'trace':' '.join(tokens)},changes

parent.mkdir(parents=True,exist_ok=True);work=parent/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-'+uuid.uuid4().hex[:8]);work.mkdir();owned=work/'owned';owned.mkdir();logs=work/'logs';logs.mkdir();fixture=json.loads(a.fixture.read_text());assert not fixture['original_zlib_binary_executed'];bridge=Bridge(a.bridge.resolve(),owned,logs);rows=[]
try:
    historical_info=fixture['native_zlib_info']
    info=bridge.ask('info').split()
    sys.path.insert(0,str(repo/'uc-library/tools/recovery'))
    from pinned_codec_replay_binding import canonical_build,read_canonical_codec_link
    codec_provider=None
    if a.bridge.resolve().parent==canonical_build(repo):
        codec_provider=read_canonical_codec_link(repo,a.bridge)
        assert info==['1.2.11','1.2.11',*historical_info[2:]],(info,historical_info)
    else:
        assert info==historical_info,(info,historical_info)
    adjusted_cases=0
    adjusted_init_calls=0
    for row in fixture['cases']:
        expected=row['expected']
        if codec_provider is not None:
            expected,changes=expected_with_codec_version(expected,historical_info[0],info[0])
            adjusted_cases+=bool(changes)
            adjusted_init_calls+=changes
        actual=native(bridge,row['input'])
        result=dict(role=row['role'],index=row['index'],actual=actual,passed=actual==expected)
        rows.append(result)
        assert result['passed'],dict(input=row,actual=result)
finally:bridge.close()
assert len(rows)==238
(work/'results.json').write_text(json.dumps(rows,indent=2)+'\n');proof=dict(passed=True,cases=len(rows),fixture_sha256=sha(a.fixture),bridge_sha256=sha(a.bridge),original_elf_executed=False,results_sha256=sha(work/'results.json'),native_zlib_info=info,historical_fixture_zlib_info=historical_info,pinned_codec_provider_binding=codec_provider,adjusted_init_version_cases=adjusted_cases,adjusted_init_version_calls=adjusted_init_calls)
(work/'validation.json').write_text(json.dumps(proof,indent=2)+'\n')
if a.report:
    path=a.report.resolve();assert path.is_relative_to(repo) and not path.exists();path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(proof,indent=2)+'\n')
print('passed',len(rows),'retained native stream cases')
