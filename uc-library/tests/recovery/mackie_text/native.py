"""Execute only original application instructions; intercept provider calls."""
import hashlib,json,struct,sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
MODE='text'
ELF=Path('/home/rs/projects/opencs/ai-line-analysis/rootfs/CS18_v13840/home/root/surface')
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
NAME='_ZN8Presonus22MackieControlComponent'+('14updateLedStateEii' if MODE=='led' else '17updateTextDisplayEiPKci')
def generate():
 raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 with ELF.open('rb') as f:
  e=ELFFile(f);s=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==NAME);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];code=raw[off:off+s['st_size']]
  info=dict(mangled=NAME,address=s['st_value'],size=s['st_size'],section=sec.name,section_index=s['st_shndx'],file_offset=off,sha256=hashlib.sha256(code).hexdigest())
 assert info['sha256']==('bd2cee2e8031a362a128bc579af810071fb34718aa9b5b2ffd8596f4141c72bf' if MODE=='led' else 'ead3053a9c71224115b93bd865519bc9a00ab5cb20358d7f44536e3b030e58c6')
 cases=[]
 for present in [0,1]:
  for state in [-2147483648,-127,-1,0,1,2,127,2147483647]:
   for unused in [-2147483648,0,1,2147483647]:
    for text in ['','A','channel_123']:
     u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(info['address']&~4095,4096);u.mem_write(info['address'],code)
     u.mem_map(0x11f000,4096);u.mem_map(0x400000,0x30000);u.mem_map(0x500000,0x10000);u.mem_map(0x600000,4096)
     def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
     w(0x401000,0x402000);w(0x402058,0x600004);w(0x402074,0x600004);u.mem_write(0x410000,text.encode()+b'\0')
     trace=[];pcs=[];writes=[]
     def hook(uc,a,size,_):
      regs=[uc.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]]
      if a==0x600000:uc.emu_stop();return
      if a==0x11f24c:
       assert regs[:2]==[0x400028,37 if MODE=='led' else 38];trace.append(['lookup',regs[1],present]);uc.reg_write(UC_ARM_REG_R0,0x401000 if present else 0)
      elif a==0x600004:
       assert regs[0]==0x401000 and regs[2]==0
       if MODE=='led':trace.append(['setValue',regs[1],regs[2]])
       else:assert regs[1]==0x410000;trace.append(['fromString',text,regs[2]])
      else:
       assert info['address']<=a<info['address']+info['size'],hex(a)
       pcs.append(a);return
      uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
     def write(uc,access,a,size,value,_):
      assert 0x500000<=a<0x510000,(a,size,value)
      writes.append([a,size,value])
     u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
     for r,v in [(UC_ARM_REG_R0,0x400000),(UC_ARM_REG_R1,37 if MODE=='led' else 38),(UC_ARM_REG_R2,state if MODE=='led' else 0x410000),(UC_ARM_REG_R3,unused),(UC_ARM_REG_SP,0x50f000),(UC_ARM_REG_LR,0x600000)]:u.reg_write(r,v&0xffffffff)
     u.emu_start(info['address'],0x600008,count=100);assert u.reg_read(UC_ARM_REG_PC)==0x600000
     cases.append(dict(input=[present,state,unused,text or '~'],trace=trace,stack_writes=writes,executed_pc_sha256=hashlib.sha256(struct.pack('<'+'I'*len(pcs),*pcs)).hexdigest()))
 return dict(elf_sha256=SHA,range=info,cases=cases,scope='Original app instructions only; lookup and virtual parameter calls intercepted. No Core guest execution, device IO or original ABI claim.')
if __name__=='__main__':
 data=generate();path=T/'fixtures.json'
 if '--verify' in sys.argv:assert data==json.loads(path.read_text())
 else:path.write_text(json.dumps(data,indent=2)+'\n')
 print(len(data['cases']),'native cases')
