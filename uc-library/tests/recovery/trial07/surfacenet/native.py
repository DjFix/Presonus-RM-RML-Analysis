"""Independent bounded ARM instruction oracle. Core providers are hooked boundaries.
No firmware programming, host network enumeration, or device execution occurs.
"""
import argparse, hashlib, json, struct, subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ELF = Path('rootfs/CS18_v13840/home/root/surface')
SHA = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
ADDRESSES=[0x9ff50,0xa0774,0xa1344,0xa0fbc,0xa0104,0xa4140,0xa35e4,0xa1450,0xa151c,0xa0388]
SIZES=[436,748,260,200,428,232,120,52,240,232]
# Input slots: target,tag,mixers,daws,selectedMixer,selectedDAW,arg,type,
# mappings,midi,targetType,localCount,firstOctet,stored,duplicate,component,
# cast,flags,pending,managerExists,elapsed,wired,parse,titleLength,model.
DEFAULT=[1,0,2,2,1,3,2,0,2,-1,0,1,10,1,0,1,1,1,0,1,1,0,1,6,1]

def cases():
 out=[]
 for target in range(1,11):
  v=DEFAULT.copy();v[0]=target
  out.append(v)
  changes={1:{1:[0,7],2:[0,1,3],4:[0,1,2,5],5:[0,3],8:[0,3],9:[-1,0,2],23:[0,127,150]},2:{7:[0,1,2],11:[0,1,2],12:[0,10],13:[0,1],14:[0,1],4:[0,1],5:[0,3]},3:{4:[0,1,2],6:[0,1,2],15:[0,1],16:[0,1],17:[0,1,2,3,-1]},4:{5:[0,2,3],6:[0,2,3],15:[0,1],16:[0,1],17:[0,2,3]},5:{10:[0,1,2],2:[0,1,3],3:[0,1,3],23:[0,127,150],24:[0,1]},6:{18:[0,1],19:[0,1]},7:{20:[0,1],21:[0,1,2]},8:{4:[0,1],5:[0,3]},9:{6:[1,2,3,4,5],7:[0,1,2],10:[0,1]},10:{4:[0,1],5:[0,3],22:[0,1]}}[target]
  for slot,values in changes.items():
   for x in values:
    a=v.copy();a[slot]=x;out.append(a)
 # important crosses
 for t in [2,9]:
  for kind in [0,1,2]:
   for selected in [0,1]:
    a=DEFAULT.copy();a[0]=t;a[7]=kind;a[4]=selected;a[5]=0;a[6]=1 if kind==0 else 3;a[10]=kind;out.append(a)
 for sm in [0,1]:
  for sd in [0,3]:
   for parse in [0,1]:
    a=DEFAULT.copy();a[0]=10;a[4]=sm;a[5]=sd;a[22]=parse;out.append(a)
 return list({tuple(v):v for v in out}.values())

