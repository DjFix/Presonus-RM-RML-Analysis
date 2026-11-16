"""Exact selected ARM constructor; providers are explicit intercepted boundaries.
The actual real CCL/portable provider observations are made separately by Replay.cpp.
No Core instruction recovery, system calls, device access, or firmware execution."""
import hashlib,json,struct,os
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
TASK=Path(__file__).parent.name
NAME='_ZN8Presonus5Panel22ChannelPresetComponentC1ERNS_5Mixer18MixerComponentBaseE'
ELF=Path(os.environ.get('PRESONUS_NATIVE_ELF','/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/prepared-main/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer'))
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
RAW=ELF.read_bytes();assert hashlib.sha256(RAW).hexdigest()==SHA
with ELF.open('rb') as f:
 e=ELFFile(f);sym=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name==NAME);sec=e.get_section(sym['st_shndx']);off=sec['sh_offset']+sym['st_value']-sec['sh_addr']
 RANGE=dict(mangled=NAME,address=sym['st_value'],size=sym['st_size'],section=sym['st_shndx'],file_offset=off,sha256=hashlib.sha256(RAW[off:off+sym['st_size']]).hexdigest())
 assert RANGE['sha256']=='56665095f65a1bb1feac1278f25b0674aafe9de96bc90c9297a7f1edd6d5f7cf'
def execute(mode):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x500000);u.mem_map(0x1000000,0x30000)
 with ELF.open('rb') as f:
  for s in ELFFile(f).iter_segments():
   if s['p_type']=='PT_LOAD':u.mem_write(s['p_vaddr'],s.data())
 obj=0x1000000;mixer=obj+0x1000;param=obj+0x2000;stop=obj+0x5000
 def w(a,x):u.mem_write(a,struct.pack('<I',x&0xffffffff))
 def word(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def string(a):return bytes(u.mem_read(a,256)).split(b'\0',1)[0].decode()
 def get(r):return u.reg_read(r)
 def ret(x=None):
  if x is not None:u.reg_write(UC_ARM_REG_R0,x)
  u.reg_write(UC_ARM_REG_PC,get(UC_ARM_REG_LR))
 calls=[];writes=[];seen=[];metadata={}
 def hook(uc,a,size,data):
  seen.append(a)
  if a==stop:uc.emu_stop();return
  x=get(UC_ARM_REG_R0);y=get(UC_ARM_REG_R1);z=get(UC_ARM_REG_R2);v=get(UC_ARM_REG_R3)
  if a==0x83b64:
   metadata.update(name=string(y),display=string(z),formatter=string(v),borrowed_mixer=word(get(UC_ARM_REG_SP))==mixer)
   calls.append(dict(boundary='PresetComponent constructor',receiver_is_this=x==obj,arguments=[y,z,v,word(get(UC_ARM_REG_SP))]));ret(obj)
  elif a==0x11ec54:
   table=bytes(u.mem_read(y,84));type_,tag=struct.unpack('<ii',table[:8]);floats=struct.unpack('<5f',table[40:60]);flags=struct.unpack('<I',table[60:64])[0];ptrs=struct.unpack('<5I',table[64:84])
   strings=[string(word(ptrs[2]+4*i)) for i in range(int(floats[1])+1)]
   metadata['parameter']=dict(type=type_,tag=tag,name=table[8:40].split(b'\0')[0].decode(),min=floats[0],max=floats[1],mid=floats[2],default=floats[3],delta=floats[4],flags=flags,title=string(ptrs[3]),strings=strings,table_sha256=hashlib.sha256(table).hexdigest(),list_sha256=hashlib.sha256(bytes(u.mem_read(ptrs[2],36))).hexdigest())
   calls.append(dict(boundary='ParamList::add',receiver_offset=x-obj,count=z,owns_info=v));ret()
  elif a==0x119c4c:calls.append(dict(boundary='Component::getParameterByTag',receiver_is_this=x==obj,tag=y));ret(param if mode else 0)
  elif a==0xacf4:calls.append(dict(boundary='runtime cast',source=x,source_type=y,destination_type=z,offset=v));ret(param if mode==2 else 0)
  elif RANGE['address']<=a<RANGE['address']+RANGE['size']:pass
  else:raise AssertionError(hex(a))
 def write(uc,access,a,size,value,data):
  if obj<=a<obj+0x400:writes.append(dict(offset=a-obj,size=size,value=value))
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 for reg,value in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,mixer),(UC_ARM_REG_SP,obj+0x2f000),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,value)
 u.emu_start(RANGE['address'],stop,count=2000);assert get(UC_ARM_REG_PC)==stop
 return dict(metadata=metadata,found=bool(mode),cast=word(obj+0xc8)==param,receiver_return=get(UC_ARM_REG_R0)==obj,calls=calls,object_writes=writes,instructions=seen)
def cases():return [dict(mode=mode,observed=execute(mode)) for mode in range(3)]
if __name__=='__main__':
 data=dict(elf_sha256=SHA,elf_path=str(ELF),range=RANGE,producer='Unicorn original ARM exact constructor; explicit Preset/ParamList/lookup/C++ runtime-cast boundary interceptions',domain='normal valid parameter, missing parameter, wrong-type cast; actual portable constructor necessarily creates valid ListParam; no original EH, layout or ARM ABI claim',cases=cases())
 (Path(__file__).parent/'fixtures.json').write_text(json.dumps(data,indent=2)+'\n');print(TASK,len(data['cases']))
