"""Original ARM instructions are the oracle; external app calls are bounded hooks."""
import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[5]
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
def observe(packet,op,present,value):
 c=json.loads((packet/'context.json').read_text()); body=next(iter(c['native_context']['bodies'].values()))
 assert hashlib.sha256(ELF.read_bytes()).hexdigest()==SHA
 with ELF.open('rb') as f:
  elf=ELFFile(f); sec=elf.get_section(body['section_index']); off=sec['sh_offset']+body['address']-sec['sh_addr'];f.seek(off);data=f.read(body['size']);assert off==body['file_offset'];assert hashlib.sha256(data).hexdigest()==body['bytes_sha256']
  if op=='M':
   helper=json.loads((ROOT/'temp/recovery-work/ranked20-cycle01/expansions/w04_17_0/expansion.json').read_text())['body'];hs=elf.get_section(helper['section_index']);ho=hs['sh_offset']+helper['address']-hs['sh_addr'];f.seek(ho);assert ho==helper['file_offset'] and hashlib.sha256(f.read(helper['size'])).hexdigest()==helper['bytes_sha256']
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x400000)
  for s in elf.iter_segments():
   if s['p_type']=='PT_LOAD':u.mem_write(s['p_vaddr'],s.data())
 u.mem_map(0x400000,0x10000);u.mem_map(0x700000,0x10000)
 obj=0x400000;listptr=0x401000; doc=0x345678
 def word(a,v):u.mem_write(a,struct.pack('<I',v))
 word(obj+8,listptr if present else 0);word(listptr,0x402000);word(0x402004,0x403000)
 word(obj+0xb4,listptr);word(listptr+0x4c,doc if present else 0);word(obj+0xb0,0x402000);word(obj+0x2c,listptr if present else 0)
 before=bytes(u.mem_read(obj,0x10000));events=[]
 target={'L':0x546d0,'M':0x403000,'V':0x681d4}[op]
 def hook(uc,a,size,unused):
  if a==0x70f000:uc.emu_stop();return
  if a==target:
   events.append(op)
   if op=='L':assert uc.reg_read(UC_ARM_REG_R0)==0x402000 and uc.reg_read(UC_ARM_REG_R1)==doc
   if op=='M':assert uc.reg_read(UC_ARM_REG_R0)==listptr and uc.reg_read(UC_ARM_REG_R1)==34 and uc.reg_read(UC_ARM_REG_R2)==37
   if op=='V':assert uc.reg_read(UC_ARM_REG_R0)==listptr
   uc.reg_write(UC_ARM_REG_R0,value);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,0x70e000);u.reg_write(UC_ARM_REG_LR,0x70f000)
 u.emu_start(body['address'],0x70f004,count=200)
 assert u.reg_read(UC_ARM_REG_PC)==0x70f000
 assert bytes(u.mem_read(obj,0x10000))==before
 return {'result':u.reg_read(UC_ARM_REG_R0),'events':events,'memory_unchanged':True,'range':body}
if __name__=='__main__':
 import sys,unicorn
 cases=[]
 for n,op in [(16,'L'),(17,'M'),(21,'V')]:
  packet=ROOT/f'temp/recovery-work/ranked20-cycle01/batch02/packets/rank20c01_w04_{n:02}'
  vals=[0,1,0x7fffffff,0x80000000,0xffffffff] if op=='M' else [0,1]
  for present in [0,1]:
   for v in vals:
    cases.append({'packet':str(packet.relative_to(ROOT)),'op':op,'present':present,'value':v,**observe(packet,op,present,v)})
 Path(sys.argv[1]).write_text(json.dumps({'oracle':'original ELF ARM execution under Unicorn; external app calls hooked only','unicorn':unicorn.__version__,'cases':cases},indent=2)+'\n')
 print('native cases',len(cases))
