"""Only assigned ARM functions execute. Virtual activation/status are trace stubs.
No guest Core, device or syscall execution. Sentinel is independently NOBITS."""
import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
ELF=R/'rootfs/RML16AI_Rack_13731/home/root/mixer';SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
RAW=ELF.read_bytes();assert hashlib.sha256(RAW).hexdigest()==SHA
NAMES=['_ZN8Presonus13MuteGroupBase8activateEv','_ZNK8Presonus23StormMuteGroupComponent8activateEj']
with ELF.open('rb') as f:
 e=ELFFile(f);syms={s.name:s for s in e.get_section_by_name('.symtab').iter_symbols()};RANGES=[]
 for name in NAMES:
  s=syms[name];sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];RANGES.append(dict(mangled=name,address=s['st_value'],size=s['st_size'],section=sec.name,file_offset=off,sha256=hashlib.sha256(RAW[off:off+s['st_size']]).hexdigest()))
 err=syms['_ZN4Core11ConstVectorIPN8Presonus13MuteGroupBaseEE5errorE'];assert e.get_section(err['st_shndx'])['sh_type']=='SHT_NOBITS';ERROR=err['st_value']
 SEGS=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
def execute(index,count,null,sentinel,base=False,abort=False):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x900000)
 for a,d in SEGS:u.mem_write(a,d)
 obj=0x800000;arr=obj+0x1000;group=obj+0x2000;vt=obj+0x3000;stop=obj+0xf000;call=stop+4
 def w(a,v):u.mem_write(a,struct.pack('<I',v))
 w(obj+0xa0,arr);w(obj+0xa4,count);w(ERROR,group+0x100 if sentinel else 0)
 for i in range(count):w(arr+4*i,0 if null else group+i*0x100)
 for i in range(3):w(group+i*0x100,vt)
 w(vt+12,call);events=[];pcs=[];target=RANGES[0 if base else 1]
 def hook(uc,pc,size,data):
  if pc==stop:u.emu_stop();return
  if target['address']<=pc<target['address']+target['size']:pcs.append(pc);return
  if pc in (call,0x74eec):
   events.append(['activate' if pc==call else 'status',u.reg_read(UC_ARM_REG_R0)-group])
   if abort and pc==call:u.emu_stop();return
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  raise AssertionError(hex(pc))
 u.hook_add(UC_HOOK_CODE,hook)
 u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,index);u.reg_write(UC_ARM_REG_SP,obj+0xe000);u.reg_write(UC_ARM_REG_LR,stop)
 before=bytes(u.mem_read(obj,0x4000));u.emu_start(target['address'],stop,count=100)
 if base:assert before==bytes(u.mem_read(obj,0x4000))
 return dict(index=index,count=count,null=null,sentinel=sentinel,base=base,abort=abort,events=events,pcs=pcs)
def cases():
 result=[execute(0,0,False,False,True)]
 for count in [0,2]:
  for i in [0,1,2,0x7fffffff,0x80000000,0xffffffff]:
   for sentinel in [False,True]:result.append(execute(i,count,False,sentinel))
 result += [execute(0,2,True,False),execute(0,2,False,False,abort=True)]
 return result
if __name__=='__main__':
 (T/'fixtures.json').write_text(json.dumps(dict(elf_sha256=SHA,ranges=RANGES,error=dict(address=ERROR,storage='SHT_NOBITS',initial=0),cases=cases()),indent=2)+'\n')
 print('27 assigned original ARM executions')
