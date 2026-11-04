#!/usr/bin/env python3
"""Execute exact selected original ARM instructions. Core/libc/app seams are
explicit deterministic boundary models, never firmware Core execution.
Expected results are collected from emulation, not the proposal C++.
"""
import argparse, hashlib, json, math, struct, re
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
ELF = Path('rootfs/CS18_v13840/home/root/surface')
ELF_HASH = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
PACKETS = Path('temp/recovery-work/reconstruction-200-02/isolated-batch01/packets')
REGS = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]
OBJ, MIX, SLAVE, MAP, PARAM, OTHER = 0x1000000, 0x1002000, 0x1003000, 0x1004000, 0x1005000, 0x1006000
VT, PV, MV, CV, GV = 0x1010000, 0x1011000, 0x1012000, 0x1013000, 0x1014000
ARR, PARENT, GROUP = 0x1015000, 0x1016000, 0x1017000
SENTINEL = 0x1030000
HELPERS = [
 ('temp/recovery-work/reconstruction-200-02/expansions04-subassign-update01',0x96ef8,536,'f709266fb92b738ea87af862722810550a0d3f659896c38997a8a411997c934c'),
 ('temp/recovery-work/reconstruction-200-02/expansions05-groups-doselect01',0x924f4,608,'1bcf8d61fe508929f681c77cce784e7ea8235ca19199d7518cc4e6110c8e2a1a'),
 ('temp/recovery-work/reconstruction-200-02/expansions06-groups-filter01',0x92404,240,'b82d0929ed7ba059b4f624539e682bc6f93ac317924e7171d1ae76c9b41e910d'),
 ('temp/recovery-work/reconstruction-200-02/expansions07-groups-selection01',0x92140,140,'e92fd446ed97f9bf4a542068f7f9e24d5fc16bb1f3d8870cbb792b63288e705f'),
 ('temp/recovery-work/reconstruction-200-02/filter-visible-research01/packet',0x5c464,52,'6bc961cd78d5f24ad0f7fbf348834a1bb2a8b6aa9932b17fb3aeef0a77ff94f7'),
 ('temp/recovery-work/reconstruction-200-02/expansions11-channel-filter-ctor01',0x5c4d0,180,'0bb3b4134045969098f1f480941b5152f0b0c4fcff86962d24cc343a75e6fdd4')]

