#!/usr/bin/env python3
"""Execute original ChannelComponent ARM targets; Core/app boundaries are stubs.

Only target functions and libgcc soft-float execute. Core implementation bodies
are never entered. powf is an explicit host-libm boundary and tested with a
bounded tolerance; no hardware or ARM object-layout compatibility is claimed.
"""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC

ELF = 'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
TARGETS = [0x3f3a0,0x3e488,0x3ee7c,0x3ef50,0x3e8c0,0x3e178,0x3e598,0x3e854,0x3e6b0,0x3e1f4]
OBJ=0x2000000; ENV=OBJ+0x1000; PAIR=OBJ+0x2000; GLOBAL=OBJ+0x3000; SOLOS=OBJ+0x4000; PARAM=OBJ+0x5000; VT=OBJ+0x10000; STOP=OBJ+0x20000; STACK=OBJ+0x30000
SLOTS=[0xe8,0xec,0xf0,0xf4,0xf8,0x10c,0x114,0x120,0x124,0x140]
NATIVE_HELPERS={0x1572ac,0x1572b0,0x157550,0x1576e8,0x1578e0,0x1578f8,0x157910,0x157928,0x157940}
libm=ctypes.CDLL('libm.so.6');libm.powf.argtypes=[ctypes.c_float,ctypes.c_float];libm.powf.restype=ctypes.c_float

def bits(f):return struct.unpack('<I',struct.pack('<f',f))[0]
def floating(v):return struct.unpack('<f',struct.pack('<I',v))[0]

