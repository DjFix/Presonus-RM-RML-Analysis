"""Exact app ARM execution; all Core/libc interfaces are bounded observations.
No Core firmware, host syscalls or reconstructed C++ provides expected output.
"""
import hashlib
import json
import struct
from pathlib import Path
import unicorn as U
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT = Path(__file__).resolve().parents[4]
SHA = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
BASE = ROOT / 'temp/recovery-work/rolling200-03/alias01/prepared01/packets'
def native():
    path = ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
    blob = path.read_bytes()
    assert hashlib.sha256(blob).hexdigest() == SHA
    ranges=[]
    with path.open('rb') as f:
        elf=ELFFile(f)
        sec=elf.get_section(12)
        segments=[(int(s['p_vaddr']), s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
        for p in sorted(BASE.iterdir()):
            req=json.loads((p/'request.json').read_text())
            t=req['targets'][0]; off=int(sec['sh_offset'])+t['address']-int(sec['sh_addr'])
            digest=hashlib.sha256(blob[off:off+t['size']]).hexdigest()
            assert digest in (p/'ELF_CONTEXT.md').read_text()
            ranges.append(dict(mangled=t['mangled'],address=t['address'],size=t['size'],section='.text',file_offset=off,sha256=digest))
    cases=[]
    for mode in ('null','empty','bind','same','replace','clear','preserve','sparse','C1','C2','changed','C1_unwind','C2_unwind','alias_ctor_unwind'):
        m=U.Uc(U.UC_ARCH_ARM,U.UC_MODE_ARM);m.mem_map(0,0x500000);m.mem_map(0x1000000,0x20000)
        for a,b in segments:m.mem_write(a,b)
        obj,orig,new,stop=0x1001000,0x1002000,0x1003000,0x101F000
        def put(a,v):m.mem_write(a,struct.pack('<I',v))
        def get(a):return struct.unpack('<I',m.mem_read(a,4))[0]
        items={}; lists={obj:[],orig:[],new:[]}; nextp=0x1005000; trace=[]; writes=[]
        def param(tag,name,enabled,alias=False):
            nonlocal nextp
            p=nextp;nextp+=256;info=p+64;table=0x1018000 if alias else 0x1018100
            put(p,table);put(p+12,info);put(info,5 if alias else 1);put(info+4,tag & 0xffffffff);m.mem_write(info+8,name.encode()+b'\0')
            items[p]=dict(tag=tag,name=name,enabled=enabled,original=0,alias=alias)
            return p
        lists[orig]=[param(7,'Level',True),param(-2,'Mute',False)]
        lists[new]=[param(31,'Other',False)]
        put(0x1018000+8,0x1019000);put(0x1018000+0x24,0x1019010);put(0x1018100+0x20,0x1019020)
        old=orig if mode in ('same','replace','clear') else 0
        if old:lists[obj]=[param(90,'Old0',True,True),param(91,'Old1',False,True)]
        if mode=='preserve':lists[obj]=[param(99,'Keep',False,True)]
        if mode=='sparse':lists[orig].insert(1,0)
        put(obj+132,old)
        target=0 if mode in ('null','clear') else new if mode=='replace' else orig
        if mode=='empty':lists[orig]=[]
        name=0x101A000;m.mem_write(name,b'alias\0')
        def cstr(a):
            b=bytearray()
            while m.mem_read(a+len(b),1)!=b'\0':b.extend(m.mem_read(a+len(b),1))
            return b.decode()
        def hook(uc,pc,size,data):
            r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2)
            # Inject an exception at the interface and enter the compiler's app
            # cleanup landing pad. This observes cleanup instructions, not the
            # original ARM unwinder/personality or provider throwing behavior.
            if pc==0x3991c and mode in ('C1_unwind','C2_unwind'):
                trace.append(['injected_exception','setOriginal'])
                uc.reg_write(UC_ARM_REG_R0,0x1234)
                uc.reg_write(UC_ARM_REG_PC,0x39bec if mode=='C1_unwind' else 0x39c44)
                return
            if pc==0x11e5b0 and mode=='alias_ctor_unwind':
                trace.append(['injected_exception','AliasParam_constructor'])
                uc.reg_write(UC_ARM_REG_R0,0x1234);uc.reg_write(UC_ARM_REG_PC,0x39a6c);return
            ret=None
            if pc==0x119624:ret=len(lists[r0]);trace.append(['count',r0==obj,ret])
            elif pc==0x119638:ret=lists[r0][r1] if r1<len(lists[r0]) else 0;trace.append(['at',r0==obj,r1])
            elif pc==0xaa60:m.mem_write(r0,bytes([r1])*r2);ret=r0
            elif pc==0xabe0:m.mem_write(r0,cstr(r1).encode()+b'\0');ret=r0
            elif pc==0xa7e4:ret=param(0,'',False,True);trace.append(['allocate',r0])
            elif pc==0x11e5b0:
                tag=get(r1+4);tag=tag if tag<0x80000000 else tag-0x100000000
                items[r0].update(tag=tag,name=cstr(r1+8));trace.append(['construct_alias',tag,cstr(r1+8),r2]);ret=r0
            elif pc==0x11d340:lists[obj].append(r1);trace.append(['add',items[r1]['tag']]);ret=0
            elif pc==0x11ee28:items[r0]['original']=r1;trace.append(['bind',items[r1]['tag']]);ret=0
            elif pc==0x1019020:ret=int(items[r0]['enabled']);trace.append(['enabled',items[r0]['tag'],ret])
            elif pc==0x1019010:items[r0]['enabled']=bool(r1);trace.append(['enable',items[r0]['tag'],r1]);ret=0
            elif pc==0x11ce28:lists[obj].remove(r1);trace.append(['remove',items[r1]['tag']]);ret=0
            elif pc==0x1019000:trace.append(['delete',items[r0]['tag']]);ret=0
            elif pc==0xac10:trace.append(['delete_unconstructed_alias',r0 in items]);ret=0
            elif pc==0x11a53c:trace.append(['component_destructor',r0==obj]);ret=0
            elif pc==0xacd0:trace.append(['resume_cleanup',r0]);uc.reg_write(UC_ARM_REG_PC,stop);return
            elif pc==0x119e8c:trace.append(['component_constructor',cstr(r1)]);ret=r0
            elif pc==0x11b7d8:trace.append(['component_paramChanged',r1,r2]);ret=0
            if ret is not None:uc.reg_write(UC_ARM_REG_R0,ret);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
            elif not (0x39908<=pc<0x39c5c) and pc!=stop:raise RuntimeError(hex(pc))
        def write(uc,access,a,size,value,data):
            if obj<=a<obj+256:writes.append([a-obj,size,value])
        m.hook_add(U.UC_HOOK_CODE,hook);m.hook_add(U.UC_HOOK_MEM_WRITE,write)
        m.reg_write(UC_ARM_REG_R0,obj);m.reg_write(UC_ARM_REG_R1,target);m.reg_write(UC_ARM_REG_R2,orig);m.reg_write(UC_ARM_REG_SP,0x101E000);m.reg_write(UC_ARM_REG_LR,stop)
        addr=0x3991c
        if mode in ('C1','C2','C1_unwind','C2_unwind'):addr=0x39bac if mode.startswith('C1') else 0x39c04;m.reg_write(UC_ARM_REG_R1,name)
        if mode=='changed':addr=0x39a88;m.reg_write(UC_ARM_REG_R1,orig);m.reg_write(UC_ARM_REG_R2,2)
        m.emu_start(addr,stop,count=10000);assert m.reg_read(UC_ARM_REG_PC)==stop
        snapshot=[{k:items[p][k] for k in ('tag','name','enabled')} for p in lists[obj]]
        m.reg_write(UC_ARM_REG_R0,obj);m.reg_write(UC_ARM_REG_LR,stop);m.emu_start(0x39908,stop,count=100)
        cases.append(dict(mode=mode,snapshot=snapshot,original_nonnull=bool(get(obj+132)),getter_matches=m.reg_read(UC_ARM_REG_R0)==get(obj+132),trace=trace,writes=writes))
    return dict(elf_sha256=SHA,ranges=ranges,cases=cases,unicorn_version=U.__version__,limitations=['Only app instructions execute; Core/libc interfaces modeled and traced, not native provider behavior.','Cleanup landing pads entered through explicit interface exception injection; no original exception personality execution; host allocation-failure checks separate.','No ARM ABI, original layout, original return declaration, or hardware claim.'])
if __name__=='__main__':print(json.dumps(native(),indent=2))
