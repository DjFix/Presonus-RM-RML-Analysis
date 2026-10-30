"""Conditional address predicates and exact physical cones, not HDL hierarchy."""
from pathlib import Path
from functools import lru_cache
from collections import defaultdict,Counter
import json
from bdd import BDD
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
B=ROOT/'evidence/recovery/2026-10-27/nimh-bus-04'
OLD=ROOT/'evidence/recovery/2026-10-27/nimh-functional-03'
save=lambda n,v:(B/n).write_text(json.dumps(v,indent=2)+'\n')
eq={r['signal']:r for r in map(json.loads,(B/'functional-equations.jsonl').open())}
aliases=json.loads((B/'state-aliases.json').read_text())
capture=json.loads((B/'address-capture.json').read_text())
addr=[r['capture'] for r in capture['low_bits']]
projections=json.loads((B/'address-stage-projections.json').read_text())
replacements={r['signal']:r['data'] for r in projections}
bdd=BDD(eq,aliases,replacements=replacements,limit=1500000)
@lru_cache(None)
def support(n):
    n=n.lstrip('~')
    if n in ('0','1'):return frozenset()
    r=eq[n]
    return frozenset([n]) if r['op'] in ('ff','latch','gap','pad') else frozenset().union(*(support(x) for x in r['args']))
related=set(addr)|set(replacements)
pred=[];failures=Counter()
for row_index,(n,r) in enumerate(sorted(eq.items())):
    if row_index%100==0:
        bdd.ite.cache_clear()
        bdd=BDD(eq,aliases,replacements=replacements,limit=200000)
    if r['op']!='ff':continue
    for ix,role in [(0,'next_data'),(2,'enable'),(3,'reset')]:
        signal=r['args'][ix]
        if not any(bdd.rep(x) in related for x in support(signal)):continue
        try:
            root=bdd.build(signal);ss=bdd.support(root)
            if not ss&set(addr):continue
            if len(ss-set(addr))>10:failures['qualifier_budget']+=1;continue
            cubes=bdd.cubes(root,limit=512)
        except OverflowError:failures['bdd_or_cube_budget']+=1;continue
        full=[]
        for cube in cubes:
            mask=value=0;other={}
            for k,v in cube.items():
                if k in addr:
                    i=addr.index(k);mask|=1<<i;value|=v<<i
                else:other[k]=v
            if mask.bit_count()>=5:full.append(dict(mask=mask,value=value,qualifiers=other))
        if full:pred.append(dict(cell=n,role=role,signal=signal,cubes=full,signature=bdd.signature(root)))
save('address-all-predicates.json',pred)
save('address-predicate-limits.json',dict(failures=failures,scope='Positive Boolean cubes, minimum five address bits. Qualifiers and sampled-state history remain explicit; cubes do not establish register identity.'))
print('All address predicates',len(pred),'limits',dict(failures),flush=True)
# Reverse combinational fan-in stops at FF/primitive/pad boundaries. Preserve
# each intervening cell and each control separately; no clock fanout pollution.
def cone(roots):
    seen=set();boundary=set();todo=list(roots)
    while todo:
        n=todo.pop().lstrip('~')
        if n in seen or n in ('0','1'):continue
        seen.add(n);r=eq[n]
        if r['op'] in ('ff','latch','gap','pad'):boundary.add(n)
        else:todo.extend(r['args'])
    return dict(equations=sorted(seen),boundaries=sorted(boundary))
io=json.loads((OLD/'physical-interface-pins.json').read_text())
tri=json.loads((B/'tristate-predicates.json').read_text())
data_balls=[r['ball'] for r in tri if r['function']=='a7eac565cad8c9c43498d7cb761775e127a432c7627125a9c9cb8d05c6a16554']
bus=[];read_front=set()
for ball in data_balls:
    pad='PAD_'+ball+'.O';front=cone([pad]);stages=[];current=front['boundaries']
    for depth in range(3):
        states=[n for n in current if eq[n]['op']=='ff']
        c=cone([eq[n]['args'][0] for n in states]);stages.append(dict(depth=depth,states=states,data_cone=c))
        read_front.update(states);current=c['boundaries']
    bus.append(dict(ball=ball,output_cone=front,registered_stages=stages))
save('fsmc-readback-cones.json',bus)
save('fsmc-interface.json',dict(clock_ball='H3',data_balls_unordered=data_balls,
    address_low_to_high=[dict(cpu_byte_bit=i+1,ball=r['ball'],capture=r['capture']) for i,r in enumerate(capture['low_bits'])],
    controls=dict(two_active_low_select_candidates=['K1','K2'],output_enable_candidate='A11',write_control_candidate='J6',unresolved_control='G1'),
    status='16-bit synchronous nonmultiplexed FSMC-shaped interface. CPU scaling is a firmware-supported candidate; data lane permutation and select-to-aperture assignment unresolved.'))
# Exact full reverse control/data cones for every positively attributed target.
targets={r['register'] for r in json.loads((B/'address-control-predicates.json').read_text())}
cells={n:dict(equation=eq[n],data=cone([eq[n]['args'][0]]),enable=cone([eq[n]['args'][2]]),reset=cone([eq[n]['args'][3]])) for n in sorted(targets)}
save('register-cell-cones.json',cells)
banks=[('AVB listener',0xc00,0xc80),('AVB talker',0x1200,0x1280),('RTC',0x4000,0x4080),('PTP RX',0x4080,0x4100),('PTP TX',0x4100,0x4180),('Ethernet SYS',0x4280,0x4300),('Ethernet MAC',0x4300,0x4380),('Router setup',0x5000,0x5100),('Audio clock',0x5100,0x5200),('InS',0x5600,0x5700),('HPLL',0x6000,0x6400)]
groups=json.loads((B/'address-decoder-groups.json').read_text())
bank_rows=[]
for label,start,end in banks:
    rows=[]
    for off in range(start,end,2):
        matches=[g for g in groups if ((off>>1)&g['mask'])==g['value']]
        if matches:rows.append(dict(offset=hex(off),matches=matches))
    bank_rows.append(dict(bank=label,start=hex(0x60000000+start),end_exclusive=hex(0x60000000+end),
       low_address_candidates=rows,exact_full_address_mapping=False,
       scope='Low-address predicate candidates only: unconstrained high bits and transaction qualifiers prevent unique bank attribution.'))
save('register-bank-candidates.json',bank_rows)
print('Readback lanes',len(bus),'control target cells',len(cells),'bank candidate halfwords',[(r['bank'],len(r['low_address_candidates'])) for r in bank_rows],flush=True)
# Qualifier history retains actual D/CE/reset for targeted decoder conditions.
qualifiers={n for r in pred for c in r['cubes'] for n in c['qualifiers']}
history={};todo=[(n,0) for n in qualifiers]
while todo:
    n,depth=todo.pop()
    if n in history or eq[n]['op']!='ff':continue
    r=eq[n];c=cone([r['args'][0]])
    history[n]=dict(equation=r,depth=depth,data_cone=c)
    if depth<5:todo.extend((x,depth+1) for x in c['boundaries'] if eq[x]['op']=='ff')
save('decoder-qualifier-history.json',history)
print('Qualifier state histories',len(history),flush=True)
