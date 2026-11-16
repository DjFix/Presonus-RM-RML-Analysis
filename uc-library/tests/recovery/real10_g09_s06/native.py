"""Original channel linking plus actual native default Delegate bodies.
Existing link-partner lookup and external Channel/Linkable/Core/Permissions
implementations remain explicit boundaries; no provider body equivalence claim.
"""
import argparse,hashlib,io,json,struct,itertools,importlib.metadata
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def generate(path):
 raw=Path(path).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 elf=ELFFile(io.BytesIO(raw));sec=elf.get_section(12);start=0x2d60c;size=408;off=sec['sh_offset']+start-sec['sh_addr'];assert hashlib.sha256(raw[off:off+size]).hexdigest()=='e11ea873b54eccc94f5c2018a04d43ff024da0b3e883f75c65858c3bfffbe8ec'
 syms=elf.get_section_by_name('.symtab');addr=lambda n:syms.get_symbol_by_name(n)[0]['st_value'];cvt=addr('_ZTVN8Presonus5Mixer16ChannelComponentE')+8;pvt=addr('_ZTVN4Core8Portable12NumericParamE')+8;dvt=addr('_ZTVN8Presonus5Mixer18MixerComponentBase8DelegateE')+8
 helper=[]
 for name in ['_ZN8Presonus5Mixer18MixerComponentBase8Delegate16selectionChangedEv','_ZN8Presonus5Mixer18MixerComponentBase8Delegate11linkChangedEv']:
  symbol=syms.get_symbol_by_name(name)[0];a=symbol['st_value'];n=symbol['st_size'];f=sec['sh_offset']+a-sec['sh_addr'];assert n==16;helper.append({'mangled':name,'address':a,'size':n,'file_offset':f,'sha256':hashlib.sha256(raw[f:f+n]).hexdigest()})
 cases=[]
 for kind,link,hasPartner,delegates,permissions,initialGuard in itertools.product([-1,0,1,2,3,4,5,6,7,8],[0,1],[0,1],[0,2],[0,1],[0,1]):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
  for seg in elf.iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
  u.mem_map(0x1000000,0x20000);obj=0x1000000;sp=obj+0x18000;stop=obj+0x1f000
  ptr=lambda i:obj+0x2000+i*0x400
  par=lambda i:obj+0x6000+i*0x100
  def word(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
  def read(a):return struct.unpack('<I',u.mem_read(a,4))[0]
  partner=2 if kind in [0,2,3] else 3 if kind==4 else 4
  for i in range(1,5):word(ptr(i),cvt);word(par(i),pvt)
  word(ptr(1)+0x16c,kind);word(obj+0x370,obj+0x9000);word(obj+0x374,delegates);word(obj+0x318,obj+0xc000 if permissions else 0);u.mem_write(obj+0x4c8,bytes([initialGuard]))
  for i in range(delegates):o=obj+0xa000+i*0x100;word(obj+0x9000+4*i,o);word(o,dvt)
  setter=read(pvt+0x58);linker=read(cvt+0x3c);unlinker=read(cvt+0x40);delegate=read(dvt+4);calls=[];lookups=[]
  def code(u,a,n,d):
   r0=u.reg_read(UC_ARM_REG_R0);r1=u.reg_read(UC_ARM_REG_R1);guard=u.mem_read(obj+0x4c8,1)[0]
   if a==0x2c9c4:
    lookups.append({'vector_offset':u.reg_read(UC_ARM_REG_R2)-obj,'target':(r1-obj-0x2000)//0x400});u.reg_write(UC_ARM_REG_R0,ptr(partner) if hasPartner else 0)
   elif a==linker:calls.append(['link',(r0-obj-0x2000)//0x400,(r1-obj-0x2000)//0x400,u.reg_read(UC_ARM_REG_R2),guard])
   elif a==unlinker:calls.append(['unlink',(r0-obj-0x2000)//0x400,guard])
   elif a==0x119c4c:
    i=(r0-obj-0x2000)//0x400;calls.append(['get',i,r1,guard]);u.reg_write(UC_ARM_REG_R0,par(i))
   elif a==setter:calls.append(['set',(r0-obj-0x6000)//0x100,r1,u.reg_read(UC_ARM_REG_R2),guard])
   elif a==delegate:
    calls.append(['delegate',(r0-obj-0xa000)//0x100,guard]);return
   elif a==0x5158c:calls.append(['permissions',guard])
   else:return
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,code)
  for r,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,ptr(1)),(UC_ARM_REG_R2,link),(UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,stop)]:u.reg_write(r,v)
  u.emu_start(start,stop,count=10000);assert u.reg_read(UC_ARM_REG_PC)==stop
  cases.append({'input':[kind,link,hasPartner,delegates,permissions,initialGuard],'partner':partner,'partner_lookup':lookups,'calls':calls,'guard':u.mem_read(obj+0x4c8,1)[0]})
 for record in helper:
  observations=[]
  for receiver in [0x1000100,0x1000200]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
   for segment in elf.iter_segments():
    if segment['p_type']=='PT_LOAD':u.mem_write(segment['p_vaddr'],segment.data())
   u.mem_map(0x1000000,0x20000);stack=0x1018000;stop=0x101f000;before=bytes([0xa5])*32;u.mem_write(receiver,before)
   u.reg_write(UC_ARM_REG_R0,receiver);u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,stop)
   u.emu_start(record['address'],stop,count=100);assert u.reg_read(UC_ARM_REG_PC)==stop
   observations.append({'receiver':receiver,'r0_after':u.reg_read(UC_ARM_REG_R0),'stack_restored':u.reg_read(UC_ARM_REG_SP)==stack,'receiver_bytes_unchanged':bytes(u.mem_read(receiver,32))==before})
   assert observations[-1]['stack_restored'] and observations[-1]['receiver_bytes_unchanged']
  record['native_default_observations']=observations
 return {'elf_sha256':SHA,'range':{'address':start,'size':size,'section':12,'file_offset':off},'helper_ranges':helper,'producer':{'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'unicorn_version':importlib.metadata.version('unicorn'),'oracle':'original app; actual default Delegate::linkChanged body executes at exact primary-table slot4. Partner lookup/Channel/Linkable/Core/Permissions bodies are explicit traced boundaries.'},'domain':'all supported/unsupported kind selectors inclnegative; both link flags; absent/present partner; zero/two real Delegate entries; optional Permissions receiver; guard initiallyfalse/true; valid tag21 parameters; callbacks and borrowed collections stable','cases':cases}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_text(json.dumps(generate(a.elf),indent=2)+'\n')
