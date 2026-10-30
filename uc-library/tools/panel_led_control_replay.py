#!/usr/bin/env python3
"""Maintained CTest replay; raw receipts retained, only pure getter diagnostic normalized."""
import argparse,hashlib,json,re,subprocess,time
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',required=True,type=Path);p.add_argument('--fixture',required=True,type=Path);p.add_argument('--normalization',required=True,type=Path);p.add_argument('--out-root',type=Path)
    a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    metadata=json.loads((a.fixture.parent/'validation.json').read_text());assert metadata['passed'] and sha(a.fixture)==metadata['fixture_sha256']
    rule=json.loads(a.normalization.read_text());assert rule['original_mangled_name']=='_ZNK4Core8Portable12NumericParam8getValueEv' and rule['source_commit']=='e8cbdea4a4a20e15111f5a690798a259c0374b31'
    assert hashlib.sha256(rule['exact_body'].encode()).hexdigest()==rule['exact_body_sha256']
    assert re.fullmatch(r'ParamValue NumericParam::getValue\s*\(\s*\)\s*const\s*\{\s*return value;\s*\}',rule['exact_body'])
    def normalize(value):
        fields=value.split('|');assert len(fields)==3
        events=[]
        for event in fields[1].split(';'):
            if not event:continue
            if event.startswith('G:'):assert re.fullmatch(r'G:[0-9]+',event)
            else:events.append(event+';')
        fields[1]=''.join(events);return '|'.join(fields)
    out=(a.out_root or a.binary.resolve().parent/'led-replays')/str(time.time_ns());out.mkdir(parents=True,exist_ok=False)
    count=0
    with (out/'native-stderr.log').open('w') as errors,(out/'results.jsonl').open('w') as results:
        child=subprocess.Popen([str(a.binary.resolve())],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,text=True)
        try:
            for line in a.fixture.open():
                row=json.loads(line);child.stdin.write(row['command']+'\n');child.stdin.flush();actual=child.stdout.readline().strip();okay=normalize(actual)==normalize(row['expected'])
                results.write(json.dumps(dict(index=count,role=row['role'],passed=okay,actual=actual,expected=row['expected']))+'\n');assert okay,(count,row['role']);count+=1
            child.stdin.write('quit\n');child.stdin.flush();assert child.stdout.readline().strip()=='OK';assert child.wait(timeout=10)==0
        finally:
            if child.poll() is None:child.terminate();child.wait(timeout=10)
    assert count==metadata['cases']
    (out/'validation.json').write_text(json.dumps(dict(passed=True,cases=count,fixture_sha256=sha(a.fixture),normalization_sha256=sha(a.normalization),binary_sha256=sha(a.binary),results_sha256=sha(out/'results.jsonl'),getter_count_equivalence_claimed=False,original_oracle_regenerated=False),indent=2)+'\n')
    print(f'PASS {count} retained LED cases; evidence {out}',flush=True)
if __name__=='__main__':main()
