"""Original ARM only; bounded NUL strings and declared libc semantic stubs."""
import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ELF=Path('rootfs/CS18_v13840/home/root/surface')
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
NAME='_ZN8Presonus7Surface20SurfaceRootComponent17isMappableControlEPKc'
TRANSPORT='_ZN8Presonus7Surface20SurfaceRootComponent18isTransportControlEPKc'
def inputs():
 out=[None,'','unrelated','t','transport','mod','mapping','fx_mix','strip_mix']
 for token in ['transport_','mod_','fx_mixselect','strip_mixselect','mapping_','main_mix','fx_tap','quick_recall','marker']:
  out += [token,token+'x',token+'_suffix','x'+token,token.upper(),token[:-1],token+'x'*4096,'x'*4096+token]
 out += ['transport_mod_mapping_','\u00ffmarker','marker\u00ff']
 return list(dict.fromkeys(out))
def generate():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 with ELF.open('rb') as f:
  elf=ELFFile(f);symbols={s.name:s for s in elf.get_section_by_name('.symtab').iter_symbols()};targets=[symbols[NAME],symbols[TRANSPORT]]
  segments=[(s['p_vaddr'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
  ranges=[]
  for s in targets:
   sec=elf.get_section(s['st_shndx']);offset=sec['sh_offset']+s['st_value']-sec['sh_addr'];ranges.append(dict(mangled=s.name,address=s['st_value'],size=s['st_size'],section=sec.name,section_index=s['st_shndx'],file_offset=offset,sha256=hashlib.sha256(data[offset:offset+s['st_size']]).hexdigest()))
 assert ranges[0]['address']==713836 and ranges[0]['size']==484 and ranges[0]['sha256']=='f0d563f2238aaa42819b051c2a27f40078d01dc3c91e968ca853922ef8819d6a'
 cases=[]
 for value in inputs():
  observations=[]
  for target in ranges:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
   for address,body in segments:u.mem_write(address,body)
   if value is not None:u.mem_write(0x500000,value.encode('latin1')+b'\0')
   trace=[];sites=[];writes=[]
   def string(p):
    assert p!=0
    return bytes(u.mem_read(p,8192)).split(b'\0')[0]
   def hook(u,a,size,user):
    if a==0xf00000:u.emu_stop();return
    if target['address']<=a<target['address']+target['size']:sites.append(a);return
    x,y=[u.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1]]
    left,right=string(x),string(y)
    if a==0xae7c:
     i=left.find(right);ret=x+i if i>=0 else 0;trace.append(['strstr',right.decode('latin1'),i])
    elif a==0xb0f8:
     ret=next((a-b for a,b in zip(left+b'\0',right+b'\0') if a!=b),0);trace.append(['strcmp',right.decode('latin1'),ret])
    elif a==0xac90:
     raise RuntimeError('unexpected provider')
    else:raise RuntimeError(hex(a))
    u.reg_write(UC_ARM_REG_R0,ret&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   def write(u,access,a,size,value,user):writes.append([a,size,value])
   u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
   for reg,val in [(UC_ARM_REG_R0,0x400000),(UC_ARM_REG_R1,0 if value is None else 0x500000),(UC_ARM_REG_SP,0x8ff000),(UC_ARM_REG_LR,0xf00000)]:u.reg_write(reg,val)
   u.emu_start(target['address'],0xf00000,count=10000);assert u.reg_read(UC_ARM_REG_PC)==0xf00000
   assert all(0x8fe000<=w[0]<0x8ff000 for w in writes),writes
   observations.append(dict(result=u.reg_read(UC_ARM_REG_R0),trace=trace,instructions=len(sites),sites=sorted(set(sites)),stack_writes=writes))
  cases.append(dict(input=value,expected=[o['result'] for o in observations],native=observations))
 return dict(elf_sha256=SHA,ranges=ranges,cases=cases,stubs='strstr first byte occurrence; strcmp unsigned-byte difference; no host passthrough; valid NUL strings only')
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
