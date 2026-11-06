"""Exact original app instructions; explicit strcmp/getValue/float-equality boundaries.
No guest Core execution, syscalls or hardware. Test memory is not production layout.
"""
import hashlib,json,struct,itertools
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
ELF=R/'rootfs/RML16AI_Rack_13731/home/root/mixer';SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
RAW=ELF.read_bytes();assert hashlib.sha256(RAW).hexdigest()==SHA
RANGES=[];SEGS=[]
with ELF.open('rb') as f:
 e=ELFFile(f)
 for method in ['shouldLoad','shouldSave']:
  name='_ZNK8Presonus13MuteGroupBase6Filter10'+method+'EiPKcPv'
  s=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==name);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr']
  RANGES.append(dict(mangled=name,address=s['st_value'],size=s['st_size'],section=sec.name,file_offset=off,sha256=hashlib.sha256(RAW[off:off+s['st_size']]).hexdigest()))
 SEGS=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
def execute(c):
 save,kind,present,name,bits,arg=c;ran=RANGES[save]
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x400000)
 for addr,data in SEGS:
  if addr<0x400000:u.mem_write(addr,data[:0x400000-addr])
 u.mem_protect(0,0x400000,5);u.mem_map(0x400000,0x40000)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 obj=0x400000;vt=0x401000;buf=0x402000;stop=0x430000
 names=['mute','Mute','','muted',' mute','m'];w(obj,vt);w(vt+0x44,stop+4)
 if name<0:w(obj+12,0xfffffff8)
 else:w(obj+12,buf-8);u.mem_write(buf,names[name].encode()+b'\0')
 calls=[];pcs=[];writes=[]
 def string(a):
  b=bytearray()
  while u.mem_read(a,1)!=b'\0':b+=u.mem_read(a,1);a+=1
  return bytes(b)
 def hook(uc,pc,size,data):
  if pc==stop:u.emu_stop();return
  if ran['address']<=pc<ran['address']+ran['size']:pcs.append(pc);return
  if pc==0xaf70:
   a=string(u.reg_read(UC_ARM_REG_R0));b=string(u.reg_read(UC_ARM_REG_R1));calls.append(['strcmp',a.decode(),b.decode()]);value=(a>b)-(a<b)
  elif pc==stop+4:calls.append(['getValue',bits]);value=bits
  elif pc==0x1578e0:
   a=u.reg_read(UC_ARM_REG_R0);b=u.reg_read(UC_ARM_REG_R1);value=int(struct.unpack('<f',struct.pack('<I',a))[0]==struct.unpack('<f',struct.pack('<I',b))[0]);calls.append(['fcmpeq',a,b,value])
  else:raise AssertionError(hex(pc))
  u.reg_write(UC_ARM_REG_R0,value&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def write(uc,access,a,size,value,data):
  assert 0x410000<=a<0x420000,hex(a)
  writes.append([a-0x410000,size,value])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 for reg,val in [(UC_ARM_REG_R0,0x403000),(UC_ARM_REG_R1,kind&0xffffffff),(UC_ARM_REG_R2,0x404000 if arg else 0),(UC_ARM_REG_R3,obj if present else 0),(UC_ARM_REG_SP,0x41ff00),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,val)
 u.mem_write(0x404000,b'ignored\0');u.emu_start(ran['address'],stop,count=300);assert u.reg_read(UC_ARM_REG_PC)==stop
 return dict(input=c,output=[u.reg_read(UC_ARM_REG_R0),sum(x[0]=='getValue' for x in calls)],calls=calls,executed_pcs=pcs,stack_writes=writes)
def cases():
 bits=[0,0x80000000,0x3f800000,0xbf800000,0x7f800000,0xff800000,0x7fc00001,0xffc00001,1,0x80000001]
 inputs=itertools.product([0,1],[1131375984,1348563553,0,-1],[0,1],[-1,0,1,2,3,4,5],bits,[0,1])
 return [execute(list(c)) for c in inputs]
if __name__=='__main__':
 data=dict(elf_sha256=SHA,ranges=RANGES,cases=cases());(T/'fixtures.json').write_text(json.dumps(data,separators=(',',':'))+'\n');print(len(data['cases']))
