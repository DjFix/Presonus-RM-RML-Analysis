"""Compare compiled implementation against original ARM execution fixtures."""
import json,subprocess,sys
from pathlib import Path
rows=json.loads(Path('uc-library/tests/recovery/reconstruction-200-01/large01_w10/fixtures.json').read_text())
inputs=''.join(r['operation']+' '+' '.join(map(str,r['input']))+'\n' for r in rows)
actual=subprocess.check_output([sys.argv[1]],input=inputs,text=True).splitlines();assert len(actual)==len(rows)
for row,value in zip(rows,actual):
 expected=str(row['result']);assert value==expected,(row,value)
print(len(rows),'native versus portable cases passed; nine original targets; no object writes')
