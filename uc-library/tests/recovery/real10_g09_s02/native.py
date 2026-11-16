"""Original stagebox app body; external RTTI/message/Core/network providers traced explicitly."""
import argparse,hashlib,io,json,struct,itertools,importlib.metadata
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def generate(path):
 raw=Path(path).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 elf=ELFFile(io.BytesIO(raw));sec=elf.get_section(12);start=0x2e288;size=272;off=sec['sh_offset']+start-sec['sh_addr'];assert hashlib.sha256(raw[off:off+size]).hexdigest()=='7ad1bbbfeae3b396af3fdf9d56b6e5d228f1da19362adf558d4489c0203eac6c'
 rows=[]
 for mode,name,component,slot in itertools.product([0,1,2],[None,'','StoreAVBScene','X"\n'],[None,'','abc','x'*300],[-2147483648,-1,0,7,2147483647]):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
  for segment in elf.iter_segments():
   if segment['p_type']=='PT_LOAD':u.mem_write(segment['p_vaddr'],segment.data())
  u.mem_map(0x1000000,0x20000);obj=0x1000000;network=obj+0x1000;sp=obj+0x18000;stop=obj+0x1f000
  def word(a,v):u.mem_write(a,struct.pack('<I',v))
  def text(a):
   if not a:return None
   b=bytearray()
   while True:
    c=u.mem_read(a+len(b),1)[0]
    if not c:return b.decode('utf-8')
    b.append(c);assert len(b)<4096
  def put(a,s):
   if s is None:return 0
   u.mem_write(a,s.encode()+b'\0');return a
  word(obj+0x320,network if mode else 0);nameptr=put(obj+0x2000,name);componentptr=put(obj+0x4000,component)
  calls=[];attributes={};valueKeys={};message=None
  def code(u,a,n,d):
   nonlocal message
   r=[u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
   if a==0xacf4:calls.append(['cast']);u.reg_write(UC_ARM_REG_R0,network if mode==2 else 0)
   elif a==0x1004e4:
    calls.append(['construct',text(r[1])]);
    if r[1]:attributes['id']=text(r[1])
   elif a==0x100484:calls.append(['url',text(r[1])]);attributes['url']=text(r[1])
   elif a==0x122b78:
    key=text(r[1]);ptr=obj+0x9000+len(valueKeys)*0x100;valueKeys[ptr]=key;u.reg_write(UC_ARM_REG_R0,ptr);calls.append(['lookup',key])
   elif a==0x123a58:
    v=r[2]|(r[3]<<32);v=v-(1<<64) if v&(1<<63) else v;attributes[valueKeys[r[0]]]=v;calls.append(['integer',v])
   elif a==0x12445c:attributes[valueKeys[r[0]]]=text(r[1]);calls.append(['string',text(r[1]),r[2]])
   elif a==0x1008e0:message={'attributes':dict(attributes),'type':r[2],'hint':r[3]};calls.append(['event',r[2],r[3]])
   elif a==0x1c324:assert r[0]==network;calls.append(['send'])
   elif a==0x10f578:calls.append(['buffer_destroy'])
   elif a==0x122720:calls.append(['attributes_destroy'])
   else:return
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,code)
  for r,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,nameptr),(UC_ARM_REG_R2,componentptr),(UC_ARM_REG_R3,slot&0xffffffff),(UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,stop)]:u.reg_write(r,v)
  u.emu_start(start,stop,count=10000);assert u.reg_read(UC_ARM_REG_PC)==stop
  rows.append({'input':[mode,name,component,slot],'calls':calls,'message':message})
 return {'elf_sha256':SHA,'range':{'address':start,'size':size,'section':12,'file_offset':off},'producer':{'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'unicorn_version':importlib.metadata.version('unicorn'),'oracle':'original app ARM instructions; RTTI/Core/message/network calls are explicit traced boundaries; message data originates in original call arguments, not reconstructed code'},'domain':'absent/failed/successful optional receiver lookup; null/empty/quoted/newline identifiers; null/empty/short/300byte component; signed32 extrema/-1/0/7; normal nonthrowing provider path','cases':rows}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_text(json.dumps(generate(a.elf),indent=2)+'\n')
