"""Bound original ARM execution; named providers are explicit test doubles."""
import hashlib,json,struct
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[5]
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def run(case, audit=None):
 assert hashlib.sha256(ELF.read_bytes()).hexdigest()==SHA
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
 with ELF.open('rb') as f:
  elf=ELFFile(f)
  for s in elf.iter_segments():
   if s['p_type']=='PT_LOAD':u.mem_write(s['p_vaddr'],s.data())
 u.mem_map(0x1000000,0x200000);u.mem_map(0x2000000,0x200000)
 def wr(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def rd(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def cs(a):return bytes(u.mem_read(a,256)).split(b'\0')[0].decode()
 def text(a,s):u.mem_write(a,s.encode()+b'\0')
 def r(i):return u.reg_read(UC_ARM_REG_R0+i)
 def ret(v=None):
  if v is not None:u.reg_write(UC_ARM_REG_R0,v&0xffffffff)
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def fl(v):return struct.unpack('<f',struct.pack('<I',v))[0]
 def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
 obj=0x1000000; pars=[0x1001000+i*0x100 for i in range(5)];vt=0x1002000
 for off,p in zip([0xc8,0xd0,0xd4,0xd8,0xdc],pars):wr(obj+off,p);wr(p,vt)
 wr(vt+0x44,0x1100000);wr(vt+0x58,0x1100004);wr(vt+0x74,0x1100008)
 text(obj+0x88,'fx');wr(obj+0xe0,case['effect'])
 values={pars[0]:case['slot'],pars[1]:case['loaded'],pars[4]:case['type']};out={'name':'initial','label':'initial','registered':0,'idle':0,'trace':[]}
 # Exact singleton cell from getFileName's bound literal.
 wr(rd(0x56028),0x1003000)
 cache=0x1004000;wr(cache+0x150,0x1005000);wr(cache+0x154,case.get('registered',0));wr(cache+0x158,4)
 if case.get('registered'):wr(0x1005000,obj+0x84)
 for a in [0x1100000,0x1100004,0x1100008,0x110000c]:u.mem_write(a,b'\x1e\xff\x2f\xe1')
 text(0x1006000,'cache-name');text(0x1006100,'unused')
 steps=[]
 writes=[]
 def write_hook(u,access,address,size,value,user):
  if obj <= address < obj+0x100 or cache <= address < cache+0x160 or 0x1005000 <= address < 0x1005100:
   writes.append(dict(address=address,size=size,value=value))
 u.hook_add(UC_HOOK_MEM_WRITE,write_hook)
 def hook(u,a,size,_):
  steps.append(a)
  if a==0x110000c:u.emu_stop();return
  if a==0x1100000:ret(bits(values[r(0)]));return
  if a==0x1100004:
   values[r(0)]=fl(r(1));out['trace'].append('set:'+str(int(fl(r(1))))+':'+str(r(2)));ret();return
  if a==0x1100008:
   key='label' if r(0)==pars[2] else 'name';out[key]=cs(r(1));out['trace'].append(key+':'+out[key]);ret();return
  if a==0x157958:ret(int(fl(r(0))));return
  if a==0x15746c:ret(bits(float(r(0))));return
  if a==0x1578e0:ret(int(fl(r(0))==fl(r(1))));return
  if a==0x1196a8:out['idle']+=1;ret();return
  if a==0x119624:ret(case.get('children',0));return
  if a==0x119638:ret(pars[r(1)%5]);return
  if a==0x129ba4 or a==0x1debc:text(r(0),'');ret();return
  if a==0x85b48:
   assert cs(r(3))=='fx' and rd(u.reg_read(UC_ARM_REG_SP))==1
   out['trace'].append('path:'+str(r(2)));text(r(0),case['path']);ret();return
  if a==0xae68:u.mem_write(r(0),bytes(u.mem_read(r(1),r(2))));ret();return
  if a==0x12784c:ret(int(case['exists']));return
  if a==0x85c14:
   assert cs(rd(u.reg_read(UC_ARM_REG_SP)))=='fx'
   out['trace'].append('info:'+str(r(3)));text(r(1),'preset-'+str(r(3)));ret();return
  if a==0x84b08:
   assert cs(r(1))=='fx'
   ret(cache if case.get('cache',True) else 0);return
  if a==0x11c2e4:out['trace'].append('remove');ret();return
 u.hook_add(UC_HOOK_CODE,hook)
 address=case['address'];u.reg_write(UC_ARM_REG_SP,0x2100000);u.reg_write(UC_ARM_REG_LR,0x110000c)
 args=[obj,case.get('arg',0),0,0]
 if case['method']=='cacheUpdated':args=[obj,cache,case['arg'],0x1006000];wr(0x2100000,0x1006100)
 if case['method']=='isChildParameter':args=[obj,pars[case['arg']],0,0]
 if case['method']=='paramChanged':args=[obj,pars[case['arg']],case['msg'],0]
 if case['method']=='getFileName':args=[obj,case['arg'],0x1007000,0]
 if case['method']=='getFxName':args=[obj,pars[3],case['arg'],0]
 for i,v in enumerate(args):u.reg_write(UC_ARM_REG_R0+i,v)
 u.emu_start(address,0,count=20000)
 assert u.reg_read(UC_ARM_REG_PC)==0x110000c,hex(u.reg_read(UC_ARM_REG_PC))
 out['slot']=values[pars[0]];out['registered']=rd(cache+0x154)
 if case['method'] in ['getSlotNum','isSlotEmpty','isChildParameter','getFileName']:out['return']=r(0)
 if case['method']=='getFileName':out['path']=cs(0x1007000)
 if audit is not None:
  audit.update(instruction_count=len(steps),executed_addresses=sorted(set(steps)),observed_state_writes=writes,original_executed=True,core_binary_recovery=False)
 return out
