"""Private-memory execution of app instructions only. All providers intercepted.
Offsets below describe oracle fixtures, never production C++ object layout.
"""
import hashlib,json,struct,itertools
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
ELF=R/'rootfs/CS18_v13840/home/root/surface';SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
RAW=ELF.read_bytes();assert hashlib.sha256(RAW).hexdigest()==SHA
NAMES=['_ZN8Presonus10PotControl12paramChangedEPN4Core8Portable9ParameterEi','_ZN8Presonus10PotControl18getHandledGesturesERN4Core15FixedSizeVectorIiLi8EEERKNS1_6TPointIiEE','_ZN8Presonus10PotControl14onGestureInputERKN4Core8Portable12GestureEventE']
RANGES=[]
with ELF.open('rb') as f:
 e=ELFFile(f)
 for name in NAMES:
  s=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==name);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];RANGES.append(dict(mangled=name,address=s['st_value'],size=s['st_size'],section=sec.name,file_offset=off,sha256=hashlib.sha256(RAW[off:off+s['st_size']]).hexdigest()))
 SEGS=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
# Verify actual vtable bytes/slots separately from app execution. No Core body runs.
TABLES=[]
for address,offset,size,digest,slots in [
 (1684392,1651624,160,'e0060904919407feb8bc3f37debe1e4596de8ee00a520bc746572e93f9d2bc7b',[(20,1108216),(100,416276)]),
 (2114296,2081528,156,'1e3fb2b40c1ac23f2088d1c8d202d8782984a4aa89b83b805e8e6b0cf631b0e4',[(112,1127700)])]:
 data=RAW[offset:offset+size];assert hashlib.sha256(data).hexdigest()==digest
 for slot,target in slots:assert struct.unpack_from('<I',data,8+slot)[0]==target
 TABLES.append(dict(address=address,file_offset=offset,size=size,sha256=digest,slots=slots))
def execute(c):
 mode,flags,a,b,d=c;ran=RANGES[mode];u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x400000)
 for addr,data in SEGS:
  if addr<0x400000:u.mem_write(addr,data[:0x400000-addr])
 u.mem_protect(0,0x400000,5);u.mem_map(0x400000,0x40000)
 def w(addr,v):u.mem_write(addr,struct.pack('<I',v&0xffffffff))
 def read(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
 obj=0x400000;vt=0x401000;p=0x402000;other=0x402100;root=0x403000;rv=0x404000;vec=0x405000;buf=0x406000;event=0x407000;stop=0x430000
 w(obj,vt);w(obj+0x40,flags);w(obj+0x48,p if b else 0);w(vt+0x64,stop+4);w(vt+0x14,stop+8);w(root,rv);w(rv+0x70,stop+12);w(p+12,0x408000-8);u.mem_write(0x408000,b'Gain\0');w(vec,buf);w(vec+4,a if mode==1 else 0)
 for i in range(8):w(buf+4*i,100+i)
 w(event,a);calls=[];pcs=[];writes=[]
 def hook(uc,pc,size,data):
  if pc==stop:u.emu_stop();return
  if ran['address']<=pc<ran['address']+ran['size']:pcs.append(pc);return
  value=0
  if pc==0xf8768:calls.append('baseParam')
  elif pc==stop+4:calls.append('frames')
  elif pc==stop+8:calls.append('root');value=root if d else 0
  elif pc==stop+12:assert u.reg_read(UC_ARM_REG_R0)==root and u.reg_read(UC_ARM_REG_R1)==obj;calls.append('focus')
  elif pc==0xf6cf8:calls.append('parameter');value=p if b else 0
  elif pc==0x10eae4:calls.append('fallback');value=0
  elif pc==0xf9668:
   assert [u.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]==[root if d else 0,p,0x408000,0]
   assert read(u.reg_read(UC_ARM_REG_SP))==1;calls.append('text')
  else:raise AssertionError(hex(pc))
  u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def write(uc,access,addr,size,value,data):
  assert 0x410000<=addr<0x420000 or (mode==1 and (vec+4==addr or buf<=addr<buf+32)),hex(addr)
  writes.append([addr,size,value])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 args=[obj,(0 if d==0 else p if d==1 else other) if mode==0 else vec if mode==1 else event,a if mode==0 else 0x409000]
 for reg,val in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2],args):u.reg_write(reg,val)
 u.reg_write(UC_ARM_REG_SP,0x41ff00);u.reg_write(UC_ARM_REG_LR,stop);u.emu_start(ran['address'],stop,count=250);assert u.reg_read(UC_ARM_REG_PC)==stop
 if mode==0:out=[calls.count('frames')];assert calls[0]=='baseParam'
 elif mode==1:out=[read(vec+4)]+[read(buf+4*i) for i in range(read(vec+4))]
 else:out=[u.reg_read(UC_ARM_REG_R0),calls.count('root'),calls.count('focus'),calls.count('text')]
 return dict(input=c,output=out,calls=calls,executed_pcs=pcs,memory_writes=writes)
def cases():
 inputs=[]
 inputs += [[0,f,m,b,p] for f,m,b,p in itertools.product([0,0x200000,0x400000],[-1,0,1,2,3,4,5,6],[0,1],[0,1,2]) if not(m==3 and b==0 and p==0)] # actual CCL dereferences null on matching changed
 inputs += [[1,f,n,0,0] for f,n in itertools.product([0,0x200000,0x400000,0x600000],range(9))]
 inputs += [[2,f,s|t,b,r] for f,s,t,b,r in itertools.product([0,0x200000,0x600000],[0,0x10000,0x20000,0x40000,0x80000,0x100000,0x110000],range(8),[0,1],[0,1])]
 return [execute(c) for c in inputs]
if __name__=='__main__':
 data=dict(elf_sha256=SHA,ranges=RANGES,tables=TABLES,cases=cases());(T/'fixtures.json').write_text(json.dumps(data,separators=(',',':'))+'\n');print(len(data['cases']))
