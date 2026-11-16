"""Original panicMuteAll instructions; CCL/application boundaries explicitly traced.
__aeabi_fcmpeq executes its original ARM runtime body; no CCL body is recovered.
"""
import argparse,hashlib,io,json,struct,itertools,importlib.metadata
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def generate(path):
 raw=Path(path).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 elf=ELFFile(io.BytesIO(raw));sec=elf.get_section(12);start=0x2d7a4;size=352;off=sec['sh_offset']+start-sec['sh_addr'];assert hashlib.sha256(raw[off:off+size]).hexdigest()=='528184d9088093564f3ea7329371b11c7404891f43de13110335074c86cc2acc'
 syms=elf.get_section_by_name('.symtab')
 addr=lambda name:syms.get_symbol_by_name(name)[0]['st_value']
 pvt=addr('_ZTVN4Core8Portable12NumericParamE')+8;mvt=addr('_ZTVN8Presonus5Mixer14MixerComponentE')+8
 cases=[]
 vectors=[[],[None],[0],[0x80000000],[0x3f800000],[0x7fc00000],[None,0,0x3f800000],[0x3f800000,None,0],[0x3f800000,0x3f800000],[None,None],[0x3f000000,0x7f800000],[0xff800000,0x80000000]]
 for values,mute,saved in itertools.product(vectors,[False,True],[False,True]):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
  for segment in elf.iter_segments():
   if segment['p_type']=='PT_LOAD':u.mem_write(segment['p_vaddr'],segment.data())
  u.mem_map(0x1000000,0x20000);obj=0x1000000;vec=obj+0x1000;sp=obj+0x18000;stop=obj+0x1f000
  def word(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
  def read(a):return struct.unpack('<I',u.mem_read(a,4))[0]
  word(obj,mvt);word(obj+0x120,vec);word(obj+0x124,len(values));word(obj+0x4ac,int(saved))
  params={};current={}
  for i,bits in enumerate(values):
   channel=obj+0x2000+i*0x400;parameter=obj+0x6000+i*0x100;word(vec+4*i,channel);word(channel+0xe8,parameter if bits is not None else 0)
   if bits is not None:word(parameter,pvt);params[parameter]=i;current[i]=bits
  get=read(pvt+0x44);setv=read(pvt+0x58);remember=read(mvt+0xac);restore=read(mvt+0xb0);calls=[]
  def code(u,a,n,d):
   r0=u.reg_read(UC_ARM_REG_R0)
   if a==get:
    calls.append(['get',params[r0]]);u.reg_write(UC_ARM_REG_R0,current[params[r0]])
   elif a==setv:
    i=params[r0];bits=u.reg_read(UC_ARM_REG_R1);calls.append(['set',i,bits,u.reg_read(UC_ARM_REG_R2)]);current[i]=bits
   elif a in [remember,restore]:
    assert r0==obj and u.reg_read(UC_ARM_REG_R1)==obj+0x498
    selector=read(u.reg_read(UC_ARM_REG_R2));calls.append(['remember' if a==remember else 'restore',selector])
    if a==remember:word(obj+0x4ac,1)
   elif a==0x121a08:
    assert r0==obj+0x498;calls.append(['clear']);word(obj+0x4ac,0)
   else:return
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,code)
  for r,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,int(mute)),(UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,stop)]:u.reg_write(r,v)
  u.emu_start(start,stop,count=10000);assert u.reg_read(UC_ARM_REG_PC)==stop
  cases.append({'input':{'values':values,'mute':mute,'saved':saved},'calls':calls,'output':{'values':[current.get(i) for i in range(len(values))],'saved':bool(read(obj+0x4ac))}})
 return {'elf_sha256':SHA,'range':{'address':start,'size':size,'section':12,'file_offset':off},'producer':{'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'unicorn_version':importlib.metadata.version('unicorn'),'oracle':'original app and original ARM soft-float equality helper; exact NumericParam/Mixer primary vtables; get/set/save/load/clear external bodies are explicit deterministic boundary stubs'},'domain':'both mute flags; empty/single/mixed lists; null mute slots; +0/-0/1/fraction/NaN/infinity; empty/populated snapshots; nonnull channels, synchronous nonmutating parameter callbacks; save boundary makes snapshot nonempty and load boundary captures only','cases':cases}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_text(json.dumps(generate(a.elf),indent=2)+'\n')
