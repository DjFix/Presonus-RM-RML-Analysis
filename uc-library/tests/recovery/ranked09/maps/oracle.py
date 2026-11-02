"""Execute unchanged ARM ELF instructions and real floating helper bodies."""
import hashlib,json,struct,random
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ELF=Path('rootfs/CS18_v13840/home/root/surface')
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
def generate():
 assert hashlib.sha256(ELF.read_bytes()).hexdigest()==SHA
 with ELF.open('rb') as f:
  elf=ELFFile(f); segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']; sections=list(elf.iter_sections())
  ranges=[]
  data_section=next(s for s in sections if s['sh_addr']<=2371904<s['sh_addr']+s['sh_size']); default_offset=data_section['sh_offset']+2371904-data_section['sh_addr']; f.seek(default_offset); default_payload=f.read(24); assert hashlib.sha256(default_payload).hexdigest()=='8ebe2b8f0b5e43b751a357e29060839769d7b53f4b9ed712c87f05595f4428fb'
  for address,expected in [(488424,'e7dc2fb8ffb8df5f04e7db1eb8de87aaca2c03d29946b97a8b7db8f4e0d7388d'),(488012,'9fc91cb45d1b91fb05ea34fb1b3b5cd19db268d0edd7d6d1a6be9daaff679955')]:
   s=sections[12];offset=s['sh_offset']+address-s['sh_addr'];f.seek(offset);data=f.read(256);assert hashlib.sha256(data).hexdigest()==expected;ranges.append(dict(address=address,size=256,section=12,file_offset=offset,sha256=expected))
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 pages=set()
 for base,size,data in segments:
  for page in range(base&~4095,(base+size+4095)&~4095,4096):
   if page not in pages:u.mem_map(page,4096);pages.add(page)
  u.mem_write(base,data)
 u.mem_map(0x10000000,0x20000);u.mem_map(0x20000000,0x10000)
 trace=[];writes=[]
 def code(uc,addr,size,user):
  if addr in (0x186f94,0x186fac):trace.append(addr)
 def write(uc,access,addr,size,value,user):
  if not 0x20000000<=addr<0x20010000:writes.append([addr,size,value])
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 cases=[];rng=random.Random(907)
 for kind in ('signature','tempo'):
  for count in [-1,0,1,2,3,4,7,8,17]:
   positions=[float(i*i) for i in range(max(count,0))]
   for query in [-float('inf'),-3.,-0.,0.,.5,1.,3.,4.,8.,16.,100.,float('inf'),float('nan')]+[rng.uniform(0,300) for _ in range(8)]:
    records=bytearray()
    for i,value in enumerate(positions):
     record=bytearray(rng.randbytes(24));struct.pack_into('<d',record,0 if kind=='signature' else 16,value);records+=record
    u.mem_write(0x10000000,struct.pack('<III',0,0x10001000,count&0xffffffff));u.mem_write(0x10001000,bytes(records)+bytes(24));before=bytes(u.mem_read(0x10000000,0x1000+len(records)+24))
    lo,hi=struct.unpack('<II',struct.pack('<d',query));u.reg_write(UC_ARM_REG_R0,0x10000000);u.reg_write(UC_ARM_REG_R2,lo);u.reg_write(UC_ARM_REG_R3,hi);u.reg_write(UC_ARM_REG_SP,0x2000fff0);u.reg_write(UC_ARM_REG_LR,0x1001f000);trace.clear();writes.clear()
    u.emu_start(488424 if kind=='signature' else 488012,0x1001f000,count=100000)
    assert u.reg_read(UC_ARM_REG_PC)==0x1001f000
    result=u.reg_read(UC_ARM_REG_R0);index=-2 if result==2371904 else -1 if result==0 else (result-0x10001000)//24
    assert result in (0,2371904) or 0<=index<count
    assert before==bytes(u.mem_read(0x10000000,len(before))) and not writes
    payload=bytes(u.mem_read(result,24)).hex() if result else ''
    cases.append(dict(kind=kind,count=count,query=struct.pack('<d',query).hex(),records=records.hex(),index=index,payload=payload,helper_calls=trace.copy(),nonstack_writes=[]))
 return dict(default_data=dict(address=2371904,size=24,file_offset=default_offset,section=data_section.name,sha256=hashlib.sha256(default_payload).hexdigest(),payload=default_payload.hex()),elf_sha256=SHA,ranges=ranges,oracle='Unicorn original ARM instructions including native comparison helpers; no call stubs',cases=cases)
if __name__=='__main__':
 data=generate();Path(__file__).with_name('fixtures.json').write_text(json.dumps(data,indent=2)+'\n');print('native cases',len(data['cases']))
