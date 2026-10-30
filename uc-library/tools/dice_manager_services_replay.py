"""Replay retained manager witnesses against an explicitly supplied native binary."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--stdin',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);a=p.parse_args()
rows=[json.loads(line) for line in a.fixture.read_text().splitlines()]
assert len(rows)==1414
r=subprocess.run([str(a.binary.resolve())],input=a.stdin.read_text(),text=True,capture_output=True)
assert r.returncode==0,(r.returncode,r.stderr)
lines=r.stdout.splitlines();assert lines[-1:]==['UART: close port -1'],'Unexpected or missing UART destructor diagnostic'
actual=[json.loads(line) for line in lines[:-1]];assert len(actual)==len(rows)
for row,value in zip(rows,actual):assert value==row['expected'],(row['index'],row['input'],row['expected'],value)
print('PASS 1414 retained original Dice3Manager witnesses; one exact terminal UART diagnostic')
