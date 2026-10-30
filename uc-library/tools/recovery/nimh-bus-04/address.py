"""Recover address-counter order and nominal address decoder projections.

Projection through address-only FF stages retains their update/reset conditions;
it is an address attribution, not an assertion of cycle-independent equality.
"""
from pathlib import Path
from collections import Counter,defaultdict
from functools import lru_cache
from itertools import product,permutations
import json
from bdd import BDD
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
B=ROOT/'evidence/recovery/2026-10-27/nimh-bus-04'
OLD=ROOT/'evidence/recovery/2026-10-27/nimh-functional-03'
eq={r['signal']:r for r in (json.loads(l) for l in (B/'functional-equations.jsonl').open())}
aliases=json.loads((B/'state-aliases.json').read_text())
io=json.loads((OLD/'physical-interface-pins.json').read_text())
save=lambda n,v:(B/n).write_text(json.dumps(v,indent=2)+'\n')
@lru_cache(maxsize=None)
def support(n):
    n=n.lstrip('~')
    if n in ('0','1'):return frozenset()
    r=eq[n]
    if r['op'] in ('ff','latch','gap','pad'):return frozenset([n])
    return frozenset().union(*(support(x) for x in r['args']))
bdd=BDD(eq,aliases)
busclock='D0X18Y64.BUFGMUX[15].O'
address_inputs={r['ilogic']+'.Q4':r for r in io if not r['output_enabled'] and eq.get(r['ilogic']+'.Q4',{}).get('op')=='ff' and eq[r['ilogic']+'.Q4']['args'][1]==busclock}
capture=[]
for n,r in sorted(eq.items()):
    if r['op']!='ff' or r['args'][1]!='~'+busclock:continue
    s=support(r['args'][0]);pads=set(s)&set(address_inputs)
    if len(pads)==1:
        capture.append(dict(signal=n,input=next(iter(pads)),enable=r['args'][2],support=sorted(s)))
groups=defaultdict(list)
for r in capture:groups[r['enable']].append(r)
save('address-capture-groups.json',[dict(enable=k,members=v) for k,v in groups.items()])
def analyze_group(group):
    common=set.intersection(*(set(r['support']) for r in group))-set(address_inputs)-{r['signal'] for r in group}
    if len(common)>4:return None
    control=sorted(common);counter=None;load_mode=None
    for values in product([0,1],repeat=len(control)):
        assignment=dict(zip(control,values))
        funcs={r['signal']:bdd.restrict(bdd.build(eq[r['signal']]['args'][0]),assignment) for r in group}
        if all(f==bdd.var(next(r['input'] for r in group if r['signal']==n)) for n,f in funcs.items()):load_mode=assignment
        toggle=[n for n,f in funcs.items() if f==bdd.inv(bdd.var(n))]
        if len(toggle)!=1:continue
        ordered=[toggle[0]];carry=bdd.var(ordered[0])
        while True:
            matches=[n for n,f in funcs.items() if n not in ordered and f==bdd.ite(bdd.var(n),bdd.inv(carry),carry)]
            if len(matches)!=1:break
            n=matches[0];ordered.append(n);carry=bdd.ite(bdd.var(n),carry,0)
        if len(ordered)>=4:counter=dict(bits_low_to_high=ordered,mode=assignment)
    if counter is None or load_mode is None:return None
    return dict(counter=counter,load_mode=load_mode,group=group,
                ordered_inputs=[next(r['input'] for r in group if r['signal']==n) for n in counter['bits_low_to_high']])
models=[r for g in groups.values() if len(g)>=8 for r in [analyze_group(g)] if r]
save('address-counter-models.json',models)
anchor='D0X17Y107.SLICE[1].AQ'
primary=next(m for m in models if any(r['signal']==anchor for r in m['group']))
group=primary['group'];counter=primary['counter'];load_mode=primary['load_mode']
secondary=max(models,key=lambda m:len(m['ordered_inputs']))
physical_order=primary['ordered_inputs']
assert set(physical_order)==set(address_inputs),physical_order
assert secondary['ordered_inputs']==physical_order
print('Address counters:',[len(m['ordered_inputs']) for m in models],'full physical order:',[address_inputs[n]['ball'] for n in physical_order],flush=True)
input_for={r['signal']:r['input'] for r in group}
low_regs=counter['bits_low_to_high']
used_inputs={input_for[n] for n in low_regs}
high_inputs=[n for n in physical_order if n not in used_inputs]
capture_for_input={r['input']:r['signal'] for r in group}
addr_vars=low_regs+[capture_for_input[n] for n in high_inputs]
print('Proven full halfword-address counter bits:',len(counter['bits_low_to_high']),flush=True)
save('address-capture.json',dict(counter=counter,load_mode=load_mode,capture_group=group,
    low_bits=[dict(bit=i,capture=n,input=input_for[n],ball=address_inputs[input_for[n]]['ball']) for i,n in enumerate(low_regs)],
    high_variables=[dict(slot=i+len(low_regs),input=n,capture=capture_for_input[n],ball=address_inputs[n]['ball']) for i,n in enumerate(high_inputs)],
    physical_input_order=physical_order,source_counter_widths=[len(m['ordered_inputs']) for m in models],
    scope='Counter significance is proved by canonical next-state functions. High-bit ordering and CPU-byte address scaling are fitted separately.'))

