"""Prove replicated control states and extract compact control predicates."""
from pathlib import Path
from collections import defaultdict,Counter
from functools import lru_cache
import json
from bdd import BDD
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
OUT=ROOT/'evidence/recovery/2026-10-27/nimh-bus-04'
eq={r['signal']:r for r in (json.loads(l) for l in (OUT/'functional-equations.jsonl').open())}
io=json.loads((ROOT/'evidence/recovery/2026-10-27/nimh-functional-03/physical-interface-pins.json').read_text())
@lru_cache(maxsize=None)
def support(n):
    n=n.lstrip('~')
    if n in ('0','1'):return frozenset()
    r=eq[n]
    if r['op'] in ('ff','latch','gap','pad'):return frozenset([n])
    return frozenset().union(*(support(x) for x in r['args']))
aliases={};proofs=[]
for iteration in range(3):
    bdd=BDD(eq,aliases);groups=defaultdict(list);skipped=0
    for n,r in sorted(eq.items()):
        if r['op']!='ff' or n in aliases:continue
        if max(len(support(x)) for x in [r['args'][0],r['args'][2],r['args'][3]])>12:continue
        try:
            d,clk,ce,sr=r['args']
            signature=(bdd.build(d),clk,bdd.build(ce),bdd.build(sr),r['init'],r.get('sr_value',r['init']),r['sr_sync'])
            groups[signature].append(n)
        except OverflowError:skipped+=1
    new=0
    for signature,ns in groups.items():
        if len(ns)<2:continue
        rep=ns[0]
        for n in ns[1:]:aliases[n]=rep;new+=1
        proofs.append(dict(iteration=iteration,members=ns,representative=rep,
          d_function=bdd.signature(signature[0]),ce_function=bdd.signature(signature[2]),sr_function=bdd.signature(signature[3]),
          clock=signature[1],init=signature[4],sr_value=signature[5],sr_sync=signature[6],
          scope='Inductive equality under decoded common clock/reset/enable/init and canonical D/CE/SR functions. No timing equivalence claimed.'))
    print('State equivalences round',iteration,'new aliases',new,'BDD nodes',len(bdd.nodes),'skipped',skipped,flush=True)
    if not new:break
bdd=BDD(eq,aliases)
records=[]
for n,r in sorted(eq.items()):
    if r['op'] not in ('ff','latch'):continue
    for i,role in [(2,'enable'),(3,'reset')]:
        v=r['args'][i]
        if v in ('0','1') or len(support(v))>22:continue
        try:
            root=bdd.build(v);cubes=bdd.cubes(root,limit=16)
        except OverflowError:continue
        records.append(dict(register=n,role=role,signal=v,function=bdd.signature(root),cubes=cubes))
for n,v in [('state-equivalences.json',proofs),('state-aliases.json',aliases),('control-predicates.json',records)]:
    (OUT/n).write_text(json.dumps(v,indent=2)+'\n')
print('Canonical predicates:',len(records),'aliases:',len(aliases),'BDD nodes:',len(bdd.nodes))
pad_records=[]
for r in io:
    if not r['output_enabled']:continue
    n='PAD_'+r['ball']+'.T'
    try:
        root=bdd.build(n);cubes=bdd.cubes(root,16)
        rec=dict(ball=r['ball'],function=bdd.signature(root),cubes=cubes)
        pad_records.append(rec)
    except OverflowError:continue
(OUT/'tristate-predicates.json').write_text(json.dumps(pad_records,indent=2)+'\n')
for sig,num in Counter(r['function'] for r in pad_records).most_common(5):
    print('Shared tristate function',num,'balls',[r['ball'] for r in pad_records if r['function']==sig])
