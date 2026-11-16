#!/usr/bin/env python3
"""Exact app ARM setMixer: vector resize is an explicitly captured provider boundary."""
import hashlib,io,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
T=Path(__file__).resolve().parent;TASK=T.name
RUN=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116');PACKET=RUN/'prepared-main/packets'/TASK
READS=json.loads((RUN/'READ_INPUTS-prepared-main-real10_g02.json').read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def generate():
 target=json.loads((PACKET/'request.json').read_text())['targets'][0];raw=Path(READS['rootfs/CS18_v13840/home/root/surface']['frozen_read_path']).read_bytes();assert sha(raw)==target['original_elf_sha256']
 elf=ELFFile(io.BytesIO(raw));section=elf.get_section(target['section']);sym=next(s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name==target['mangled']);assert (sym['st_value'],sym['st_size'],sym['st_shndx'])==(target['address'],target['size'],target['section'])
 start=target['address'];size=target['size'];offset=section['sh_offset']+start-section['sh_addr'];body=raw[offset:offset+size];assert section.name=='.text'
 rows=[]
 inputs=[(0,-1,0,1),(0,-1,0,0),(0,-1,5,0),(1,0,5,0),(3,0,5,0),(3,1,5,0),(3,2,5,0),(3,-1,5,0),(5,-1,5,0),(6,-1,10,0),(11,10,15,0),(5,-1,5,1)]
 for self in [0x2000100,0x2000500]:
  for n,dup,capacity,null in inputs:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
   for base in {start&~4095,0x5c000,0x2000000,0x3000000,0x4000000}:u.mem_map(base,4096)
   u.mem_write(start,body);mixer=0x2000900;array=0x2000a00;observer=self+0xcc;other=0x2000b00
   initial=bytes((j+71)%256 for j in range(4096));u.mem_write(0x2000000,initial)
   def put(addr,v):u.mem_write(addr,struct.pack('<I',v))
   def get(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
   put(mixer+0x10,array);put(mixer+0x14,n);put(mixer+0x18,capacity)
   for j in range(n):put(array+4*j,observer if j==dup else other)
   before=bytes(u.mem_read(0x2000000,4096));sp=0x3000800;stop=0x4000000;pcs=[];writes=[];calls=[]
   def code(uc,pc,l,data):
    if pc==stop:uc.emu_stop();return
    if pc==0x5cb04:
     calls.append(dict(address=pc,receiver_offset=uc.reg_read(UC_ARM_REG_R0)-mixer,requested=uc.reg_read(UC_ARM_REG_R1)))
     # Provider boundary model: successful capacity establishment only. Native
     # caller reloads count; actual pinned allocation is observed in host replay.
     put(mixer+0x18,20);uc.reg_write(UC_ARM_REG_R0,1);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
    assert start<=pc<start+size,hex(pc);pcs.append(pc)
   def write(uc,access,addr,l,value,data):
    assert sp-24<=addr<sp or 0x2000000<=addr<0x2001000
    writes.append([addr,l,value&((1<<(l*8))-1)])
   u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write);u.reg_write(UC_ARM_REG_CPSR,0x10);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R0,self);u.reg_write(UC_ARM_REG_R1,0 if null else mixer)
   u.emu_start(start,stop+4,count=200);assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==sp
   count=get(mixer+0x14);expected=[int(get(self+0xe4)==mixer),count]+[int(get(array+4*j)==observer) for j in range(count)]
   final=bytes(u.mem_read(0x2000000,4096));norm=bytearray(before)
   for addr,l,value in writes:
    if 0x2000000<=addr<0x2001000:norm[addr-0x2000000:addr-0x2000000+l]=value.to_bytes(l,'little')
   if calls:norm[mixer+0x18-0x2000000:mixer+0x1c-0x2000000]=struct.pack('<I',20)
   assert bytes(norm)==final
   rows.append(dict(self=self,argv=list(map(str,[n,dup,capacity,null])),expected=' '.join(map(str,expected)),pcs=pcs,writes=writes,calls=calls,unchanged_bytes_preserved=True,stack_restored=True))
 return dict(task_id=TASK,target=target,elf_sha256=sha(raw),section=section.name,file_offset=offset,range_sha256=sha(body),producer_sha256=sha(Path(__file__).read_bytes()),unicorn_version=unicorn.__version__,cases=rows,domain='Null/empty, first/middle/last duplicate, spare/full capacity, resize success and 2 receiver addresses; original caller memory/call effects captured.',limitations='Core resize body is captured boundary with successful capacity establishment. Actual pinned vector execution separately observed in C++. Allocation failure/EH, negative or inconsistent vector counts, dangling pointers and original layout/ABI excluded; source-port requires explicit borrowed typed binding.')
if __name__=='__main__':print(json.dumps(generate(),indent=2))
