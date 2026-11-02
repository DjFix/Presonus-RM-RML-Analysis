"""Original ARM comparator executions, independently of portable C++.
No firmware Core implementation is executed. Full range checks use ELF sections.
"""
import hashlib,json,pathlib,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR
ROOT=pathlib.Path(__file__).resolve().parents[5]
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
def main():
 raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 out=[];ranges=[]
 with ELF.open('rb') as f:
  elf=ELFFile(f)
  for i in range(1,11):
   p=ROOT/f'temp/recovery-work/graph-live-trial-08/batch03/packets/trial08_mackie_{i}/native-context.json'
   ctx=json.loads(p.read_text()); ident=ctx['roots'][0];body=ctx['bodies'][ident];node=ctx['nodes'][ident]['metadata'];sec=elf.get_section(body['section_index']);offset=int(sec['sh_offset'])+body['address']-int(sec['sh_addr']);assert offset==body['file_offset'];data=raw[offset:offset+body['size']];assert hashlib.sha256(data).hexdigest()==body['bytes_sha256'];ranges.append(dict(packet=i,mangled=node['mangled'],address=body['address'],size=body['size'],section=body['section'],file_offset=offset,sha256=body['bytes_sha256']))
   if i not in (1,2):continue
   for a in [-2147483648,-129,-1,0,1,127,2147483647]:
    for b in [-2147483648,-129,-1,0,1,127,2147483647]:
     u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(body['address']&~4095,4096);u.mem_write(body['address'],data);u.mem_map(0x400000,0x10000);u.mem_write(0x400000,struct.pack('<iii',a,a,0));u.mem_write(0x400100,struct.pack('<iii',b,b,0));u.reg_write(UC_ARM_REG_R0,0x400000);u.reg_write(UC_ARM_REG_R1,0x400100);u.reg_write(UC_ARM_REG_SP,0x408000);u.reg_write(UC_ARM_REG_LR,0x40f000);u.emu_start(body['address'],0x40f000,count=100);r=u.reg_read(UC_ARM_REG_R0);r=r if r<2**31 else r-2**32;out.append(dict(method=i,a=a,b=b,result=r))
 target=pathlib.Path(__file__).parent/'comparator-fixtures.json';target.write_text(json.dumps({'elf_sha256':SHA,'ranges':ranges,'cases':out},indent=2)+'\n');print('Original ARM observations:',len(out),'verified ranges:',len(ranges))
if __name__=='__main__':main()