def execute(words,segments,runtime_allowed):
    w=words; u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    for base,size,data in segments:u.mem_map(base,size);u.mem_write(base,data)
    u.mem_map(OBJ,0x50000)
    def put(a,v):u.mem_write(a,struct.pack('<I',v))
    def get(a):return struct.unpack('<I',u.mem_read(a,4))[0]
    def ptr(i):return PARAM+i*0x100 if w[1]&(1<<i) else 0
    trace=[];boundary=[];writes=[];pair_custom=False;linked=bool(w[34])
    for i,off in enumerate(SLOTS):put(OBJ+off,ptr(i))
    if not w[50]:put(OBJ+0x140,0)
    for i in range(14):put(PARAM+i*0x100,VT+0x1000);put(PARAM+i*0x100+4,w[2+i])
    # Each virtual slot has a unique explicit boundary trampoline.
    for slot,code in [(0x44,0),(0x58,1),(0x60,2),(0x74,3)]:put(VT+0x1000+slot,STOP+0x100+code*4)
    put(OBJ,VT);put(PAIR,VT)
    for slot,code in [(0x4c,4),(0x50,5),(0x54,6),(0x14,7)]:put(VT+slot,STOP+0x100+code*4)
    put(OBJ+0x174,ENV);put(ENV+0x2dc,GLOBAL if w[37] else 0);put(ENV+0x2d8,SOLOS if w[38] else 0)
    u.mem_write(ENV+0x364,bytes([bool(w[35]),bool(w[36])]))
    for i in range(3):put(OBJ+0x150+4*i,w[18+i])
    for i in range(2):put(OBJ+0x15c+4*i,w[21+i])
    put(OBJ+0x164,w[23]);put(OBJ+0x168,w[24]);put(OBJ+0x170,w[32]);u.mem_write(OBJ+0x8d,bytes([bool(w[33])]))
    for i in range(8):put(OBJ+0x178+4*i,w[40+i])
    put(0x493e58,w[31]);put(0x493e5c,ptr(10) if w[39] else 0)
    NAME=PARAM+0x2000;PNAME=PARAM+0x2200;DEFAULT=PARAM+0x2400
    for a in [NAME,PNAME]:put(a,VT+0x1000)
    u.mem_write(NAME+0x2c,b'custom\0' if w[48]==2 else b'default\0');u.mem_write(PNAME+0x2c,b'pair\0');u.mem_write(DEFAULT,b'default\0')
    put(OBJ+0x14c,NAME if w[48] else 0);put(PAIR+0x14c,PNAME if w[49]==2 else 0)
    def cstring(a):
        s=bytearray()
        while True:
            c=u.mem_read(a,1)[0];a+=1
            if not c:return bytes(s)
            s.append(c)
    def ret(value=None):
        if value is not None:u.reg_write(UC_ARM_REG_R0,value)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(uc,address,size,data):
        nonlocal pair_custom,linked
        r=[u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
        if address==STOP:u.emu_stop();return
        if STOP+0x100<=address<STOP+0x120:
            code=(address-STOP-0x100)//4
            if code in [0,1,2]:
                i=(r[0]-PARAM)//0x100
                boundary.append([address,*r[:3]])
                if code==0:
                    if i<9 or (i==9 and w[50]) or (i==10 and w[39]):trace.append(100+i)
                    ret(get(r[0]+4));return
                if code==1:trace.extend([300+i,r[1],r[2]]);put(r[0]+4,r[1]);ret();return
                trace.append(200+i);ret(w[16] if i==3 else w[17]);return
            if code==3:pair_custom=cstring(r[1])==b'custom';ret();return
            if code==4:trace.append(6 if r[1] else 5);ret();return
            if code==5:
                trace.append(7)
                if w[26]:put(OBJ+0x17c,int(w[26]==1))
                ret();return
            if code==6:trace.append(8);ret();return
            name=cstring(r[1]);i={b'comp':0,b'gate':1,b'eq':2}[name];trace.append(400+i);ret(ENV+0x800+i*0x100 if w[51]&(1<<i) else 0);return
        if address==0x823c0:trace.append(1);ret(int(linked));return
        if address==0x822a4:
            trace.append(2);linked=False
            if w[25]:u.mem_write(OBJ+0x8d,bytes([not bool(u.mem_read(OBJ+0x8d,1)[0])]))
            ret();return
        if address==0x2f610:trace.append(3);ret(PAIR if w[49] else 0);return
        if address==0x2fafc:trace.append(4);ret();return
        if address==0x119c4c:
            boundary.append([address,*r[:3]])
            i={45:10,48:11,47:12,46:13,12:9}[r[1]];ret(ptr(i));return
        if address==0x11add4:
            i=(r[0]-ENV-0x800)//0x100;trace.extend([500+i,r[1],r[2]]);ret();return
        if address==0x11c874:boundary.append([address,*r[:3]]);ret(DEFAULT);return
        if address==0xaf70:ret(int(cstring(r[0])!=cstring(r[1])));return
        if address==0xae5c:
            boundary.append([address,*r[:3]]);ret(bits(libm.powf(floating(r[0]),floating(r[1]))));return
        # Fail if execution escapes the target or the permitted non-Core runtime.
        if not any(a<=address<a+n for a,n in zip(TARGETS,[52,272,212,1104,120,92,280,108,420,660])) and not any(a<=address<a+n for a,n in runtime_allowed):
            raise RuntimeError(f'unexpected native execution {address:#x}')
    def write_hook(uc, access, address, size, value, data):
        if OBJ <= address < OBJ+0x20000 or address in [0x493e58,0x493e5c]:
            writes.append([address,size,value])
    u.hook_add(UC_HOOK_MEM_WRITE,write_hook)
    u.hook_add(UC_HOOK_CODE,hook)
    u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,w[27]);u.reg_write(UC_ARM_REG_SP,STACK+0xff00);u.reg_write(UC_ARM_REG_LR,STOP)
    u.emu_start(TARGETS[w[0]-1],STOP,count=200000)
    if u.reg_read(UC_ARM_REG_PC)!=STOP:raise RuntimeError('instruction budget exhausted')
    result=u.reg_read(UC_ARM_REG_R0) if w[0] in [2,10] else -1
    output=[result]+[get(OBJ+0x150+4*i) for i in range(3)]+[get(OBJ+0x15c+4*i) for i in range(2)]+[get(OBJ+0x164)]+[get(OBJ+0x178+4*i) for i in range(8)]+[int(get(0x493e5c)!=0),int(get(OBJ+0x140)!=0),get(ptr(1)+4) if ptr(1) else 0,get(ptr(5)+4) if ptr(5) else 0,int(pair_custom),u.mem_read(OBJ+0x8d,1)[0]]+trace
    return output,boundary,writes

