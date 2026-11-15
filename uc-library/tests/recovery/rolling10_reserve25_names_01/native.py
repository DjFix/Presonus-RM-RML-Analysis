import json,hashlib,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
C={'elf': '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared06/snapshot/rootfs/CS18_v13840/home/root/surface', 'sha': '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0', 'mangled': '_ZN8Presonus7Surface14CascadeHandlerC1ERNS0_20SurfaceRootComponentE', 'address': 503420, 'size': 100, 'page': False, 'call': 404156}

def observations():
 data=Path(C['elf']).read_bytes();assert hashlib.sha256(data).hexdigest()==C['sha']
 with open(C['elf'],'rb') as f:
  e=ELFFile(f);s=next(s for s in e.get_section_by_name('.symtab').get_symbol_by_name(C['mangled']) if s['st_value']==C['address'] and s['st_size']==C['size']);sec=e.get_section(s['st_shndx']);offset=sec['sh_offset']+C['address']-sec['sh_addr'];assert sec.name=='.text'
 code=data[offset:offset+C['size']];cases=[]
 if C['page']:
  with open(C['elf'],'rb') as f:
   e=ELFFile(f);sec=next(s for s in e.iter_sections() if s['sh_type']!='SHT_NOBITS' and s['sh_addr']<=0x1f2670<s['sh_addr']+s['sh_size']);literaloffset=sec['sh_offset']+0x1f2670-sec['sh_addr'];assert data[literaloffset:literaloffset+1]==b'\0'
 for pointer in ([0,0x201000] if C['page'] else [0x201000,0x201100]):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for a in set([C['address']&~4095,C['call']&~4095,0x200000,0x201000,0x202000,0x300000,0x400000,0x401000]):u.mem_map(a,4096)
  u.mem_write(C['address'],code);u.mem_write(0x200000,b'\xa5'*256)
  if C['page']:
   u.mem_write(0x2000cc,struct.pack('<I',pointer));u.mem_write(0x201000,struct.pack('<I',0x202000));u.mem_write(0x202074,struct.pack('<I',0x401000))
  for r,v in [(UC_ARM_REG_R0,0x200000),(UC_ARM_REG_R1,pointer),(UC_ARM_REG_SP,0x300f00),(UC_ARM_REG_LR,0x400000)]:u.reg_write(r,v)
  events=[]
  def hook(uc,pc,size,_):
   if pc==0x400000:uc.emu_stop();return
   if pc==C['call'] or pc==0x401000:
    events.append(dict(pc=pc,args=[uc.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]],memory=bytes(uc.mem_read(0x200000,256)).hex()))
    uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   assert C['address']<=pc<C['address']+C['size'],hex(pc)
  u.hook_add(UC_HOOK_CODE,hook);u.emu_start(C['address'],0,count=100)
  assert u.reg_read(UC_ARM_REG_PC)==0x400000
  if C['page']:
   assert events[0]['pc']==C['call'];assert len(events)==(2 if pointer else 1)
   if pointer:assert events[1]['args']==[pointer,0x1f2670,0]
  else:
   assert len(events)==1 and events[0]['args'][:2]==[0x20000c,0]
   words=struct.unpack('<8I',bytes(u.mem_read(0x200000,32)));assert words== (0x19e110,0x19e134,pointer,0x19abb8,0,0,0,5)
  cases.append(dict(pointer=pointer,events=events,return_pc=u.reg_read(UC_ARM_REG_PC)))
 result=dict(elf_sha256=C['sha'],address=C['address'],size=C['size'],file_offset=offset,section='.text',range_sha256=hashlib.sha256(code).hexdigest(),cases=cases,limitations='Source provider call boundaries only; no Core firmware executed. Captured app writes and argument order; provider effects require separate actual-source execution.')
 if C['page']:result['literal']=dict(address=0x1f2670,file_offset=literaloffset,size=1,hex='00',sha256=hashlib.sha256(b'\0').hexdigest())
 return result
if __name__=='__main__':print(json.dumps(observations(),indent=2))
