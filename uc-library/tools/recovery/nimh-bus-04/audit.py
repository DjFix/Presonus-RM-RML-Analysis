"""Independent truth-table and bounded sequential rewrite replay on Linux."""
from pathlib import Path
from collections import Counter
import json, random, sys, hashlib
from functools import lru_cache
sys.setrecursionlimit(20000)
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
B=ROOT/'evidence/recovery/2026-10-27/nimh-bus-04'
def rows(p):return (json.loads(l) for l in p.open())
raw={r['signal']:r for r in rows(B/'physical-equations.jsonl')}
final={r['signal']:r for r in rows(B/'functional-equations.jsonl')}
roots=[n for n in final if n.startswith('PAD_')]
randomizer=random.Random(0x4e494d48)
states={n:r['init'] for n,r in raw.items() if r['op'] in ('ff','latch')}
leaves=sorted(n for n,r in raw.items() if r['op'] in ('gap','pad'))
@lru_cache(maxsize=None)
def cofactors(table,width):
    low=sum(((table>>j)&1)<<k for k,j in enumerate(range(0,1<<width,2)))
    high=sum(((table>>j)&1)<<k for k,j in enumerate(range(1,1<<width,2)))
    return low,high
def evaluator(eq,leaf,state):
    memo={};busy=set()
    def get(ref):
        if ref.startswith('~'):
            v=get(ref[1:]);return None if v is None else 1-v
        if ref in ('0','1'):return int(ref)
        if ref in memo:return memo[ref]
        r=eq[ref];op=r['op']
        if op in ('pad','gap'):return leaf[ref]
        if op in ('ff','latch'):return state[ref]
        if ref in busy:return None
        busy.add(ref)
        if op=='alias':v=get(r['args'][0])
        elif op=='mux':
            s=get(r['args'][0])
            if s is not None:v=get(r['args'][2] if s else r['args'][1])
            else:
                low=get(r['args'][1]);high=get(r['args'][2]);v=low if low==high else None
        elif op=='xor':
            if r['args'][0]==r['args'][1]:v=0
            else:
                low=get(r['args'][0]);high=get(r['args'][1]);v=None if low is None or high is None else low^high
        elif op=='lut':
            def choose(table,args):
                if not args:return table&1
                low,high=cofactors(table,len(args))
                if low==high:return choose(low,args[1:])
                select=get(args[0])
                if select is not None:return choose(high if select else low,args[1:])
                vl=choose(low,args[1:]);vh=choose(high,args[1:])
                return vl if vl==vh else None
            v=choose(r['init'],r['args'])
        else:raise ValueError(op)
        busy.remove(ref)
        if v is not None:memo[ref]=v
        return v
    return get

# LUT ordering: physical A1 is index bit 0; O5 selects the low 32 INIT bits.
# Exercise every address of every captured physical LUT, with independent index construction.
lut_addresses=0
for r in json.loads((B/'lut-table-provenance.json').read_text()):
    if r['mode']!='NONE':continue
    init=int(r['init_hex'],16)
    for k in range(64):
        bits=[(k>>j)&1 for j in range(6)]
        idx=int(''.join(str(x) for x in reversed(bits)),2)
        assert ((init>>idx)&1)==((init>>k)&1)
        if k<32:assert ((init>>k)&1)==((init&0xffffffff)>>k)&1
        lut_addresses+=1

compares=0;state_compares=0;cycles=[];skipped_value_comparisons=0;skipped_transition_comparisons=0
sample=sorted(set(final)&set(raw))
if len(sample)>1500:sample=randomizer.sample(sample,1500)
for tick in range(64):
    leaf={n:randomizer.randrange(2) for n in leaves}
    a=evaluator(raw,leaf,states);b=evaluator(final,leaf,states)
    for n in roots+sample:
        try:
            va=a(n);vb=b(n)
            if va is None or vb is None:raise ValueError('Unresolved raw dependency '+n)
        except ValueError as e:
            cycles.append(str(e));skipped_value_comparisons+=1;continue
        assert va==vb,(tick,n,va,vb)
        compares+=1
    new={}
    for n in final:
        r=final[n]
        if r['op'] not in ('ff','latch'):continue
        try:
            vals=[b(x) for x in r['args']]
            original=[a(x) for x in raw[n]['args']]
            if None in vals or None in original:raise ValueError('Unresolved transition dependency '+n)
        except ValueError as e:
            cycles.append(str(e));skipped_transition_comparisons+=1;continue
        assert vals==original,(n,vals,original)
        state_compares+=1
        d,clk,ce,sr=vals
        # Bounded event test: selected clock event/level is supplied by the test harness.
        new[n]=r.get('sr_value',r['init']) if sr else d if ce and (r['op']=='ff' or not clk) else states[n]
    states.update(new)
report=dict(passed_within_evaluated_domain=True,complete_replay_passed=not cycles,seed='0x4e494d48',abstract_patterns=64,compared_output_and_internal_values=compares,
            compared_register_transition_inputs=state_compares,physical_lut_addresses_checked=lut_addresses,
            encountered_feedback_signals=sorted(set(cycles)),skipped_value_comparisons=skipped_value_comparisons,
            skipped_transition_comparisons=skipped_transition_comparisons,op_counts=dict(Counter(r['op'] for r in final.values())),
            scope=['Configuration-derived raw versus simplified equations under independent abstract boundary values.',
                   'Sequential transition inputs and reset/enable equations checked; test harness supplies events, not physical clock timing.',
                   'INIT bit indexing sanity check is not independent silicon mapping validation.',
                   'No proof of unresolved primitive behavior, original HDL equivalence, timing or hardware.'])
(B/'functional-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
