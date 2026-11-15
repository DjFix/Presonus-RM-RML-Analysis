#!/usr/bin/env python3
import argparse,hashlib,io,json,random,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import *
from unicorn.arm_const import *
T=Path(__file__).resolve().parent;R=T.parents[3];TASK=T.name;PACKET=R/'temp/recovery-work/rolling10x10-20261114/prepared06/packets'/TASK
READ=R/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared06-rolling10_fx.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def generate(exe=None):
 target=json.loads((PACKET/'request.json').read_text())['targets'][0];raw=Path(json.loads(READ.read_text())['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path']).read_bytes();assert sha(raw)==target['original_elf_sha256'];elf=ELFFile(io.BytesIO(raw));syms=list(elf.get_section_by_name('.symtab').iter_symbols())
 def get(a,n):
  s=next(s for s in elf.iter_sections() if s['sh_type']!='SHT_NOBITS' and s['sh_addr']<=a<a+n<=s['sh_addr']+s['sh_size']);o=s['sh_offset']+a-s['sh_addr'];return raw[o:o+n],s.name,o
 start,size=target['address'],target['size'];body,section,offset=get(start,size);sym=next(s for s in syms if s.name==target['mangled']);assert(sym['st_value'],sym['st_size'],sym['st_shndx'])==(start,size,target['section'])
 tables=[]
 for addr,n in [(0x33ab64,104),(0x33abcc,64),(0x33ac0c,104),(0x33ac74,64),(0x33acb4,104),(0x33ad1c,64)]:
  b,sec,off=get(addr,n);tables.append(dict(address=addr,size=n,section=sec,file_offset=off,sha256=sha(b),values=list(struct.unpack('<'+'i'*(n//4),b)),original_symbols=[s.name for s in syms if s['st_value']==addr and s['st_size']==n]))
 tablemap={t['address']:t['values'] for t in tables};rows=[];rng=random.Random(614)
 groups=[-2147483648,-1,0,1,2,3,4,2147483647]+[rng.randint(-2147483648,2147483647) for _ in range(32)]
 for group in groups:
  for alias in [0,1]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
   for a in [start&~4095,0x2000000,0x3000000,0x4000000]:u.mem_map(a,4096)
   u.mem_write(start,body);u.mem_write(0x2000000,b'\xa5'*4096);self=0x2000800;a=0x2000100;b=a if alias else a+4;count=0x2000110;sp=0x3000800;stop=0x4000000
   def w(addr,v):u.mem_write(addr,struct.pack('<I',v&0xffffffff))
   def rd(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
   w(a,0x2000500);w(b,0x2000600);w(count,77);w(sp,count);before=bytes(u.mem_read(0x2000000,4096));pcs=[];writes=[]
   def code(uc,pc,n,d):
    if pc==stop:uc.emu_stop();return
    assert start<=pc<start+size;pcs.append(pc)
   def write(uc,access,addr,n,v,d):
    assert sp-16<=addr<addr+n<=sp or (addr in [a,b,count] and n==4);writes.append([addr,n,v&((1<<(8*n))-1)])
   u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write);u.reg_write(UC_ARM_REG_CPSR,0x10);u.reg_write(UC_ARM_REG_R0,self);u.reg_write(UC_ARM_REG_R1,group&0xffffffff);u.reg_write(UC_ARM_REG_R2,a);u.reg_write(UC_ARM_REG_R3,b);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop);u.emu_start(start,stop+4,count=100);assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==sp
   after=bytes(u.mem_read(0x2000000,4096));expected=bytearray(before)
   for addr in [a,b,count]:expected[addr-0x2000000:addr-0x2000000+4]=after[addr-0x2000000:addr-0x2000000+4]
   assert after==bytes(expected)
   first,second=rd(a),rd(b);rows.append(dict(input=[group,alias],first_address=first,second_address=second,first_values=tablemap.get(first),second_values=tablemap.get(second),count=rd(count),r0=u.reg_read(UC_ARM_REG_R0),pcs=pcs,writes=writes,stack_restored=True,other_memory_unchanged=True))
 return dict(task_id=TASK,elf_sha256=sha(raw),mangled=target['mangled'],address=start,size=size,section=section,file_offset=offset,range_sha256=sha(body),tables=tables,cases=rows,producer_sha256=sha(Path(__file__).read_bytes()),unicorn_version=unicorn.__version__,limitations='All six complete original integer table ranges including sentinel verified; native count output is independent and must not be interpreted as a safe extent for either array. Same-typed pointer output aliasing included; count-reference type punning excluded. Return declaration unresolved; portable void choice.')
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(generate(),indent=2)+'\n')
if __name__=='__main__':main()
