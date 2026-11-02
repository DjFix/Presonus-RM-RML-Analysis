"""Execute original addMapping wrapper and expanded app callee; emulate libc qsort only."""
import json,pathlib,struct,hashlib
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from native_oracle import ROOT,ELF,SHA

def main():
 raw=ELF.read_bytes();x=json.loads((ROOT/'temp/recovery-work/graph-live-trial-08/expansions/mackie-47/native-context.json').read_text());b=next(iter(x['bodies'].values()));assert hashlib.sha256(raw[b['file_offset']:b['file_offset']+b['size']]).hexdigest()==b['bytes_sha256']
 cases=[]
 for count in [0,1,109,110,111]:
  for tag,note in [(-1,-1),(-1,12),(12,-1),(12,34),(0,0),(2147483647,2147483647)]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
   with ELF.open('rb') as f:
    for seg in ELFFile(f).iter_segments():
     if seg['p_type']=='PT_LOAD':
      start=int(seg['p_vaddr']);base=start&~4095;u.mem_map(base,((start+int(seg['p_memsz'])+4095)&~4095)-base);u.mem_write(start,seg.data())
   u.mem_map(0x400000,0x20000)
   def word(p,v):u.mem_write(p,struct.pack('<I',v&0xffffffff))
   for offset,base in [(4,0x402000),(0x534,0x404000),(0xa64,0x406000)]:word(0x400000+offset,base);word(0x400004+offset,count)
   initial=[[i*2,i*2,i] for i in range(count)]
   for base in [0x402000,0x404000]:
    for i,row in enumerate(initial):u.mem_write(base+i*12,struct.pack('<iii',*row))
   u.mem_write(0x406000,bytes([1])*count)
   u.reg_write(UC_ARM_REG_SP,0x418000);u.reg_write(UC_ARM_REG_LR,0x41f000);u.reg_write(UC_ARM_REG_R0,0x400000);u.reg_write(UC_ARM_REG_R1,tag&0xffffffff);u.reg_write(UC_ARM_REG_R2,note&0xffffffff)
   traces=[]
   def hook(u,address,size,user):
    if address!=0xaa44:return
    base=u.reg_read(UC_ARM_REG_R0);n=u.reg_read(UC_ARM_REG_R1);width=u.reg_read(UC_ARM_REG_R2);cmp=u.reg_read(UC_ARM_REG_R3);rows=[struct.unpack('<iii',u.mem_read(base+i*width,12)) for i in range(n)];rows.sort(key=lambda a:a[1 if cmp==0xc01a0 else 0]);
    for i,row in enumerate(rows):u.mem_write(base+i*width,struct.pack('<iii',*row))
    traces.append({'table':'midi' if base==0x404000 else 'tags','count':n,'width':width,'comparator':cmp});u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0xc0ab0,0x41f000,count=1000)
   result={}
   for name,offset,base in [('tags',4,0x402000),('midi',0x534,0x404000)]:
    n=struct.unpack('<I',u.mem_read(0x400004+offset,4))[0];result[name]=[list(struct.unpack('<iii',u.mem_read(base+i*12,12))) for i in range(n)]
   n=struct.unpack('<I',u.mem_read(0x400a68,4))[0];result['buttons']=list(u.mem_read(0x406000,n));cases.append({'initial_count':count,'tag':tag,'note':note,'result':result,'trace':traces})
 (pathlib.Path(__file__).parent/'mapping-fixtures.json').write_text(json.dumps({'elf_sha256':SHA,'callee_range':b,'cases':cases},indent=2)+'\n');print('Original mapping wrapper and callee',len(cases))
if __name__=='__main__':main()
