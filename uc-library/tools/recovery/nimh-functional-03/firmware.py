"""Thumb CFG and bounded straight-line constant-address analysis.

Pointer-seeded code is explicitly separate from reset reachability. No execution.
"""
from pathlib import Path
from collections import defaultdict, Counter, deque
import json, re, hashlib
from capstone import *
from capstone.arm import *

ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
OUT=ROOT/'evidence/recovery/2026-10-27/nimh-functional-03'
FW=ROOT/'evidence/recovery/2026-10-27/xmen-stm32/images/mixer-analysis/_ZL13nimh_arm_code.bin'
data=FW.read_bytes();BASE=0x08000000
CODE_END=BASE+0x24200 # Conservative boundary before the banner/string region.
md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_LITTLE_ENDIAN);md.detail=True
save=lambda n,v:(OUT/n).write_text(json.dumps(v,indent=2)+'\n')
def word(addr,size=4):
    off=addr-BASE
    return int.from_bytes(data[off:off+size],'little') if 0<=off<=len(data)-size else None
def valid(a):return BASE<=a<CODE_END and a%2==0
cache={}
def insn(a):
    if a not in cache:cache[a]=next(md.disasm(data[a-BASE:a-BASE+4],a,count=1),None)
    return cache[a]
def successors(i):
    mn=i.mnemonic.split('.')[0];end=i.address+i.size
    if mn in ('bx','bxj') or (mn.startswith('pop') and ARM_REG_PC in i.regs_access()[1]):return []
    if mn.startswith('ldr') and i.operands[0].type==ARM_OP_REG and i.operands[0].reg==ARM_REG_PC:return []
    if mn in ('tbb','tbh'):return []
    if mn in ('bl','blx'):
        return [end]+([i.operands[0].imm&~1] if i.operands[0].type==ARM_OP_IMM else [])
    if mn=='b' or (mn.startswith('b') and mn[1:] in ('eq','ne','cs','cc','hs','lo','mi','pl','vs','vc','hi','ls','ge','lt','gt','le')):
        targets=[i.operands[-1].imm&~1]
        return targets if mn=='b' else targets+[end]
    if mn in ('cbz','cbnz'):return [i.operands[-1].imm&~1,end]
    if mn.startswith('mov') and i.operands[0].type==ARM_OP_REG and i.operands[0].reg==ARM_REG_PC:return []
    return [end]
reset=int.from_bytes(data[4:8],'little')&~1
def walk(seeds):
    q=list(seeds);seen=set();bad=[]
    while q:
        a=q.pop()
        if a in seen or not valid(a):continue
        i=insn(a)
        if i is None:bad.append(hex(a));continue
        seen.add(a);q.extend(successors(i))
    return seen,bad
reset_code,reset_bad=walk([reset])
ptr_seeds=defaultdict(list)
for off in list(range(0,16,4))+list(range(0x24200,len(data)-3,4)):
    w=int.from_bytes(data[off:off+4],'little')
    if w&1 and valid(w&~1):ptr_seeds[w&~1].append(BASE+off)
code,bad=walk(set(ptr_seeds)|{reset})
incoming=defaultdict(set);calls=[];indirect=[]
for a in sorted(code):
    i=insn(a)
    for s in successors(i):incoming[s].add(a)
    if i.mnemonic in ('bl','blx'):
        if i.operands[0].type==ARM_OP_IMM:calls.append(dict(pc=hex(a),target=hex(i.operands[0].imm&~1)))
        else:indirect.append(hex(a))
entries={reset}|set(ptr_seeds)|{int(r['target'],16) for r in calls}
blocks={a for a in code if len(incoming[a])!=1 or a in entries}
for a in code:
    i=insn(a)
    ss=successors(i)
    if len(ss)!=1 or i.mnemonic in ('bl','blx'):
        blocks.update(s for s in ss if s in code)

refs=[];access=[];call_args=[]
def opval(o,regs,pc):
    if o.type==ARM_OP_IMM:return o.imm&0xffffffff
    if o.type==ARM_OP_REG:
        x=((pc+4)&~3) if o.reg==ARM_REG_PC else regs.get(o.reg)
        if x is not None and o.shift.type:
            if o.shift.type==ARM_SFT_LSL:x=(x<<o.shift.value)&0xffffffff
            elif o.shift.type==ARM_SFT_LSR:x>>=o.shift.value
            else:return None
        return x
    return None
