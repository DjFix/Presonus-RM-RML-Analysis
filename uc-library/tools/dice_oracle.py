#!/usr/bin/env python3
"""Generate codec fixtures by executing original ARM instructions in Unicorn."""
import argparse
import hashlib
import json
import random
import struct
from pathlib import Path
import unicorn
from unicorn import arm_const as arm


class Oracle:
    packet=0x10000000
    data=0x10001000
    midi=0x10002000
    length=0x10003000
    stack=0x20000000
    stop=0x30000000
    def __init__(self,repository):
        directory=repository/'uc-library/recovered-dice/server'
        manifest=json.loads((directory/'manifest.json').read_text())
        raw=(repository/manifest['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==manifest['sha256']
        self.u=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM)
        self.u.mem_map(0x103000,0x1000)
        self.u.mem_map(self.packet,0x10000)
        self.u.mem_map(self.stack,0x10000)
        self.u.mem_map(self.stop,0x1000)
        self.functions={}
        self.blocks=set()
        symbols=json.loads((directory/'symbols.json').read_text())
        for operation,prefix in [('encode','Presonus::UC::DicePacketQueue::toMIDI('),('decode','Presonus::UC::DicePacketQueue::fromMIDI(')]:
            sym=next(s for s in symbols if s['demangled'].startswith(prefix))
            code=(directory/sym['export_path']).read_bytes()
            assert raw[sym['file_offset']:sym['file_offset']+sym['size']]==code
            self.u.mem_write(sym['address'],code)
            self.functions[operation]=sym
        self.u.hook_add(unicorn.UC_HOOK_BLOCK,lambda uc,address,size,user:self.blocks.add(address))
        def memory_guard(uc,access,address,size,value,user):
            permitted=[(self.packet,20),(self.data,200),(self.midi,255),(self.length,1),(self.stack,0x10000)]
            if not any(start<=address and address+size<=start+count for start,count in permitted):
                raise AssertionError(f'original codec accessed outside declared buffers: {address:#x}+{size}')
        self.u.hook_add(unicorn.UC_HOOK_MEM_READ|unicorn.UC_HOOK_MEM_WRITE,memory_guard)
        self.manifest=manifest

    def call(self,operation,data,length,midi,output_length):
        u=self.u
        u.mem_write(self.packet,b'\0'*12+struct.pack('<Ii',self.data,length))
        u.mem_write(self.data,data)
        u.mem_write(self.midi,midi)
        u.mem_write(self.length,bytes([output_length]))
        for i in range(13): u.reg_write(getattr(arm,f'UC_ARM_REG_R{i}'),0)
        u.reg_write(arm.UC_ARM_REG_CPSR,0x10)
        u.reg_write(arm.UC_ARM_REG_SP,self.stack+0xff00)
        u.reg_write(arm.UC_ARM_REG_LR,self.stop)
        u.reg_write(arm.UC_ARM_REG_R0,self.packet)
        u.reg_write(arm.UC_ARM_REG_R1,self.midi)
        u.reg_write(arm.UC_ARM_REG_R2,self.length)
        u.emu_start(self.functions[operation]['address'],self.stop,count=20000)
        assert u.reg_read(arm.UC_ARM_REG_PC)==self.stop,'instruction limit reached'
        assert u.reg_read(arm.UC_ARM_REG_SP)==self.stack+0xff00,'stack not restored'
        returned=u.reg_read(arm.UC_ARM_REG_R0)
        assert returned in (0,1)
        return dict(success=returned,length=struct.unpack('<i',u.mem_read(self.packet+16,4))[0],
                    data=bytes(u.mem_read(self.data,200)),midi=bytes(u.mem_read(self.midi,255)),
                    midi_length=u.mem_read(self.length,1)[0])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('repository',type=Path)
    a=p.parse_args()
    root=a.repository/'uc-library/tests/vectors'
    root.mkdir(exist_ok=True)
    oracle=Oracle(a.repository)
    rng=random.Random(0x44494345)
    random_bytes=lambda n:bytes(rng.randrange(256) for _ in range(n))
    lines=[]
    counts={'encode':0,'decode':0}
    sizes=[-2147483648,-1,0]+list(range(1,221))+[255,256,1000,2147483647]
    patterns=[bytes(200),bytes([255])*200,bytes((i*37+13)&255 for i in range(200)),random_bytes(200)]
    for data in patterns:
        for length in sizes:
            midi=random_bytes(255)
            seed_length=rng.randrange(256)
            result=oracle.call('encode',data,length,midi,seed_length)
            counts['encode']+=1
            lines.append(f'E e{counts["encode"]} {length} {data.hex()} {midi.hex()} {seed_length} {result["success"]} {result["midi_length"]} {result["midi"].hex()}\n')
    def decode(midi):
        data=random_bytes(200)
        length=rng.randrange(-1000,1000)
        result=oracle.call('decode',data,length,midi,177)
        counts['decode']+=1
        lines.append(f'D d{counts["decode"]} {midi.hex()} {data.hex()} {length} {result["success"]} {result["length"]} {result["data"].hex()}\n')
    for padding in range(4):
        for terminator in list(range(3,255))+[None]:
            midi=bytearray(random_bytes(255))
            midi[:3]=bytes([0xf0,0x40,padding])
            for i in range(3,255):
                if midi[i]==0xf7:midi[i]=0xf6
            if terminator is not None:midi[terminator]=0xf7
            decode(bytes(midi))
    for prefix in [b'\0\x40\0',b'\xf0\0\0',b'\xf0\x40\4',b'\xf0\x40\xff']:
        decode(prefix+random_bytes(252))
    for i in range(256):
        midi=bytearray(random_bytes(255))
        if i%2==0:midi[:3]=bytes([0xf0,0x40,i%4])
        decode(bytes(midi))
    vectors=root/'dice-arm-vectors.txt'
    vectors.write_text(''.join(lines))
    report=dict(oracle='Unicorn original ARM instruction execution',unicorn_version=unicorn.__version__,
                original_elf_sha256=oracle.manifest['sha256'],functions=oracle.functions,
                cases=counts,vectors_sha256=hashlib.sha256(vectors.read_bytes()).hexdigest(),
                original_basic_blocks_exercised=[hex(x) for x in sorted(oracle.blocks)],
                domain='Disjoint valid Packet/data/MIDI buffers; 200 data bytes, 255 MIDI bytes, int32 logical lengths. No hardware.',
                cpp_differential_passed=False)
    (root/'dice-arm-oracle.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items() if key!='functions'},indent=2))


if __name__=='__main__':main()
