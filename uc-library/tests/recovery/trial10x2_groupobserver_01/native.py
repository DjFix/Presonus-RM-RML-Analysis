"""Exact ELF app execution, with named source-provider boundaries only."""
import io,json,hashlib,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[4]
B=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/trial10x2-20261115')
READ=json.load(open(ROOT/'temp/recovery-work/trial10x2-20261115/READ_INPUTS-prepared01-trial10x2_groupobserver.json'))
ELFKEY='rootfs/RML16AI_Rack_13731/home/root/mixer'
ELF_SHA=READ[ELFKEY]['sha256']
PREFIX='_ZN8Presonus5Mixer19GroupChangeObserver'
CALLBACK=PREFIX+'12paramChangedEPN4Core8Portable9ParameterEi'
def sha(b):return hashlib.sha256(b).hexdigest()
class Oracle:
 def __init__(self,variant):
  self.raw=Path(READ[ELFKEY]['frozen_read_path']).read_bytes();assert sha(self.raw)==ELF_SHA
  self.elf=ELFFile(io.BytesIO(self.raw));self.symbols={s.name:s for s in self.elf.get_section_by_name('.symtab').iter_symbols()}
  self.ctor=PREFIX+variant+'EPNS0_16ChannelComponentERNS0_22AutoFilterGroupManagerE'
  self.ranges={}
  for name in (self.ctor,CALLBACK):
   s=self.symbols[name];sec=self.elf.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];raw=self.raw[off:off+s['st_size']]
   self.ranges[name]=dict(address=s['st_value'],size=s['st_size'],section=sec.name,section_index=s['st_shndx'],file_offset=off,sha256=sha(raw))
  supplementary=ROOT/'uc-library/candidates/trial10x2_groupobserver_01/callback-evidence'
  receipt=json.load(open(supplementary/'RECEIPT.json'));assert sha((supplementary/'RECEIPT.json').read_bytes())=='c41a7c9aa6594613b0347e005c6627355847ffd881823fe75775a35c3b6f02f4'
  for n,h in receipt['artifacts'].items():assert sha((supplementary/n).read_bytes())==h
  check=receipt['range_checks'][0];assert self.ranges[CALLBACK]['sha256']==check['bytes_sha256'] and self.ranges[CALLBACK]['file_offset']==check['file_offset']
  assert self.ranges[self.ctor]['size']==112 and self.ranges[CALLBACK]['size']==56
  self.boundaries={self.symbols[n]['st_value']:label for n,label in [('_ZN4Core8Portable9ComponentC2EPKc','component'),('_ZNK4Core8Portable9Component17getParameterByTagEi','lookup'),('_ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE','add'),('_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE','remove'),('_ZN8Presonus5Mixer22AutoFilterGroupManager16addUpdateChannelEPNS0_16ChannelComponentE','update')]}
 def run(self,present,message,null_callback=False):
  m=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for seg in self.elf.iter_segments():
   if seg['p_type']=='PT_LOAD':
    lo=seg['p_vaddr']&~4095;hi=(seg['p_vaddr']+seg['p_memsz']+4095)&~4095;m.mem_map(lo,hi-lo);m.mem_write(seg['p_vaddr'],seg.data())
  m.mem_map(0x10000000,0x100000);m.mem_map(0x20000000,4096)
  obj,ch,manager,param,sp,stop=0x10001000,0x10002000,0x10003000,0x10004000,0x100f0000,0x20000000
  events=[];writes=[];executed=[];phase=['ctor'];invalid=[None]
  def reg(r):return m.reg_read(r)
  def ret():m.reg_write(UC_ARM_REG_PC,reg(UC_ARM_REG_LR))
  def word(a):return struct.unpack('<I',m.mem_read(a,4))[0]
  def hook(u,pc,n,_):
   r=self.ranges[self.ctor if phase[0]=='ctor' else CALLBACK]
   if r['address']<=pc<r['address']+r['size']:executed.append(pc);return
   label=self.boundaries.get(pc);a,b=reg(UC_ARM_REG_R0),reg(UC_ARM_REG_R1)
   if label=='component':
    assert a==obj;literal=bytes(m.mem_read(b,1));assert literal==b'\0';events.append(['component','']);ret()
   elif label=='lookup':
    assert a==(0 if present==0 else ch) and b==25;events.append(['lookup',present,25])
    if present==0:invalid[0]='null channel at Core lookup boundary';m.emu_stop();return
    m.reg_write(UC_ARM_REG_R0,param if present==1 else 0);ret()
   elif label=='add':
    assert a==(param if present==1 else 0) and b==obj+4;events.append(['add',present,'observer-subobject+4'])
    if not a:invalid[0]='missing tag25 at Core addObserver boundary';m.emu_stop();return
    ret()
   elif label=='update':assert a==manager and b==ch;events.append(['update']);ret()
   elif label=='remove':assert a==param and b==obj+4;events.append(['remove']);ret()
   else:raise AssertionError(('unexpected instruction',hex(pc)))
  def write(u,access,a,n,v,_):
   if obj<=a<obj+0x100:writes.append([a-obj,n,v])
   elif not sp-0x1000<=a<sp:raise AssertionError(('unexpected app write',hex(a)))
  m.hook_add(UC_HOOK_CODE,hook);m.hook_add(UC_HOOK_MEM_WRITE,write)
  m.reg_write(UC_ARM_REG_SP,sp);m.reg_write(UC_ARM_REG_LR,stop);m.reg_write(UC_ARM_REG_R0,obj);m.reg_write(UC_ARM_REG_R1,0 if present==0 else ch);m.reg_write(UC_ARM_REG_R2,manager)
  m.emu_start(self.ranges[self.ctor]['address'],stop,count=200)
  if invalid[0]:return dict(events=events,invalid=invalid[0],writes=writes,executed=executed)
  assert reg(UC_ARM_REG_PC)==stop and reg(UC_ARM_REG_R0)==obj
  assert word(obj+0x84)==ch and word(obj+0x88)==manager
  assert word(obj+4)==word(obj)+0x34
  phase[0]='callback';m.reg_write(UC_ARM_REG_SP,sp);m.reg_write(UC_ARM_REG_LR,stop);m.reg_write(UC_ARM_REG_R0,obj);m.reg_write(UC_ARM_REG_R1,0 if null_callback else param);m.reg_write(UC_ARM_REG_R2,message&0xffffffff)
  m.emu_start(self.ranges[CALLBACK]['address'],stop,count=100);assert reg(UC_ARM_REG_PC)==stop
  return dict(events=events,invalid=None,writes=writes,executed=executed)
def generate(variant):
 o=Oracle(variant);cases=[]
 for present in [0,1,2]:
  for count in ([0,1,3] if present==1 else [0]):
   for message in ([-2147483648,-1,0,1,2,3,4,5,6,7,2147483647] if present==1 else [3]):
    cases.append(dict(args=[present,count,message],native=o.run(present,message)))
 for message in [-2147483648,-1,0,1,2,3,4,6,7,2147483647]:
  cases.append(dict(args=[1,0,message,'null'],native=o.run(1,message,True)))
 return dict(elf_sha256=ELF_SHA,ranges=o.ranges,cases=cases,scope='App instruction executions only; Core calls are typed hooks, Core bodies not executed. Null channel/missing parameter reach unchecked provider boundary; portable rejection is intentional adaptation. Complete native exception and destructor excluded.')
if __name__=='__main__':
 import sys
 print(json.dumps(generate(sys.argv[1] if len(sys.argv)>1 else 'C1'),indent=2))
