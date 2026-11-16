#!/usr/bin/env python3
"""Independent original ARM execution, with named application/Core/RTTI boundaries.
Soft-float runtime instructions execute from the hash-identified firmware.
"""
import json,hashlib,struct,itertools,argparse
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
SHA="9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
SYMBOL="_ZN8Presonus5Mixer14InputComponent14auxLevelUpdateERNS_3Dsp18MultiParamPropertyE"
def bits(v):return struct.unpack("<I",struct.pack("<f",v))[0]
def cases():
 out=[]
 for n in (0,1,2,4):
  for mask in range(64):
   out.append(dict(n=n,talkback=bool(mask&1),global_mute=bool(mask&2),mute=1.0 if mask&4 else 0.0,self_link=bool(mask&8),linked_pan=bool(mask&16),parity=(mask>>5)&1,law=(0.0,0.5,1.0)[mask%3],base=0.75,prop_count=(0,58,59,60)[mask%4],aux=[dict(send=(0.0,0.25,0.8,1.0)[(mask+i)%4],post=bool((mask+i)&1),sub=bool((mask//2+i)&1),assigned=bool((mask//4+i)&1),linked=bool((mask//8+i)&1),slave=bool(i&1),pan=(0.0,0.25,0.5,1.0)[(mask//3+i)%4],width=(-1.0,0.0,0.5,1.0)[(mask+i)%4]) for i in range(n)]))
 return out

def produce(elf,evidence=None):
 raw=Path(elf).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 with open(elf,"rb") as f:
  e=ELFFile(f);sec=e.get_section(12);off=int(sec["sh_offset"])+0x42be8-int(sec["sh_addr"])
  assert any(s["st_value"]==0x42be8 and s["st_size"]==1724 and s["st_shndx"]==12 for s in e.get_section_by_name(".symtab").get_symbol_by_name(SYMBOL))
  seg=[(int(s["p_vaddr"]),s.data()) for s in e.iter_segments() if s["p_type"]=="PT_LOAD"]
 results=[];visited=set()
 for case in cases():
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
  for a,d in seg:u.mem_write(a,d)
  u.mem_map(0x800000,0x40000)
  obj=0x800100;mix=0x801000;prop=0x802000;arr=0x803000;vt=0x804000;auxbase=0x805000;params={};byaddr={};nextparam=0x80a000
  def word(a,v):u.mem_write(a,struct.pack("<I",v))
  def getword(a):return struct.unpack("<I",u.mem_read(a,4))[0]
  def param(tag,v):
   nonlocal nextparam
   a=nextparam;nextparam+=16;params[tag]=a;byaddr[a]=v;word(a,0x804400);return a
  for slot in (0x60,0x70,0x74):word(vt+slot,0x820000+slot)
  word(0x804400+0x44,0x820200)
  word(obj,vt);word(obj+0x174,mix);word(mix+0x174,case['n']);word(mix+0x170,arr)
  word(obj+0x164,bits(case['base']));word(obj+0x170,case['parity']);u.mem_write(obj+0x198,bytes([case['linked_pan']]))
  word(obj+0xe8,param(-1,case['mute']));word(4800088,bits(case['law']))
  for i in range(8):word(obj+0x19c+4*i,bits(0.125))
  for i,a in enumerate(case['aux']):
   aux=auxbase+0x200*i;word(arr+4*i,aux);word(aux+0x104,param(-10-i,float(a['linked'])));param(0xe0+i,a['send'])
  for i in range(2):
   a=case['aux'][min(2*i,len(case['aux'])-1)] if case['aux'] else dict(pan=0.5,width=0.)
   param(0xf0+i,a['pan']);param(0xf8+i,a['width'])
  param(19,0.25);param(20,-0.5)
  word(prop+0x1ec,case['prop_count'])
  for i in range(case['prop_count']):word(prop+12+8*i,1000+i);word(prop+16+8*i,bits(0.2))
  u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,prop);u.reg_write(UC_ARM_REG_SP,0x818000);u.reg_write(UC_ARM_REG_LR,0x830000)
  calls=[]
  def code(uc,address,size,_):
   if 0x42be8<=address<0x43294:visited.add(address)
   r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);ret=None;name=None
   if address==0xacf4:ret=obj if case['talkback'] else 0;name='dynamic_cast'
   elif address==0x119c4c:ret=params.get(r1,0);name='getParameterByTag'
   elif address==0x820200:ret=bits(byaddr[r0]);name='getValue'
   elif address in (0x820060,0x820070,0x820074):
    a=case['aux'][r1]; key={0x820060:'assigned',0x820070:'post',0x820074:'sub'}[address];ret=int(a[key]);name=key
   elif address==0x40180:ret=int(case['global_mute']);name='isGlobalAuxMute'
   elif address==0x823dc:ret=int(case['aux'][(r0-auxbase)//0x200]['slave']);name='isLinkSlave'
   elif address==0x823c0:ret=int(case['self_link']);name='isLinked'
   if ret is not None:
    calls.append([name,r0,r1,ret]);uc.reg_write(UC_ARM_REG_R0,ret);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,code);u.emu_start(0x42be8,0x830000,count=200000);assert u.reg_read(UC_ARM_REG_PC)==0x830000
  count=getword(prop+0x1ec);assert count<=60
  results.append(dict(input=case,cache=[getword(obj+0x19c+4*i) for i in range(8)],property_count=count,entries=[[getword(prop+12+8*i),getword(prop+16+8*i)] for i in range(count)],calls=calls))
 capture=dict(task_id='real10_g05_s03',original_elf_sha256=SHA,mangled=SYMBOL,address=0x42be8,size=1724,section=12,file_offset=off,range_sha256=hashlib.sha256(raw[off:off+1724]).hexdigest(),case_count=len(results),cases=results,visited_original_instruction_addresses=sorted(visited),producer_domain='Original ARM application and soft-float runtime executed; explicit Core parameter, application virtual/global/link and RTTI boundaries; host actual providers separately observed. Finite single-threaded input snapshot, no null required parameters, n=0/1/2/4, finite pan/send/law, property counts0/58/59/60; no original ABI/layout/hardware claim.')
 if evidence:Path(evidence).write_text(json.dumps(capture,indent=2)+'\n')
 for row in capture['cases']:row.pop('calls')
 capture.pop('visited_original_instruction_addresses')
 return capture
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_text(json.dumps(produce(a.elf),indent=2)+'\n')
