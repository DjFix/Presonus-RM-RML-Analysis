"""Recognize exact self-feedback binary increment recurrences, without role names."""
import json
from pathlib import Path
from functools import lru_cache
B=Path('/home/rs/projects/opencs/ai-line-analysis/evidence/recovery/2026-10-27/nimh-functional-03')
eq={r['signal']:r for r in (json.loads(l) for l in (B/'functional-equations.jsonl').open())}
regs={k:v for k,v in eq.items() if v['op']=='ff'}
def recurrence(n):
    d=regs[n]['args'][0]
    if d=='~'+n:return '1'
    if d.startswith('~'):return None
    e=eq.get(d,{})
    if e.get('op')=='xor':
        a,b=e['args']
        if a==n:return b
        if b==n:return a
    return None
@lru_cache(maxsize=None)
def carry_bits(n):
    if n=='1':return ()
    if n in regs:return (n,)
    if n.startswith('~'):return None
    e=eq.get(n,{})
    if e.get('op')=='mux':
        q,lo,hi=e['args']
        if q in regs and lo=='0':
            bits=carry_bits(hi)
            if bits is not None and q not in bits:return bits+(q,)
    return None
words=[]
for n in regs:
    c=recurrence(n)
    if c is None:continue
    bits=carry_bits(c)
    if bits is None or n in bits:continue
    bits=bits+(n,)
    if len(bits)<4:continue
    ok=True
    for i,q in enumerate(bits):
        ci=recurrence(q)
        if ci is None or carry_bits(ci)!=bits[:i]:ok=False;break
        if regs[q]['args'][1:]!=regs[n]['args'][1:] or regs[q]['sr_sync']!=regs[n]['sr_sync']:ok=False;break
    if ok:words.append(bits)
maximal=[w for w in words if not any(len(v)>len(w) and v[:len(w)]==w for v in words)]
records=[]
for bits in sorted(maximal,key=lambda x:(-len(x),x)):
    state=sum(regs[q]['init']<<i for i,q in enumerate(bits))
    records.append(dict(width=len(bits),bits_low_to_high=list(bits),clock=regs[bits[0]]['args'][1],
                        enable=regs[bits[0]]['args'][2],reset=regs[bits[0]]['args'][3],reset_value=state,
                        recurrence='Q_next = (Q + 1) mod 2**width when enabled; common reset has priority',
                        role='unassigned; a counter alone does not establish RTC, PTP or an audio timer'))
    for value in range(1<<len(bits)):
        result=0;carry=1
        for i in range(len(bits)):
            q=(value>>i)&1;result|=(q^carry)<<i;carry=q&carry
        assert result==(value+1)% (1<<len(bits))
(B/'binary-counters.json').write_text(json.dumps(records,indent=2)+'\n')
print('Exact increment recurrences:',len(records),'widths:',[r['width'] for r in records])
