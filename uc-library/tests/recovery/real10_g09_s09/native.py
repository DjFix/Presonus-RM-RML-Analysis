"""Original route construction. Unknown sink body remains an explicit traced boundary."""
import argparse,hashlib,io,json,struct,itertools,importlib.metadata
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def generate(path):
 raw=Path(path).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 elf=ELFFile(io.BytesIO(raw));sec=elf.get_section(12);start=0x802fc;size=588;off=sec['sh_offset']+start-sec['sh_addr'];assert hashlib.sha256(raw[off:off+size]).hexdigest()=='8191b5afce0540af73aefa2b9428d57cc977fdaa754734ba03ff40300bd1b82e'
 cases=[];patterns=[[],[[1,1]],[[0,0],[2,1]],[[2,0],[2,1]],[[1,1],[2,1],[2,1]]]
 for first,aux,fx,inputs in itertools.product([0,1,32,0xffffffff],[0,2,16,0xffffffff],[0,4],patterns):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
  for seg in elf.iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
  u.mem_map(0x1000000,0x20000);obj=0x1000000;sp=obj+0x18000;stop=obj+0x1f000;sink=obj+0x1000;vec=obj+0x2000
  def word(a,v):u.mem_write(a,struct.pack('<I',v))
  word(obj+0x138,first);word(obj+0x174,aux);word(obj+0x2a0,fx);word(obj+0x380,sink);word(sink,obj+0x1100);word(obj+0x1100,stop-0x800);word(obj+0x148,vec);word(obj+0x14c,len(inputs));ids={}
  for i,(kind,present) in enumerate(inputs):
   channel=obj+0x3000+i*0x400;word(vec+4*i,channel if kind else 0);ids[channel]=i
  routes=[];calls=[]
  def code(u,a,n,d):
   r0=u.reg_read(UC_ARM_REG_R0);r1=u.reg_read(UC_ARM_REG_R1)
   if a==0x116a38:calls.append(['debug',r1])
   elif a==stop-0x800:
    assert r0==sink;routes.append(list(struct.unpack('<6I',u.mem_read(r1,24))));calls.append(['route',len(routes)-1])
   elif a==0xacf4:
    i=ids[r0];calls.append(['cast',i]);u.reg_write(UC_ARM_REG_R0,r0 if inputs[i][0]==2 else 0)
   elif a==0x119c4c:
    i=ids[r0];calls.append(['get',i,r1]);u.reg_write(UC_ARM_REG_R0,obj+0x8000+4*i if inputs[i][1] else 0)
   elif a==0x11dc28:calls.append(['changed',(r0-obj-0x8000)//4])
   else:return
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,code)
  for r,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,stop)]:u.reg_write(r,v)
  u.emu_start(start,stop,count=10000);assert u.reg_read(UC_ARM_REG_PC)==stop
  cases.append({'input':{'first':first,'aux':aux,'fx':fx,'inputs':inputs},'routes':routes,'calls':calls})
 return {'elf_sha256':SHA,'range':{'address':start,'size':size,'section':12,'file_offset':off},'producer':{'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'unicorn_version':importlib.metadata.version('unicorn'),'oracle':'original app ARM; sink/RTTI/Core boundaries explicitly traced, no sink body execution claimed'},'domain':'7 route packets, unsigned32 arithmetic including zero/wrap boundaries; null/non-Digital/Digital list entries; absent/present tag360; first Digital terminates scan even when parameter absent; raw extreme count words are instruction-domain tests, not valid original vector-layout claims','cases':cases}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_text(json.dumps(generate(a.elf),indent=2)+'\n')
