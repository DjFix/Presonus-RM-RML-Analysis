#!/usr/bin/env python3
"""Execute five sealed ARM ranges; hooks represent unresolved app/virtual boundaries."""
import hashlib,json,struct,sys,random,datetime,time
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
OUT=Path('uc-library/candidates/graph-live-trial-05-groups')
ELF=Path('rootfs/CS18_v13840/home/root/surface')
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
TARGETS=[(0x92ee4,28,'bde1bb3f8d8d4cd325a16e5f2e22fdf4cc9dfa6802509b5d4b16428966856e87'),(0x91de8,44,'42fa9eb3976696242f20bbac678781a7ec208d5a37e92a452e48ed576fa22b20'),(0x92e94,80,'5e3529ce46bcfe0d9b1eddc9c5deda95b8541726933933ce3b276fddfe5c7b29'),(0x92854,132,'49604c79d873774d5c52e06ebe218efbb0b964c1483214f7a0aa70f1507bbb75'),(0x92140,140,'e92fd446ed97f9bf4a542068f7f9e24d5fc16bb1f3d8870cbb792b63288e705f')]
def signed(x):return (x+2**31)%2**32-2**31
def main():
 raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 ranges=[]
 with ELF.open('rb') as f:
  elf=ELFFile(f); sec=elf.get_section(12);assert sec.name=='.text'
  segments=[(s['p_vaddr'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
  for address,size,sha in TARGETS:
   offset=address-sec['sh_addr']+sec['sh_offset']; assert hashlib.sha256(raw[offset:offset+size]).hexdigest()==sha
   ranges.append(dict(address=address,size=size,sha256=sha,file_offset=offset,section='.text',section_index=12))
 def run(c):
  op,a,b,old,arg,selection,observed,n=c
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x280000)
  for address,data in segments:u.mem_write(address,data)
  u.mem_map(0x300000,0x300000);u.mem_map(0x700000,0x10000)
  obj=0x300000; stop=0x710000;trace=[];writes=[]
  def put(addr,v):u.mem_write(addr,struct.pack('<I',v&0xffffffff))
  def get(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
  put(obj+0xd4,old);put(obj+0xd8,selection);put(obj+0x10c,a);put(obj+0x120,b);put(obj+0x134,observed)
  put(obj+0x108,0x420000);put(obj+0x11c,0x430000);put(obj+0xe0,0x440000);put(obj+0xe4,n)
  for i in range(64):put(0x420000+4*i,0x400000+4*i);put(0x430000+4*i,0x410000+4*i)
  for i in range(n):put(0x440000+4*i,0x500000+0x100*i);put(0x500000+0x100*i,0x450000)
  put(0x450000+0x58,0x460000)
  # Core pointer error cells are SHT_NOBITS in this ELF, initialized to null.
  assert get(2451468)==0 and get(2533800)==0
  def hook(uc,pc,size,_):
   if pc==stop:uc.emu_stop();return
   if pc==0x92c80:trace.extend([1,signed(get(obj+0xd4))]);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   elif pc==0x924f4:trace.extend([2,signed(get(obj+0xd8))]);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   elif pc==0x92048:trace.extend([3,uc.reg_read(UC_ARM_REG_R1),get(obj+0x134)]);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   elif pc==0x460000:
    trace.extend([4,uc.reg_read(UC_ARM_REG_R0),signed(uc.reg_read(UC_ARM_REG_R1)),uc.reg_read(UC_ARM_REG_R2)])
    uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   elif not(any(address<=pc<address+size for address,size,_sha in TARGETS)):
    raise RuntimeError('Unexpected native PC '+hex(pc))
  def write(uc,access,addr,size,value,_):
   if obj<=addr<obj+0x138:writes.append([addr-obj,size,value&((1<<(size*8))-1)])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
  u.reg_write(UC_ARM_REG_SP,0x708000);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,arg&0xffffffff)
  u.emu_start(TARGETS[op-1][0],stop,count=2000)
  assert u.reg_read(UC_ARM_REG_PC)==stop
  result=signed(u.reg_read(UC_ARM_REG_R0)) if op==2 else 0
  out=[result,signed(get(obj+0xd4)),signed(get(obj+0xd8)),get(obj+0x134),len(trace)]+trace
  return {'input':c,'output':out,'object_writes':writes}
 cases=[]
 # Exhaustive small nonnegative count pairs + signed arithmetic extremes.
 for a in range(21):
  for b in range(21):cases.append([2,a,b,0,0,-1,0,0])
 for a,b in [(0,0),(4,4),(5,6),(10,20),(0,64),(0x7fffffff,0x7fffffff),(-1,0),(0x7fffffff,8)]:
  for old in [0,1,2,8,-1,0x7fffffff,-0x80000000]:
   for arg in [-0x80000000,-17,-1,0,1,2,3,7,8,11,63,0x7fffffff]:
    for op in [1,3]:cases.append([op,a,b,old,arg,-1,0,0])
 for a,b in [(0,0),(1,0),(0,1),(3,4),(5,6)]:
  for sel in [-5,-1,0,1,2,3,4,6,7,10,11,99,0x7fffffff]:
   for observed in [0,0x400000,0x410000]:cases.append([5,a,b,0,0,sel,observed,0])
 for n in range(17):
  for sel in [-1,0,8]:cases.append([4,3,4,8,0,sel,0x400000,n])
 records=[]; timings={}
 for op in range(1,6):
  start=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic()
  group=[c for c in cases if c[0]==op]
  records.extend(run(c) for c in group)
  timings[str(op)]={"phase":"native_execution","start_utc":start,"end_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"duration_seconds":time.monotonic()-clock,"case_count":len(group)}
 # Producer records are observations, not expected-value computations.
 proof={'elf_sha256':SHA,'elf_path':str(ELF),'ranges':ranges,'unicorn_version':unicorn.__version__,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boundary_hooks':{'0x92c80':'refreshList capture only','0x924f4':'doselect capture only','0x92048':'observeGroup capture only','0x460000':'virtual slot 0x58 capture only'},'assumptions':['stable parameter/group arrays','valid parameter pointers and vtables','no boundary callbacks mutate state','null NOBITS error cells'],'cases':records,'per_target_timing':timings}
 OUT.joinpath('fixtures.json').write_text(json.dumps(proof,indent=2)+'\n')
 print('native cases',len(records))
if __name__=='__main__':main()