S = {'value':0x1020000, 'setvalue':0x1020004, 'channel':0x1020008,'slave':0x102000c,'group':0x1020010,'param':0x1020014,'mapping':0x1020018,'text':0x102001c,'cleanup':0x1020020,'find':0x1020024,'default':0x1020028,'root':0x102002c,'enable':0x1020030,'fromtext':0x1020034,'selected':0x1020038,'edit':0x102003c}
def bits(f): return struct.unpack('<I', struct.pack('<f', f))[0]
def f32(i): return struct.unpack('<f', struct.pack('<I', i))[0]
def signed(i): return i - 2**32 if i >= 2**31 else i
COUNTS = {1:2,3:2,4:3,5:4,6:6,7:5,8:4,9:5,11:6,12:2,14:6,15:3,16:6,17:3,19:4,23:4,24:2,25:4,27:3,28:4,29:5}
class Oracle:
    def __init__(self, requests, segments):
        self.requests, self.segments = requests, segments
    def run(self, ident, variant):
        u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        u.mem_map(0x8000, 0x400000)
        for address, data in self.segments: u.mem_write(address, data)
        u.mem_map(OBJ, 0x40000)
        def put(a, v): u.mem_write(a, struct.pack('<I', v & 0xffffffff))
        def get(a): return struct.unpack('<I',u.mem_read(a,4))[0]
        def string(a):
            b=bytearray()
            while True:
                c=bytes(u.mem_read(a,1));a+=1
                if c==b'\0':return b.decode('ascii')
                b.extend(c)
        def reg(n):return u.reg_read(REGS[n])
        trace, writes = [], []
        enabled = {}
        active_observers = set()
        result = {'refreshes':0,'selects':0,'queries':0,'deletes':0,'edits':0,'allocation_live':True}
        alias_bindings={}
        put(OBJ,VT);put(MIX,MV);put(MIX+0x30,GV);put(SLAVE,MV);put(MAP,CV);put(PARAM,PV);put(OTHER,PV);put(OTHER+0x200,PV)
        for o in [0xdc,0xf0,0x104,0x118]: put(OBJ+o,VT)
        put(VT,S['cleanup']);put(VT+0x18,S['find'])
        put(MV+0x1c,S['selected']);put(MV+0xc,S['root']);put(MV+0x20,S['channel']);put(MV+0x28,S['slave']);put(GV+0x14,S['group']);put(CV+0xc,S['mapping']);put(CV+0x10,S['mapping'])
        put(PV+0x1c,S['edit']);put(PV+0x40,S['default']);put(PV+0x44,S['value']);put(PV+0x58,S['setvalue']);put(PV+0x70,S['text']);put(PV+0x24,S['enable']);put(PV+0x74,S['fromtext'])
        values={PARAM:bits(0),OTHER:bits(1),OTHER+0x200:bits(1)}
        counts=[0,16,17,32,40,20];offsets=[0,0,0,4,20,2];requests=[-1,0,1,99,-30,2147483647]
        put(OBJ+0xd8,0xffffffff);put(OBJ+0xdc,ARR);put(OBJ+0xf4,ARR)
        if ident in [1,3]: put(OBJ+(0xcc if ident==1 else 0xd0),0)
        if ident in [6,11,14,16]: put(OBJ+0xe0,counts[variant]);put(OBJ+0xd4,offsets[variant])
        if ident==4:
            put(OBJ+0xcc,MIX if variant else 0)
            for j,c in enumerate([2,1,1]):
                cobj=GROUP+j*0x200;put(cobj+0x58,ARR+j*0x40);put(cobj+0x5c,c)
                for k in range(c):put(ARR+j*0x40+4*k,0x1019000+j*0x100+k*4)
        if ident==5:
            put(GROUP+0x50,PARENT if variant>=2 else 0)
            u.mem_write(PARENT+8,b'autofiltergroup\0' if variant==3 else b'filtergroup\0')
        if ident==7:
            put(PARAM+0x1800,PV);values[PARAM+0x1800]=0
            put(OBJ+0xd4,4);put(OBJ+0xe0,ARR);put(OBJ+0xe4,2)
            put(ARR,OTHER);put(ARR+4,PARAM)
            values[PARAM]=bits([0,1,-1,float('nan'),1][variant])
        if ident==8 and variant:
            put(OBJ+0x134,GROUP);put(OBJ+0xcc,MIX)
        if ident==9:
            put(GROUP,VT);put(PARAM+0xc,ARR);put(ARR+0x3c,2)
            values[PARAM]=bits([0,0,.5,.000001,float('nan')][variant])
        if ident in [12,19]:put(OBJ+0xcc,MIX if ident==12 or variant else 0)
        if ident==12:
            for j in range(2):
                container=GROUP+0x800+j*0x200
                put(container+0x58,ARR+j*0x40);put(container+0x5c,1)
                put(ARR+j*0x40,GROUP+j*0x400)
        if ident==14:
            put(PARAM+0xc,ARR);put(ARR+4,101 if variant%2 else 100)
            values[PARAM]=bits(0 if variant==0 else 1)
        if ident==17:put(OBJ+0xd0,MAP if variant else 0)
        if ident==19:
            put(OBJ+0xd8,4)
            if variant>=2:
                put(GROUP+0x800+0x58,ARR);put(GROUP+0x800+0x5c,2)
                put(ARR,GROUP);put(ARR+4,GROUP+0x400)
                put(OBJ+0x108,ARR+0x100);put(OBJ+0x11c,ARR+0x200)
        if ident==24 and variant:
            for i in range(16):
                p=0x1021000+i*0x200;put(p,PV);values[p]=0;enabled[p]=True
        if ident==23:
            put(OBJ+0xcc,MIX if variant>=2 else 0)
            put(OBJ+0xf8,2);put(ARR,PARAM);put(ARR+4,OTHER)
            active_observers.update([(PARAM,OBJ+4),(OTHER,OBJ+4)])
        if ident==24:put(OBJ+0xd4,3);put(OBJ+0xd8,4)
        if ident==25:
            put(OBJ+0xcc,MIX);put(OBJ+0xd4,0xffffffff if variant==3 else variant)
            put(GROUP+0x58,ARR);put(GROUP+0x5c,2)
            put(ARR,GROUP+0x1000);put(ARR+4,GROUP+0x1200)
            put(GROUP+0x400+0x58,ARR+0x40);put(GROUP+0x400+0x5c,1);put(ARR+0x40,GROUP+0x1400)
        if ident==27:
            put(OBJ+0xcc,MIX);put(OBJ+0xd0,MAP);put(OBJ+0xd8,0xffffffff if variant==0 else 0)
            put(OBJ+0x108,ARR);put(OBJ+0x10c,1);put(ARR,GROUP)
            put(GROUP+0x50,PARENT);u.mem_write(PARENT+8,b'autofiltergroup\0' if variant==2 else b'filtergroup\0')
            for off,value in [(0x1800,0),(0x1900,0),(0x4000,bits(1 if variant==1 else 0)),(0x4200,bits(1 if variant==2 else 0)),(0x4a00,bits(1)),(0x4b00,bits(-1))]:
                put(PARAM+off,PV);values[PARAM+off]=value
            put(OBJ+0x13c,ARR+0x500);put(OBJ+0x140,39)
            put(OBJ+0x150,ARR+0x600);put(OBJ+0x154,32)
        if ident==28:
            put(OBJ+4,ARR);put(OBJ+8,2);u.mem_write(ARR,bytes([0,1]))
        if ident==29:u.mem_write(ARR,bytes([0x55])*50)
        allowed=[(r['address'],r['address']+r['size']) for r in self.requests.values()]+[(a,a+n) for _,a,n,_ in HELPERS]
        def callback(uc, address, size, user):
            if address==SENTINEL:uc.emu_stop();return
            if any(lo<=address<hi for lo,hi in allowed):return
            args=[reg(n) for n in range(4)];a,b,c,d=args
            trace.append({'address':address,'args':args})
            ret=0
            if address==S['value']:ret=values[a]
            elif address==S['default']:ret=0
            elif address==S['setvalue']:
                values[a]=b
                result['edits']+=int(c!=0)
            elif address==S['mapping']:
                ret=PARAM if ident==17 and variant==2 else 0
                if ident==27:ret=PARAM+0x4000 if b==0 else PARAM+0x4200 if b==6 else 0
            elif address==S['edit']:result['edits']+=1
            elif address==S['channel']:
                ret=GROUP+0x200 if a==SLAVE else GROUP+(0x400 if b==2 else 0)
                if ident==25:ret=GROUP if b==0 else GROUP+0x400 if b==4 else 0
            elif address==S['selected']:ret=GROUP+0x1400
            elif address==S['slave']:ret=SLAVE if (ident==4 and variant==2) or (ident==8 and variant>=2) else 0
            elif address==S['root']:ret=0 if variant==3 else GROUP
            elif address==S['enable']:enabled[a]=bool(b)
            elif address==S['fromtext']:pass
            elif address==S['group']:
                result['queries']+=1
                ret=GROUP+0x800 if ident==19 and variant>=2 and string(b)=='filtergroup' else 0
                if ident==12:ret=GROUP+0x800+(0 if string(b)=='filtergroup' else 0x200)
            elif address==S['find']:
                if ident==25:
                    name=string(b)
                    names=['assign_slot_01','assign_slot_name_01','assign_slot_02','assign_slot_name_02']
                    if name in names:ret=PARAM+0x2000+names.index(name)*0x100
            elif address==S['text']:u.mem_write(b,b'named\0' if (ident==9 and variant==0) or (ident==19 and a==PARAM) else b'\0')
            elif address==S['cleanup']:pass
            elif address==0x5c9a4:
                capacity=((b+4)//5)*5 if b else 0
                put(a+4,ARR if capacity else 0);put(a+0xc,capacity);ret=1
            elif address==0x8bee4:
                put(a+0xc,b)
                if get(a+8)>b:put(a+8,b)
                ret=1
            elif address in [0x8c04c,0x94c80]:
                # MutableVector::add is passed the ConstVector subobject.
                n=get(a+4);put(get(a)+4*n,get(b));put(a+4,n+1);ret=1
            elif address in [0x5d36c,0x11b5e0,0x8c01c,0x5cad4,0x613bc]:pass
            elif address==0xad5c:
                if a!=OBJ or not result['allocation_live']:raise RuntimeError('invalid original delete request')
                uc.mem_unmap(OBJ,0x1000)
                result['allocation_live']=False;result['deletes']+=1
            
            
            elif address==0x681d4:ret=int((ident==24 and variant!=0) or ident==25)
            elif address==0x11acf0:
                ret=PARAM
                if ident==15:ret=PARAM if b==646 else OTHER if b==685 else 0
                if ident==19:ret=PARAM if a==GROUP else OTHER
                if ident==7:ret=PARAM+0x1800 if a==OBJ and b==1008 else 0
                if ident==27:
                    ret=PARAM+0x1800 if a==OBJ and b==1008 else PARAM+0x1900 if a==OBJ and b==1009 else PARAM+0x4a00 if a==GROUP and b==646 else PARAM+0x4b00 if a==GROUP and b==647 else 0
                if ident==25:ret=a+0x100 if b==256 else a+0x104 if b==1 else 0
                if ident==12:ret=PARAM+(0 if a==GROUP else 0x400)+(0 if b==603 else 0x100)
            elif address==0x24268:u.mem_write(a,(string(b).encode('ascii') if b else b'')+b'\0');ret=a
            elif address==0xb02c:ret=len(string(a))
            elif address==0xb0f8:ret=0 if string(a)==string(b) else 1
            elif address==0x11a6c8:ret=0 if ident==19 else 1
            elif address==0x11a6dc:ret=PARAM
            elif address==0x1877e0:ret=int(f32(a)>f32(b))
            elif address==0x187780:ret=int(f32(a)==f32(b))
            elif address==0x187798:ret=int(f32(a)<f32(b))
            elif address==0x18714c:ret=bits(f32(a)-f32(b))
            elif address==0x11f4f0:active_observers.add((a,b))
            elif address==0x11e2e0:active_observers.discard((a,b))
            elif address==0x11ca80:u.mem_write(b,b'x\0')
            elif address==0x4b47c:u.mem_write(a,(string(a)+(string(b)%c)).encode('ascii')+b'\0');ret=a
            elif address==0xae58:ret=a
            elif address==0x120e24:alias_bindings[a]=b
            elif address==0x18730c:ret=bits(float(a))
            elif address==0x11ad08:
                if string(b)!='x':raise RuntimeError('unexpected lookup path')
                ret=OTHER
            elif address==0x91de8:ret=0
            elif address==0x11f24c:
                index=(b-100)//102;is_label=(b-100)%102
                if is_label not in [0,1] or index not in range(8):raise RuntimeError('unexpected param tag')
                ret=0x1021000+(2*index+is_label)*0x200
            else:raise RuntimeError(f'unmodeled external execution {address:#x} target={ident}')
            uc.reg_write(UC_ARM_REG_R0,ret);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        def write(uc,access,address,size,value,user):
            if OBJ<=address<OBJ+0x180:writes.append({'address':address,'size':size,'value':value})
        u.hook_add(UC_HOOK_CODE,callback);u.hook_add(UC_HOOK_MEM_WRITE,write)
        u.reg_write(UC_ARM_REG_R0,OBJ)
        arg=0
        if ident in [1,3]:arg=(MIX if ident==1 else MAP) if variant else 0
        if ident==5:arg=GROUP if variant else 0
        if ident in [6,16]:arg=requests[variant]&0xffffffff
        if ident in [7,9,14]:arg=OTHER+0x200 if ident==7 and variant==4 else GROUP if ident==9 else PARAM
        if ident==15:arg=GROUP if variant else 0
        if ident==19 and variant==3:arg=GROUP+0x400
        if ident==28:arg=[0,1,2,0xffffffff][variant];u.reg_write(UC_ARM_REG_R2,int(variant!=1))
        if ident==29:arg=[0,1,5,6,39][variant]
        if ident==12:arg=0;u.reg_write(UC_ARM_REG_R2,variant)
        if ident==14:u.reg_write(UC_ARM_REG_R2,3 if variant==5 else 2)
        if ident==23:arg=MIX if variant%2 else 0
        u.reg_write(UC_ARM_REG_R1,arg);u.reg_write(UC_ARM_REG_SP,0x103f000);u.reg_write(UC_ARM_REG_LR,SENTINEL)
        start=0x96ef8 if ident==25 else 0x924f4 if ident==27 else 0x5c464 if ident==28 else 0x5c4d0 if ident==29 else self.requests[ident]['address']
        try:u.emu_start(start,SENTINEL,count=100000)
        except Exception as error:raise RuntimeError(f'id={ident} variant={variant} pc={u.reg_read(UC_ARM_REG_PC):#x} last={trace[-3:]}') from error
        if u.reg_read(UC_ARM_REG_PC)!=SENTINEL:raise RuntimeError('native instruction budget exhausted')
        if ident==15 and variant==2:
            u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,0);u.reg_write(UC_ARM_REG_LR,SENTINEL)
            u.emu_start(start,SENTINEL,count=100000)
        if ident in [1,3]:out=[int(get(OBJ+(0xcc if ident==1 else 0xd0))!=0)]
        elif ident in [2,10,13,18,20,21,22]:out=[result['deletes'],int(result['allocation_live'])]
        elif ident==4:out=[get(OBJ+0xe0)]
        elif ident in [5,9,11]:out=[signed(reg(0))]
        elif ident==8:out=[int(reg(0)!=0)]
        elif ident in [6,14,16]:out=[signed(get(OBJ+0xd4))]
        elif ident==7:out=[signed(get(OBJ+0xd8)),int(f32(values[OTHER])==1),int(f32(values[PARAM])==1),int(f32(values[PARAM+0x1800]))]
        elif ident==12:out=[len(active_observers)]
        elif ident==15:out=[get(OBJ+0xf8)]
        elif ident==17:out=[int(f32(values[PARAM])),result['edits']]
        elif ident==19:out=[get(OBJ+0x10c),get(OBJ+0x120),signed(get(OBJ+0xd8))]
        elif ident==23:out=[int(get(OBJ+0xcc)!=0),signed(get(OBJ+0xd8)),get(OBJ+0xf8)]
        elif ident==24:
            out=[signed(get(OBJ+0xd4)),signed(get(OBJ+0xd8))]
            if variant:out += [sum(enabled[0x1021000+i*0x400] for i in range(8)),sum(int(f32(values[0x1021000+i*0x400])) for i in range(8))]
        elif ident==27:
            out=[int(f32(values[PARAM+0x1800])),int(f32(values[PARAM+0x1900])),int(f32(values[PARAM+0x4000])),result['edits'],int(get(MIX+4)!=0),int(get(MIX+0x688)!=0),sum(u.mem_read(ARR+0x500,39))]
        elif ident==28:out=[*u.mem_read(ARR,2),u.mem_read(get(0x5c494),1)[0]]
        elif ident==29:out=[get(OBJ+8),get(OBJ+0xc),sum(u.mem_read(ARR,get(OBJ+0xc))) if get(OBJ+0xc) else 0]
        elif ident==25:
            out=[]
            for n in range(4):
                original=alias_bindings.get(PARAM+0x2000+n*0x100,0)
                out.append(-1 if not original else 256 if original%0x100==0 else 1)
        else:raise RuntimeError(ident)
        return {'id':ident,'variant':variant,'expected':out,'native_call_trace':trace,'native_object_writes':writes}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args()
    assert hashlib.sha256(ELF.read_bytes()).hexdigest()==ELF_HASH
    for path,address,size,digest in HELPERS:
        assert Path(path,'ELF_CONTEXT.md').is_file()
        assert hashlib.sha256(ELF.read_bytes()[address-0x8000:address-0x8000+size]).hexdigest()==digest
    with ELF.open('rb') as f:
        e=ELFFile(f);segments=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
    targets={i:json.loads((PACKETS/f'large02_w07_{i:02}'/'request.json').read_text())['targets'][0] for i in range(1,25)}
    oracle=Oracle(targets,segments)
    cases=[oracle.run(i,v) for i in list(range(1,26))+[27,28,29] for v in range(COUNTS.get(i,1))]
    Path(args.out).write_text(json.dumps({'elf':str(ELF),'elf_sha256':ELF_HASH,'engine':'Unicorn exact original ARM execution; explicit stubbed Core/libc/unreconstructed app boundaries','helper_ranges':[{'packet':p,'mangled':re.search(r'original `([^`]+)`',Path(p,'ELF_CONTEXT.md').read_text()).group(1),'address':a,'size':n,'range_sha256':h,'elf_sha256':ELF_HASH,'section':'.text','file_offset':a-0x8000} for p,a,n,h in HELPERS],'original_targets':[json.loads((PACKETS/f'large02_w07_{i:02}'/'request.json').read_text())['originals'][0]['original'] for i in range(1,25)],'cases':cases},indent=2)+'\n')
    print(f'original native cases: {len(cases)}')
if __name__=='__main__':main()