for start in sorted(blocks):
    regs={};a=start;visited=set();it_left=0
    while a in code and a not in visited:
        visited.add(a);i=insn(a);ops=i.operands;mn=i.mnemonic
        before=dict(regs)
        for r in i.regs_access()[1]:regs.pop(r,None)
        base_mn=mn.split('.')[0]
        conditional=(i.cc not in (ARM_CC_AL,ARM_CC_INVALID)) or it_left>0
        if mn.startswith('it'):
            it_left=len(mn)-1
        elif it_left:it_left-=1
        dest=ops[0].reg if ops and ops[0].type==ARM_OP_REG else None
        if not conditional and base_mn in ('mov','movs','movw') and len(ops)>1:
            v=opval(ops[1],before,a)
            if v is not None:regs[dest]=v
        elif not conditional and base_mn=='movt' and dest in before:
            regs[dest]=(before[dest]&0xffff)|(ops[1].imm<<16)
        elif not conditional and base_mn in ('add','adds','sub','subs','orr','orrs','and','ands','bic','bics','lsl','lsls','lsr','lsrs'):
            ar=ops[1:] if len(ops)>2 else ops
            x,y=[opval(o,before,a) for o in ar[:2]]
            if x is not None and y is not None:
                if base_mn.startswith('add'):v=x+y
                elif base_mn.startswith('sub'):v=x-y
                elif base_mn.startswith('orr'):v=x|y
                elif base_mn.startswith('and'):v=x&y
                elif base_mn.startswith('bic'):v=x&~y
                elif base_mn.startswith('lsl'):v=x<<min(y,32)
                else:v=x>>min(y,32)
                regs[dest]=v&0xffffffff
        if mn.startswith(('ldr','str')) and len(ops)>1 and ops[1].type==ARM_OP_MEM:
            mem=ops[1].mem
            bv=((a+4)&~3) if mem.base==ARM_REG_PC else before.get(mem.base)
            ix=before.get(mem.index,0) if mem.index else 0
            if mem.index and ops[1].shift.type==ARM_SFT_LSL:ix=None if ix is None else ix<<ops[1].shift.value
            address=None if bv is None or ix is None else (bv+ix+mem.disp)&0xffffffff
            size=1 if mn.startswith(('ldrb','strb')) else 2 if mn.startswith(('ldrh','strh')) else 4
            if address is not None:
                if mn.startswith('ldr') and BASE<=address<BASE+len(data):
                    v=word(address,size)
                    refs.append(dict(pc=hex(a),address=hex(address),value=hex(v),reset_reachable=a in reset_code))
                    if not conditional:regs[dest]=v
                elif address>=0x40000000:
                    access.append(dict(pc=hex(a),instruction=mn+' '+i.op_str,address=hex(address),size=size,
                        direction='read' if mn.startswith('ldr') else 'write',
                        value=hex(before[dest]) if mn.startswith('str') and dest in before else None,
                        block=hex(start),reset_reachable=a in reset_code))
        if mn in ('bl','blx'):
            call_args.append(dict(pc=hex(a),target=hex(ops[0].imm&~1) if ops[0].type==ARM_OP_IMM else None,
                                  args={f'r{j}':hex(before[r]) for j,r in enumerate([ARM_REG_R0,ARM_REG_R1,ARM_REG_R2,ARM_REG_R3]) if r in before}))
            for r in [ARM_REG_R0,ARM_REG_R1,ARM_REG_R2,ARM_REG_R3,ARM_REG_R12,ARM_REG_LR]:regs.pop(r,None)
        ss=successors(i);end=a+i.size
        if end not in ss or len(ss)!=1 or end in blocks:break
        a=end

strings=json.loads((OUT/'stm32-strings.json').read_text())
def findstr(v):
    for s in strings:
        start=int(s['address'],16)
        if start<=v<start+len(s['text']):return s['text'][v-start:]
    return None
xrefs=[]
for r in refs:
    s=findstr(int(r['value'],16))
    if s:xrefs.append(dict(**r,text=s))
tables=[]
for s in strings:
    start=int(s['address'],16)
    for off in range(0x24200,len(data)-4,4):
        value=word(BASE+off)
        if start<=value<start+len(s['text']):
            nearby=[]
            for delta in range(-16,20,4):
                v=word(BASE+off+delta)
                if v is not None and v&1 and valid(v&~1):nearby.append(dict(delta=delta,target=hex(v&~1)))
            if nearby:tables.append(dict(pointer=hex(BASE+off),text=s['text'][value-start:],nearby_code_pointers=nearby))
save('stm32-cfg-summary.json',dict(image_sha256=hashlib.sha256(data).hexdigest(),base=hex(BASE),code_candidate_limit=hex(CODE_END),
    reset=hex(reset),reset_reachable_instructions=len(reset_code),pointer_seeded_instructions=len(code),
    pointer_seeds=len(ptr_seeds),call_edges=len(calls),unresolved_indirect_calls=len(indirect),
    known_address_accesses=len(access),external_accesses=sum(0x60000000<=int(r['address'],16)<0x70000000 for r in access),
    scope='Static reset and pointer-seeded CFG; conservative code limit, unresolved indirect branches/jump tables, no runtime observation; straight-line constants stop at joins and calls.'))
save('stm32-mmio-accesses.json',access);save('stm32-code-literal-refs.json',refs)
save('stm32-string-xrefs.json',xrefs);save('stm32-registration-candidates.json',tables)
save('stm32-call-arguments.json',call_args);save('stm32-call-edges.json',calls)
save('stm32-pointer-seeds.json',{hex(k):[hex(x) for x in v] for k,v in ptr_seeds.items()})
with (OUT/'stm32-cfg-disassembly.txt').open('w') as f:
    for a in sorted(code):
        i=insn(a);f.write(f'{a:08x}: {i.bytes.hex():8} {i.mnemonic:9} {i.op_str}\n')
print((OUT/'stm32-cfg-summary.json').read_text())
print('External 256-byte blocks:',dict(Counter(hex(int(r['address'],16)&~255) for r in access if 0x60000000<=int(r['address'],16)<0x70000000)))
