"""Original AVB notification orchestration with explicit external CCL/RTTI boundaries."""
import argparse,hashlib,io,json,struct,itertools,importlib.metadata
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def generate(path):
 raw=Path(path).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 elf=ELFFile(io.BytesIO(raw));sec=elf.get_section(12);start=0x2cf04;size=260;off=sec['sh_offset']+start-sec['sh_addr'];assert hashlib.sha256(raw[off:off+size]).hexdigest()=='c870bb14ef845ffa67d9bf5bf1b08a862da50082efc65b4415f86ac962dd1f46'
 lists=[[],[0],[1],[1,0,1]];digital=[[],[[1,1]],[[0,0],[2,1]],[[2,0],[2,1]],[[1,1],[2,1],[2,1]]];cases=[]
 for first,second,third in itertools.product(lists,digital,lists):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
  for seg in elf.iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
  u.mem_map(0x1000000,0x20000);obj=0x1000000;sp=obj+0x18000;stop=obj+0x1f000
  def word(a,v):u.mem_write(a,struct.pack('<I',v))
  ids={};present={};types={}
  for group,(values,items,count) in enumerate([(first,0x134,0x138),(second,0x148,0x14c),(third,0x1fc,0x200)]):
   vec=obj+0x1000+group*0x100;word(obj+items,vec);word(obj+count,len(values))
   for i,value in enumerate(values):
    kind,has=value if group==1 else (1,value);identity=group*4+i;channel=obj+0x3000+identity*0x200;word(vec+4*i,channel if kind else 0);ids[channel]=identity;present[identity]=has;types[identity]=kind
  calls=[]
  def code(u,a,n,d):
   r0=u.reg_read(UC_ARM_REG_R0);r1=u.reg_read(UC_ARM_REG_R1)
   if a==0xacf4:
    identity=ids[r0];calls.append(['cast',identity]);u.reg_write(UC_ARM_REG_R0,r0 if types[identity]==2 else 0)
   elif a==0x119c4c:
    identity=ids[r0];calls.append(['get',identity,r1]);u.reg_write(UC_ARM_REG_R0,obj+0xa000+identity*4 if present[identity] else 0)
   elif a==0x11dc28:calls.append(['changed',(r0-obj-0xa000)//4])
   else:return
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,code)
  for r,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,stop)]:u.reg_write(r,v)
  u.emu_start(start,stop,count=10000);assert u.reg_read(UC_ARM_REG_PC)==stop;cases.append({'input':[first,second,third],'calls':calls})
 return {'elf_sha256':SHA,'range':{'address':start,'size':size,'section':12,'file_offset':off},'producer':{'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'unicorn_version':importlib.metadata.version('unicorn'),'oracle':'original app ARM instructions; CCL lookup/changed and RTTI are explicit traced external boundaries'},'domain':'empty/single/multiple first+third collections; required nonnull first/third channels; null/non-Digital/Digital middle collection; missing/present tags304/360/340; stop after first Digital even if missing parameter; stable synchronous collections','cases':cases}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_text(json.dumps(generate(a.elf),indent=2)+'\n')
