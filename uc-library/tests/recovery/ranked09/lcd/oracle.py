"""Execute original stack instructions; record sentinel reads and all stack writes."""
import hashlib,json,struct,argparse
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[5]
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
THIS=0x400000;ITEMS=0x401000;STOP=0x600000;ERROR=2528048

def capture():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 ranges=[];cases=[]
 for target in (2,3):
  packet=ROOT/f'temp/recovery-work/ranked-trial-09-small01/batch02/packets/rank09_lcd_0{target}'
  c=json.loads((packet/'context.json').read_text());n=c['native_context'];b=n['bodies'][n['roots'][0]]
  code=data[b['file_offset']:b['file_offset']+b['size']];assert hashlib.sha256(code).hexdigest()==b['bytes_sha256']
  with ELF.open('rb') as f:
   e=ELFFile(f);s=e.get_section(b['section_index']);assert b['file_offset']==s['sh_offset']+b['address']-s['sh_addr']
   sentinel=[x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name=='_ZN4Core11ConstVectorIPN8Presonus13PageComponentEE5errorE'][0]
   assert sentinel['st_value']==ERROR;assert e.get_section(sentinel['st_shndx'])['sh_type']=='SHT_NOBITS'
  ranges.append(dict(target=target,address=b['address'],size=b['size'],file_offset=b['file_offset'],sha256=b['bytes_sha256'],section=b['section'],sentinel_storage='SHT_NOBITS zero-initialized before app execution'))
  for count in range(10):
   for arg in (0,0x510000,0x520000):
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x10000,0x600000)
    # Include original literal cells from the checked symbol ranges.
    u.mem_write(b['address'],code)
    w=lambda a,v:u.mem_write(a,struct.pack('<I',v))
    w(THIS+0xc4,ITEMS);w(THIS+0xc8,count);w(ERROR,0)
    initial=[0x500000+i*0x100 for i in range(10)]
    for i,v in enumerate(initial):w(ITEMS+4*i,v)
    reads=[];writes=[]
    def read(uc,access,a,size,value,user):
     if a==ERROR:reads.append([a,size,struct.unpack('<I',bytes(uc.mem_read(a,4)))[0]])
    def write(uc,access,a,size,value,user):
     if THIS<=a<ITEMS+40:writes.append([a,size,value])
    u.hook_add(UC_HOOK_MEM_READ,read);u.hook_add(UC_HOOK_MEM_WRITE,write)
    u.reg_write(UC_ARM_REG_R0,THIS);u.reg_write(UC_ARM_REG_R1,arg);u.reg_write(UC_ARM_REG_SP,0x608000);u.reg_write(UC_ARM_REG_LR,STOP)
    u.emu_start(b['address'],STOP,count=1000);assert u.reg_read(UC_ARM_REG_PC)==STOP
    r=lambda a:struct.unpack('<I',bytes(u.mem_read(a,4)))[0]
    cases.append(dict(target=target,count=count,arg=arg,initial=initial,observed=dict(count=r(THIS+0xc8),items=[r(ITEMS+4*i) for i in range(10)],result=r(THIS+0xc8) if target==3 else u.reg_read(UC_ARM_REG_R0),sentinel_reads=reads,writes=writes)))
 return dict(elf_sha256=SHA,range_checks=ranges,cases=cases,scope='Valid stack counts 0..9; zero-initialized native NOBITS sentinel, no runtime mutation; no Core instructions reconstructed.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out');p.add_argument('--verify');a=p.parse_args();result=capture()
 if a.verify:assert result==json.loads(Path(a.verify).read_text());print('60 original ARM stack executions verified')
 else:Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
