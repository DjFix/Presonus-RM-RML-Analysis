#!/usr/bin/env python3
"""Replay retained original-app fixtures against a fresh native consumer."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--bridge',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--unique',action='store_true',help='Keep each repeated CTest run in a new child directory');args=p.parse_args()
repo=args.repo.resolve();out=args.out.resolve();assert out.is_relative_to(repo) and out!=repo
if args.unique:out=out/('run-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'))
out.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with (out/'bridge-stderr.log').open('w') as stderr,(out/'results.jsonl').open('w') as results:
    process=subprocess.Popen([str(args.bridge.resolve())],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,text=True,bufsize=1)
    count=0;totals={}
    try:
        for line in args.fixture.read_text().splitlines():
            case=json.loads(line);assert case['passed'] and case['expected']==case['actual']
            process.stdin.write(case['command']+'\n');process.stdin.flush();actual=process.stdout.readline().strip()
            record=dict(role=case['role'],kind=case['kind'],constructor=case['constructor'],actual=actual,passed=actual==case['expected'])
            results.write(json.dumps(record)+'\n');results.flush();assert record['passed'],(case,record)
            count+=1;totals[case['kind']]=totals.get(case['kind'],0)+1
        process.stdin.write('quit\n');process.stdin.flush();assert process.stdout.readline().strip()=='OK';assert process.wait(timeout=10)==0
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=10)
(out/'validation.json').write_text(json.dumps(dict(passed=True,cpp_differential_passed=True,cases=count,totals=totals,fixture_sha256=sha(args.fixture),bridge_sha256=sha(args.bridge),results_sha256=sha(out/'results.jsonl'),replay_tool_sha256=sha(Path(__file__)),original_elf_executed=False,oracle_regenerated=False),indent=2)+'\n')
print(out/'validation.json',flush=True)
