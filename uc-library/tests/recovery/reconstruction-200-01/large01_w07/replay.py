import json,subprocess,sys
from pathlib import Path
exe=sys.argv[1];fixture=Path(sys.argv[2]);j=json.loads(fixture.read_text());count=0
for c in j['cases']:
 if c['address'] not in (0xb7280,0xb7264,0xb68d8):continue
 mode='output' if c['address']==0xb7280 else ('input' if c['address']==0xb7264 else 'lookup')
 actual=int(subprocess.check_output([exe,mode,str(c['input'])],text=True));assert actual==c['native']['result'];count+=1
assert subprocess.check_output([exe,'cleanup'],text=True).strip()=='2'
print(f'{count} original-return cases and actual pinned provider owned-child cleanup passed; lifecycle native boundary traces retained separately')
