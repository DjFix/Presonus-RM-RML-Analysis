#!/usr/bin/env python3
"""Execute the original ARM event codecs; only libc memcpy/strlen are modeled."""
import argparse
import collections
import hashlib
import json
import struct
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
from core_uc_oracle import Oracle as BufferOracle

METHODS = [
    ('_ZNK8Presonus2UC10EventClass5writeERNS0_12BufferWriterERKNS0_5EventE', 'headerWrite'),
    ('_ZNK8Presonus2UC10EventClass4readERNS0_5EventERNS0_12BufferReaderE', 'headerRead'),
    ('_ZNK8Presonus2UC20ParamValueEventClass5writeERNS0_12BufferWriterERKNS0_15ParamValueEventE', 'valueWrite'),
    ('_ZNK8Presonus2UC20ParamValueEventClass4readERNS0_15ParamValueEventERNS0_12BufferReaderE', 'valueRead'),
    ('_ZNK8Presonus2UC21ParamStringEventClass5writeERNS0_12BufferWriterERKNS0_16ParamStringEventE', 'stringWrite'),
    ('_ZNK8Presonus2UC21ParamStringEventClass4readERNS0_16ParamStringEventERNS0_12BufferReaderE', 'stringRead'),
]


class Oracle:
    obj = BufferOracle.obj
    data = BufferOracle.data
    event = BufferOracle.aux
    codec = BufferOracle.obj + 0x3000
    stack = BufferOracle.stack
    stop = BufferOracle.stop

def make_oracle(repository, role):
    # A fresh loader subclass captures every registered hook, avoiding private
    # Unicorn state and preserving the sealed buffer tool unchanged.
    original = unicorn.Uc.hook_add
    handles = []
    def capture(uc, *args, **kwargs):
        handle = original(uc, *args, **kwargs)
        handles.append(handle)
        return handle
    unicorn.Uc.hook_add = capture
    try:
        loader = BufferOracle(repository, role)
    finally:
        unicorn.Uc.hook_add = original
    obj = Oracle.__new__(Oracle)
    obj.u = loader.u
    obj.manifest = loader.manifest
    for handle in handles:
        obj.u.hook_del(handle)
    symbols = json.loads((repository/'uc-library/recovered'/role/'all-symbols.json').read_text())
    by_name = {s['mangled']: s for s in symbols}
    obj.functions = [by_name[name] for name, _ in METHODS]
    regions = [(obj.obj,obj.obj+12),(obj.data,obj.data+512),
               (obj.event,obj.event+512),(obj.codec,obj.codec+16),
               (obj.stack,obj.stack+0x10000)]
    def allowed(address, size, write=False):
        return any(a <= address and address+size <= b for a,b in (regions if write else regions+loader.loads))
    def guard(uc,access,address,size,value,user):
        assert allowed(address,size,access==unicorn.UC_MEM_WRITE), (hex(address),size)
    obj.u.hook_add(unicorn.UC_HOOK_MEM_READ|unicorn.UC_HOOK_MEM_WRITE,guard)
    obj.helpers = collections.Counter()
    def memcpy(uc,address,size,user):
        dst,src,n = [uc.reg_read(r) for r in (arm.UC_ARM_REG_R0,arm.UC_ARM_REG_R1,arm.UC_ARM_REG_R2)]
        assert n <= 512 and allowed(src,n) and allowed(dst,n,True)
        assert n == 0 or dst+n <= src or src+n <= dst
        if n: uc.mem_write(dst,bytes(uc.mem_read(src,n)))
        uc.reg_write(arm.UC_ARM_REG_R0,dst)
        uc.reg_write(arm.UC_ARM_REG_PC,uc.reg_read(arm.UC_ARM_REG_LR))
        obj.helpers['memcpy'] += 1
    def strlen(uc,address,size,user):
        src=uc.reg_read(arm.UC_ARM_REG_R0)
        for n in range(256):
            assert allowed(src+n,1)
            if uc.mem_read(src+n,1)[0]==0: break
        else: raise AssertionError('unterminated input to strlen')
        uc.reg_write(arm.UC_ARM_REG_R0,n)
        uc.reg_write(arm.UC_ARM_REG_PC,uc.reg_read(arm.UC_ARM_REG_LR))
        obj.helpers['strlen'] += 1
    for name,callback in [('memcpy',memcpy),('strlen',strlen)]:
        symbol=next(s for s in symbols if s['address'] and s['mangled'].startswith(name+'@@'))
        obj.u.hook_add(unicorn.UC_HOOK_CODE,callback,begin=symbol['address'],end=symbol['address'])
    return obj


