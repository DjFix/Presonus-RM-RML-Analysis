#!/usr/bin/env python3
"""Execute pure original DSP methods and original ARM soft-float helpers."""
import argparse
import collections
import hashlib
import json
import random
import struct
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
from elftools.elf.elffile import ELFFile

PREFIXES={
 'N':'Presonus::Dsp::BilinearInterpolator::normalizedToRange(',
 'R':'Presonus::Dsp::BilinearInterpolator::rangeToNormalized(',
 'M':'Presonus::Dsp::BilinearInterpolator::setMidPoint(',
 'S':'Presonus::Dsp::BilinearInterpolator::setRange(',
 'G':'Presonus::Dsp::ShelbyGEQController::denormalizeValue(',
 'E':'Presonus::Dsp::EQController::biquadFromBandType(',
}
def bits(value):return struct.unpack('<I',struct.pack('<f',value))[0]
def state(values):return struct.pack('<9f',*values)

class Oracle:
    obj=0x10000000
    stack=0x20000000
    stop=0x30000000
    def __init__(self,repository,role='server'):
        directory=repository/'uc-library/recovered-all'/role
        self.manifest=json.loads((directory/'manifest.json').read_text())
        binary=repository/self.manifest['path']
        raw=binary.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==self.manifest['sha256']
        self.u=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM)
        mapped=set()
        self.ranges=[]
        with binary.open('rb') as stream:
            elf=ELFFile(stream)
            for segment in elf.iter_segments():
                if segment['p_type']!='PT_LOAD':continue
                address=int(segment['p_vaddr']);count=int(segment['p_memsz'])
                for page in range(address&~4095,(address+count+4095)&~4095,4096):
                    if page not in mapped:self.u.mem_map(page,4096);mapped.add(page)
                self.u.mem_write(address,segment.data())
                self.ranges.append((address,address+count))
        self.u.mem_map(self.obj,4096)
        self.u.mem_map(self.stack,65536)
        self.u.mem_map(self.stop,4096)
        symbols=json.loads((directory/'symbols.json').read_text())
        self.functions={}
        for op,prefix in PREFIXES.items():
            matches=[s for s in symbols if s['kind']=='STT_FUNC' and s['demangled'].startswith(prefix)]
            if matches:self.functions[op]=matches[0]
        for item in self.functions.values():
            code=(directory/item['export_path']).read_bytes()
            assert raw[item['file_offset']:item['file_offset']+item['size']]==code
        self.blocks=set()
        self.u.hook_add(unicorn.UC_HOOK_BLOCK,lambda uc,address,size,user:self.blocks.add(address))
        def guard(uc,access,address,size,value,user):
            allowed=self.ranges+[(self.obj,self.obj+40),(self.stack,self.stack+65536)]
            assert any(start<=address and address+size<=end for start,end in allowed),f'out-of-domain original access {address:#x}+{size}'
        self.u.hook_add(unicorn.UC_HOOK_MEM_READ|unicorn.UC_HOOK_MEM_WRITE,guard)
    def call(self,operation,storage,args):
        u=self.u
        u.mem_write(self.obj,b'\0'*4+storage)
        for i in range(13):u.reg_write(getattr(arm,f'UC_ARM_REG_R{i}'),0)
        u.reg_write(arm.UC_ARM_REG_CPSR,0x10)
        u.reg_write(arm.UC_ARM_REG_SP,self.stack+0xff00)
        u.reg_write(arm.UC_ARM_REG_LR,self.stop)
        if operation=='E':u.reg_write(arm.UC_ARM_REG_R0,args[0])
        else:
            u.reg_write(arm.UC_ARM_REG_R0,self.obj)
            for i,value in enumerate(args,1):u.reg_write(getattr(arm,f'UC_ARM_REG_R{i}'),value)
        u.emu_start(self.functions[operation]['address'],self.stop,count=200000)
        assert u.reg_read(arm.UC_ARM_REG_PC)==self.stop,'instruction limit'
        assert u.reg_read(arm.UC_ARM_REG_SP)==self.stack+0xff00,'stack restoration'
        return u.reg_read(arm.UC_ARM_REG_R0),bytes(u.mem_read(self.obj+4,36))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('repository',type=Path)
    p.add_argument('--role',choices=['client','server'],default='server');a=p.parse_args()
    oracle=Oracle(a.repository,a.role);rng=random.Random(0x44535031)
    vectors=[];counts=collections.Counter()
    def emit(op,storage,args):
        args=list(args)+[0]*(3-len(args))
        returned,changed=oracle.call(op,storage,args)
        if op in ('M','S'):returned=0 # Setter R0 is incidental; return type unresolved.
        counts[op]+=1
        vectors.append(f'{op} {counts[op]} {storage.hex()} '+ ' '.join(f'{x:08x}' for x in args)+f' {returned:08x} {changed.hex()}\n')
        return changed
    edges=[0,0x80000000,bits(-2),bits(-1),bits(.1),bits(.5),bits(.9),bits(1),bits(2),0x00000001,0x80000001,0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,0x7fc12345,0xffc12345,0x7fa12345]
    initial=state([0,1,.5,123,.5,1,1,1,1])
    if 'G' in oracle.functions:
        for value in edges+[rng.getrandbits(32) for _ in range(1000)]:emit('G',initial,[value])
    if 'E' in oracle.functions:
        for index in range(4):emit('E',initial,[index])
    ranges=[(-1,1),(-60,12),(0,1),(1,1000),(0,0),(1,-1),(-1e20,1e20)]
    stored=[]
    for minimum,maximum in ranges:
        seed=state([minimum,maximum,0,123,.5,1,1,1,1])
        mids=[bits(minimum),bits(maximum),bits((minimum+maximum)/2),bits(minimum-1),bits(maximum+1),0x7f800000,0xff800000,0x7fc12345]
        for midpoint in mids:
            for normalized in edges:
                changed=emit('M',seed,[midpoint,normalized])
                stored.append(changed)
    for storage in stored:
        for value in edges[:10]+[0x7f800000,0xff800000,0x7fc12345]:
            emit('N',storage,[value]);emit('R',storage,[value])
    for normalized in edges:
        seed=state([0,1,.5,123,0,1,1,1,1])
        seed=seed[:16]+struct.pack('<I',normalized)+seed[20:]
        for minimum,maximum in ranges:
            for midpoint in [minimum,maximum,(minimum+maximum)/2,minimum-1,maximum+1]:
                emit('S',seed,[bits(minimum),bits(maximum),bits(midpoint)])
    out=a.repository/'uc-library/validation/mixer-dsp';out.mkdir(parents=True,exist_ok=True)
    if a.role=='client':out=out/'client';out.mkdir(exist_ok=True)
    path=out/'arm-vectors.txt';path.write_text(''.join(vectors))
    report=dict(role=a.role,original_elf_sha256=oracle.manifest['sha256'],functions=oracle.functions,
      oracle='Original ELF ARM code, including original soft-float helpers, in Unicorn',unicorn_version=unicorn.__version__,cases=dict(counts),
      vectors_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
      original_method_blocks={op:[hex(b) for b in sorted(oracle.blocks) if item['address']<=b<item['address']+item['size']] for op,item in oracle.functions.items()},
      signature_caveats={'M':'Setter return type unresolved; R0 ignored.','S':'Setter return type unresolved; R0 ignored.','E':'32-bit table-code result established; original return enum name unresolved.'},
      domain='Portable nine-float interpolation state; original ARM state at this+4..36, non-overlapping valid memory. Scalar-gain random bit patterns plus NaN/Inf/zero boundaries; adversarial configured-state cases and EQ indices 0..3 when present. Requires IEEE binary32 FE_TONEAREST and gradual underflow, no fast-math. Results/state only, not host floating exception flags. No object/vtable ABI or hardware claim.',
      cpp_differential_passed=False)
    (out/'arm-oracle.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items() if key!='functions'},indent=2),flush=True)

if __name__=='__main__':main()
