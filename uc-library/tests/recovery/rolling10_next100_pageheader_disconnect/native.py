import json,hashlib,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
C={'elf': '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared06/snapshot/rootfs/CS18_v13840/home/root/surface', 'sha': '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0', 'mangled': '_ZN8Presonus7Surface19PageHeaderComponent19disconnectMappablesEv', 'address': 580344, 'size': 68, 'page': True, 'call': 380408}

def observations():
 data=Path(C['elf']).read_bytes();assert hashlib.sha256(data).hexdigest()==C['sha']
 with open(C['elf'],'rb') as f:
  e=ELFFile(f);s=next(s for s in e.get_section_by_name('.symtab').get_symbol_by_name(C['mangled']) if s['st_value']==C['address'] and s['st_size']==C['size']);sec=e.get_section(s['st_shndx']);offset=sec['sh_offset']+C['address']-sec['sh_addr'];assert sec.name=='.text'
 code=data[offset:offset+C['size']];cases=[]
 # Original Core data/interface identity only: no Core instructions executed.
 with open(C['elf'],'rb') as f:
  e=ELFFile(f); table=next(s for s in e.get_section_by_name('.symtab').get_symbol_by_name('_ZTVN4Core8Portable11StringParamE') if s['st_value']==2117800 and s['st_size']==128)
  section=e.get_section(table['st_shndx']); voffset=section['sh_offset']+table['st_value']-section['sh_addr']; assert voffset==2085032
  vbytes=data[voffset:voffset+128]; assert hashlib.sha256(vbytes).hexdigest()=='8089de65fb03251a2e5755a165ac19520fd28f5ac41934711bfe00a4d9103832'
  target=struct.unpack_from('<I',vbytes,8+29*4)[0]; assert target==1184588
  method=next(s for s in e.get_section_by_name('.symtab').get_symbol_by_name('_ZN4Core8Portable11StringParam10fromStringEPKcb') if s['st_value']==target and s['st_size']==224)
  dispatch_identity=dict(vtable_address=2117800,vtable_size=128,section_index=table['st_shndx'],file_offset=voffset,vtable_sha256=hashlib.sha256(vbytes).hexdigest(),slot=29,address_point_bias=8,original_target=target,original_mangled=method.name,original_size=method['st_size'],application_site=580400,modeled_trampoline=0x401000,scope='Original ELF data/interface witness only; Core instructions not executed')

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
 result=dict(elf_sha256=C['sha'],address=C['address'],size=C['size'],file_offset=offset,section='.text',range_sha256=hashlib.sha256(code).hexdigest(),dispatch_identity=dispatch_identity,cases=cases,limitations='Source provider call boundaries only; no Core firmware executed. Captured app writes and argument order; provider effects require separate actual-source execution.')
 if C['page']:result['literal']=dict(address=0x1f2670,file_offset=literaloffset,size=1,hex='00',sha256=hashlib.sha256(b'\0').hexdigest())
 return result
if __name__=='__main__':print(json.dumps(observations(),indent=2))
