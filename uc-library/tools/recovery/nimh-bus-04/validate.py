"""Exhaustive configured counter checks and bounded primitive/control checks."""
from pathlib import Path
from functools import lru_cache
from itertools import product
import json,random
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
B=ROOT/'evidence/recovery/2026-10-27/nimh-bus-04'
eq={r['signal']:r for r in map(json.loads,(B/'functional-equations.jsonl').open())}
def evaluator(values):
    @lru_cache(None)
    def get(n):
        if n.startswith('~'):return 1-get(n[1:])
        if n in ('0','1'):return int(n)
        if n in values:return values[n]
        r=eq[n];op=r['op']
        if op in ('ff','latch','gap','pad'):return 0
        a=[get(x) for x in r['args']]
        if op=='alias':return a[0]
        if op=='lut':return (r['init']>>sum(v<<i for i,v in enumerate(a)))&1
        if op=='xor':return a[0]^a[1]
        if op=='mux':return a[2] if a[0] else a[1]
        raise ValueError(op)
    return get
checks=0;loads=0
for model in json.loads((B/'address-counter-models.json').read_text()):
    bits=model['counter']['bits_low_to_high'];inputs=model['ordered_inputs']
    for value in range(1<<len(bits)):
        values=dict(model['counter']['mode']);values.update({n:(value>>i)&1 for i,n in enumerate(bits)})
        get=evaluator(values)
        result=sum(get(eq[n]['args'][0])<<i for i,n in enumerate(bits))
        assert result==((value+1)&((1<<len(bits))-1)),(value,result)
        checks+=1
    for value in range(1<<len(inputs)):
        values=dict(model['load_mode']);values.update({n:(value>>i)&1 for i,n in enumerate(inputs)})
        get=evaluator(values)
        assert all(get(eq[n]['args'][0])==((value>>i)&1) for i,n in enumerate(bits))
        loads+=1
tri=json.loads((B/'tristate-predicates.json').read_text());balls=['A5','A6','A7','A8','A9','B6','B8','B9','C1','D1','D2','D3','E1','E3','F1','F2']
aliases=json.loads((B/'state-aliases.json').read_text())
def rep(n):
    while n in aliases:n=aliases[n]
    return n
control_checks=0
for p,q,r,f in product([0,1],repeat=4):
    values={'D0X0Y55.IOB[0].PAD':p,'D0X0Y55.IOB[1].PAD':q,'D0X32Y127.IOB[0].PAD':r}
    values.update({n:f for n,e in eq.items() if e['op']=='ff' and rep(n)=='D0X17Y114.SLICE[1].AQ'})
    get=evaluator(values)
    for ball in balls:
        assert get('PAD_'+ball+'.T')==(r|f|(p&q)),(ball,p,q,r,f)
        control_checks+=1
report=dict(passed=True,counter_increment_states=checks,counter_load_vectors=loads,tristate_truth_comparisons=control_checks,
    io_ff_count=sum(r['op']=='ff' and 'primitive' in r for r in eq.values()),
    scope=['All 16384 values of each of two 14-bit configured next-state counters and all 16384 input vectors per counter.',
      'Common tristate Boolean identity exhaustively checked under decoded state aliases.',
      'No claim about transaction reachability, bus setup/hold, clock ratios or bank-address uniqueness.'])
(B/'bus-model-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
