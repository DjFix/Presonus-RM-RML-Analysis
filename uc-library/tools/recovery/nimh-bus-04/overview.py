"""Inventory small control cones at pads and state boundaries, without role guesses."""
import json
from pathlib import Path
from collections import Counter,defaultdict
from functools import lru_cache
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
OLD=ROOT/'evidence/recovery/2026-10-27/nimh-functional-03'
OUT=ROOT/'evidence/recovery/2026-10-27/nimh-bus-04'
OUT.mkdir(parents=True,exist_ok=True)
eq={r['signal']:r for r in (json.loads(l) for l in (OLD/'functional-equations.jsonl').open())}
io=json.loads((OLD/'physical-interface-pins.json').read_text())
pins=json.loads((OLD/'functional-input-pins.json').read_text())
@lru_cache(maxsize=None)
def support(n):
    n=n.lstrip('~')
    if n in ('0','1'):return frozenset()
    r=eq[n]
    if r['op'] in ('ff','latch','gap','pad'):return frozenset([n])
    return frozenset().union(*(support(x) for x in r['args']))
def cone(n,depth=0):
    n=n.lstrip('~');r=eq.get(n)
    if r is None:return n
    if depth>=3 or r['op'] in ('ff','latch','gap','pad'):return dict(signal=n,op=r['op'])
    return dict(signal=n,op=r['op'],init=hex(r['init']) if 'init' in r else None,args=[cone(x,depth+1) for x in r['args']])
records=[]
for r in io:
    if not r['output_enabled']:continue
    n='PAD_'+r['ball']+'.T'
    s=sorted(support(n))
    record=dict(ball=r['ball'],tristate_support=s,cone=cone(n))
    records.append(record)
    if r['input_enabled']:print(r['ball'],'T support',s,'cone',record['cone'])
(OUT/'pad-control-overview.json').write_text(json.dumps(records,indent=2)+'\n')
controls=[]
for n,r in eq.items():
    if r['op']!='ff':continue
    for index,role in [(2,'enable'),(3,'reset')]:
        x=r['args'][index]
        if x in ('0','1'):continue
        s=sorted(support(x))
        controls.append(dict(register=n,role=role,signal=x,support=s))
(OUT/'state-control-support.json').write_text(json.dumps(controls,indent=2)+'\n')
print('Control support width histogram:',Counter(len(r['support']) for r in controls))
print('Most frequent control supports:')
for s,num in Counter(tuple(r['support']) for r in controls if len(r['support'])<=25).most_common(12):print(num,s)
