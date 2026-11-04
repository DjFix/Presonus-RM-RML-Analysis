"""Compare canonical built source-port executable with independently captured ARM fixtures."""
import argparse,json,struct,subprocess
from pathlib import Path

def replay(exe,fixture):
    data=json.loads(Path(fixture).read_text());lines=[];expected=[]
    for case in data['cases']:
        c=case['input'];e=case['expected'];k=c['kind']
        if k=='getter':line=f"getter {c['target']} {c['seed']}";want=str(e['offset'])
        elif k=='name':line='name';want=e['text']
        elif k=='destructor':
            assert e['vptr']==1691928 and e['writes']==[[0,4,1691928]]
            assert bytes.fromhex(e['object'])[4:]==bytes([c['seed']])*508
            line=f"destructor {c['seed']}";want='base-vptr-only'
        elif k=='bar':line=' '.join(map(str,['bar',len(c['bars']),*c['bars'],c['value']]));want=f"{e['index']} {e['record']}"
        elif k=='tempo':line=' '.join(map(str,['tempo',len(c['records']),*(v for r in c['records'] for v in r),c['value']]));want=struct.pack('<d',e['value']).hex()
        elif k=='delta':line=' '.join(map(str,['delta',int(c['musical']),int(c['blocked']),c['count'],c['delta'],*c['values']]));want=e['event']
        lines.append(line);expected.append(want)
    result=subprocess.run([str(exe)],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True)
    observed=result.stdout.splitlines();assert len(observed)==len(expected),(len(observed),len(expected),result.stderr)
    for i,(a,b) in enumerate(zip(observed,expected)):
        assert a==b,(i,lines[i],a,b)
    print(f"PASS {len(expected)} original ARM/source-port comparisons; complete 112-byte event buffers, getter identity, map records, binary64 tempo, D1 opaque base-dispatch identity reset in live borrowed state")
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args();replay(a.executable,a.fixtures)
