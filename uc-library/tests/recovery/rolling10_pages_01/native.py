"""Run original address-returning ARM body on independently initialized text."""
import hashlib,json
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ROOT=Path(__file__).resolve().parents[4];TASK=Path(__file__).parent.name
PACKET=ROOT/'temp/recovery-work/rolling10x10-20261114/prepared05/packets'/TASK
READS=json.loads((ROOT/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-rolling10_pages.json').read_text())
def generate():
 t=json.loads((PACKET/'request.json').read_text())['targets'][0]
 elfpath=Path(READS['rootfs/CS18_v13840/home/root/surface']['frozen_read_path'])
 assert hashlib.sha256(elfpath.read_bytes()).hexdigest()==t['original_elf_sha256']
 with elfpath.open('rb') as f:
  e=ELFFile(f);s=e.get_section(12);sym=e.get_section_by_name('.symtab').get_symbol_by_name(t['mangled'])[0]
  assert (sym['st_value'],sym['st_size'],sym['st_shndx'])==(t['address'],t['size'],12)
  offset=s['sh_offset']+t['address']-s['sh_addr'];f.seek(offset);body=f.read(t['size'])
  constructor_ranges=[]
  for variant,address,digest in [('C1',0x6820c,'65e20ec1cf8b049da615bcae003a207bbec948326ec8fb420a46b315dc57bff3'),('C2',0x6826c,'1c2691d428d80ff128981fc02501a5063dc7783acdb9e4fb0ecceaf483745914')]:
   name='_ZN8Presonus13PageComponent'+variant+'EPKcS2_i';cs=e.get_section_by_name('.symtab').get_symbol_by_name(name)[0]
   assert (cs['st_value'],cs['st_size'],cs['st_shndx'])==(address,96,12)
   coff=s['sh_offset']+address-s['sh_addr'];f.seek(coff);cb=f.read(96);assert hashlib.sha256(cb).hexdigest()==digest
   # Static non-Core constructor identity only. Never execute binary Core.
   assert cb[72:76]==bytes.fromhex('0610a0e1') and cb[76:80]==bytes.fromhex('900084e2')
   import struct
   instruction=struct.unpack_from('<I',cb,80)[0];imm=instruction&0xffffff;imm=imm-(1<<24) if imm&(1<<23) else imm
   assert instruction>>24==0xeb and address+80+8+imm*4==0x24268
   provider=e.get_section_by_name('.symtab').get_symbol_by_name('_ZN4Core13CStringBufferILi32EEC1EPKc')[0]
   assert provider['st_value']==0x24268
   constructor_ranges.append(dict(mangled=name,address=address,size=96,section=12,file_offset=coff,sha256=digest,buffer_offset=144,buffer_provider_mangled='_ZN4Core13CStringBufferILi32EEC1EPKc',provider_target=0x24268,scope='Static application constructor call binding only; no constructor or Core binary execution'))
 texts=[b'',b'x',b'MainMixer',b'name with spaces',bytes.fromhex('d0bcd0b8d0bad188d0b5d180'),b'a'*30,b'z'*31]
 cases=[]
 for obj in (0x1000000,0x1000200):
  for text in texts:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);address=t['address'];u.mem_map(address&~4095,4096);u.mem_write(address,body);u.mem_map(0x1000000,4096);u.mem_map(0x2000000,65536)
   state=bytes([0xa5])*144+text+b'\0'+bytes([0x5a])*(367-len(text));u.mem_write(obj,state)
   u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,0x2008000);u.reg_write(UC_ARM_REG_LR,0x1000800)
   pcs=[];writes=[];u.hook_add(UC_HOOK_CODE,lambda uc,a,n,x:pcs.append(a));u.hook_add(UC_HOOK_MEM_WRITE,lambda uc,k,a,n,v,x:writes.append([a,n,v]))
   u.emu_start(address,0x1000800,count=12)
   assert u.reg_read(UC_ARM_REG_PC)==0x1000800;result=u.reg_read(UC_ARM_REG_R0)
   assert bytes(u.mem_read(obj,len(state)))==state
   assert all(address<=pc<address+20 for pc in pcs);assert all(0x2007ff0<=a<0x2008000 for a,n,v in writes)
   observed=bytes(u.mem_read(result,len(text)+1));assert result==obj+144 and observed==text+b'\0'
   cases.append(dict(input_hex=text.hex(),object=obj,returned_offset=result-obj,observed_hex=observed[:-1].hex(),executed=pcs,stack_writes=writes,application_writes=[],external_calls=[]))
 return dict(constructor_ranges=constructor_ranges,elf_sha256=t['original_elf_sha256'],mangled=t['mangled'],address=t['address'],size=t['size'],section=12,file_offset=offset,range_sha256=hashlib.sha256(body).hexdigest(),unicorn_version=unicorn.__version__,cases=cases,domain='14 ARM cases: two valid caller-owned objects, empty/ASCII/spaces/UTF-8/30/31-byte zero-terminated text; borrowed embedded-address return, object immutability, stack-only writes, no external execution. Portable storage is CCL CString32, supported by C1/C2 calls to actual CStringBuffer<32> at +0x90; full original class layout remains unverified.')
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