def call(obj, op, capacity, offset, io, event):
    u=obj.u
    u.mem_write(obj.obj,struct.pack('<IIi',obj.data,obj.data+offset,capacity))
    u.mem_write(obj.data,io);u.mem_write(obj.event,event);u.mem_write(obj.codec,bytes(16))
    for i in range(13):u.reg_write(getattr(arm,f'UC_ARM_REG_R{i}'),0)
    u.reg_write(arm.UC_ARM_REG_CPSR,0x10)
    u.reg_write(arm.UC_ARM_REG_SP,obj.stack+0xff00)
    u.reg_write(arm.UC_ARM_REG_LR,obj.stop)
    u.reg_write(arm.UC_ARM_REG_R0,obj.codec)
    u.reg_write(arm.UC_ARM_REG_R1,obj.event if op%2 else obj.obj)
    u.reg_write(arm.UC_ARM_REG_R2,obj.obj if op%2 else obj.event)
    u.emu_start(obj.functions[op]['address'],obj.stop,count=100000)
    assert u.reg_read(arm.UC_ARM_REG_PC)==obj.stop
    assert u.reg_read(arm.UC_ARM_REG_SP)==obj.stack+0xff00
    result=u.reg_read(arm.UC_ARM_REG_R0)
    assert result in (0,1)
    base,cursor,size=struct.unpack('<IIi',u.mem_read(obj.obj,12))
    assert base==obj.data and size==capacity
    return result,cursor-obj.data,bytes(u.mem_read(obj.data,512)),bytes(u.mem_read(obj.event,512))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository',type=Path)
    args=parser.parse_args()
    target=args.repository/'uc-library/validation/uc-events'
    target.mkdir(parents=True,exist_ok=True)
    vectors=target/'arm-vectors.bin'
    assert not vectors.exists(), 'preserve existing oracle fixtures'
    records=0;counts=collections.Counter();failed=collections.Counter();partial=collections.Counter();originals=[]
    def pattern(seed):return bytes((i*29+seed*17)%255+1 for i in range(512))
    with vectors.open('wb') as output:
        output.write(b'UCEVv001'+struct.pack('<I',0))
        for role_index,role in enumerate(('client','server')):
            obj=make_oracle(args.repository,role)
            def emit(op,capacity,offset,io,event):
                nonlocal records
                result,next_offset,out_io,out_event=call(obj,op,capacity,offset,io,event)
                output.write(struct.pack('<BBBBiii',role_index,op,result,0,capacity,offset,next_offset))
                output.write(io+event+out_io+out_event)
                key=role+':'+METHODS[op][1];counts[key]+=1
                if not result:
                    failed[key]+=1
                    if next_offset!=offset or out_io!=io or out_event!=event:partial[key]+=1
                records+=1
            for offset in (0,1,7):
                for remaining in range(13):
                    for seed in range(12):
                        emit(0,offset+remaining,offset,pattern(seed),pattern(seed+1))
                        emit(1,offset+remaining,offset,pattern(seed),pattern(seed+1))
            bits=(0,1,0x80000000,0x7f800000,0xff800000,0x7fc12345,0x7f812345,0xffffffff)
            for op in (2,3,4,5):
                for path_length in (0,1,2,7,31,126,127):
                    for text_length in ((0,1,31,254,255) if op>=4 else (0,)):
                        for seed in range(8):
                            event=bytearray(pattern(seed+3));event[16+path_length]=0
                            event[144:146]=struct.pack('<H',(0,1,32767,32768,65534,65535,255,256)[seed])
                            if op<4:event[148:152]=struct.pack('<I',bits[seed])
                            else:event[146+text_length]=0
                            payload=bytes(event[16:17+path_length])+bytes(event[144:146])+ (bytes(event[148:152]) if op<4 else bytes(event[146:147+text_length]))
                            cuts=sorted({0,1,path_length,path_length+1,path_length+2,path_length+3,len(payload)-1,len(payload),len(payload)+1,512-7})
                            for offset in (0,7):
                                for remaining in cuts:
                                    io=bytearray(pattern(seed));io[offset:offset+len(payload)]=payload
                                    emit(op,offset+remaining,offset,bytes(io),bytes(event))
                if op%2:
                    # Reader path has no NUL in 128 bytes; text has none in 256.
                    for offset in (0,7):
                        for remaining in (0,1,127,128,129,255,256,511-offset):
                            emit(op,offset+remaining,offset,pattern(9),pattern(10))
                        if op==5:
                            for remaining in (3,4,257,258,259,260,511-offset):
                                io=bytearray(pattern(9));io[offset]=0
                                emit(op,offset+remaining,offset,bytes(io),pattern(10))
            originals.append(dict(role=role,elf_sha256=obj.manifest['sha256'],functions=obj.functions,helpers=dict(obj.helpers)))
            print(role,records,'ARM fixtures',flush=True)
        output.seek(8);output.write(struct.pack('<I',records))
    report=dict(records=records,cases=dict(counts),failure_cases=dict(failed),partial_mutation_failures=dict(partial),originals=originals,
                vectors_sha256=hashlib.sha256(vectors.read_bytes()).hexdigest(),unicorn_version=unicorn.__version__,
                domain='Disjoint valid 512-byte IO/event images, cursor<=capacity<=512, bounded writer path NUL<=127 and text NUL<=255; valid codec/buffer objects. Raw value bits include infinities, signed zero and NaNs. Reader cases include truncation and absent path/text NUL. No pointer wrap, invalid pointers, memcpy overlap, signed overflow or concurrent mutation.',
                dependencies='Original ARM buffer operations execute; only imported memcpy and strlen are modeled by standard contracts. Their libc implementations are excluded.',
                limitations=['Portable event storage and bool declarations; original inheritance, vtables, constructors, ARM ABI and non-template return spelling unproved.','EventClass reader expects tag already consumed by EventFactory; typed codecs process payload only. EventItem virtual dispatch remains pending.','Hardware testing deferred.'])
    (target/'oracle.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(records=records,partial_mutation_failures=dict(partial)),indent=2))

if __name__=='__main__':main()
