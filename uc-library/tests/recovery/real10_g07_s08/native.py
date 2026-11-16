"""Fresh exact ARM target execution; app getCategory and parameter virtual boundaries
are explicit test stubs. Softfloat helpers execute their original instructions.
No devices, syscalls, or Core binary recovery."""
import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
NAME='_ZN8Presonus5Panel22ChannelPresetComponent23onPresetCategoryChangedEv'
RAW=ELF.read_bytes()
assert hashlib.sha256(RAW).hexdigest()==SHA
with ELF.open('rb') as f:
 e=ELFFile(f);sym=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==NAME)
 sec=e.get_section(sym['st_shndx']);off=sec['sh_offset']+sym['st_value']-sec['sh_addr']
 RANGE=dict(mangled=NAME,address=sym['st_value'],size=sym['st_size'],section=sym['st_shndx'],file_offset=off,sha256=hashlib.sha256(RAW[off:off+sym['st_size']]).hexdigest())
 assert RANGE['sha256']=='705dc27c86d85e32e46a0c6b35428202f955f770f95eac93d77a4c2d7703180b'
def execute(case):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x500000);u.mem_map(0x1000000,0x30000)
 with ELF.open('rb') as f:
  for seg in ELFFile(f).iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 obj=0x1000000;gate=obj+0x1000;category=obj+0x2000;slot=obj+0x3000;vt=obj+0x4000;stop=obj+0x5000;buf=obj+0x6000
 def w(a,x):u.mem_write(a,struct.pack('<I',x&0xffffffff))
 def get(reg):return u.reg_read(reg)
 def ret(value=None):
  if value is not None:u.reg_write(UC_ARM_REG_R0,value&0xffffffff)
  u.reg_write(UC_ARM_REG_PC,get(UC_ARM_REG_LR))
 def text(a):return bytes(u.mem_read(a,256)).split(b'\0',1)[0].decode()
 def string(a,s):u.mem_write(a,s.encode()+b'\0')
 w(obj+0x88,gate if case['gate_present'] else 0);w(obj+0xc8,category);w(obj+0x8c,slot)
 for p in [gate,category,slot]:w(p,vt)
 w(vt+0x44,stop+4);w(vt+0x70,stop+8);w(vt+0x58,stop+12)
 trace=[];writes=[];instructions=[];result={'slot':77,'search':[],'sets':[]}
 def hook(uc,a,size,data):
  instructions.append(a)
  if a==stop:uc.emu_stop();return
  x=get(UC_ARM_REG_R0);y=get(UC_ARM_REG_R1);z=get(UC_ARM_REG_R2)
  if a==stop+4:trace.append(['getValue']);ret(case['gate_bits'])
  elif a==stop+8:trace.append(['toString',z]);string(y,case['selected'][:z-1]);ret()
  elif a==stop+12:
   value=struct.unpack('<f',struct.pack('<I',y))[0];result['slot']=int(value);result['sets'].append([int(value),z]);ret()
  elif a==0x39c5c:
   result['search'].append(y);s=case['categories'][y];string(buf,s);ret(buf)
  elif a==0xae98:ret(len(text(x)))
  elif a==0xafe8:u.mem_write(x,bytes(u.mem_read(y,z)));ret(x)
  elif a==0xaf70:ret(0 if text(x)==text(y) else 1)
  elif RANGE['address']<=a<RANGE['address']+RANGE['size'] or 0x157000<=a<0x157958:pass
  else:raise AssertionError(hex(a))
 def writing(uc,access,a,size,val,data):
  writes.append([a,size,val])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,writing)
 for reg,val in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_SP,obj+0x2f000),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,val)
 u.emu_start(RANGE['address'],stop,count=20000);assert get(UC_ARM_REG_PC)==stop
 return dict(projection=result,trace=trace,writes=writes,instructions=instructions)
def cases():
 out=[]
 for present,bits in [(False,0x3f800000),(True,0),(True,0x80000000),(True,0xbf800000),(True,0x3f000000),(True,0x7fc00000),(True,0x7f800000),(True,1)]:
  for match in [-1,0,1,50,98]:
   cats=['other']*99
   if match>=0:cats[match]='selected'
   c=dict(gate_present=present,gate_bits=bits,selected='selected',categories=cats)
   out.append(dict(input=c,output=execute(c)))
 for selected,candidate in [('', ''),('A'*31,'A'*40),('A'*32,'A'*40),('Case','case')]:
  cats=['other']*99;cats[0]=candidate
  c=dict(gate_present=True,gate_bits=0x3f800000,selected=selected,categories=cats);out.append(dict(input=c,output=execute(c)))
 return out
if __name__=='__main__':
 data=dict(elf_sha256=SHA,range=RANGE,producer='Unicorn original ARM target; explicit parameter/getCategory/libc boundary stubs; native softfloat',cases=cases())
 for row in data['cases']:row['output']={k:row['output'][k] for k in ['projection','trace']}
 (Path(__file__).parent/'fixtures.json').write_text(json.dumps(data,indent=2)+'\n');print(len(data['cases']))
