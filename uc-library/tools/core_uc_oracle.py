#!/usr/bin/env python3
"""Original ARM differential fixtures for BufferReader/Writer (libc contracts modeled)."""
import argparse
import collections
import hashlib
import json
import struct
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
from elftools.elf.elffile import ELFFile

METHODS=[
('_ZN8Presonus2UC12BufferReader7readRawEPvi','readRaw'),
('_ZN8Presonus2UC12BufferReader7readRawEPvii','readRawCapped'),
('_ZN8Presonus2UC12BufferReader11readCStringEPci','readCString'),
('_ZN8Presonus2UC12BufferReader4readItEEbRT_','readU16'),
('_ZN8Presonus2UC12BufferWriter8writeRawEPKvi','writeRaw'),
('_ZN8Presonus2UC12BufferWriter12writeCStringEPKc','writeCString'),
('_ZN8Presonus2UC12BufferWriter5writeItEEbT_','writeU16')]


class Oracle:
    obj=0x10000000
    data=0x10001000
    aux=0x10002000
    stack=0x20000000
    stop=0x30000000
    def __init__(self,repository,role):
        recovered=repository/'uc-library/recovered'/role
        self.manifest=json.loads((recovered/'manifest.json').read_text())
        path=repository/self.manifest['path']
        raw=path.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==self.manifest['sha256']
        symbols=json.loads((recovered/'all-symbols.json').read_text())
        by_name={s['mangled']:s for s in symbols}
        self.functions=[by_name[name] for name,_ in METHODS]
        self.u=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM)
        loads=[]
        with path.open('rb') as stream:
            elf=ELFFile(stream)
            segments=[s for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
            pages=set()
            for segment in segments:
                begin=int(segment['p_vaddr']);end=begin+int(segment['p_memsz'])
                loads.append((begin,end))
                pages.update(range(begin&~4095,(end+4095)&~4095,4096))
            for page in sorted(pages):self.u.mem_map(page,4096)
            for segment in segments:self.u.mem_write(int(segment['p_vaddr']),segment.data())
        self.loads=loads
        self.u.mem_map(self.obj,0x10000)
        self.u.mem_map(self.stack,0x10000)
        self.u.mem_map(self.stop,4096)
        self.helper_counts=collections.Counter()
        self.regions=[(self.obj,self.obj+12),(self.data,self.data+64),(self.aux,self.aux+64),(self.stack,self.stack+0x10000)]
        def allowed(address,size,write=False):
            regions=self.regions if write else self.regions+self.loads
            return any(a<=address and address+size<=b for a,b in regions)
        def guard(uc,access,address,size,value,user):
            assert allowed(address,size,access==unicorn.UC_MEM_WRITE),f'outside buffer domain {address:#x}+{size}'
        self.u.hook_add(unicorn.UC_HOOK_MEM_READ|unicorn.UC_HOOK_MEM_WRITE,guard)
        def memcpy(uc,address,size,user):
            destination=uc.reg_read(arm.UC_ARM_REG_R0)
            source=uc.reg_read(arm.UC_ARM_REG_R1)
            count=uc.reg_read(arm.UC_ARM_REG_R2)
            assert count<=64 and allowed(source,count) and allowed(destination,count,True), 'unsafe memcpy domain'
            assert count==0 or destination+count<=source or source+count<=destination,'memcpy overlap excluded'
            if count:uc.mem_write(destination,bytes(uc.mem_read(source,count)))
            uc.reg_write(arm.UC_ARM_REG_R0,destination)
            uc.reg_write(arm.UC_ARM_REG_PC,uc.reg_read(arm.UC_ARM_REG_LR))
            self.helper_counts['memcpy']+=1
        def strlen(uc,address,size,user):
            source=uc.reg_read(arm.UC_ARM_REG_R0)
            for count in range(64):
                assert allowed(source+count,1)
                if uc.mem_read(source+count,1)[0]==0:break
            else:raise AssertionError('strlen source lacks bounded NUL')
            uc.reg_write(arm.UC_ARM_REG_R0,count)
            uc.reg_write(arm.UC_ARM_REG_PC,uc.reg_read(arm.UC_ARM_REG_LR))
            self.helper_counts['strlen']+=1
        for name,callback in [('memcpy',memcpy),('strlen',strlen)]:
            symbol=next(s for s in symbols if s['address'] and s['mangled'].startswith(name+'@@'))
            self.u.hook_add(unicorn.UC_HOOK_CODE,callback,begin=symbol['address'],end=symbol['address'])

    def call(self,operation,capacity,offset,arg1,arg2,null,io,aux):
        u=self.u
        u.mem_write(self.obj,struct.pack('<IIi',self.data,self.data+offset,capacity))
        u.mem_write(self.data,io);u.mem_write(self.aux,aux)
        for i in range(13):u.reg_write(getattr(arm,f'UC_ARM_REG_R{i}'),0)
        u.reg_write(arm.UC_ARM_REG_CPSR,0x10)
        u.reg_write(arm.UC_ARM_REG_SP,self.stack+0xff00)
        u.reg_write(arm.UC_ARM_REG_LR,self.stop)
        u.reg_write(arm.UC_ARM_REG_R0,self.obj)
        u.reg_write(arm.UC_ARM_REG_R1,arg1 if operation==6 else (0 if null else self.aux))
        u.reg_write(arm.UC_ARM_REG_R2,arg1&0xffffffff)
        u.reg_write(arm.UC_ARM_REG_R3,arg2&0xffffffff)
        u.emu_start(self.functions[operation]['address'],self.stop,count=10000)
        assert u.reg_read(arm.UC_ARM_REG_PC)==self.stop,'instruction limit reached'
        assert u.reg_read(arm.UC_ARM_REG_SP)==self.stack+0xff00,'stack not restored'
        returned=u.reg_read(arm.UC_ARM_REG_R0)
        assert returned in (0,1),'nonboolean ARM result'
        base,cursor,size=struct.unpack('<IIi',u.mem_read(self.obj,12))
        assert base==self.data and size==capacity,'base/capacity unexpectedly modified'
        return returned,cursor-self.data,bytes(u.mem_read(self.data,64)),bytes(u.mem_read(self.aux,64))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('repository',type=Path)
    a=p.parse_args()
    target=a.repository/'uc-library/validation/core-uc'
    target.mkdir(parents=True,exist_ok=True)
    vectors=target/'arm-vectors.bin'
    patterns=[bytes(((i*29+j*17)%255)+1 for i in range(64)) for j in range(256)]
    counts=collections.Counter();failures=collections.Counter();partial=collections.Counter()
    records=0;metadata=[]
    with vectors.open('wb') as output:
        output.write(b'UCBFv001'+struct.pack('<I',0))
        for role_index,role in enumerate(('client','server')):
            oracle=Oracle(a.repository,role)
            def emit(op,capacity,offset,arg1=0,arg2=0,null=False,terminator=None):
                nonlocal records
                io=bytearray(patterns[records&255]);aux=bytearray(patterns[(records*37+11)&255])
                if op==2 and terminator is not None and offset+terminator<64:io[offset+terminator]=0
                if op==5:aux[arg1]=0
                before_io=bytes(io);before_aux=bytes(aux)
                returned,next_offset,after_io,after_aux=oracle.call(op,capacity,offset,arg1,arg2,null,before_io,before_aux)
                output.write(struct.pack('<BBBBiiiii',role_index,op,int(null),returned,capacity,offset,arg1,arg2,next_offset))
                output.write(before_io+before_aux+after_io+after_aux)
                key=role+':'+METHODS[op][1];counts[key]+=1
                if not returned:
                    failures[key]+=1
                    if next_offset!=offset or after_io!=before_io or after_aux!=before_aux:partial[key]+=1
                records+=1
                if records%10000==0:print(f'{records} original-ARM buffer fixtures generated',flush=True)
            capacities=(0,1,2,3,4,7,8,15,16,31,32,63,64)
            requests=(0,1,2,3,4,7,8,15,16,31,32,63,64,65)
            for capacity in capacities:
                for offset in range(capacity+1):
                    for request in requests:
                        emit(0,capacity,offset,request)
                        emit(4,capacity,offset,request)
                        for limit in sorted({0,1,max(0,request-1),request,request+1,64,65}):
                            emit(1,capacity,offset,request,limit)
                    emit(3,capacity,offset)
                    for value in (0,1,127,128,255,256,32767,32768,65534,65535):emit(6,capacity,offset,value)
                    for limit in (-2,-1,0,1,2,3,7,8,16,32,64,65):
                        for terminator in sorted({0,1,7,max(0,capacity-offset-1),capacity-offset}):
                            emit(2,capacity,offset,limit,terminator=terminator)
                        emit(2,capacity,offset,limit,terminator=None)
                    for length in (0,1,2,7,8,15,16,31,32,63):emit(5,capacity,offset,length)
                    emit(5,capacity,offset,0,null=True)
            metadata.append(dict(role=role,original_elf_sha256=oracle.manifest['sha256'],functions=oracle.functions,helper_calls=dict(oracle.helper_counts)))
            print(role,'complete',flush=True)
        output.seek(8);output.write(struct.pack('<I',records))
    report=dict(oracle='Original ARM routines executed with Unicorn',unicorn_version=unicorn.__version__,
                vector_format='UCBFv001; LE count; 280-byte records',records=records,cases=dict(counts),
                failure_cases=dict(failures),partial_mutation_failures=dict(partial),originals=metadata,
                vectors_sha256=hashlib.sha256(vectors.read_bytes()).hexdigest(),
                external_dependencies='memcpy and strlen modeled by their standard contracts; libc implementations are not recovered or verified',
                domain='Disjoint valid 64-byte IO and auxiliary allocations; capacities/cursors 0..64; raw counts and destination limits nonnegative <=65 without signed overflow; NUL-terminated writer strings <=63 bytes or null; CString reader limits include <=0. Original object layout, overlapping memcpy, unsafe negative raw lengths and concurrent mutation excluded.',
                declaration_uncertainties=['Non-template original C++ return spelling unencoded; portable bool matches observed 0/1 results.','Original constructors/ownership/layout not recovered.'])
    (target/'oracle.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('originals','cases','failure_cases')},indent=2),flush=True)


if __name__=='__main__':main()
