#!/usr/bin/env python3
"""Original ARM factory control flow with explicit registry/callback contracts."""
import argparse,collections,hashlib,json,struct
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
from core_uc_oracle import Oracle as Loader

METHODS=[('_ZN8Presonus2UC12EventFactory13hashEventTypeERKii','hash'),
('_ZN8Presonus2UC12EventFactory6createERKNS0_5EventE','clone'),
('_ZN8Presonus2UC12EventFactory10createTypeEi','createType'),
('_ZN8Presonus2UC12EventFactory5writeERNS0_12BufferWriterERKNS0_5EventE','writeBuffer'),
('_ZN8Presonus2UC12EventFactory5writeEPciRKNS0_5EventE','writeRaw'),
('_ZN8Presonus2UC12EventFactory4readERNS0_12BufferReaderE','readBuffer'),
('_ZN8Presonus2UC12EventFactory4readEPKci','readRaw')]

def signed(x):return x if x<0x80000000 else x-0x100000000
def remainder(x,n):return x%n if x>=0 else -((-x)%n)

class Oracle:
    def __init__(self,repository,role):
        original=unicorn.Uc.hook_add;handles=[]
        def capture(u,*args,**kwargs):
            h=original(u,*args,**kwargs);handles.append(h);return h
        unicorn.Uc.hook_add=capture
        try: loader=Loader(repository,role)
        finally:unicorn.Uc.hook_add=original
        self.u=loader.u;self.manifest=loader.manifest
        for h in handles:self.u.hook_del(h)
        self.base=loader.obj;self.buffer=self.base;self.io=loader.data;self.event=loader.aux
        self.factory=self.base+0x4000;self.codec=self.base+0x5000;self.vtables=self.base+0x6000
        self.item=self.base+0x8000;self.buckets=self.base+0x9000+140;self.entries=self.base+0xa000
        self.callbacks=self.base+0xf000;self.stack=loader.stack;self.stop=loader.stop
        symbols=json.loads((repository/'uc-library/recovered'/role/'all-symbols.json').read_text())
        byname={s['mangled']:s for s in symbols};self.functions=[byname[n] for n,_ in METHODS]
        self.trace=[];self.selected=0;self.hashcalls=0;self.activebuffer=self.buffer
        regions=[(self.base,self.base+0x10000),(self.stack,self.stack+0x10000)]
        def allowed(address,size,write=False):return any(a<=address and address+size<=b for a,b in (regions if write else regions+loader.loads))
        def guard(u,access,address,size,value,user):assert allowed(address,size,access==unicorn.UC_MEM_WRITE),(hex(address),size)
        self.u.hook_add(unicorn.UC_HOOK_MEM_READ|unicorn.UC_HOOK_MEM_WRITE,guard)
        def memcpy(u,address,size,user):
            dst,src,n=[u.reg_read(r) for r in (arm.UC_ARM_REG_R0,arm.UC_ARM_REG_R1,arm.UC_ARM_REG_R2)]
            assert n<=64 and allowed(src,n) and allowed(dst,n,True)
            assert n==0 or dst+n<=src or src+n<=dst
            if n:u.mem_write(dst,bytes(u.mem_read(src,n)))
            u.reg_write(arm.UC_ARM_REG_R0,dst);u.reg_write(arm.UC_ARM_REG_PC,u.reg_read(arm.UC_ARM_REG_LR))
        memcpy_symbol=next(s for s in symbols if s['address'] and s['mangled'].startswith('memcpy@@'))
        self.u.hook_add(unicorn.UC_HOOK_CODE,memcpy,begin=memcpy_symbol['address'],end=memcpy_symbol['address'])
        def hash_hook(u,address,size,user):self.hashcalls+=1
        self.u.hook_add(unicorn.UC_HOOK_CODE,hash_hook,begin=self.functions[0]['address'],end=self.functions[0]['address'])
        def buffer_hook(u,address,size,user):self.activebuffer=u.reg_read(arm.UC_ARM_REG_R1)
        for index in (3,5):self.u.hook_add(unicorn.UC_HOOK_CODE,buffer_hook,begin=self.functions[index]['address'],end=self.functions[index]['address'])
        def callback(u,address,size,user):
            slot=(address-self.callbacks)//4
            if slot==4:
                assert u.reg_read(arm.UC_ARM_REG_R0)==self.item
                self.trace.append(50+self.selected);result=0
            else:
                codec=(u.reg_read(arm.UC_ARM_REG_R0)-self.codec)//32
                assert codec in (0,1,2);self.selected=codec
                self.trace.append((10,20,30,40)[slot]+codec)
                if slot in (0,1):
                    if slot==1:assert u.reg_read(arm.UC_ARM_REG_R1)==self.event
                    result=0 if (self.allocnull if slot==0 else self.clonenull) else self.item
                else:
                    buffer=u.reg_read(arm.UC_ARM_REG_R1 if slot==2 else arm.UC_ARM_REG_R2)
                    item=u.reg_read(arm.UC_ARM_REG_R1) if slot==3 else self.item
                    assert slot==2 and u.reg_read(arm.UC_ARM_REG_R2)==self.event or slot==3 and item in (0,self.item)
                    base,cursor,capacity=struct.unpack('<IIi',u.mem_read(buffer,12));assert base==self.io
                    result=1
                    chunks=(bytes([0x41+codec,0x80]),bytes([0x51+codec,0,0xff]))
                    for chunk in chunks:
                        if cursor-base+len(chunk)>capacity:result=0;break
                        if slot==2:u.mem_write(cursor,chunk)
                        elif item:
                            marker=struct.unpack('<I',u.mem_read(item+4,4))[0]
                            marker^=int.from_bytes(u.mem_read(cursor,len(chunk)),'little')
                            u.mem_write(item+4,struct.pack('<I',marker))
                        cursor+=len(chunk);u.mem_write(buffer+4,struct.pack('<I',cursor))
                    result=int(bool(result and (self.writeflag if slot==2 else self.readflag)))
            u.reg_write(arm.UC_ARM_REG_R0,result);u.reg_write(arm.UC_ARM_REG_PC,u.reg_read(arm.UC_ARM_REG_LR))
        for slot in range(5):self.u.hook_add(unicorn.UC_HOOK_CODE,callback,begin=self.callbacks+4*slot,end=self.callbacks+4*slot)

    def call(self,op,capacity,offset,type_,scenario,writeflag,readflag,allocnull,clonenull,divisor):
        u=self.u;self.trace=[];self.hashcalls=0;self.activebuffer=self.buffer;self.selected=0
        self.writeflag=writeflag;self.readflag=readflag;self.allocnull=allocnull;self.clonenull=clonenull
        io=bytearray((i*29+17)&255 for i in range(64));io[0:2]=bytes([(type_>>8)&255,type_&255])
        if offset:io[offset:offset+2]=bytes([(type_>>8)&255,type_&255])
        event=bytearray((i*31+3)&255 for i in range(64));event[0:4]=struct.pack('<I',type_&0xffffffff)
        u.mem_write(self.io,bytes(io));u.mem_write(self.event,bytes(event))
        u.mem_write(self.buffer,struct.pack('<IIi',self.io,self.io+offset,capacity))
        codecaddr=lambda n:0 if n is None else self.codec+32*n
        for n in range(3):
            u.mem_write(self.codec+n*32,struct.pack('<I',self.vtables+n*32))
            u.mem_write(self.vtables+n*32,struct.pack('<IIIII',0,*[self.callbacks+i*4 for i in range(4)]))
        u.mem_write(self.item,struct.pack('<II',self.vtables+96,0xdeadbeef))
        u.mem_write(self.vtables+96,struct.pack('<II',0,self.callbacks+16))
        fallback=0 if scenario in (2,3,5,6) else None
        entries=[]
        if scenario in (1,6):entries=[(type_,1)]
        if scenario in (3,7):entries=[(type_,None)]
        collision=signed((type_&0xffffffff)^8)
        if scenario==4:entries=[(collision,2),(type_,1),(type_,2)]
        if scenario==5:entries=[(collision,2)]
        groups=collections.defaultdict(list)
        for key,codec in entries:groups[remainder(key,8)].append((key,codec))
        for bucket in range(-7,8):
            rows=groups[bucket];ptr=self.entries+(bucket+7)*64
            u.mem_write(self.buckets+bucket*20,struct.pack('<IIIII',0,ptr,len(rows),0,0))
            for index,(key,codec) in enumerate(rows):u.mem_write(ptr+8*index,struct.pack('<II',key&0xffffffff,codecaddr(codec)))
        u.mem_write(self.factory,struct.pack('<IIIIII',0,8,self.functions[0]['address'],self.buckets,0,codecaddr(fallback)))
        for i in range(13):u.reg_write(getattr(arm,f'UC_ARM_REG_R{i}'),0)
        u.reg_write(arm.UC_ARM_REG_CPSR,0x10);u.reg_write(arm.UC_ARM_REG_SP,self.stack+0xff00);u.reg_write(arm.UC_ARM_REG_LR,self.stop)
        args=[self.factory,0,0,0]
        if op==0:args=[self.event,divisor,0,0]
        elif op==1:args[1]=self.event
        elif op==2:args[1]=type_&0xffffffff
        elif op==3:args[1:3]=[self.buffer,self.event]
        elif op==4:args[1:4]=[self.io,capacity,self.event]
        elif op==5:args[1]=self.buffer
        elif op==6:args[1:3]=[self.io,capacity]
        for i,value in enumerate(args):u.reg_write(getattr(arm,f'UC_ARM_REG_R{i}'),value)
        u.emu_start(self.functions[op]['address'],self.stop,count=100000)
        assert u.reg_read(arm.UC_ARM_REG_PC)==self.stop
        assert u.reg_read(arm.UC_ARM_REG_SP)==self.stack+0xff00
        returned=u.reg_read(arm.UC_ARM_REG_R0)
        if op in (1,2,5,6):assert returned in (0,self.item);returned=int(bool(returned))
        else:returned=signed(returned)
        cursor=struct.unpack('<I',u.mem_read(self.activebuffer+4,4))[0]-self.io
        if op in (0,1,2):cursor=offset
        marker=struct.unpack('<I',u.mem_read(self.item+4,4))[0]
        assert self.hashcalls==1 and len(self.trace)<=8
        assert bytes(u.mem_read(self.event,64))==bytes(event)
        return returned,cursor,marker,bytes(io),bytes(u.mem_read(self.io,64)),list(self.trace)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('repository',type=Path);a=p.parse_args()
    target=a.repository/'uc-library/validation/uc-factory';target.mkdir(parents=True,exist_ok=True)
    vectors=target/'arm-vectors.bin';assert not vectors.exists(),'preserve previous fixtures'
    types=(0,1,17473,21837,20566,65535,-1,-8,-2147483648,2147483647)
    records=0;counts=collections.Counter();originals=[]
    with vectors.open('wb') as output:
        output.write(b'UCFAv001'+struct.pack('<I',0))
        for role_id,role in enumerate(('client','server')):
            oracle=Oracle(a.repository,role)
            def emit(op,capacity,offset,type_,scenario,flags=(1,1,0,0),divisor=8):
                nonlocal records
                result,cursor,marker,io,out,trace=oracle.call(op,capacity,offset,type_,scenario,*flags,divisor)
                meta=[role_id,op,capacity,offset,type_,scenario,*flags,divisor,result,cursor,len(trace),*trace]
                meta += [0]*(22-len(meta));meta += [signed(marker),1]
                assert len(meta)==24
                output.write(struct.pack('<24i',*meta)+io+out)
                counts[role+':'+METHODS[op][1]]+=1;records+=1
            for type_ in types:
                for divisor in (1,2,7,8,31):emit(0,0,0,type_,0,divisor=divisor)
                for scenario in range(8):
                    for op in (1,2):
                        for flags in ((1,1,0,0),(1,1,1,1)):emit(op,0,0,type_,scenario,flags)
                    for op in (3,4,5,6):
                        for capacity in (0,1,2,3,4,5,6,7,11):
                            for offset in (sorted({0,min(1,capacity),capacity}) if op in (3,5) else (0,)):
                                for flags in ((1,1,0,0),(0,0,0,0),(1,0,1,0),(0,1,1,1)):
                                    emit(op,capacity,offset,type_,scenario,flags)
            originals.append(dict(role=role,elf_sha256=oracle.manifest['sha256'],functions=oracle.functions))
            print(role,records,'ARM factory fixtures',flush=True)
        output.seek(8);output.write(struct.pack('<I',records))
    report=dict(records=records,cases=dict(counts),partial_mutation_failures={},originals=originals,
                vectors_sha256=hashlib.sha256(vectors.read_bytes()).hexdigest(),unicorn_version=unicorn.__version__,
                domain='Valid synthetic ARM factory/bucket/vtable structures with modulus8 and provisioned signed buckets -7..7; hash separately tests positive divisors1,2,7,8,31. Types0,1,17473,21837,20566,65535,-1,-8,INT_MIN,INT_MAX. Registration misses/collisions/duplicates/null keys/fallbacks; capacities0..11 and valid cursors; callback result/null-allocation combinations. Callback contracts explicitly tolerate null items. No invalid memory, divisionzero, signed overflow, concurrent mutation or hardware.',
                dependencies='Actual original ARM factory hash, signed division, lookup, wrappers and control flow execute. Synthetic registry/vtable layout is initialized directly. Allocation/clone/codec write/read/delete callbacks and imported memcpy are modeled contracts, not recovered Core containers, pooled allocators, registrations or virtual implementations. Callback read/write attempt atomic chunks2 then3, retaining earlier cursor/bytes on second-chunk failure; null-item callbacks perform no item memory access.',
                limitations=['Portable registry and EventItem bridge; original constructors, registrations, container/pool implementations, destructor variants, layout/ABI and non-template return spelling unproved.','Factory write intentionally ignores codec result; short read tag still looks up type0; matching null key suppresses fallback; failed read deletes only nonnull item.','Factory readiness is conditional on supplied valid registry/callback contracts; no claim original codec allocation-null handling is safe.','Hardware testing deferred.'])
    (target/'oracle.json').write_text(json.dumps(report,indent=2)+'\n')
    print(records,'ARM factory cases complete',flush=True)

if __name__=='__main__':main()
