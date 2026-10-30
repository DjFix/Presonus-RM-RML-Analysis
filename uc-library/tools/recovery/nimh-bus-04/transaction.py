"""Exploratory bus-event replay. Candidate protocol, no hardware equivalence."""
from pathlib import Path
from functools import lru_cache
import json
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis');B=ROOT/'evidence/recovery/2026-10-27/nimh-bus-04'
OLD=ROOT/'evidence/recovery/2026-10-27/nimh-functional-03'
eq={r['signal']:r for r in map(json.loads,(B/'functional-equations.jsonl').open())}
io=json.loads((OLD/'physical-interface-pins.json').read_text())
ball={r['ball']:r['iob']+'.PAD' for r in io}
capture=json.loads((B/'address-capture.json').read_text())['low_bits']
pred=json.loads((B/'address-all-predicates.json').read_text())
targets={r['cell'] for r in pred if r['role']=='enable'}
needed=set();todo=[eq[n]['args'][2] for n in targets]
while todo:
    n=todo.pop().lstrip('~')
    if n in needed or n in ('0','1'):continue
    needed.add(n);r=eq[n]
    if r['op'] in ('gap','pad'):continue
    todo.extend(r['args'][:1]+r['args'][2:] if r['op'] in ('ff','latch') else r['args'])
stateset={n for n in needed if eq[n]['op'] in ('ff','latch')}
resetn='D0X18Y63.SLICE[0].AQ'
core='D0X18Y64.BUFGMUX[1].O';bus='D0X18Y64.BUFGMUX[15].O'
data=['A5','A6','A7','A8','A9','B6','B8','B9','C1','D1','D2','D3','E1','E3','F1','F2']
def run(offset,select,adlevel):
    state={n:eq[n]['init'] for n in stateset};state[resetn]=1
    pads={ball[n]:1 for n in ['K1','K2','A11','J6','G1']+data}
    for i,r in enumerate(capture):pads[ball[r['ball']]]=(offset>>(i+1))&1
    active=set();counts={};steps=0
    def event(clock,collect=False):
        nonlocal steps
        steps+=1
        @lru_cache(None)
        def get(n):
            if n.startswith('~'):return 1-get(n[1:])
            if n in ('0','1'):return int(n)
            if n==resetn:return 1
            if n in state:return state[n]
            r=eq[n];op=r['op']
            if op=='pad':return pads.get(n,0)
            if op=='gap':return 0
            if op in ('ff','latch'):return r['init']
            a=[get(x) for x in r['args']]
            if op=='alias':return a[0]
            if op=='xor':return a[0]^a[1]
            if op=='mux':return a[2] if a[0] else a[1]
            if op=='lut':return (r['init']>>sum(v<<i for i,v in enumerate(a)))&1
            raise ValueError(op)
        if collect:
            for n in targets:
                if get(eq[n]['args'][2]):active.add(n);counts[n]=counts.get(n,0)+1
        new={}
        for n in stateset:
            if n==resetn:continue
            r=eq[n];d,clk,ce,sr=r['args']
            if not r.get('sr_sync',False) and get(sr):new[n]=r.get('sr_value',r['init'])
            elif clk==clock:
                if get(sr):new[n]=r.get('sr_value',r['init'])
                elif get(ce):new[n]=get(d)
        state.update(new)
    def cycle(collect=False):
        event(bus,collect)
        for _ in range(4):event(core,collect)
        event('~'+bus,collect)
        for _ in range(4):event(core,collect)
    for _ in range(8):cycle()
    baseline=set()
    for n in targets:
        if eq[n]['args'][2]=='1':baseline.add(n)
    pads[ball[select]]=0;pads[ball['G1']]=adlevel;pads[ball['J6']]=0
    for _ in range(2):cycle(True)
    pads[ball['G1']]=1-adlevel
    for _ in range(4):cycle(True)
    pads[ball['J6']]=1;pads[ball[select]]=1
    for _ in range(6):cycle(True)
    return dict(offset=hex(offset),select=select,address_valid_level=adlevel,active_cells=sorted(active-baseline),steps=steps)
results=[]
for select in ['K1','K2']:
    for adlevel in [0,1]:
        for off in [0xc04,0x1200,0x4288,0x4308,0x5000,0x5100,0x5640,0x6000]:
            r=run(off,select,adlevel);results.append(r)
            print(select,adlevel,hex(off),len(r['active_cells']),flush=True)
report=dict(status='Exploratory assumed protocol; not an admitted register map',state_closure=len(stateset),
 assumptions=['Core/bus event ratio 8:1; external data all ones; non-bus pads and opaque primitives zero.',
 'Decoded reset-release state forced high. Chip selects K1/K2, write J6 and address-valid G1 are candidate roles.',
 'INIT used for inactive clock domains. No electrical timing, RAM operation or device execution.'],results=results)
(B/'transaction-experiment.json').write_text(json.dumps(report,indent=2)+'\n')