# Find pure address combinational functions and their sequential replicas.
deps={n:frozenset([n]) for n in addr_vars};deps.update({'0':frozenset(),'1':frozenset()})
replacements={};stages={n:0 for n in addr_vars};projections=[]
# Both aperture capture chains have independently proved the same input order.
# Relate their nominal addresses while retaining separate load/enable conditions.
# This is conditional transaction attribution, never a live-state equivalence.
for model in models:
    for lane in model['group']:
        n=bdd.rep(lane['signal'])
        target=addr_vars[physical_order.index(lane['input'])]
        if n==target:continue
        replacements[n]=target;deps[n]=frozenset([target]);stages[n]=0
        r=eq[n]
        projections.append(dict(signal=n,data=target,clock=r['args'][1],enable=r['args'][2],reset=r['args'][3],stage=0,
          dependencies=[target],physical_input=lane['input'],load_mode=model['load_mode'],
          scope='Alternative aperture address capture: same physical lane, conditional on its own load event. Not simultaneous state equality.'))
for iteration in range(60):
    added=0
    for n,r in sorted(eq.items()):
        n=bdd.rep(n)
        if n in deps:continue
        r=eq[n];op=r['op']
        if op in ('gap','pad','latch'):continue
        args=r['args'][:1] if op=='ff' else r['args']
        names=[bdd.rep(x.lstrip('~')) if x.lstrip('~') not in ('0','1') else x.lstrip('~') for x in args]
        if not all(x in deps for x in names):continue
        d=frozenset().union(*(deps[x] for x in names))
        if op=='ff' and not d:continue
        deps[n]=d;stages[n]=max((stages.get(x,0) for x in names),default=0)+(op=='ff');added+=1
        if op=='ff':
            replacements[n]=r['args'][0]
            projections.append(dict(signal=n,data=r['args'][0],clock=r['args'][1],enable=r['args'][2],reset=r['args'][3],stage=stages[n],
              dependencies=sorted(d),scope='Address-only registered projection; valid after its decoded update condition, not an unconditional combinational equivalence.'))
    if not added:break
# Expand address-qualified predicate stages as well as pure address copies.
# Keep at most four independent qualifier variables, and reject self-feedback.
for qualified_round in range(8):
    probe=BDD(eq,aliases,replacements=dict(replacements),limit=1000000);new={}
    for n,r in sorted(eq.items()):
        n=probe.rep(n)
        if n in deps or n in replacements or eq[n]['op']!='ff':continue
        r=eq[n];s=support(r['args'][0])
        if len(s)>24:continue
        if not any(probe.rep(x) in deps and deps[probe.rep(x)] for x in s):continue
        try:
            root=probe.build(r['args'][0]);ss=probe.support(root);av=ss&set(addr_vars);other=ss-set(addr_vars)
            if not av or len(other)>4 or n in other:continue
        except OverflowError:continue
        new[n]=r['args'][0]
        projections.append(dict(signal=n,data=r['args'][0],clock=r['args'][1],enable=r['args'][2],reset=r['args'][3],
          qualified_round=qualified_round,address_dependencies=sorted(av),sampled_qualifier_dependencies=sorted(other),
          scope='Address-qualified sampled predicate. Valid after its decoded update condition; qualifier samples and FF latency are retained, not asserted cycle-independent.'))
        deps[n]=frozenset(av)
    replacements.update(new)
    print('Qualified address projection round',qualified_round,'added',len(new),flush=True)
    probe.ite.cache_clear()
    if not new:break
save('address-stage-projections.json',projections)
print('Address state projections:',len(projections),'pure passes',iteration+1,flush=True)
bdd=BDD(eq,aliases,replacements=replacements,limit=1000000)
variables=set(addr_vars)
pred=[];groups=defaultdict(list)
for n,r in sorted(eq.items()):
    if r['op']!='ff':continue
    for ix,role in [(2,'enable'),(3,'reset')]:
        s=r['args'][ix]
        if s in ('0','1'):continue
        # Address-related leaves in this control must exist before expansion.
        if not any(bdd.rep(x) in deps and deps[bdd.rep(x)] for x in support(s)):continue
        try:
            root=bdd.build(s);sup=bdd.support(root)
            if len(sup-variables)>4:continue
            cubes=bdd.cubes(root,limit=64)
        except OverflowError:continue
        masks=set();full=[]
        for cube in cubes:
            amask=aval=0;other={}
            for name,val in cube.items():
                if name in variables:
                    i=addr_vars.index(name);amask|=1<<i;aval|=val<<i
                else:other[name]=val
            full.append(dict(mask=amask,value=aval,controls=other))
            if amask.bit_count()>=10:masks.add((amask,aval))
        if not masks:continue
        rec=dict(register=n,role=role,signal=s,function=bdd.signature(root),cubes=full)
        pred.append(rec)
        for m,v in masks:groups[(m,v)].append(dict(register=n,role=role))
save('address-control-predicates.json',pred)
mask_rows=[dict(mask=m,value=v,targets=ns) for (m,v),ns in sorted(groups.items())]
save('address-decoder-groups.json',mask_rows)
print('Decoder groups:',len(mask_rows),'attributed register controls:',len(pred),flush=True)

writes=sorted({int(r['address'],16)&0xffff for r in json.loads((OLD/'stm32-mmio-accesses.json').read_text())
              if r['direction']=='write' and 0x60000000<=int(r['address'],16)<0x60008000})
scores=[]
for shift in [1,2]:
    for permutation in [tuple(range(len(high_inputs)))]:
        def encode(a):
            word=a>>shift;out=word&((1<<len(low_regs))-1)
            for j,slot in enumerate(permutation):out|=((word>>(len(low_regs)+j))&1)<<(len(low_regs)+slot)
            return out
        matched=[a for a in writes if any((encode(a)&r['mask'])==r['value'] for r in mask_rows)]
        scores.append(dict(shift=shift,high_permutation=permutation,matched=len(matched),total=len(writes),addresses=[hex(a) for a in matched]))
scores.sort(key=lambda x:(-x['matched'],x['shift'],x['high_permutation']))
save('address-fit-candidates.json',scores)
print('Best firmware-address fits:',scores[:5],flush=True)