def cases():
    def base(method):
        w=[0]*52;w[0]=method;w[1]=(1<<14)-1
        for i in range(14):w[2+i]=bits(1.)
        w[2]=bits(0.);w[3]=bits(.3);w[4]=bits(.8);w[5]=bits(-6.);w[16]=bits(.4);w[17]=bits(.6)
        for i,v in enumerate([.1,.2,.3,.4,.5,.6,.7]):w[18+i]=bits(v)
        w[27]=bits(.5);w[31]=bits(.5);w[33]=1;w[37]=w[38]=1;w[39]=w[50]=1
        for i in range(8):w[40+i]=i+1
        w[48]=w[49]=2;w[51]=7;return w
    out=[]
    def add(w):out.append({'id':f'channel-{len(out):04d}','input':w})
    for method in range(1,11):add(base(method))
    for mask in [0,1,2,3,0x80000000]:
        w=base(1)
        for i in range(8):w[40+i]=(mask+i)&0xffffffff
        add(w)
    for mode in [0.,-1.,1.,float('nan')]:
      for main in [0.,1.]:
       for mono in [0.,1.]:
        for cached in [0,1]:
         w=base(2);w[12]=bits(mode);w[9]=bits(main);w[10]=bits(mono);w[39]=cached;add(w)
    w=base(2);w[37]=0;w[39]=0;add(w)
    for missing in [7,8,10]:
      w=base(2);w[1]&=~(1<<missing);w[39]=0;add(w)
    for linked in [0,1]:
     for active in [0,1]:
      for side in [0,1,2,3]:
       for mutate in [0,1]:
        w=base(3);w[34]=linked;w[33]=active;w[32]=side;w[25]=mutate;add(w)
    for level in [-145.,-144.,-100.,-84.,-83.,-6.,0.,6.]:
     for pan in [0.,.25,.5,.75,1.]:
      for lcr in [0,1]:
       w=base(4);w[5]=bits(level);w[3]=bits(pan);w[12]=bits(float(lcr));add(w)
    for law in [0.,.5,1.]:
     for side in [0,1]:
      w=base(4);w[31]=bits(law);w[34]=1;w[32]=side;add(w)
    w=base(4);w[2]=bits(1.);add(w)
    for name in [0,1,2]:
     for pair in [0,1,2]:w=base(5);w[48]=name;w[49]=pair;add(w)
    for first in [0,1,0x80000000]:
     for second in [0,1]:
      for mutate in [0,1,2]:w=base(6);w[40]=first;w[41]=second;w[26]=mutate;add(w)
    for solo in [0.,1.,-1.,float('nan')]:
     for mode in [0.,1.]:
      for blocked in range(4):
       w=base(7);w[6]=bits(solo);w[11]=bits(mode);w[35]=blocked&1;w[36]=blocked>>1;add(w)
    for value in [0.,1.]:
      w=base(7);w[6]=bits(value);w[21]=w[22]=bits(value);add(w)
    w=base(7);w[50]=0;add(w)
    w=base(7);w[50]=0;w[1]&=~(1<<9);add(w)
    for position in [0.,.65,.75,.75000006,.8,1.,float('nan')]:
      w=base(8);w[8]=bits(position);w[24]=bits(.7);add(w)
    for position in [.05]:
      for delta in [-1,0,1]:
        w=base(8);w[8]=bits(position)+delta;w[24]=bits(0.);add(w)
    for enabled in range(8):
     for children in [0,7]:
      w=base(9);w[51]=children
      for i in range(3):w[13+i]=bits(float(bool(enabled&(1<<i))))
      add(w)
    for missing in [11,12,13]:w=base(9);w[1]&=~(1<<missing);add(w)
    for current in [0.,.4,1.]:
     for previous in [0.,.4,1.]:
      for delta in [-101.,-100.,-50.,-19.,-7.,-3.,-2.,-1.,-.9,0.,.9,1.,2.,3.,7.,19.,50.,100.,101.]:
       w=base(10);w[16]=bits(current);w[17]=bits(previous);w[27]=bits(current+delta/255.);add(w)
    for missing in [3,5,6]:w=base(10);w[1]&=~(1<<missing);add(w)
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args()
    raw=Path(ELF).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
    with Path(ELF).open('rb') as f:
        e=ELFFile(f);segments=[];ranges=[]
        symbols={symbol.name:symbol for symbol in e.get_section_by_name('.symtab').iter_symbols() if symbol.name}
        runtime_ranges=[]
        for symbol in symbols.values():
            if symbol['st_value'] in NATIVE_HELPERS and symbol['st_size']:
                section=e.get_section(symbol['st_shndx']);offset=section['sh_offset']+symbol['st_value']-section['sh_addr'];size=symbol['st_size']
                runtime_ranges.append({'mangled':symbol.name,'address':symbol['st_value'],'size':size,'section':section.name,'offset':offset,'sha256':hashlib.sha256(raw[offset:offset+size]).hexdigest()})
        for seg in e.iter_segments():
            if seg['p_type']!='PT_LOAD':continue
            start=seg['p_vaddr']&~4095;length=(seg['p_vaddr']+seg['p_memsz']-start+4095)&~4095
            segments.append((start,length,bytes(seg['p_vaddr']-start)+seg.data()))
        provenance=json.loads(Path('evidence/recovery/2026-11-02/dependency-graph/live-trial-07-10x10/channel-oracle-runtime-ranges.json').read_text())
        assert provenance['elf_sha256']==SHA
        for r in provenance['ranges']:
            symbol=symbols[r['mangled']];assert symbol['st_value']==r['address'] and symbol['st_size']==r['size'] and symbol['st_shndx']==r['section_index']
            assert hashlib.sha256(raw[r['file_offset']:r['file_offset']+r['size']]).hexdigest()==r['bytes_sha256']
            runtime_ranges.append({'mangled':r['mangled'],'address':r['address'],'size':r['size'],'section':r['section'],'offset':r['file_offset'],'sha256':r['bytes_sha256']})
        runtime_allowed=[(r['address'],r['size']) for r in runtime_ranges]
        for i in range(1,11):
            packet=Path(f'temp/recovery-work/graph-live-trial-07/trial07_channel_{i}-packet');c=json.loads((packet/'context.json').read_text());o=c['originals'][0]['original'];symbol=symbols[o['mangled']];assert symbol['st_value']==o['address'] and symbol['st_size']==o['size'] and symbol['st_shndx']==int(o['section_json']);s=e.get_section(int(o['section_json']));off=s['sh_offset']+o['address']-s['sh_addr'];b=raw[off:off+o['size']]
            n=json.loads((packet/'native-context.json').read_text());body=next(iter(n['bodies'].values()));expected=body['bytes_sha256'];assert hashlib.sha256(b).hexdigest()==expected;assert off==body['file_offset']
            ranges.append({'method':i,'mangled':o['mangled'],'address':o['address'],'size':o['size'],'section':s.name,'offset':off,'sha256':hashlib.sha256(b).hexdigest()})
    allcases=cases()
    for case in allcases:case['expected'],case['native_boundaries'],case['native_writes']=execute(case['input'],segments,runtime_allowed)
    # Build unchanged-coefficient cases from an independent first native run.
    for case in list(allcases):
        if case['input'][0] == 4:
            w=list(case['input']);w[18:21]=case['expected'][1:4]
            result,boundaries,writes=execute(w,segments,runtime_allowed)
            allcases.append({'id':f'channel-{len(allcases):04d}','input':w,'expected':result,'native_boundaries':boundaries,'native_writes':writes,'initial_state_origin':case['id']})
    Path(args.out).write_text(json.dumps({'version':1,'elf':ELF,'elf_sha256':SHA,'ranges':ranges,'runtime_ranges':runtime_ranges,'cases':allcases,'domain':'Synthetic mapped ARM32 object memory; target instructions and libgcc floats; Core/app/host powf boundary substitutions explicitly logged.'},indent=2)+'\n')
    print('native cases',len(allcases))
if __name__=='__main__':main()
