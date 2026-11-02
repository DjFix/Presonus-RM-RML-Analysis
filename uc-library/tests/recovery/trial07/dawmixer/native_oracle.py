#!/usr/bin/env python3
"""Offline original ARM target execution; Core and unresolved app calls are boundaries.
No pseudocode or reconstructed C++ participates in expected observations.
"""
import argparse, hashlib, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ELF = Path('rootfs/CS18_v13840/home/root/surface')
SHA = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
TARGETS = [0x7cb1c,0x7e724,0x7c984,0x7c220,0x7e658,0x7e510,0x7e55c,0x7dc10,0x7e624,0x7bf9c]
SIZES = [172,96,408,404,196,76,192,60,44,176]
SELF, CLIENT, MAPPING, CHANNEL, SEND, CUE, SLOT = [0x300000+i*0x10000 for i in range(7)]
PARAM_VT, MAP_VT = 0x400100,0x400200
ENABLED, VALUE, SET, MODIFIERS, MAPPARAM, MAPFOCUS = [0x401000+i*0x100 for i in range(6)]
STOP = 0x402000
SP = 0x91f000
REGS = [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def bits(v): return struct.unpack('<I',struct.pack('<f',v))[0]
def value(v): return struct.unpack('<f',struct.pack('<I',v))[0]
def run(x, segments):
 u=Uc(UC_ARCH_ARM, UC_MODE_ARM);u.mem_map(0x8000,0x280000);u.mem_map(SELF,0x70000);u.mem_map(0x400000,0x10000);u.mem_map(0x600000,0x10000);u.mem_map(0x900000,0x20000)
 for a,b in segments:u.mem_write(a,b)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def reg(i):return u.reg_read(REGS[i])
 def ret(v=0):u.reg_write(UC_ARM_REG_R0,v&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 ids={};ptrs={};values={};events=[];calls=[];writes=[];visited=set()
 def param(identity,tag,v=bits(.25)):
  p=0x600000+len(ids)*0x100;ids[p]=identity;ptrs[identity]=p;values[p]=v
  w(p,PARAM_VT);w(p+12,p+0x80);w(p+0x84,tag);return p
 for t in [1,2,3,6,8,9,11,12,14,15,18,1000]:param(10000+t,t,x[19] if t==18 else bits(.25))
 for t in [1,2,3]:param(20000+t,t)
 for t in range(4):param(30000+t,t)
 param(40018,18)
 arg=param(60000,x[11])
 for i in range(4):ptrs[50000+i]=0x620000+i*0x100;ids[ptrs[50000+i]]=50000+i
 w(SELF+4,0x370000);w(SELF+8,MAPPING if x[3] else 0);w(SELF+20,CLIENT if x[2] else 0)
 u.mem_write(SELF+0x70,bytes([x[14],x[15],x[12]]))
 groups=[0x380000+i*0x100 for i in range(4)]
 for off,g in zip([0x680,0x678,0x67c],groups[1:]):w(CLIENT+off,g)
 for folder in [SEND,CUE]:
  w(folder+0x58,folder+0x100);w(folder+0x5c,x[8])
  for i in range(8):w(folder+0x100+i*4,SLOT if x[9] else 0)
 w(MAPPING,MAP_VT)
 for off,target in [(0,MODIFIERS),(16,MAPPARAM),(32,MAPFOCUS)]:w(MAP_VT+off,target)
 for off,target in [(32,ENABLED),(68,VALUE),(88,SET)]:w(PARAM_VT+off,target)
 targets=SELF+0x200
 for i in range(4):w(targets+i*4,ptrs[50000+i] if x[23] else 0)
 def text(a):
  if not a:return None
  out=bytearray()
  while u.mem_read(a,1)!=b'\0':out+=u.mem_read(a,1);a+=1
  return out.decode()
 def identity(a):return ids.get(a,0) if a else 0
 def lookup(obj,tag):
  if not x[17]:return 0
  return ptrs.get((20000 if obj==SLOT else 10000)+tag,0)
 def hook(uc,a,size,data):
  if a==STOP:uc.emu_stop();return
  handlers={0x7b8c0:'showMeters',0x53244:'focus',0x7b848:'selected',0x7c1a4:'main',0x55aa0:'sends',0x55b28:'cues',0x52e20:'used',0x53f50:'type',0x11acf0:'lookup',0x11f24c:'autoLookup',0xb0f8:'strcmp',0x76d0c:'connect',0x7dfd8:'assign',0x7cd98:'control',0x7d8a4:'updateFocus',0x7c5e0:'names',ENABLED:'enabled',VALUE:'value',SET:'set',MODIFIERS:'modifiers',MAPPARAM:'mappingParam',MAPFOCUS:'mappingFocus',0x186964:'f2d',0x186608:'dadd',0x186ff4:'d2iz'}
  if a not in handlers:
   if not any(lo<=a<lo+n for lo,n in zip(TARGETS,SIZES)):raise RuntimeError(('execution outside bound target/hook',hex(a),x))
   visited.add(a);return
  name=handlers[a];calls.append({'address':a,'boundary':name,'args':[reg(i) for i in range(4)]})
  if name=='showMeters':ret(x[16])
  elif name=='focus':events.append('focus');ret(CHANNEL if x[21] else CHANNEL+0x1000)
  elif name=='selected':events.append('selected');ret(x[1])
  elif name=='main':events.append('main');ret(CHANNEL if x[5] else 0)
  elif name in ['sends','cues']:ret((SEND if name=='sends' else CUE) if x[6] else 0)
  elif name=='used':ret(x[7])
  elif name=='type':ret(0 if x[10]==0 else (0x19e354 if x[10]==1 else 0x19cc38))
  elif name=='lookup':ret(lookup(reg(0),reg(1)))
  elif name=='autoLookup':ret(ptrs[30000+reg(1)] if x[18]&(1<<reg(1)) else 0)
  elif name=='strcmp':ret(0 if text(reg(0))==text(reg(1)) else 1)
  elif name=='enabled':ret(x[20])
  elif name=='value':ret(values[reg(0)])
  elif name=='set':
   events.append(f'set:{identity(reg(0))}:{reg(1)}:{reg(2)}');values[reg(0)]=reg(1);ret()
  elif name=='connect':
   events.append(f'connect:{text(reg(1))}:{identity(reg(2))}:{text(reg(3)) or "-"}:{r(u.reg_read(UC_ARM_REG_SP))}');ret()
  elif name=='assign':events.append('assign');ret()
  elif name=='control':events.append('control');ret()
  elif name=='updateFocus':events.append('updateFocus');ret()
  elif name=='names':events.append('names');ret()
  elif name=='modifiers':events.append('modifiers');ret(x[13])
  elif name=='mappingParam':events.append(f'mappingParam:{reg(1)}');ret(ptrs[40018] if x[22] else 0)
  elif name=='mappingFocus':events.append('mappingFocus');ret()
  elif name=='f2d':
   lo,hi=struct.unpack('<II',struct.pack('<d',value(reg(0))));u.reg_write(UC_ARM_REG_R1,hi);ret(lo)
  elif name=='dadd':
   a1=struct.unpack('<d',struct.pack('<II',reg(0),reg(1)))[0];a2=struct.unpack('<d',struct.pack('<II',reg(2),reg(3)))[0]
   lo,hi=struct.unpack('<II',struct.pack('<d',a1+a2));u.reg_write(UC_ARM_REG_R1,hi);ret(lo)
  elif name=='d2iz':ret(int(struct.unpack('<d',struct.pack('<II',reg(0),reg(1)))[0]))
 def write(uc,access,a,size,v,data):
  if SELF<=a<SELF+0x1000:writes.append({'address':a,'size':size,'value':v})
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 args=[SELF,0,0,0]
 if x[0]==2:args[1]=groups[x[4]]
 if x[0]==3:args[1:]=[targets,CHANNEL if x[5] else 0,x[1]]
 if x[0]==5:args[1:3]=[CHANNEL if x[5] else 0,arg]
 if x[0]==7:args[1]=arg
 if x[0]==9:args[1]=SEND
 if x[0]==10:args[1]=CHANNEL if x[5] else 0
 for i,v in enumerate(args):u.reg_write(REGS[i],v&0xffffffff)
 u.reg_write(UC_ARM_REG_SP,SP);u.reg_write(UC_ARM_REG_LR,STOP)
 try: u.emu_start(TARGETS[x[0]-1],STOP,count=10000)
 except Exception as exc: raise RuntimeError({"input":x,"pc":hex(u.reg_read(UC_ARM_REG_PC)),"calls":calls[-6:]}) from exc
 assert u.reg_read(UC_ARM_REG_PC)==STOP,hex(u.reg_read(UC_ARM_REG_PC))
 out=[u.mem_read(SELF+0x70,1)[0],u.mem_read(SELF+0x71,1)[0]]
 out += [identity(r(targets+i*4)) for i in range(4)] if x[0]==3 else [0]*4
 out += [values[ptrs[30000+i]] for i in range(4)] + [values[ptrs[40018]]]
 return {'input':x,'observed':out,'events':events,'native_calls':calls,'native_writes':writes,'executed_target_instructions':sorted(visited)}
def cases():
 base=[1,33,1,1,0,1,1,8,8,1,2,0,0,0,0,0,0,1,15,bits(2.5),1,1,1,0]
 def c(method,**changes):
  x=base.copy();x[0]=method
  for k,v in changes.items():x[int(k[1:])]=v
  return x
 out=[]
 # Boundaries, null folders/slots, actual vs used count, nonzero prior targets.
 for method in [1,3]:
  for mix in [-1,0,12,13,14,20,21,22,28,29,32,33,34,2147483647]:
   out.append(c(method,a1=mix))
  for changes in [{'a5':0},{'a2':0},{'a6':0},{'a7':0},{'a7':1},{'a8':0},{'a9':0},{'a10':0},{'a10':1},{'a17':0},{'a20':0}]:
   for mix in [13,21,33]:out.append(c(method,a1=mix,**changes))
  for mix in [0,13,21,33]:out.append(c(method,a1=mix,a23=1)) if method==3 else None
 for group in range(4):
  for client,mapping in [(1,1),(0,1),(1,0),(0,0)]:out.append(c(2,a4=group,a2=client,a3=mapping))
 for ch in [0,1]:
  for params in [0,1]:out.append(c(4,a5=ch,a17=params))
 for tag in list(range(-1,25))+[2147483647]:
  for flags in [0,1]:out.append(c(5,a11=tag,a12=flags,a21=flags))
 for old in [0,1,2]:
  for mods in [0,1,2,3,4,5,7,8,0xffffffff]:out.append(c(6,a14=old,a13=mods))
 for tag in [-1,0,6,7,12,13,33,34,35,36,37,38,2147483647]:
  for old,new in [(0,0),(0,1),(1,0),(1,1),(2,1)]:
   for mapping,present in [(1,1),(0,1),(1,0)]:out.append(c(7,a11=tag,a15=old,a16=new,a3=mapping,a22=present))
 for mapping in [0,1]:out.append(c(8,a3=mapping))
 for mix in [-1,0,13,21,32,33,34]:out.append(c(9,a1=mix))
 for v in [-2,-.6,-.5,0,.49,.5,1,1.49,1.5,2,2.49,2.5,3.5,4.49,4.5,6]:
  for mask in [0,1,5,15]:out.append(c(10,a19=bits(v),a18=mask))
 out.extend([c(10,a5=0),c(10,a17=0)])
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
 assert hashlib.sha256(ELF.read_bytes()).hexdigest()==SHA
 ranges=[]
 with ELF.open('rb') as f:
  e=ELFFile(f);segments=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
  syms={s.name:s for s in e.get_section_by_name('.symtab').iter_symbols()}
  for i,(address,size) in enumerate(zip(TARGETS,SIZES),1):
   packet=Path(f'temp/recovery-work/graph-live-trial-07/trial07_dawmixer_{i}-packet');ctx=json.loads((packet/'context.json').read_text());orig=ctx['originals'][0]['original'];symbol=syms[orig['mangled']]
   assert (symbol['st_value'],symbol['st_size'])==(address,size)
   assert symbol['st_shndx']==12
   # Range mapping uses actual section headers, never symbol row number.
   sec=next(s for s in e.iter_sections() if s['sh_addr']<=address<address+size<=s['sh_addr']+s['sh_size'])
   offset=sec['sh_offset']+address-sec['sh_addr'];f.seek(offset);data=f.read(size)
   native=json.loads((packet/'native-context.json').read_text());bound=next(iter(native['bodies'].values()))
   assert (offset,hashlib.sha256(data).hexdigest())==(bound['file_offset'],bound['bytes_sha256'])
   ranges.append({'original':orig,'address':address,'size':size,'section':sec.name,'offset':offset,'sha256':hashlib.sha256(data).hexdigest()})
 records=[run(x,segments) for x in cases()]
 Path(a.out).write_text(json.dumps({'elf':str(ELF),'elf_sha256':SHA,'ranges':ranges,'cases':records},indent=2)+'\n')
 print(f'Original ARM executions: {len(records)}; all ten exact ranges independently recorded')
if __name__=='__main__':main()
