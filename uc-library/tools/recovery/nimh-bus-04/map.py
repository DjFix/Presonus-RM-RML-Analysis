"""Indexed bank candidates, exact endpoint cones and typed memory consumers."""
from pathlib import Path
from collections import defaultdict,Counter
from functools import lru_cache
import json
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis');B=ROOT/'evidence/recovery/2026-10-27/nimh-bus-04'
save=lambda n,v:(B/n).write_text(json.dumps(v,indent=2)+'\n')
eq={r['signal']:r for r in map(json.loads,(B/'functional-equations.jsonl').open())}
raw={r['signal']:r for r in map(json.loads,(B/'physical-equations.jsonl').open())}
pred=json.loads((B/'address-all-predicates.json').read_text())
@lru_cache(None)
def support(n):
    n=n.lstrip('~')
    if n in ('0','1'):return frozenset()
    if n not in eq:
        if n in raw and raw[n]['op']=='alias':return support(raw[n]['args'][0])
        return frozenset([n])
    r=eq[n]
    return frozenset([n]) if r['op'] in ('ff','latch','gap','pad') else frozenset().union(*(support(x) for x in r['args']))
groups=defaultdict(list)
for r in pred:
    if r['role']!='enable':continue
    for c in r['cubes']:
        key=(c['mask'],c['value'],tuple(sorted(c['qualifiers'].items())))
        groups[key].append(r['cell'])
index=[]
for i,((mask,value,qualifiers),cells) in enumerate(sorted(groups.items())):
    index.append(dict(id=i,address_mask=hex(mask<<1),address_value=hex(value<<1),halfword_mask=mask,halfword_value=value,
      halfword_aliases=1<<(14-mask.bit_count()),qualifiers=dict(qualifiers),cells=sorted(set(cells))))
save('conditional-register-groups.json',index)
banks=[('AVB listener',0xc00,0xc80),('AVB talker',0x1200,0x1280),('RTC',0x4000,0x4080),('PTP RX',0x4080,0x4100),('PTP TX',0x4100,0x4180),('Ethernet SYS',0x4280,0x4300),('Ethernet MAC',0x4300,0x4380),('Router setup',0x5000,0x5100),('Audio clock',0x5100,0x5200),('InS',0x5600,0x5700),('HPLL',0x6000,0x6400)]
out=[]
for name,start,end in banks:
    selected=[]
    for g in index:
        offsets=[hex(x) for x in range(start,end,2) if ((x>>1)&g['halfword_mask'])==g['halfword_value']]
        if offsets:selected.append(dict(group=g['id'],compatible_offsets=offsets))
    cells=sorted({n for r in selected for n in index[r['group']]['cells']})
    unique=[r for r in selected if index[r['group']]['halfword_aliases']==1]
    out.append(dict(bank=name,base=hex(0x60000000+start),end_exclusive=hex(0x60000000+end),candidate_groups=selected,
      candidate_cells=cells,unique_address_groups=unique,bank_assignment_proven=False,
      scope='Exact physical candidate cells under recorded predicates. Aliases and sequential qualifier history are unresolved; no unique bank assignment claimed.'))
save('register-bank-cones.json',out)
targets={n for g in index for n in g['cells']}
consumers=defaultdict(list)
for n,r in eq.items():
    if r['op'] not in ('ff','latch'):continue
    for i,role in [(0,'data'),(2,'enable'),(3,'reset')]:
        for leaf in support(r['args'][i])&targets:consumers[leaf].append(dict(cell=n,role=role,signal=r['args'][i]))
ram=json.loads((B/'bram-storage-models.json').read_text())
for r in ram:
    for ab,p in r['ports'].items():
        for role in ['address_low_to_high','enable','reset','regce','write_data','write_parity','write_enable']:
            signals=p[role] if isinstance(p[role],list) else [p[role]]
            for bit,signal in enumerate(signals):
                for leaf in support(signal)&targets:consumers[leaf].append(dict(cell=r['cell'],port=ab,role=role,bit=bit,signal=signal))
save('register-datapath-consumers.json',dict(consumers))
def cone(n):
    seen=set();todo=[n]
    while todo:
        n=todo.pop().lstrip('~')
        if n in seen or n in ('0','1'):continue
        seen.add(n)
        if eq[n]['op'] not in ('ff','latch','gap','pad'):todo.extend(eq[n]['args'])
    return sorted(seen)
with (B/'conditional-cell-cones.jsonl').open('w') as f:
    for n in sorted(targets):
        r=eq[n]
        f.write(json.dumps(dict(cell=n,equation=r,data_cone=cone(r['args'][0]),enable_cone=cone(r['args'][2]),reset_cone=cone(r['args'][3]),
          data_boundaries=sorted(support(r['args'][0])),consumers=consumers[n]))+'\n')
summary=dict(conditional_enable_groups=len(index),conditional_target_cells=len(targets),immediate_consumer_edges=sum(map(len,consumers.values())),
   unique_full_address_enable_groups=sum(g['halfword_aliases']==1 for g in index),
   proven_named_bank_assignments=sum(r['bank_assignment_proven'] for r in out),
   banks=[dict(bank=r['bank'],candidate_groups=len(r['candidate_groups']),candidate_cells=len(r['candidate_cells']),unique_address_groups=len(r['unique_address_groups'])) for r in out],
   scope='Direct combinational fan-in and first sequential/BRAM consumer. Clock fanout excluded. Candidate sets overlap and must not be summed as utilization or bank coverage.')
save('register-map-coverage.json',summary);print(json.dumps(summary,indent=2))
