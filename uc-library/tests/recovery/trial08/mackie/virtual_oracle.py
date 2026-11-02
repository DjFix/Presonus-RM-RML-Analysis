"""Observe original ARM virtual-call boundaries, including pre-call state writes."""
import json,pathlib,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from native_oracle import ROOT,ELF,SHA

def execute(method,arg,state,bits):
 ctx=json.loads((ROOT/f'temp/recovery-work/graph-live-trial-08/batch03/packets/trial08_mackie_{method}/native-context.json').read_text());body=ctx['bodies'][ctx['roots'][0]]
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 with ELF.open('rb') as f:
  for seg in ELFFile(f).iter_segments():
   if seg['p_type']=='PT_LOAD':
    start=int(seg['p_vaddr']);base=start&~4095;u.mem_map(base,((start+int(seg['p_memsz'])+4095)&~4095)-base);u.mem_write(start,seg.data())
 u.mem_map(0x400000,0x10000)
 def word(p,v):u.mem_write(p,struct.pack('<I',v&0xffffffff))
 word(0x400000,0x402000);word(0x400ae4,0x401000);word(0x401000,0x403000);word(0x402034,0x404000);word(0x403010,0x404010);word(0x40301c,0x40401c);word(0x400ae8,state)
 u.mem_write(0x400b68,b'0123456789X');u.mem_write(0x400b73,b'ABX');u.mem_write(0x400b76,bytes([state&255])*9)
 u.reg_write(UC_ARM_REG_SP,0x408000);u.reg_write(UC_ARM_REG_LR,0x40f000);u.reg_write(UC_ARM_REG_R0,0x400000);u.reg_write(UC_ARM_REG_R1,arg&0xffffffff);u.reg_write(UC_ARM_REG_R2,bits)
 trace=[]
 def hook(u,address,size,user):
  if address in (0x404000,0x404010,0x40401c):
   r1=u.reg_read(UC_ARM_REG_R1);r2=u.reg_read(UC_ARM_REG_R2)
   if address==0x404000:trace.append({'slot':52,'state':struct.unpack('<I',u.mem_read(0x400ae8,4))[0]})
   elif address==0x404010:trace.append({'slot':16,'tag':r1,'float_bits':r2})
   else:
    val=bytes(u.mem_read(r2,32)).split(b'\0',1)[0].decode('ascii');trace.append({'slot':28,'tag':r1,'text':val})
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(body['address'],0x40f000,count=500)
 return {'method':method,'arg':arg,'state':state,'float_bits':bits,'trace':trace,'connection':struct.unpack('<I',u.mem_read(0x400ae8,4))[0],'assignment':bytes(u.mem_read(0x400b73,3)).hex(),'timecode':bytes(u.mem_read(0x400b68,11)).hex()}
def main():
 cases=[]
 for method in [4,5,6]:
  for state in [0,1,4,255]:cases.append(execute(method,0,state,0))
 for arg in [-2147483648,-1,0,1,7,8,9,2147483647]:
  for state in [0,1,255]:
   for bits in [0,0x3f000000,0x7fc01234,0x80000000]:cases.append(execute(7,arg,state,bits))
 (pathlib.Path(__file__).parent/'virtual-fixtures.json').write_text(json.dumps({'elf_sha256':SHA,'cases':cases},indent=2)+'\n');print('Virtual boundary observations',len(cases))
if __name__=='__main__':main()
