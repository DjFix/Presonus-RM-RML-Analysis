#!/usr/bin/env python3
"""Original app ARM oracle. Core is captured, actual supplemental empty app hook executes."""
import hashlib,io,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
T=Path(__file__).resolve().parent;TASK=T.name
RUN=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116');PACKET=RUN/'prepared-main/packets'/TASK
READS=json.loads((RUN/'SCOPED_READ_INPUTS-remaining18_phase03-real10_g02.json').read_text())
SUPPLEMENT=RUN/'expansions/presets-row-followon/row-selected'
def sha(b):return hashlib.sha256(b).hexdigest()
def u32(v):return v&0xffffffff
def signed(v):return v if v<0x80000000 else v-0x100000000
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def floating(v):return struct.unpack('<f',struct.pack('<I',v))[0]
def generate():
 target=json.loads((PACKET/'request.json').read_text())['targets'][0];raw=Path(READS['rootfs/CS18_v13840/home/root/surface']['frozen_read_path']).read_bytes();assert sha(raw)==target['original_elf_sha256']
 elf=ELFFile(io.BytesIO(raw));syms=list(elf.get_section_by_name('.symtab').iter_symbols())
 def get(addr,size):
  sec=next(s for s in elf.iter_sections() if s['sh_type']!='SHT_NOBITS' and s['sh_addr']<=addr and addr+size<=s['sh_addr']+s['sh_size']);off=sec['sh_offset']+addr-sec['sh_addr'];return raw[off:off+size],sec.name,off
 sym=next(s for s in syms if s.name==target['mangled']);assert (sym['st_value'],sym['st_size'],sym['st_shndx'])==(target['address'],target['size'],target['section'])
 start=target['address'];size=target['size'];body,section,offset=get(start,size);assert sha(body)=='072d0d6320f41991a2ec298ed9981d15923e71ec4297897999cb3fadf5e46b3f'
 hook,_,hookoff=get(0xb3ffc,16);assert sha(hook)=='60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad'
 vtable,_,vtableoff=get(0x1e9058,216);assert sha(vtable)=='9a67c70ead2dbfbca35a1c49af1bc3f61c0554797001c689e966cd296f3feb7f'
 for slot,addr in [(0x4c,0xb3ffc),(0x54,0xb4368),(0x58,0xb431c)]:assert struct.unpack_from('<I',vtable,slot+8)[0]==addr
 inputs=[]
 tags=[-2147483648,-4,-2,-1,0,1,2,4,7,10,998,999,1000,1001,1002,1003,1004,1005,1006,2147483647]
 for tag in tags:
  for msg,value in [(2,-1.),(2,0.),(2,.5),(2,1.),(2,2.),(1,1.),(3,1.)]:inputs.append([tag,msg,value,3,7,1,1])
 for tag in [1,4,7,10]:
  for rows,mask,inc in [(0,0,0),(1,1,1),(3,5,1),(3,7,0)]:inputs.append([tag,2,1.,rows,mask,inc,0])
 rowsout=[]
 for self in [0x2000100,0x2000500]:
  for tag,msg,value,nrows,mask,included,storable in inputs:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
   for base in [0xb3000,0xb4000,0x110000,0x11c000,0x11f000,0x187000,0x2000000,0x2001000,0x3000000,0x4000000,0x5000000]:u.mem_map(base,4096)
   u.mem_write(start,body);u.mem_write(0xb3ffc,hook)
   p=0x2000a00;info=0x2000b00;pvt=0x2000c00;pagevt=0x2000d00;table=0x2001000;sp=0x3000800;stop=0x4000000
   def put(a,v):u.mem_write(a,struct.pack('<I',u32(v)))
   def getword(a):return struct.unpack('<I',u.mem_read(a,4))[0]
   put(self,pagevt);put(self+0xd8,nrows);put(self+0xdc,20);put(self+0xe0,4)
   put(pagevt+0x4c,0xb3ffc);put(pagevt+0x54,0xb4368);put(pagevt+0x58,0xb431c)
   put(pvt+0x44,0x5000000);put(pvt+0x58,0x5000004)
   parameter_tags={};values={};lookup={}
   def parameter(addr,tag,v,inf):
    put(addr,pvt);put(addr+12,inf);put(inf+4,tag);parameter_tags[addr]=tag;values[addr]=bits(v)
   for j in range(nrows):
    if mask&(1<<j):
     a=table+32*j;it=1+3*j;lookup[it]=a;parameter(a,it,value if tag==it and included else 1.,table+0x400+32*j)
   if included and tag in lookup:p=lookup[tag]
   else:parameter(p,tag,value,info)
   events=[];pcs=[];writes=[];calls=[];provider_writes=[]
   def ret(uc,v=None):
    if v is not None:uc.reg_write(UC_ARM_REG_R0,u32(v))
    uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   def code(uc,pc,l,data):
    if pc==stop:uc.emu_stop();return
    a=uc.reg_read(UC_ARM_REG_R0);b=uc.reg_read(UC_ARM_REG_R1);c=uc.reg_read(UC_ARM_REG_R2)
    if pc==0xb3ffc:events.append('row');calls.append(dict(address=pc,receiver=a));pcs.append(pc);return
    if pc in [0x11c87c,0x1877e0,0x187798,0x11f24c,0x5000000,0x5000004,0xb4588,0xb4368,0xb431c,0xb4658]:
     calls.append(dict(address=pc,r0=a,r1=b,r2=c))
     if pc==0x11c87c:ret(uc);return
     if pc==0x5000000:events.append('v'+str(parameter_tags[a]));ret(uc,values[a]);return
     if pc==0x5000004:events.append('s'+str(parameter_tags[a]));assert b==0 and c==0;values[a]=b;ret(uc);return
     if pc==0x1877e0:ret(uc,int(floating(a)>floating(b)));return
     if pc==0x187798:ret(uc,int(floating(a)<floating(b)));return
     if pc==0x11f24c:assert a==self+0x28;ret(uc,lookup.get(signed(b),0));return
     if pc==0xb4588:
      # Interior offset domain: observe selected delta; canonical helper runs
      # separately in C++ and no clamp/division boundary is reached here.
      val=u32(getword(self+0xdc)+b);put(self+0xdc,val);provider_writes.append([self+0xdc,4,val]);ret(uc);return
     events.append({0xb4368:'recall',0xb431c:'remove',0xb4658:'prompt'}[pc]);ret(uc);return
    assert start<=pc<start+size or 0xb3ffc<=pc<0xb400c,hex(pc)
    pcs.append(pc)
   def write(uc,access,addr,l,val,data):
    assert sp-80<=addr<sp or self<=addr<self+0x200
    writes.append([addr,l,val&((1<<(8*l))-1)])
   u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write);u.reg_write(UC_ARM_REG_CPSR,0x10);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R0,self);u.reg_write(UC_ARM_REG_R1,p);u.reg_write(UC_ARM_REG_R2,u32(msg))
   before=bytes(u.mem_read(0x2000000,8192));u.emu_start(start,stop+4,count=1000);assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==sp
   final=bytes(u.mem_read(0x2000000,8192));expected_memory=bytearray(before)
   for addr,l,val in writes+provider_writes:
    if 0x2000000<=addr<0x2002000:expected_memory[addr-0x2000000:addr-0x2000000+l]=val.to_bytes(l,'little')
   assert final==bytes(expected_memory)
   result=[signed(getword(self+0xe0)),signed(getword(self+0xdc)),values[p]]+[values[lookup[1+3*j]] if 1+3*j in lookup else 0xffffffff for j in range(nrows)]
   expected=' '.join(map(str,result))+' | '+','.join(events)
   rowsout.append(dict(argv=[str(tag),str(msg),str(value),str(nrows),str(mask),str(included),str(storable)],self=self,expected=expected,pcs=pcs,writes=writes,provider_boundary_writes=provider_writes,calls=calls,stack_restored=True,unmodified_memory_preserved=True))
 return dict(task_id=TASK,target=target,elf_sha256=sha(raw),section=section,file_offset=offset,range_sha256=sha(body),producer_sha256=sha(Path(__file__).read_bytes()),unicorn_version=unicorn.__version__,cases=rowsout,supplement=dict(path=str(SUPPLEMENT),root_observation_sha256=sha((SUPPLEMENT/'ROOT_OBSERVATION.json').read_bytes()),row_hook=dict(address=0xb3ffc,size=16,file_offset=hookoff,sha256=sha(hook)),vtable=dict(address=0x1e9058,size=216,file_offset=vtableoff,sha256=sha(vtable))),domain='312 normal-path cases: two page addresses; finite float thresholds; literal message2 and other messages; six commands; negative/out-of-range tags; 0/1/3 rows; missing rows and external parameter identity; full app receiver/stack writes and call arguments. Exact supplemental rowSelected instructions execute.',limitations='Core Component, ParamList, parameter accessors, runtime float comparisons and existing canonical app actions are explicit test boundaries. Actual pinned providers and existing app helpers execute separately in host replay. Offset helper domain stays strictly inside clamp bounds; positive rows for offset operations; no null/dangling input, EH, hardware or original ABI claims. Numeric message2 app behavior is retained even though current CCL kChanged is3.')
if __name__=='__main__':print(json.dumps(generate(),indent=2))
