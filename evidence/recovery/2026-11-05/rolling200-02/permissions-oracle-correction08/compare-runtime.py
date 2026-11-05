import io,json,struct,hashlib
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis');OUT=Path(__file__).resolve().parent
raw=(ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer').read_bytes();assert hashlib.sha256(raw).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07';elf=ELFFile(io.BytesIO(raw));symtab=elf.get_section_by_name('.symtab');ranges=[]
for name in ['__aeabi_fcmpge','__aeabi_cfrcmple','__aeabi_cfcmple','__cmpsf2']:
 s=symtab.get_symbol_by_name(name)[0];sec=elf.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];body=raw[off:off+s['st_size']];ranges.append(dict(original_mangled=name,address=s['st_value'],size=s['st_size'],section=sec.name,file_offset=off,sha256=hashlib.sha256(body).hexdigest()))
cases=[]
for bits in [0,0x80000000,0x3f800000,0xbf800000,0x7f800000,0xff800000,0x7fc00000,0xffc00000,1,0x80000001,0x7f7fffff,0xff7fffff]:
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x150000,0x10000);sec=elf.get_section_by_name('.text');start=0x157000;u.mem_write(start,sec.data()[start-sec['sh_addr']:start-sec['sh_addr']+0x1000]);u.mem_map(0x2000000,0x10000);stop=0x200ff00;pcs=[];writes=[]
 def code(u,a,n,data):
  if a==stop:u.emu_stop();return
  assert any(x['address']<=a<x['address']+x['size'] for x in ranges),hex(a)
  pcs.append(a)
 def write(u,access,a,n,v,data):
  assert 0x2000000<=a and a+n<0x200f000
  writes.append([a,n,v])
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 for reg,v in [(UC_ARM_REG_R0,bits),(UC_ARM_REG_R1,0),(UC_ARM_REG_SP,0x200e000),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,v)
 u.emu_start(0x157928,stop,count=500);assert u.reg_read(UC_ARM_REG_PC)==stop
 result=u.reg_read(UC_ARM_REG_R0);value=struct.unpack('<f',struct.pack('<I',bits))[0];model=int(value>=0.0);assert result==model,(bits,result,model);cases.append(dict(input_float_bits=hex(bits),rhs_bits='0x0',native_result=result,model_greater_equal=model,executed_pcs=pcs,writes=writes))
(OUT/'compare-runtime-proof.json').write_text(json.dumps(dict(version=1,producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_elf_sha256=hashlib.sha256(raw).hexdigest(),ranges=ranges,cases=cases,scope='Actual original compiler-runtime ARM comparison closure, not Core; private memory, code/write allowlist, no syscalls. Supports corrected explicit boundary model; no recovered C++ supplies expectations.'),indent=2)+'\n');print('Original __aeabi_fcmpge ARM executions:',len(cases))
