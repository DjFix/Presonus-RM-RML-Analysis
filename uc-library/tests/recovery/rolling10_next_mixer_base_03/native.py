"""Execute exact non-Core ARM ranges; Core call sites are explicit boundary models."""
import hashlib,json,pathlib,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
LANE='rolling10_next_mixer_base_03'
class Native:
 def __init__(self,lane=LANE):
  self.lane=lane
  read=json.loads((ROOT/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-rolling10_mixer_base.json').read_text())
  p=pathlib.Path(read['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path']);raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
  packet=ROOT/'temp/recovery-work/rolling10x10-20261114/prepared05/packets'/lane
  j=json.loads((packet/'native-context.json').read_text());self.body=j['bodies'][j['roots'][0]]
  self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);self.u.mem_map(0,0x600000)
  with p.open('rb') as f:
   elf=ELFFile(f)
   for s in elf.iter_sections():
    a,n,o=s['sh_addr'],s['sh_size'],s['sh_offset']
    if a and a+n<0x600000 and s['sh_type']!='SHT_NOBITS':self.u.mem_write(a,raw[o:o+n])
   b=self.body;s=elf.get_section(b['section_index']);assert s.name==b['section'];assert s['sh_offset']+b['address']-s['sh_addr']==b['file_offset']
  b=self.body;assert hashlib.sha256(raw[b['file_offset']:b['file_offset']+b['size']]).hexdigest()==b['bytes_sha256']
  self.u.mem_map(0x1000000,0x40000);self.u.mem_map(0x1100000,0x10000);self.u.mem_map(0x1200000,0x1000)
  self.u.hook_add(UC_HOOK_CODE,self.hook);self.u.hook_add(UC_HOOK_MEM_WRITE,self.write)
 def w(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def string(self,a):
  out=bytearray()
  while True:
   b=bytes(self.u.mem_read(a,1));a+=1
   if b==b'\0':return out.decode()
   out+=b
 def write(self,u,access,a,size,value,data):
  if 0x1000000<=a<0x1040000:self.writes.append([a,size,value])
 def hook(self,u,a,size,data):
  if a==0x1200000:u.emu_stop();return
  b=self.body
  if b['address']<=a<b['address']+b['size']:return
  r0,r1,r2,r3=[u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
  if a==0x12640:
   self.trace.append(['resize',r1,not self.fail]);u.reg_write(UC_ARM_REG_R0,0 if self.fail else 1)
   if not self.fail:self.w(r0+12,((r1+9)//10)*10)
  elif a==0x11f9a0:self.trace.append(['removeAll']);self.items=[]
  elif a==0x11ecd8:
   s=self.string(r1);self.items.append(s);self.trace.append(['appendString',s])
  elif a==0x12af4:
   fmt=self.string(r1);s=fmt%(r2,r3);u.mem_write(r0,s.encode()+b'\0');self.trace.append(['appendFormat',fmt,r2,r3,s])
  elif a==0x11dbd4:self.trace.append(['rangeChanged'])
  else:raise RuntimeError('Unbound execution '+hex(a))
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def execute(self,case):
  self.trace=[];self.writes=[];self.items=['old'];self.fail=case.get('fail',False)
  self.u.mem_write(0x1000000,bytes(0x40000));self.w(0x1000000+0x174,case.get('count',0))
  channels=case.get('channels',[]);self.w(0x1000120,0x1001000);self.w(0x1000124,len(channels));self.w(0x10002c4,0x1020000);self.w(0x10002c8,len(case.get('seed',[])));self.w(0x10002cc,case.get('capacity',0))
  for i,v in enumerate(case.get('seed',[])):self.w(0x1020000+4*i,v)
  for i,(kind,mute) in enumerate(channels):
   a=0x1002000+0x200*i;self.w(0x1001000+4*i,a);self.w(a+0x16c,kind);self.w(a+0xe8,mute)
  self.u.reg_write(UC_ARM_REG_SP,0x1108000);self.u.reg_write(UC_ARM_REG_LR,0x1200000);self.u.reg_write(UC_ARM_REG_R0,0x1000000);self.u.reg_write(UC_ARM_REG_R1,0x1030000)
  self.u.emu_start(self.body['address'],0x1200004,count=100000)
  return {'input':case,'items':self.items if self.lane.endswith('03') else [self.r(0x1020000+4*i) for i in range(self.r(0x10002c8))], 'trace':self.trace,'writes':self.writes}
def generate():
 n=Native();cases=[n.execute({'count':count}) for count in [-2147483648,-1,0,1,2,3,4,5,6,8,12,16,32,64]]
 literals=[{'address':a,'text':n.string(a),'size':len(n.string(a).encode())+1,'sha256':hashlib.sha256(bytes(n.u.mem_read(a,len(n.string(a).encode())+1))).hexdigest()} for a in [0x16dbf0,0x3567b0,0x16dc20,0x16dc30,0x16dc3c,0x16dc70,0x16dc78,0x15fb50]]
 return {'elf_sha256':SHA,'range':n.body,'literals':literals,'cases':cases,'boundary_scope':'Core binaries excluded: removeAll/appendString/rangeChanged record app calls; formatting modeled from verified literal and native integer operands. Actual CCL providers tested separately. Signed selector count -2^31 through 64 sampled; no hardware table inferred.'}
if __name__=='__main__':
 (ROOT/'uc-library/tests/recovery'/LANE/'fixtures.json').write_text(json.dumps(generate(),indent=2)+'\n')
