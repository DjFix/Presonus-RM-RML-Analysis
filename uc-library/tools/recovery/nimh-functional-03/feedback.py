"""Structural feedback components excluding state and unresolved primitive boundaries."""
from pathlib import Path
import json,sys
sys.setrecursionlimit(50000)
B=Path('/home/rs/projects/opencs/ai-line-analysis/evidence/recovery/2026-10-27/nimh-functional-03')
eq={r['signal']:r for r in (json.loads(l) for l in (B/'functional-equations.jsonl').open())}
comb={n for n,r in eq.items() if r['op'] in ('alias','mux','xor','lut')}
adj={n:[a.lstrip('~') for a in eq[n]['args'] if a.lstrip('~') in comb] for n in comb}
indexes={};low={};stack=[];on=set();components=[]
def visit(n):
    indexes[n]=low[n]=len(indexes);stack.append(n);on.add(n)
    for x in adj[n]:
        if x not in indexes:visit(x);low[n]=min(low[n],low[x])
        elif x in on:low[n]=min(low[n],indexes[x])
    if low[n]==indexes[n]:
        group=[]
        while True:
            x=stack.pop();on.remove(x);group.append(x)
            if x==n:break
        if len(group)>1 or n in adj[n]:components.append(sorted(group))
for n in sorted(comb):
    if n not in indexes:visit(n)
records=[dict(signals=g,equations=[eq[n] for n in g],status='unresolved combinational feedback; no timing or latch interpretation assigned') for g in sorted(components)]
(B/'functional-feedback-components.json').write_text(json.dumps(records,indent=2)+'\n')
print('Structural feedback components:',len(records),'sizes:',[len(r['signals']) for r in records])
