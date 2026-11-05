"""Exact original ARM ranges, synthetic state, observed external call boundaries.
Core binary bodies are not executed. Clock and signed division are explicit
boundary models; strings and register/write observations originate in ELF.
"""
import hashlib,json,pathlib,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=pathlib.Path.cwd(); ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
PACK='temp/recovery-work/rolling200-02/implementation-plan01/packets-isolated-rack_panel02/packets'
raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
checks=[];cases=[]
with ELF.open('rb') as f:
 e=ELFFile(f);loads=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
 for i in range(1,5):
  req=json.loads((ROOT/PACK/f'rolling200_02_impl_w01_0{i}/request.json').read_text());t=req['targets'][0];a=t['address'];size=t['size']
  sym=next(s for s in e.get_section_by_name('.symtab').get_symbol_by_name(t['mangled']) if s['st_value']==a and s['st_size']==size)
  sec=e.get_section(sym['st_shndx']);off=sec['sh_offset']+a-sec['sh_addr'];rhash=hashlib.sha256(raw[off:off+size]).hexdigest()
  assert rhash in (ROOT/PACK/f'rolling200_02_impl_w01_0{i}/ELF_CONTEXT.md').read_text()
  checks.append(dict(task=req['task_id'],mangled=t['mangled'],address=a,size=size,section=sec.name,file_offset=off,sha256=rhash))
  inputs=[{}]
  if i==2:
   inputs=[dict(flags=flags,raw_ns=raw_ns,start=start) for flags in [0,1,4,5,8,16,24,0x80000005] for raw_ns,start in [(0,0),(999999999,0),(1000000000,0),(1000999999,0),(2000000000,1000),(-1000000,0),(0,1),(1000000000,(1<<64)-1000),(0,1<<63),(0,(1<<63)+1),(9223372036854000000,0),(-9223372036854000000,0)]]
  if i==2:inputs.append(dict(flags=0,raw_ns=2500000000,start=2000,shared=True))
  for c in inputs:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x700000);u.mem_map(0x1000000,0x100000)
   for va,data in loads:u.mem_write(va,data)
   SELF=0x1000000;MIX=SELF+0x1000;OWNER=SELF+0x2000;PAR=SELF+0x3000;STOP=SELF+0xf0000
   def w(p,v,n=4):u.mem_write(p,int(v&((1<<(n*8))-1)).to_bytes(n,'little'))
   def r(p,n=4):return int.from_bytes(u.mem_read(p,n),'little')
   w(SELF+0x8c,MIX);w(MIX+0x2dc,OWNER);w(SELF+0x1d8,c.get('flags',0));w(0x494bd0,c.get('start',0),8)
   trace=[]
   def ret(v=None):
    if v is not None:u.reg_write(UC_ARM_REG_R0,v&0xffffffff)
    u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   def hook(uc,pc,sz,data):
    if pc==STOP:uc.emu_stop();return
    if a<=pc<a+size:return
    r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1)
    if pc==0x7d3fc:assert r0==SELF;trace.append('update');ret()
    elif pc==0x116908:
     trace.append('clock');v=c['raw_ns']&((1<<64)-1);uc.reg_write(UC_ARM_REG_R0,v&0xffffffff);uc.reg_write(UC_ARM_REG_R1,v>>32);ret()
    elif pc==0x157a08:
     assert uc.reg_read(UC_ARM_REG_R2)==1000000 and uc.reg_read(UC_ARM_REG_R3)==0
     v=(r1<<32)|r0;v=v-(1<<64) if v>>63 else v;q=(abs(v)//1000000)*(-1 if v<0 else 1);q&=(1<<64)-1
     uc.reg_write(UC_ARM_REG_R0,q&0xffffffff);uc.reg_write(UC_ARM_REG_R1,q>>32);ret()
    elif pc==0x32244:assert r0==MIX;trace.append('reset');ret()
    elif pc==0x119c4c:assert r0==OWNER;trace.append('lookup '+str(r1));ret(PAR+r1*16)
    elif pc==0x11dc28:trace.append('changed '+str((r0-PAR)//16));ret()
    elif pc==0x116a38:
     text=bytes(uc.mem_read(r0,256)).split(b'\0')[0].decode();trace.append(text);ret()
    else:raise RuntimeError('unbound PC '+hex(pc))
   u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_R0,SELF);u.reg_write(UC_ARM_REG_SP,SELF+0xef000);u.reg_write(UC_ARM_REG_LR,STOP);u.emu_start(a,STOP,count=1000);assert u.reg_read(UC_ARM_REG_PC)==STOP
   shared_flags=[]
   if c.get('shared'):
    shared_flags.append(r(SELF+0x1d8))
    OTHER=SELF+0x400
    w(OTHER+0x8c,MIX);w(OTHER+0x1d8,0)
    for obj,change in [(OTHER,False),(SELF,True),(OTHER,False)]:
     if change:w(0x494bd0,1000,8)
     u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,SELF+0xef000);u.reg_write(UC_ARM_REG_LR,STOP)
     u.emu_start(a,STOP,count=1000);assert u.reg_read(UC_ARM_REG_PC)==STOP
     shared_flags.append(r(obj+0x1d8))
   cases.append(dict(task=i,input=c,trace=trace,flags=r(SELF+0x1d8),startup=r(0x494bd0,8),shared_flags=shared_flags))
print(json.dumps(dict(elf_sha256=SHA,ranges=checks,cases=cases,limitations='External calls observed and returned by declared boundary models; original Core bodies excluded. Synthetic mapped state is not object-layout validation.'),indent=2))
