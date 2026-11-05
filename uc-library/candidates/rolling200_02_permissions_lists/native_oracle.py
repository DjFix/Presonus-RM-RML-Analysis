#!/usr/bin/env python3
"""Exact app ARM execution in private memory; explicit CCL/source boundary models.
Never imports or executes reconstructed C++. No syscalls or original Core bodies.
"""
import io,json,struct,hashlib,argparse
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import *
from unicorn.arm_const import *
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
HASH='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
PACKETS=Path('temp/recovery-work/rolling200-02/implementation-plan01/packets-current-permissions-lists03-01/packets')
SELF,CLIENT,MIX,OTHER,TEXT,VT,CHANNELS,MIXER= [0x1000000+i*0x1000 for i in range(8)]
STACK,STOP,HOOK=0x1100000,0x1200000,0x1300000
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def sha(b):return hashlib.sha256(b).hexdigest()
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def flt(v):return struct.unpack('<f',struct.pack('<I',v))[0]
class Oracle:
 def __init__(self):
  self.raw=ELF.read_bytes();assert sha(self.raw)==HASH
  self.elf=ELFFile(io.BytesIO(self.raw));self.syms={s.name:s for s in self.elf.get_section_by_name('.symtab').iter_symbols() if s.name}
  self.ranges=[];self.targets=[]
  for p in sorted(PACKETS.iterdir()):
   t=json.loads((p/'request.json').read_text())['targets'][0];self.targets.append(t['address']);self.ranges.append(self.verify(t['mangled'],t))
  names=['_ZNK8Presonus5Mixer20PermissionsComponent20getSelectedDeviceAppEv','_ZNK8Presonus5Mixer20PermissionsComponent10getAppTypeERKNS_2UC18ClientSubscriptionE','_ZNK8Presonus17LinkableComponent8isLinkedEv','_ZN8Presonus5Mixer20PermissionsComponent14syncMixStringsEv']
  self.ranges.extend(self.verify(n) for n in names)
  self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
  for s in self.elf.iter_segments():
   if s['p_type']!='PT_LOAD':continue
   for a in range(s['p_vaddr']&~4095,(s['p_vaddr']+s['p_memsz']+4095)&~4095,4096):
    if a not in pages:self.u.mem_map(a,4096);pages.add(a)
   self.u.mem_write(s['p_vaddr'],s.data())
  for a,n in [(SELF,0x10000),(STACK,0x10000),(STOP,4096),(HOOK,4096)]:self.u.mem_map(a,n)
  self.u.hook_add(UC_HOOK_CODE,self.code);self.u.hook_add(UC_HOOK_MEM_WRITE,self.write)
  self.boundaries={0x11f430:'getString',0x11f9a0:'remove',0x11ecd8:'append',0x1a134:'stringCtor',0x12af4:'format',0x1578e0:'floatEqual',0x157928:'floatGreaterEqual',0x157958:'floatToInt',0x157474:'intToFloat',0xad18:'strstr',0xaf70:'strcmp',0x119c4c:'getTag',0x121dbc:'allocator',0x121a68:'attributesCtor',0x1228b0:'attributesDtor',0x129ba4:'filenameCtor',0x50c94:'selectedFilename',0x117fa8:'archiveLoad',0x116a38:'debug'}
  self.virtual={0x3c:'max',0x44:'value',0x58:'set',0x5c:'reset',0x70:'toString',0x74:'fromString'}
  for off,name in self.virtual.items():self.boundaries[HOOK+off]=name
  self.boundaries[HOOK+0x200]='treeLoad'
  for obj in [MIX,OTHER,TEXT]:self.put(obj,VT)
  for off in self.virtual:self.put(VT+off,HOOK+off)
  self.put(SELF,VT+0x100);self.put(VT+0x120,HOOK+0x200)
 def verify(self,n,t=None):
  s=self.syms[n];sec=self.elf.get_section(s['st_shndx']);a=s['st_value'];z=s['st_size'];off=sec['sh_offset']+a-sec['sh_addr'];body=self.raw[off:off+z]
  if t:assert a==t['address'] and z==t['size']
  assert sec.name=='.text';return dict(mangled=n,address=a,size=z,section=sec.name,file_offset=off,sha256=sha(body))
 def put(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def string(self,a):
  if not a:return ''
  out=bytearray()
  for i in range(1024):
   b=self.u.mem_read(a+i,1)[0]
   if not b:return out.decode('latin1')
   out.append(b)
  raise AssertionError('unterminated')
 def mem(self,a,b):
  assert STACK<=a and a+len(b)<=STACK+0x10000,('boundary write',hex(a),len(b))
  self.writes.append([a,b.hex(),'boundary']);self.u.mem_write(a,b)
 def write(self,u,access,a,n,v,data):
  assert STACK<=a and a+n<=STACK+0x10000 or a in [SELF+0x98,SELF+0x108] and n==1,('unexpected write',hex(a),n)
  self.writes.append([a,n,v])
 def set(self,p,v):
  lo,hi=sorted([0,self.max[p]]);v=max(lo,min(hi,v))
  if self.val[p]!=v:self.val[p]=v;self.events.append([p,'changed'])
 def maxset(self,p,m):
  if self.max[p]==m:return
  self.max[p]=m
  if self.val[p]>m:self.set(p,m)
  else:self.events.append([p,'changed'])
 def textset(self,s):
  if self.text!=s:self.text=s;self.events.append([TEXT,'changed'])
 def code(self,u,a,n,data):
  if a==STOP:self.done=True;u.emu_stop();return
  if a not in self.boundaries:
   assert any(r['address']<=a<r['address']+r['size'] for r in self.ranges),('PC outside allowlist',hex(a))
   self.pcs.append(a);return
  name=self.boundaries[a];r0,r1,r2,r3=[u.reg_read(r) for r in REGS];result=0;detail={}
  if name=='strstr':
   hay,needle=self.string(r0),self.string(r1);idx=hay.find(needle);result=r0+idx if idx>=0 else 0;detail=dict(hay=hay,needle=needle)
  elif name=='strcmp':
   x,y=self.string(r0),self.string(r1);result=(x>y)-(x<y)
  elif name=='remove':
   if self.lists[r0]:self.lists[r0]=[];self.maxset(r0,-1)
  elif name=='append':
   text=self.string(r1);self.lists[r0].append(text);self.maxset(r0,len(self.lists[r0])-1);detail['text']=text
  elif name=='max':result=bits(self.max[r0])
  elif name=='value':result=bits(float(self.case['rawValue'])) if self.case['op']==4 else bits(self.val[r0])
  elif name=='set':self.set(r0,flt(r1));detail['float']=flt(r1);assert r2==0
  elif name=='fromString':
   text=self.string(r1);detail['text']=text;assert r2==0
   if r0==TEXT:self.textset(text)
   elif text in self.lists[r0]:self.set(r0,self.lists[r0].index(text))
  elif name=='reset':assert r0==TEXT and r1==0;self.textset('default')
  elif name=='getString':
   text=self.lists[r0][r3] if r3<len(self.lists[r0]) else '';self.mem(r1,text.encode()+b'\0')
  elif name=='toString':
   text=self.text if r0==TEXT else (('%.2f' % (float(self.case['rawValue']) or 0.0)) if self.case['op']==4 else (self.lists[r0][int(self.val[r0])] if 0<=int(self.val[r0])<len(self.lists[r0]) else ''))
   self.mem(r1,text.encode()+b'\0')
  elif name=='stringCtor' or name=='filenameCtor':self.mem(r0,b'\0')
  elif name=='format':
   prefix=self.string(r2);number=r3 if r3<2**31 else r3-2**32;fmt=self.string(r1)
   text=prefix+str(number)
   if fmt=='%s%d%s%d':
    sp=u.reg_read(UC_ARM_REG_SP);p,q=struct.unpack('<II',u.mem_read(sp,8));text+=self.string(p)+str(q if q<2**31 else q-2**32)
   self.mem(r0,text.encode()+b'\0');detail['text']=text
  elif name=='floatEqual':result=int(flt(r0)==flt(r1))
  elif name=='floatGreaterEqual':result=int(flt(r0)>=flt(r1))
  elif name=='floatToInt':result=int(flt(r0))
  elif name=='intToFloat':result=bits(r0 if r0<2**31 else r0-2**32)
  elif name=='getTag':assert r1==2;result=TEXT
  elif name=='allocator':result=0x100f000
  elif name in ['attributesCtor','attributesDtor','debug']:pass
  elif name=='selectedFilename':self.mem(r1,(('fixture.perms' if self.case['file']!='empty' else '').encode()+b'\0'))
  elif name=='archiveLoad':result=int(self.case['file'] in ['match','missing','unknown','other']);detail['success']=result
  elif name=='treeLoad':
   if self.case['file']=='other':self.set(OTHER,1)
   self.textset(self.case['saved']) if self.case['file']!='missing' else None
  else:raise AssertionError(name)
  self.calls.append(dict(pc=a,name=name,args=[r0,r1,r2,r3],result=result,**detail));u.reg_write(UC_ARM_REG_R0,result&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def run(self,c):
  self.case=c;self.calls=[];self.pcs=[];self.writes=[];self.events=[];self.done=False
  self.lists={MIX:['seed'+str(i) for i in range(c['old'])],OTHER:['oldOther']};self.max={p:len(v)-1 for p,v in self.lists.items()};self.val={MIX:float(c['value']),OTHER:0.};self.text='initial'
  self.u.mem_write(STACK,b'\xcc'*0x10000)
  for off,v in [(0x88,MIX if c['optional'] else 0),(0x8c,OTHER),(0x94,MIXER),(0xf8,CLIENT if c['app']!='null' else 0)]:self.put(SELF+off,v)
  self.u.mem_write(SELF+0x85,bytes([c['defaults']]));self.u.mem_write(SELF+0x98,bytes([c['loading']]));self.u.mem_write(SELF+0x108,bytes([c['dirty']]))
  self.u.mem_write(CLIENT+0x58,c['app'].encode()+b'\0');self.put(MIXER+0x170,CHANNELS);self.put(MIXER+0x174,len(c['channels']))
  for i,item in enumerate(c['channels']):
   p=0 if item is None else SELF+0x8000+i*0x400;self.put(CHANNELS+i*4,p)
   if item:
    self.put(p+0x170,item[0]);self.put(p+0x88,SELF if item[1] else 0)
  for r in REGS:self.u.reg_write(r,0)
  self.u.reg_write(UC_ARM_REG_CPSR,0x10);self.u.reg_write(UC_ARM_REG_SP,STACK+0xff00);self.u.reg_write(UC_ARM_REG_LR,STOP);self.u.reg_write(UC_ARM_REG_R0,SELF)
  before=bytes(self.u.mem_read(SELF,0x10000))
  self.u.emu_start((0x50b14 if c['op']==4 else self.targets[c['op']-1]),STOP+4,count=20000);assert self.done
  after=bytes(self.u.mem_read(SELF,0x10000))
  assert all(x==y or i in [0x98,0x108] for i,(x,y) in enumerate(zip(before,after)))
  result=dict(mix=self.lists[MIX],other=self.lists[OTHER],mixValue=self.val[MIX],otherValue=self.val[OTHER],max=self.max[MIX],dirty=after[0x108],loading=after[0x98],saved=self.text,events=[[{MIX:'mix',OTHER:'other',TEXT:'saved'}[p],e] for p,e in self.events])
  return result,dict(pcs=self.pcs,calls=self.calls,writes=self.writes,input_guard_checked=True)
def cases():
 apps=['null','unknown','qmix','ucapp','ucremoteapp','ucappqmix','QMIX']
 channels=[[],[None],[[0,False]],[[4,True],[5,False],[9,False]],[[1,False],None,[6,True]],[[0xffffffff,False]],[[0xfffffffe,True]]]
 for op in [1,2,3]:
  for app in apps:
   for ch in channels:
    for old in [0,1,2,5]:
     for dirty in [0,1]:
      yield dict(op=op,app=app,channels=ch,old=old,value=0 if old<2 else old-1,dirty=dirty,loading=0,optional=True,defaults=1,file='absent',saved='FOH')
 for app in ['qmix','ucapp','ucremoteapp']:
  for file in ['empty','absent','invalid','match','missing','unknown','other']:
   for defaults in [0,1]:
    for saved in ['None','FOH','All Auxes','Aux 5/6','Aux 10','unknown','']:
     yield dict(op=3,app=app,channels=[[4,True],[5,False],[9,False]],old=5,value=3,dirty=0,loading=0,optional=True,defaults=defaults,file=file,saved=saved)
 for app in apps:
  yield dict(op=2,app=app,channels=[],old=2,value=1,dirty=0,loading=1,optional=False,defaults=0,file='empty',saved='')
 for value in ['-1','-0','0','1','nan']:
  yield dict(op=4,app='qmix',channels=[],old=2,value=0,dirty=0,loading=0,optional=True,defaults=0,file='empty',saved='',rawValue=value)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);o=Oracle();rows=[]
 with (out/'native-traces.jsonl').open('w') as f:
  for i,c in enumerate(cases()):
   result,trace=o.run(c);rows.append(dict(id=i,input=c,observed=result));f.write(json.dumps(dict(id=i,**trace))+'\n')
 (out/'native-fixtures.json').write_text(json.dumps(dict(cases=rows),indent=2)+'\n')
 (out/'native-proof.json').write_text(json.dumps(dict(elf_path=str(ELF),elf_sha256=HASH,ranges=o.ranges,cases=len(rows),producer_sha256=sha(Path(__file__).read_bytes()),unicorn=unicorn.__version__,boundaries=o.boundaries,domain='Exact original list/load app bodies plus classifier, link and sync helpers; Core/libc/AEABI boundaries explicitly modeled from provider/source contracts. No original Core instructions, constructors, host syscalls or devices.',write_guard='Native stores restricted to stack and SELF+0x98/+0x108; all boundary stores stack; whole private object/input region compared.',fixture_sha256=sha((out/'native-fixtures.json').read_bytes()),trace_sha256=sha((out/'native-traces.jsonl').read_bytes())),indent=2)+'\n');print(len(rows))
if __name__=='__main__':main()
