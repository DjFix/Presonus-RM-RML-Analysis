"""Configuration-derived functional equations, preserving unsupported boundaries.

No guessed module names, no timing model, and no hardware equivalence claim.
"""
from pathlib import Path
from collections import defaultdict, Counter, deque
import json, hashlib, re, sys, itertools

sys.setrecursionlimit(20000)
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
BASE=ROOT/'evidence/recovery/2026-10-27/nimh-fpga-connectivity-02'
OUT=ROOT/'evidence/recovery/2026-10-27/nimh-bus-04'
OUT.mkdir(parents=True,exist_ok=True)
def rows(p):
    with p.open() as f:
        for l in f: yield json.loads(l)
def save(n,v): (OUT/n).write_text(json.dumps(v,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((BASE/'evidence-manifest.json').read_text())['files']
for n in ['export/primitive-terminals.jsonl','input-pin-net-status.jsonl','dependencies/primitive-settings.jsonl','bonded-io-connectivity.json']:
    assert sha(BASE/n)==manifest[n]['sha256'],n

attrs=defaultdict(dict);classes={};pins=defaultdict(dict);outpins=defaultdict(list)
for r in rows(BASE/'dependencies/primitive-settings.jsonl'):
    if 'bel' in r and 'value' in r:attrs[r['tile'].split('.')[0]+'.'+r['bel']][r['attribute']]=r['value']
for r in rows(BASE/'export/primitives.jsonl'):classes[r['id']]=r['class']
def neg(x):return str(1-int(x)) if x in ('0','1') else x[1:] if x.startswith('~') else '~'+x
def bare(x):return x.lstrip('~')
for r in rows(BASE/'input-pin-net-status.jsonl'):
    s=r.get('abstract_source')
    if s:
        if s.startswith('constant:'):v='0' if s.endswith('Tie0') else '1'
        else:v=s[10:]
        mask=r['inversion_paths_mask']
        assert mask in (1,2)
        if (mask==2)^r['terminal_inversion']:v=neg(v)
    else:v='UNRESOLVED_NET_'+str(r['net'])
    pins[r['primitive']][r['pin']]=v
for r in rows(BASE/'export/primitive-terminals.jsonl'):
    if r['status']=='mapped' and r['direction']=='output':outpins[r['primitive']].append(r['pin'])
prev={r['dst_primitive']:r['src_primitive'] for r in rows(BASE/'export/dedicated-neighbors.jsonl') if r['kind']=='carry_neighbor_geometry'}
package=json.loads((BASE/'bonded-io-connectivity.json').read_text())
balls={r['iob']:r['ball'] for r in package}
eq={};built=set();lut_records=[];reg_records=[];boundaries=[]
def attr(p,a,d=None):
    v=attrs[p].get(a,d)
    return v[0] if isinstance(v,list) and len(v)==1 else v
def inp(p,k):return pins[p].get(k,p+'.UNDECLARED_'+k)
def put(n,op,args=(),**kw):eq[n]=dict(op=op,args=list(args),**kw);return n
def alias(n,x):return put(n,'alias',[x])
def mux(n,s,a,b):return put(n,'mux',[s,a,b]) # s ? b : a
def gap(n,reason,args=(),**kw):
    put(n,'gap',args,reason=reason,**kw);boundaries.append(n);return n
def ff(n,d,p,init,**kw):
    a=attrs[p]
    ce=inp(p,'CE') if a.get('FF_CE_ENABLE')=='1' else '1'
    sr=inp(p,'SR') if a.get('FF_SR_ENABLE')=='1' else '0'
    op='latch' if a.get('FF_LATCH')=='1' else 'ff'
    put(n,op,[d,inp(p,'CLK'),ce,sr],init=int(init or '0',16),sr_sync=a.get('FF_SR_SYNC')=='1',**kw)
    reg_records.append(dict(signal=n,primitive=p,**eq[n]))
def build_slice(p):
    a=attrs[p];sel={}
    for l in 'ABCD':
        mode=attr(p,l+'RAMMODE','NONE')
        init=int(attr(p,l+'6LUT'),16)
        o6=p+'.'+l+'_O6';o5=p+'.'+l+'_O5'
        inputs=[inp(p,l+str(i)) for i in range(1,7)]
        if mode=='NONE':
            put(o6,'lut',inputs,init=init,width=6,primitive=p,lane=l)
            put(o5,'lut',inputs[:5],init=init&0xffffffff,width=5,primitive=p,lane=l)
        else:
            # Preserve physical modes and controls; do not pretend a static LUT is SRL behavior.
            dep=inputs+[inp(p,k) for k in ['CLK','CE','WE','AX','BX','CX','DX','AI','BI','CI','DI'] if k in pins[p]]
            for n in [o6,o5]:gap(n,'SLICEM '+mode+' data/cascade mapping not behaviorally validated',dep,mode=mode,init=init,primitive=p,lane=l)
        lut_records.append(dict(primitive=p,lane=l,mode=mode,init_hex=f'{init:016x}',inputs=inputs,o6=o6,o5=o5))
        sel[l]={'O6':o6,'O5':o5,l+'X':inp(p,l+'X')}
        alias(p+'.'+l,o6)
    # UG384 F7A selects A/B with AX; F7B selects C/D with CX; F8 uses BX.
    gap(p+'.F7A','F7 physical input polarity not independently established',[inp(p,'AX'),p+'.A_O6',p+'.B_O6'])
    gap(p+'.F7B','F7 physical input polarity not independently established',[inp(p,'CX'),p+'.C_O6',p+'.D_O6'])
    gap(p+'.F8','F8 physical input polarity not independently established',[inp(p,'BX'),p+'.F7A',p+'.F7B'])
    if 'CYINIT' in a:
        if attr(p,'CYINIT')=='CIN':
            ci=prev.get(p)
            ci=ci+'.COUT' if ci else p+'.UNRESOLVED_CIN'
        else:
            choice=attr(p,'PRECYINIT');ci={'CONST_0':'0','CONST_1':'1','AX':inp(p,'AX')}[choice]
        for l in 'ABCD':
            s=p+'.'+l+'_O6';di=sel[l][attr(p,'MUX_'+l+'CY0')]
            co=mux(p+'.'+l+'_CY',s,di,ci)
            xo=put(p+'.'+l+'_XOR','xor',[s,ci])
            sel[l].update(CY=co,XOR=xo);ci=co
        alias(p+'.COUT',ci)
    sel['A']['F7']=p+'.F7A';sel['C']['F7']=p+'.F7B';sel['B']['F8']=p+'.F8'
    for l in 'ABCD':
        choice=attr(p,'MUX_FF'+l)
        d=sel[l].get(choice,p+'.UNSUPPORTED_FF_'+str(choice))
        ff(p+'.'+l+'Q',d,p,attr(p,'FF'+l+'_SRINIT'))
        ff(p+'.'+l+'5Q',p+'.'+l+'_O5',p,attr(p,'FF'+l+'5_SRINIT'))
        choice=attr(p,'MUX_'+l+'OUT')
        if choice=='NONE':gap(p+'.'+l+'MUX','disabled slice output selected as source')
        elif choice==l+'5Q':alias(p+'.'+l+'MUX',p+'.'+l+'5Q')
        else:alias(p+'.'+l+'MUX',sel[l].get(choice,p+'.UNSUPPORTED_MUX_'+str(choice)))

def build(p):
    if p in built:return
    built.add(p);cls=classes.get(p);a=attrs[p]
    if cls=='SLICE':build_slice(p);return
    if cls=='IOB':
        put(p+'.PAD','pad',[],ball=balls.get(p))
        alias(p+'.I',neg(p+'.PAD') if a.get('I_INV')=='1' else p+'.PAD')
        return
    if cls=='ILOGIC':
        cell,tail=p.rsplit('.',1);idx=int(re.search(r'\[(\d+)\]',tail)[1])
        iob=cell+f'.IOB[{idx}]'
        selection=attr(p,'MUX_D')
        if selection=='OTHER_IOB_I':iob=cell+f'.IOB[{idx^1}]'
        # Some instance variants omit the selector; the verifier's same-index D path is preserved.
        data=iob+'.I'
        alias(p+'.FABRICOUT',data)
        for pin in outpins[p]:
            if pin=='FABRICOUT':continue
            if pin=='Q4' and a.get('ENABLE')=='1' and a.get('DDR')=='0' and a.get('IOCE_ENABLE')=='0' and a.get('FFI_LATCH')=='0' and a.get('FFI_REV_ENABLE')=='0' and a.get('CASCADE_ENABLE')=='0' and all(a.get('ROW'+str(i)+'_CLK_ENABLE')=='0' for i in range(1,5)):
                op=p.replace('.ILOGIC[','.OLOGIC[')
                sr=inp(op,'SR') if attr(p,'MUX_SR')=='OLOGIC_SR' and attr(op,'MUX_SR')=='INT' else inp(p,'SR') if attr(p,'MUX_SR')=='INT' else '0'
                put(p+'.Q4','ff',[data,inp(p,'CLK'),inp(p,'CE0') if a.get('FFI_CE_ENABLE')=='1' else '1',sr if a.get('FFI_SR_ENABLE')=='1' else '0'],
                    init=int(a.get('FFI_INIT','0'),16),sr_value=int(a.get('FFI_SRVAL','0'),16),sr_sync=a.get('FFI_SR_SYNC')=='1',primitive=p,basis='Pinned IFFTYPE_FF/UG381 SDR input mode; Q4 is terminal IFF output')
            else:gap(p+'.'+pin,'ILOGIC sequential/DDR mapping',list(dict.fromkeys([data]+list(pins[p].values()))),primitive=p,settings=a)
        return
    if cls=='OLOGIC':
        for kind,dp,tp in [('O','D1','FFO'),('T','T1','FFT')]:
            out=p+'.'+('OQ' if kind=='O' else 'TQ')
            if attr(p,'MUX_'+kind)==dp:alias(out,inp(p,dp));continue
            if a.get(tp+'_RANK1_BYPASS')=='1' and a.get(tp+'_LATCH')=='0' and a.get('IOCE_ENABLE')=='0' and a.get(tp+'_REV_ENABLE')=='0' and a.get('CASCADE_ENABLE')=='0':
                sr=inp(p,'SR') if attr(p,'MUX_SR')=='INT' and a.get(tp+'_SR_ENABLE')=='1' else '0'
                ce=inp(p,'OCE' if kind=='O' else 'TCE') if a.get(tp+'_CE_ENABLE')=='1' else '1'
                put(out,'ff',[inp(p,dp),inp(p,'CLK'),ce,sr],init=int(a.get(tp+'_INIT','0'),16),sr_value=int(a.get(tp+'_SRVAL','0'),16),sr_sync=a.get(tp+'_SR_SYNC')=='1',primitive=p,basis='Pinned OUTFFTYPE_FF/TFFTYPE_FF and UG381 SDR output mode')
            elif a.get(tp+'_RANK1_BYPASS')=='0' and a.get(tp+'_RANK1_CLK_ENABLE')=='0' and a.get(tp+'_RANK2_CLK_ENABLE')=='0' and attr(p,'MUX_'+kind)==tp and a.get(tp+'_INIT')==a.get(tp+'_SRVAL'):
                alias(out,str(int(a.get(tp+'_INIT','0'),16)))
            else:gap(out,'OLOGIC DDR/serializer/register mapping',list(dict.fromkeys(pins[p].values())),primitive=p,settings=a)
        return
    if cls in ('BUFGMUX','BUFIO2','BUFIO2FB','IOI_DDR'):
        for pin in outpins[p]:gap(p+'.'+pin,'Clock buffer/DDR clock selection not yet modeled',list(dict.fromkeys(pins[p].values())),primitive=p,settings=a)
        return
    for pin in outpins[p]:gap(p+'.'+pin,(cls or 'unknown')+' primitive behavior boundary',list(dict.fromkeys(pins[p].values())),primitive=p,settings=a)

roots=[]
for r in package:
    if r['output_driver_configured']:
        for kind,suffix in [('data','OQ'),('tristate','TQ')]:
            name='PAD_'+r['ball']+('.O' if kind=='data' else '.T')
            alias(name,r['ologic']+'.'+suffix);roots.append(name)

todo=deque(roots);seen=set()
while todo:
    name=bare(todo.popleft())
    if name in ('0','1') or name in seen:continue
    seen.add(name)
    if name not in eq:
        if '.' in name:build(name.rsplit('.',1)[0])
        if name not in eq:gap(name,'No equation or declared source for this dependency')
    todo.extend(eq[name]['args'])

with (OUT/'physical-equations.jsonl').open('w') as f:
    for n in sorted(seen):f.write(json.dumps(dict(signal=n,**eq[n]))+'\n')

def value(x,env):return (env[bare(x)] ^ x.startswith('~')) if bare(x) not in ('0','1') else int(bare(x))^x.startswith('~')
def lut_reduce(init,args):
    unique=list(dict.fromkeys(bare(x) for x in args if bare(x) not in ('0','1')))
    table=0
    for mask in range(1<<len(unique)):
        env={x:(mask>>i)&1 for i,x in enumerate(unique)}
        idx=sum(value(x,env)<<i for i,x in enumerate(args))
        table|=((init>>idx)&1)<<mask
    for i in reversed(range(len(unique))):
        n=len(unique)
        if all(((table>>k)&1)==((table>>(k|(1<<i)))&1) for k in range(1<<n) if not(k&(1<<i))):
            bits=[(table>>k)&1 for k in range(1<<n) if not(k&(1<<i))]
            table=sum(b<<j for j,b in enumerate(bits));unique.pop(i)
    return table,unique

def resolve(x,trail=None):
    sign=x.startswith('~');n=bare(x);trail=set() if trail is None else trail
    while n in eq and eq[n]['op']=='alias' and n not in trail:
        trail.add(n);x=eq[n]['args'][0];sign^=x.startswith('~');n=bare(x)
    return neg(n) if sign else n

changes=0
for iteration in range(100):
    count=0
    for name in sorted(seen):
        e=eq[name];op=e['op'];args=[resolve(x) for x in e['args']]
        new=dict(e,args=args)
        if op=='lut':
            table,inputs=lut_reduce(e['init'],args)
            if not inputs:new=dict(op='alias',args=[str(table&1)])
            elif len(inputs)==1:new=dict(op='alias',args=[inputs[0] if table==2 else neg(inputs[0])])
            else:new.update(init=table,width=len(inputs),args=inputs)
        elif op=='mux':
            s,a,b=args
            if s in ('0','1'):new=dict(op='alias',args=[b if s=='1' else a])
            elif a==b:new=dict(op='alias',args=[a])
            elif a=='0' and b=='1':new=dict(op='alias',args=[s])
            elif a=='1' and b=='0':new=dict(op='alias',args=[neg(s)])
        elif op=='xor':
            a,b=args
            if a==b:new=dict(op='alias',args=['0'])
            elif a==neg(b):new=dict(op='alias',args=['1'])
            elif a in ('0','1'):new=dict(op='alias',args=[b if a=='0' else neg(b)])
            elif b in ('0','1'):new=dict(op='alias',args=[a if b=='0' else neg(a)])
        elif op in ('ff','latch'):
            d,clk,ce,sr=args
            init=str(e['init'])
            if sr=='1' or ce=='0' or d==init or d==name or (op=='ff' and clk in ('0','1')):
                if str(e.get('sr_value',e['init']))==init:new=dict(op='alias',args=[init])
        if new!=e:eq[name]=new;count+=1
    changes+=count
    if not count:break
else:raise RuntimeError('simplification failed to converge')

active=set();todo=deque(roots)
while todo:
    n=bare(todo.popleft())
    if n in ('0','1') or n in active:continue
    active.add(n)
    assert n in eq,n
    todo.extend(eq[n]['args'])
with (OUT/'functional-equations.jsonl').open('w') as f:
    for n in sorted(active):f.write(json.dumps(dict(signal=n,**eq[n]))+'\n')
save('lut-table-provenance.json',lut_records)
save('slice-register-provenance.json',reg_records)
save('functional-boundaries.json',[dict(signal=n,**eq[n]) for n in sorted(active) if eq[n]['op']=='gap'])

# Clock-domain and pad-cone inventories stop at sequential outputs for local data dependencies.
def cone(seed,stop_seq=True):
    q=[seed];seen2=set();pads=set();gaps=set();regs=set()
    while q:
        n=bare(q.pop())
        if n in ('0','1') or n in seen2:continue
        seen2.add(n);e=eq[n]
        if e['op']=='pad':pads.add(e.get('ball') or n)
        elif e['op']=='gap':gaps.add(n)
        elif e['op'] in ('ff','latch'):
            regs.add(n)
            if not stop_seq:q.extend(e['args'])
        else:q.extend(e['args'])
    return dict(equations=len(seen2),pads=sorted(pads),boundaries=sorted(gaps),registers=sorted(regs))
pad_cones=[dict(output=r,**cone(r)) for r in roots]
save('pad-cones.json',pad_cones)
domains=defaultdict(list)
for n in sorted(active):
    if eq[n]['op'] in ('ff','latch'):domains[eq[n]['args'][1]].append(n)
save('clock-domains.json',[dict(clock=k,registers=v,count=len(v),clock_cone=cone(k)) for k,v in sorted(domains.items(),key=lambda x:-len(x[1]))])
used_classes=Counter(classes.get(n.rsplit('.',1)[0],'synthetic') for n in active if n in boundaries)
coverage=dict(roots=len(roots),configured_output_pads=len(roots)//2,cone_equations=len(active),
    equation_ops=dict(Counter(eq[n]['op'] for n in active)),boundary_classes=dict(used_classes),
    reconstructed_slice_instances=len({n.rsplit('.',1)[0] for n in active if classes.get(n.rsplit('.',1)[0])=='SLICE'}),
    clock_domains=len(domains),simplification_iterations=iteration+1,
    scope='Configuration-derived equations in configured pad output/tristate cones. Gaps retain conservative dependencies. Counts are not functional equivalence or utilization.')
save('functional-coverage.json',coverage)

# A standalone partial Verilog module: every unsupported boundary is an explicit input.
names={n:'n'+str(i) for i,n in enumerate(sorted(active))}
def vref(x):
    if x in ('0','1'):return "1'b"+x
    return ('~' if x.startswith('~') else '')+names[bare(x)]
ports=[];body=[];exported=[]
for n in sorted(active):
    e=eq[n];v=names[n];op=e['op'];ar=[vref(x) for x in e['args']]
    body.append('// '+n)
    if op in ('gap','pad'):
        ports.append('input wire '+v);exported.append(dict(port=v,signal=n,kind=op))
    elif n in roots:ports.append('output wire '+v)
    elif op in ('ff','latch'):body.append('reg '+v+" = 1'b"+str(e['init'])+';')
    else:body.append('wire '+v+';')
    if op=='alias':body.append(f'assign {v} = {ar[0]};')
    elif op=='xor':body.append(f'assign {v} = {ar[0]} ^ {ar[1]};')
    elif op=='mux':body.append(f'assign {v} = {ar[0]} ? {ar[2]} : {ar[1]};')
    elif op=='lut':
        w=1<<e['width'];ix='{'+', '.join(reversed(ar))+'}'
        body.append(f"assign {v} = ({w}'h{e['init']:x} >> {ix}) & 1'b1;")
    elif op in ('ff','latch'):
        d,clk,ce,sr=ar
        init="1'b"+str(e.get('sr_value',e['init']))
        if op=='latch':body.append(f'always @* if ({sr}) {v} <= {init}; else if (!({clk}) && {ce}) {v} <= {d};')
        else:
            # Clock inversions already folded into the resolved expression.
            body.append(f'wire {v}_clk = {clk};')
            body.append(f'wire {v}_sr = {sr};')
            sens='posedge '+v+'_clk'
            if not e['sr_sync'] and e['args'][3]!='0':sens+=' or posedge '+v+'_sr'
            body.append(f'always @({sens}) if ({v}_sr) {v} <= {init}; else if ({ce}) {v} <= {d};')
(OUT/'functional-partial.v').write_text('// Partial physical logic; GAP ports are unresolved behavior.\nmodule nimh_partial(\n'+',\n'.join(ports)+'\n);\n'+'\n'.join(body)+'\nendmodule\n')
save('verilog-port-map.json',exported+[dict(port=names[r],signal=r,kind='output') for r in roots])
save('functional-input-pins.json',dict(pins))
print(json.dumps(coverage,indent=2))