class Oracle:
 def __init__(self,v,segments):
  self.v=v;self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);self.u.mem_map(0,0x1000000)
  for addr,data in segments:self.u.mem_write(addr,data)
  self.instruction_count=0;self.executed_sites=set();self.memory_writes=[];self.trace=[];self.params={0:{'strings':[],'requested_value':0},7:{'strings':[],'requested_value':0},29:{'text':''}}
  self.rows=[];self.modelSelected=0;self.heap=0x700000;self.reset=0
  self.obj=0x400000;self.stop=0xf00000
  self.w(self.obj+0xf8,self.ptr(v[4]));self.w(self.obj+0xfc,self.ptr(v[5]));self.w(self.obj+0x100,v[9]);self.w(self.obj+0x104,0x600000 if v[24] else 0);self.u.mem_write(self.obj+0x108,bytes([v[18]]))
  self.w(2429136,0x620000 if v[19] else 0)
  for addr in [0x600000,0x620000,0x630000]:self.w(addr,0x640000)
  self.w(0x640008,0x900008);self.w(0x640000,0x900000);self.w(0x640028,0x900028);self.w(0x64005c,0x90005c);self.w(0x640074,0x900074)
  for tag in [0,7,29]:
   p=self.param(tag);self.w(p,0x650000);self.w(0x650058,0x900158);self.w(0x650074,0x900174)
  self.vector(self.obj+0xd0,list(range(1,1+v[2])));self.vector(self.obj+0xe4,list(range(3,3+v[3])))
  for i in range(1,9):
   self.w(self.ptr(i),v[7] if i==v[6] else (0 if i<3 else 1));self.w(self.ptr(i)+0x1d4,self.ptr(v[6]) if v[14] else 0)
   self.u.mem_write(self.ptr(i)+12,b'10.0.0.1\0')
  self.w(self.obj+0xc0,0x610000);self.w(self.obj+0xc4,0x610004);self.w(self.obj+0xc8,0x610008)
  self.u.hook_add(UC_HOOK_CODE,self.hook);self.u.hook_add(UC_HOOK_MEM_WRITE,self.write_hook)
 def w(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def ptr(self,i):return 0x500000+i*0x400 if i else 0
 def ident(self,p):return (p-0x500000)//0x400 if p else 0
 def param(self,tag):return 0x660000+tag*0x100
 def ptag(self,p):return (p-0x660000)//0x100
 def string(self,p):return bytes(self.u.mem_read(p,512)).split(b'\0')[0].decode('ascii') if p else ''
 def put(self,p,s):self.u.mem_write(p,s.encode()+b'\0')
 def vector(self,p,ids):
  items=0x680000+(p-self.obj)*0x100;self.w(p+4,items);self.w(p+8,len(ids))
  for i,x in enumerate(ids):self.w(items+4*i,self.ptr(x))
 def ids(self,p):return [self.ident(self.r(self.r(p+4)+4*i)) for i in range(self.r(p+8))]
 def event(self,name,*args):self.trace.append([name,*args])
 def write_hook(self,u,access,address,size,value,user):
  if self.obj<=address<self.obj+0x120:self.memory_writes.append({'offset':address-self.obj,'size':size,'value':value})
 def hook(self,u,a,size,user):
  self.instruction_count+=1
  if any(begin<=a<begin+n for begin,n in zip(ADDRESSES,SIZES)):self.executed_sites.add(a)
  if a==self.stop:u.emu_stop();return
  r=[u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];ret=0;handled=True
  if a==0x11f24c:ret=self.param(r[1])
  elif a==0x12199c:self.params[self.ptag(r[0])]['strings']=[]
  elif a==0x120cd4:self.params[self.ptag(r[0])]['strings'].append(self.string(r[1])[:127])
  elif a==0x11e78:self.put(r[0],self.string(r[1])[:127])
  elif a==0x622f0:
   i=self.ident(r[0]);self.put(r[1],('T'+str(i)+'x'*self.v[23])[:127]);self.event('title',i)
  elif a==0x187314:ret=struct.unpack('<I',struct.pack('<f',float(struct.unpack('<i',struct.pack('<I',r[0]))[0])))[0]
  elif a==0xb86a8:self.event('mappingCount');ret=self.v[8]
  elif a==0xb86bc:
   self.event('mappingName',r[1]);ret=0x6f0000+r[1]*0x100;self.put(ret,'Map'+str(r[1]))
  elif a==0x900158:
   t=self.ptag(r[0]);value=struct.unpack('<f',struct.pack('<I',r[1]))[0];self.params[t]['requested_value']=int(value);self.event('setValue',t,int(value),r[2])
  elif a==0x11fbd0:self.event('rangeChanged',self.ptag(r[0]))
  elif a==0xdd84c:
   self.event('localAddresses');ret=self.v[11]
   for i in range(ret):u.mem_write(r[0]+36*i+12,bytes([self.v[12],0,0,1]))
  elif a==0x9f4e0:self.event('targetType');ret=self.v[10]
  elif a in [0xa463c,0xa439c]:
   base=r[0]-4;ids=self.ids(base);item=self.ident(self.r(r[1]));
   if a==0xa463c:ids.append(item)
   elif item in ids:ids.remove(item)
   self.vector(base,ids);ret=1
  elif a==0xa0668:self.event('stored',self.string(r[1]),self.ident(r[2]));ret=self.v[13]
  elif a in [0x7cbc8,0x7c09c,0x8b868]:self.event({0x7cbc8:'setDAW',0x7c09c:'setTransport',0x8b868:'setMixer'}[a],1 if r[1] else 0)
  elif a==0x624dc:self.event('release',self.ident(r[0]),r[1])
  elif a==0x62204:self.event('acquire',self.ident(r[0]))
  elif a==0x61844:self.event('component',self.ident(r[0]));ret=0x6a0000 if self.v[15] else 0
  elif a==0xae58:ret=0x6b0000 if self.v[16] else 0
  elif a==0xa0a60:self.event('itemInfo',r[1],self.ident(r[2]))
  elif a==0xa11e0:self.event('storeSelected',self.string(r[1]),self.ident(r[2]),struct.unpack('<i',struct.pack('<I',r[3]))[0])
  elif a==0x11a5c4:ret=0x6a0000
  elif a==0x29478:ret=0x630000
  elif a==0x900028:self.event('setNetworkRoot',1 if r[1] else 0)
  elif a==0x900008:self.rows=[]
  elif a==0xa90c:ret=self.heap;self.heap+=0x400
  elif a==0x108ed8:self.put(r[0],self.string(r[1])[:127])
  elif a==0x108b18:self.rows.append(r[1])
  elif a==0xb02c:ret=len(self.string(r[0]))
  elif a==0xb170:u.mem_write(r[0],bytes(u.mem_read(r[1],r[2])))
  elif a==0x900000:self.event('modelChanged')
  elif a==0x9f574:self.modelSelected=self.ident(r[1]);self.event('selectModelItem',self.modelSelected)
  elif a==0x90005c:self.event('enableNetwork',r[1])
  elif a==0x287e8:self.w(r[0],0x640000)
  elif a==0x128c6c:self.event('singletonRegistered')
  elif a==0x1179d4:pass
  elif a==0x900074:self.event('resumeAdaptors')
  elif a==0xa3e88:self.event('setupLocalIP')
  elif a==0x11a74c:pass
  elif a==0x12110:ret=self.v[20]
  elif a==0x11ff8:self.reset=1
  elif a==0x9f24c:ret=self.v[21]
  elif a==0xa333c:self.event('configureNetwork',self.string(r[1]))
  elif a==0xdd3cc:self.event('parseAddress',self.string(r[1]));ret=self.v[22]
  elif a==0x59410:self.put(r[0],self.string(r[1])[:127]);ret=r[0]
  elif a==0x900174:self.params[29]['text']=self.string(r[1]);self.event('fromString',29,self.string(r[1]),r[2])
  else:handled=False
  if handled:u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  elif not any(begin<=a<begin+n for begin,n in zip(ADDRESSES,SIZES)):raise RuntimeError(f"unhandled external execution {a:#x}")
 def run(self):
  u=self.u;u.reg_write(UC_ARM_REG_SP,0x8ff000);u.reg_write(UC_ARM_REG_LR,self.stop);u.reg_write(UC_ARM_REG_R0,self.obj)
  target=self.v[0];u.reg_write(UC_ARM_REG_R1,self.ptr(self.v[6]));u.reg_write(UC_ARM_REG_R2,self.v[17]&0xffffffff)
  if target==1:
   tag=self.v[1];u.reg_write(UC_ARM_REG_R1,tag);u.reg_write(UC_ARM_REG_R2,self.obj+(0xe4 if tag==7 else 0xd0));u.reg_write(UC_ARM_REG_R3,self.ptr(self.v[5] if tag==7 else self.v[4]))
  u.emu_start(ADDRESSES[target-1],self.stop,count=100000)
  if u.reg_read(UC_ARM_REG_PC)!=self.stop:raise RuntimeError('instruction budget exhausted')
  # singleton construction is app-provider behavior and tracked separately;
  # source port delegates ensuring singleton to required enableNetwork boundary.
  internals=[x for x in self.trace if x[0]=='singletonRegistered']
  self.trace=[x for x in self.trace if x[0]!='singletonRegistered']
  return {'trace':self.trace,'mixers':self.ids(self.obj+0xd0),'daws':self.ids(self.obj+0xe4),'selectedMixer':self.ident(self.r(self.obj+0xf8)),'selectedDAW':self.ident(self.r(self.obj+0xfc)),'pending':self.u.mem_read(self.obj+0x108,1)[0],'params':self.params,'rows':[[self.string(p),self.ident(self.r(p+0x80))] for p in self.rows],'timerReset':self.reset},internals

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
 assert hashlib.sha256(ELF.read_bytes()).hexdigest()==SHA
 with ELF.open('rb') as f:
  e=ELFFile(f);originals=[];symtab=e.get_section_by_name('.symtab');segments=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD'];sec=e.get_section(12);ranges=[]
  for address,size in zip(ADDRESSES,SIZES):
   matches=[x for x in symtab.iter_symbols() if x['st_value']==address and x['st_size']==size and x.name.startswith('_ZN') and 'NetworkSetupComponent' in x.name];assert len(matches)==1;originals.append(dict(elf_sha256=SHA,firmware='CS18AI surface 13840',role='client',mangled=matches[0].name,demangled=subprocess.check_output(['/usr/bin/c++filt',matches[0].name],text=True).strip(),address=address,size=size,section=sec.name));offset=sec['sh_offset']+address-sec['sh_addr'];data=ELF.read_bytes()[offset:offset+size];ranges.append({'address':address,'size':size,'section':sec.name,'offset':offset,'sha256':hashlib.sha256(data).hexdigest()})
 result=[]
 for i,v in enumerate(cases()):
  oracle=Oracle(v,segments);observation,internals=oracle.run();result.append({'id':i,'input':v,'expected':observation,'provider_internal_trace':internals,'native_instruction_count':oracle.instruction_count,'native_target_instruction_sites':sorted(oracle.executed_sites),'native_object_memory_writes':oracle.memory_writes})
 Path(a.out).write_text(json.dumps({'elf_sha256':SHA,'originals':originals,'ranges':ranges,'producer':'native.py: Unicorn original ARM instructions; hooked Core/app providers; no Core binary execution','cases':result},indent=2)+'\n')
 print('original ARM cases',len(result))
if __name__=='__main__':main()
