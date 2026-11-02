#!/usr/bin/env python3
"""Original ARM instruction observations; app/provider boundaries are explicit stubs.
Does not execute Core firmware implementations. Native field addresses are fixture
memory assumptions, not recovered class declarations. No reconstructed C++ imported.
"""
import argparse, hashlib, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
ELF_PATH='rootfs/CS18_v13840/home/root/surface'
ELF_HASH='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
BASE=0x500000; STACK=0x800000; STOP=0x410000
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]

def observe(index, cfg):
    data=Path(ELF_PATH).read_bytes(); assert hashlib.sha256(data).hexdigest()==ELF_HASH
    packet=Path(f'temp/recovery-work/graph-live-trial-07/trial07_mapping_{index}-packet')
    context=json.loads((packet/'native-context.json').read_text()); body=context['bodies'][context['roots'][0]]
    raw=data[body['file_offset']:body['file_offset']+body['size']]
    assert hashlib.sha256(raw).hexdigest()==body['bytes_sha256']
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000)
    with open(ELF_PATH,'rb') as f:
        elf=ELFFile(f)
        section=elf.get_section(body['section_index']); assert section.name==body['section'];assert body['file_offset']==body['address']-section['sh_addr']+section['sh_offset']
        for seg in elf.iter_segments():
            if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
    u.mem_map(0x400000,0x20000);u.mem_map(BASE,0x40000);u.mem_map(STACK,0x20000)
    def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
    def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
    def s(a):
        if not a:return '-'
        b=bytearray()
        while (x:=u.mem_read(a+len(b),1))!=b'\0':b+=x
        return b.decode()
    def put(a,x):u.mem_write(a,x.encode()+b'\0')
    trace=[]; executed=[]; params={}; vals={}; fns={}; timer=[dict(ex=bool(cfg.get('ex0',0)),long=bool(cfg.get('long0',0)),was=bool(cfg.get('was0',0))),dict(ex=bool(cfg.get('ex1',0)),long=bool(cfg.get('long1',0)),was=bool(cfg.get('was1',0)))]
    for ordinal,tag in enumerate(list(range(0,41))+list(range(10000,10040))):
        a=BASE+0x1000+ordinal*128;params[tag]=a; vals[a]=float(cfg.get('value',0))
        if tag in (8,9,10):vals[a]=float(bool(cfg.get('mods',0)&{9:1,10:2,8:4}[tag]))
        w(a,BASE+0x30000);w(a+12,BASE+0x31000+ordinal*8);w(BASE+0x31000+ordinal*8+4,tag)
    # Distinct methods in the original parameter vtable. New C++ uses current CCL API.
    for slot in (0x24,0x44,0x58,0x5c):w(BASE+0x30000+slot,0x400000+slot)
    for role,offset in ((1,0x88),(2,0x98),(3,0x9c)):
        a=BASE+0x800+role*16;vt=BASE+0x500+role*128;w(a,vt)
        w(BASE+offset,a if cfg.get('handlers',0)&(1<<(role-1)) else 0)
        for slot in (0x10,0x14,0x18,0x24,0x28,0x3c):
            fn=0x401000+role*256+slot;w(vt+slot,fn);fns[fn]=(role,slot)
    w(BASE+0x8c, r(BASE+0x98) if cfg.get('same',0) else 0)
    u.mem_write(BASE+0x140,bytes([cfg.get('blink',0)]))
    # Preinitialized singleton. Static initialization, allocator and exceptions excluded.
    w(2453136,1)
    put(BASE+0x32000,'fixture_control');put(BASE+0x32100,'fixture_color')
    target=body['address']; end=target+body['size']; branch_calls={}
    for e in context['edges']:
        if e['src']==context['roots'][0] and e['kind'] in ('ELF_CALLS','ELF_TAIL_BRANCH'):
            branch_calls[e['metadata']['target_address']]=True
    def tagof(p):return next((t for t,a in params.items() if a==p),-1)
    def emit(*v):trace.append(' '.join(str(x) for x in v))
    def hook(uc,pc,size,user):
        if pc==STOP:uc.emu_stop();return
        if target<=pc<end or (index==10 and 0x7fc68<=pc<0x7fd4c) or (index==6 and 0x801dc<=pc<0x80484):
            executed.append(pc);return
        if pc in fns:
            role,slot=fns[pc];emit('handler',role,slot,tagof(uc.reg_read(UC_ARM_REG_R1)) if slot==0x28 else '-')
        elif pc in (0x11acf0,0x11f24c):
            tag=uc.reg_read(UC_ARM_REG_R1);uc.reg_write(UC_ARM_REG_R0,params.get(tag,0) if cfg.get('present',1) else 0)
        elif pc==0x400044:uc.reg_write(UC_ARM_REG_R0,struct.unpack('<I',struct.pack('<f',vals[uc.reg_read(UC_ARM_REG_R0)]))[0])
        elif pc==0x400058:
            p=uc.reg_read(UC_ARM_REG_R0);v=struct.unpack('<f',struct.pack('<I',uc.reg_read(UC_ARM_REG_R1)))[0];vals[p]=v;emit('set',tagof(p),format(v,'.9g'),uc.reg_read(UC_ARM_REG_R2))
        elif pc==0x40005c:
            p=uc.reg_read(UC_ARM_REG_R0);vals[p]=0;emit('reset',tagof(p),uc.reg_read(UC_ARM_REG_R1))
        elif pc==0x400024:emit('enable',tagof(uc.reg_read(UC_ARM_REG_R0)),uc.reg_read(UC_ARM_REG_R1))
        elif pc==0x187780:
            a,b=[struct.unpack('<f',struct.pack('<I',uc.reg_read(reg)))[0] for reg in REGS[:2]];uc.reg_write(UC_ARM_REG_R0,int(a==b))
        elif pc==0x1877f8:
            v=struct.unpack('<f',struct.pack('<I',uc.reg_read(UC_ARM_REG_R0)))[0];uc.reg_write(UC_ARM_REG_R0,int(v)&0xffffffff)
        elif pc==0xb02c:uc.reg_write(UC_ARM_REG_R0,len(s(uc.reg_read(UC_ARM_REG_R0))))
        elif pc==0xaf84:
            a,b,n=[uc.reg_read(reg) for reg in REGS[:3]];put(a,s(a)+s(b)[:n])
        elif pc==0x4b47c:
            a,fmt,prefix,num=[uc.reg_read(reg) for reg in REGS];put(a,s(a)+(s(fmt)%(s(prefix),num)))
        elif pc==0x76d0c:
            a,name,p,unit=[uc.reg_read(reg) for reg in REGS];emit('connect',s(name),tagof(p),s(unit),r(uc.reg_read(UC_ARM_REG_SP)))
        elif pc==0x766b0:emit('color',s(uc.reg_read(UC_ARM_REG_R1)),s(uc.reg_read(UC_ARM_REG_R2)),uc.reg_read(UC_ARM_REG_R3))
        elif pc==0x769d8:emit('disconnect')
        elif pc==0x764fc:emit('blink',s(uc.reg_read(UC_ARM_REG_R1)),s(uc.reg_read(UC_ARM_REG_R2)))
        elif pc==0x7fc68:
            emit('control',uc.reg_read(UC_ARM_REG_R1),s(uc.reg_read(UC_ARM_REG_R2)),s(uc.reg_read(UC_ARM_REG_R3)))
        elif pc in (0x11a74c,0x11c87c):pass # pinned provider boundary, not firmware execution
        elif pc==0x5d414:uc.reg_write(UC_ARM_REG_R0,2453140)
        elif pc in (0x11a5c4,0xae58,0xad000):uc.reg_write(UC_ARM_REG_R0,BASE+0x900 if cfg.get('root',0) else 0)
        elif pc==0x7efb4:emit('verify',tagof(uc.reg_read(UC_ARM_REG_R1)))
        elif pc==0x80624:emit('daw',uc.reg_read(UC_ARM_REG_R1))
        elif pc==0x7f080:pass # null existing footswitch handlers, separately validated dependency
        elif pc==0x801dc:emit('footmode',uc.reg_read(UC_ARM_REG_R1))
        elif pc in (0x12020,0x12078,0x12110,0x121b0,0x12228,0x11ff8):
            k=1 if uc.reg_read(UC_ARM_REG_R0)==BASE+0x120 else 0;t=timer[k]
            if pc==0x12020:uc.reg_write(UC_ARM_REG_R0,int(t['was']))
            elif pc==0x12078:uc.reg_write(UC_ARM_REG_R0,int(t['ex']))
            elif pc==0x12110:uc.reg_write(UC_ARM_REG_R0,int(t['long']))
            elif pc==0x121b0:t['ex']=False
            elif pc==0x11ff8:t.update(ex=False,was=False)
            else:t['ex']=True;t['was']=False;t['long']=False
        else:raise RuntimeError(f'unmodelled boundary {pc:x} at target {index}')
        uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_SP,STACK+0x10000);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,BASE)
    if index==2:
        u.reg_write(UC_ARM_REG_R1,cfg.get('tag',1));u.reg_write(UC_ARM_REG_R2,BASE+0x32000);u.reg_write(UC_ARM_REG_R3,BASE+0x32100 if cfg.get('color',0) else 0)
    elif index==6:u.reg_write(UC_ARM_REG_R1,params[cfg['tag']]);u.reg_write(UC_ARM_REG_R2,cfg['msg'])
    elif index==8:u.reg_write(UC_ARM_REG_R1,cfg['mode']&0xffffffff)
    u.emu_start(target,STOP,count=100000)
    result={'trace':trace,'blink':u.mem_read(BASE+0x140,1)[0],'timers':[int(t['ex']) for t in timer]}
    result['parameter_bits']={str(t):struct.unpack('<I',struct.pack('<f',vals[a]))[0] for t,a in params.items()}
    result['native_executed_addresses']=sorted(set(executed))
    result['native_instruction_count']=len(executed)
    if index==9:result['return']=u.reg_read(UC_ARM_REG_R0)
    return result,{'address':target,'size':body['size'],'section':body['section'],'file_offset':body['file_offset'],'sha256':body['bytes_sha256']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args();cases=[];ranges={}
    for index in (1,4,5):
        for handlers in range(8):
            cfg={'handlers':handlers};o,r=observe(index,cfg);cases.append({'target':index,'input':cfg,'observation':o});ranges[index]=r
    for present in (0,1):
        for color in (0,1):
            cfg={'present':present,'color':color,'tag':1};o,r=observe(2,cfg);cases.append({'target':2,'input':cfg,'observation':o});ranges[2]=r
    for mode in (-1,0,1,2,3,4,7):
        for present in (0,1):
            cfg={'mode':mode,'present':present};o,r=observe(8,cfg);cases.append({'target':8,'input':cfg,'observation':o});ranges[8]=r
    for mods in range(8):
        cfg={'mods':mods};o,r=observe(9,cfg);cases.append({'target':9,'input':cfg,'observation':o});ranges[9]=r
    for index in (3,10):
        for present in (0,1):
            for root in ((0,1) if index==10 else (0,)):
                cfg={'present':present,'root':root};o,r=observe(index,cfg);cases.append({'target':index,'input':cfg,'observation':o});ranges[index]=r
    for msg in range(5):
        for tag in (0,7,8,9,10,11,12,13,32,33,34,37,38,39,40):
            for value in (0,1):
                cfg={'msg':msg,'tag':tag,'value':value,'handlers':6,'present':1,'was0':int(value==1),'ex1':int(value==1)}
                o,r=observe(6,cfg);cases.append({'target':6,'input':cfg,'observation':o});ranges[6]=r
    for bits in range(32):
        cfg={'ex0':bits&1,'long0':(bits>>1)&1,'ex1':(bits>>2)&1,'long1':(bits>>3)&1,'blink':(bits>>4)&1,'handlers':6,'present':1}
        o,r=observe(7,cfg);cases.append({'target':7,'input':cfg,'observation':o});ranges[7]=r
    Path(args.out).write_text(json.dumps({'elf':{'path':ELF_PATH,'sha256':ELF_HASH},'ranges':ranges,'cases':cases,'boundary_policy':__doc__},indent=2)+'\n');print(len(cases),'original ARM executions')
if __name__=='__main__':main()
