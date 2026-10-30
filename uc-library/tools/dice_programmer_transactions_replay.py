"""Replay retained programmer fixtures through an offline transport bridge."""
import argparse
import json
from pathlib import Path
import subprocess
p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--stdin',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);a=p.parse_args()
rows=list(map(json.loads,a.fixture.read_text().splitlines()));assert len(rows)==4352
result=subprocess.run([str(a.binary)],input=a.stdin.read_text(),text=True,capture_output=True);assert result.returncode==0,result.stderr
actual=list(map(json.loads,result.stdout.splitlines()));assert len(actual)==len(rows)
for row,value in zip(rows,actual):assert row['expected']==value,(row['index'],row['expected'],value)
print('PASS 4352 retained original programmer transaction/status/JEDEC witnesses; no device calls')
