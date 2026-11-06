"""Exact app ARM execution with independent CCL service boundaries.
Native RTTI records are pointer-width adapted and queried by host __dynamic_cast;
Core firmware never executes. This is runtime boundary evidence, not ARM ABI proof.
"""
import ctypes as C,hashlib,itertools,json,pathlib,struct,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UcError
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4];BASE=pathlib.Path('uc-library/tests/recovery/scene_filter')
PACKETS=pathlib.Path('temp/recovery-work/rolling200-02/next-implementation133/prepared133/packets')
ELF='rootfs/RML16AI_Rack_13731/home/root/mixer';SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
TYPES=[0x41ad38,0x173594,0x173488,0x173230,0x17212c,0x1732c8,0x1733f0,0x173358,0x171408,0x16fd2c,0x31c45c,0x31960c,0x31b8b0,0x177e18,0x1765ec,0x1765bc,0x1743bc,0x1742e4]
OBJ=0x1000000;MIX=OBJ+0x1000;COMP=OBJ+0x2000;PAR=OBJ+0x3000;INFO=OBJ+0x4000;SETTINGS=OBJ+0x5000;CHANNEL=OBJ+0x6000;VECTOR=OBJ+0x7000;VT=OBJ+0x8000;PARAMS=OBJ+0x9000
STACK=0x1100000;SP=STACK+0x8000;STOP=0x1200000;GETVALUE=STOP+4
BITS=[6,7,2,3,0,4,1,5,8,9]
class Native:
 def __init__(self):
  self.raw=(ROOT/ELF).read_bytes();assert hashlib.sha256(self.raw).hexdigest()==SHA
  with (ROOT/ELF).open('rb') as f:
   e=ELFFile(f);self.sections=[(s['sh_addr'],s['sh_size'],s['sh_offset'],s.name,s['sh_type']) for s in e.iter_sections()]
   self.names={s['st_value']:s.name for s in e.get_section_by_name('.symtab').iter_symbols() if s.name.startswith('_ZTI')}
  self.ranges=[]
  for p in sorted((ROOT/PACKETS).glob('*')):
   j=json.loads((p/'native-context.json').read_text());b=j['bodies'][j['roots'][0]];raw=self.read(b['address'],b['size'])
   s=next(s for s in self.sections if s[3]==b['section']);assert s[2]+b['address']-s[0]==b['file_offset']
   assert hashlib.sha256(raw).hexdigest()==b['bytes_sha256']
   self.ranges.append({k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']})
  # All Core services are intercepted. Map ELF PT_LOAD-equivalent sections for
  # literal/RTTI/string reads, without executing any Core binary body.
  self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  self.u.mem_map(0,0x600000);self.u.mem_write(0,bytes(0x1000))
  for a,n,o,_,typ in self.sections:
   if a and a+n<0x600000 and typ!='SHT_NOBITS':self.u.mem_write(a,self.raw[o:o+n])
  self.u.mem_map(OBJ,0x10000);self.u.mem_map(STACK,0x10000);self.u.mem_map(STOP,0x1000)
  self.u.hook_add(UC_HOOK_CODE,self.hook);self.u.hook_add(UC_HOOK_MEM_WRITE,self.write)
  self.build_rtti();self.active={};self.trace=[];self.writes=[]
 def read(self,a,n):
  s=next(s for s in self.sections if s[0]<=a and a+n<=s[0]+s[1] and s[4]!='SHT_NOBITS');return self.raw[s[2]+a-s[0]:s[2]+a-s[0]+n]
 def word(self,a):return struct.unpack('<I',self.read(a,4))[0]
 def build_rtti(self):
  self.lib=C.CDLL('libstdc++.so.6');self.cast=getattr(self.lib,'__dynamic_cast');self.cast.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_long];self.cast.restype=C.c_void_p
  self.rtti={};self.keep=[];self.records=[];self.edges={}
  def build(a):
   if a in self.rtti:return self.rtti[a]
   v,name=self.word(a),self.word(a+4);s=self.read(name,200).split(b'\0')[0];buf=C.create_string_buffer(s);self.keep.append(buf)
   if v==0x492948:kind='__class_type_info';bases=[];n=8
   elif v==0x492980:kind='__si_class_type_info';bases=[(self.word(a+8),0,2)];n=12
   else:
    assert v==0x4929b0,hex(v);kind='__vmi_class_type_info';cnt=self.word(a+12);n=16+cnt*8
    bases=[]
    for i in range(cnt):
     b,flags=struct.unpack('<Ii',self.read(a+16+i*8,8));assert not flags&1,'virtual base needs explicit adaptation';bases.append((b,flags>>8,flags&255))
   words=2+(1 if kind=='__si_class_type_info' else 1+2*len(bases) if kind=='__vmi_class_type_info' else 0)
   data=(C.c_uint64*words)();self.keep.append(data)
   # vtable address point skips offset-to-top and RTTI pointers.
   symbol='_ZTVN10__cxxabiv1'+str(len(kind))+kind+'E';vt=C.c_uint64.in_dll(self.lib,symbol);data[0]=C.addressof(vt)+16;data[1]=C.addressof(buf)
   self.rtti[a]=C.addressof(data);self.edges[a]=bases
   if kind=='__si_class_type_info':data[2]=build(bases[0][0])
   if kind=='__vmi_class_type_info':
    data[2]=self.word(a+8)|(len(bases)<<32)
    for i,(b,off,flags) in enumerate(bases):data[3+i*2]=build(b);data[4+i*2]=(off*8<<8)|flags
   self.records.append(dict(address=a,name=self.names[a],size=n,sha256=hashlib.sha256(self.read(a,n)).hexdigest(),bases=bases))
   return self.rtti[a]
  for a in TYPES:build(a)
  self.query={}
  for actual in TYPES+[0x1595b4]:
   offsets={}
   def offsets_for(a,off=0):
    offsets.setdefault(a,[]).append(off)
    for b,delta,_ in self.edges[a]:offsets_for(b,off+delta*8)
   offsets_for(actual)
   mem=C.create_string_buffer(16384);top=C.addressof(mem);tables=[]
   for off in {i for o in offsets.values() for i in o}:
    vt=(C.c_int64*3)(-off,self.rtti[actual],0);tables.append(vt);C.c_void_p.from_address(top+off).value=C.addressof(vt)+16
   for src in [0x41ad38,0x1595b4,0x173594]:
    for dst in TYPES:
     if src not in offsets:self.query[actual,src,dst]=False;continue
     hint=(4*8 if dst==0x41ad38 else -1) if src==0x1595b4 else 0
     def base_of(a,b):return a==b or any(base_of(a,x[0]) for x in self.edges[b])
     result=(top+offsets[dst][0]) if base_of(dst,src) else self.cast(top+offsets[src][0],self.rtti[src],self.rtti[dst],hint)
     self.query[actual,src,dst]=bool(result)
     # Runtime result is independently cross-checked against native ancestry.
     assert bool(result)==(dst in offsets),(hex(actual),hex(src),hex(dst),result,offsets)
 def w(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def ret(self,val):self.u.reg_write(UC_ARM_REG_R0,val&0xffffffff);self.u.reg_write(UC_ARM_REG_PC,self.u.reg_read(UC_ARM_REG_LR))
 def hook(self,u,a,n,_):
  if a==0 and self.current==0x4fe1c and self.missing in range(7,17):self.fault=True;u.emu_stop();return
  r=lambda reg:u.reg_read(reg)
  if a==0xacf4:
   obj,src,dst,hint=[r(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
   actual=self.active.get(obj);assert actual is not None,(hex(obj),hex(src),hex(dst))
   yes=self.query[actual,src,dst];self.trace.append(['cast',hex(src),hex(dst),int(yes)]);self.ret(obj if yes else 0);return
  if a==0x11c1d4:
   assert r(UC_ARM_REG_R0)==PAR;v=COMP if self.controller else 0;self.trace.append(['controller',int(bool(v))]);self.ret(v);return
  if a==0x119c4c:
   obj,tag=r(UC_ARM_REG_R0),r(UC_ARM_REG_R1);assert obj in [SETTINGS,COMP]
   v=PARAMS+(tag-7)*16 if obj==SETTINGS and 7<=tag<=16 and tag!=self.missing else 0
   self.trace.append(['lookup',tag,int(bool(v))]);self.ret(v);return
  if a==GETVALUE:
   p=r(UC_ARM_REG_R0);i=(p-PARAMS)//16;assert 0<=i<10 and p==PARAMS+i*16
   self.trace.append(['getValue',i]);self.ret(self.values[i]);return
  if a==0x157940:
   x=struct.unpack('<f',struct.pack('<I',r(UC_ARM_REG_R0)))[0];assert r(UC_ARM_REG_R1)==0;self.ret(int(x>0));return
  if a==0xaf70:
   ptr,literal=r(UC_ARM_REG_R0),r(UC_ARM_REG_R1);assert ptr==COMP+8
   def s(p):return bytes(u.mem_read(p,64)).split(b'\0')[0]
   self.ret(0 if s(ptr)==s(literal) else 1);return
  if a==0x5aedc:
   # Boundary is actual delivered helper with independent native/provider proof.
   # The component decision replay varies both delivered helper results; its
   # actual CCL implementation runs in the portable executable, never a lambda.
   assert r(UC_ARM_REG_R0)==COMP;self.trace.append(['FilterGroup.isConfigured',self.configured]);self.ret(self.configured);return
  assert any(b['address']<=a and a+n<=b['address']+b['size'] for b in self.ranges),(hex(a),self.current)
 def write(self,u,access,a,n,v,_):
  if OBJ<=a<a+n<=OBJ+0x10000:self.writes.append([a-OBJ,n,v]);return
  assert SP-128<=a<a+n<=SP,(hex(a),n)
 def invoke(self,address,args):
  self.trace=[];self.writes=[];self.current=address;self.fault=False
  for reg,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):self.u.reg_write(reg,v&0xffffffff)
  self.u.reg_write(UC_ARM_REG_SP,SP);self.u.reg_write(UC_ARM_REG_LR,STOP)
  try:self.u.emu_start(address,STOP,count=1500)
  except UcError:return None
  if self.fault:return None
  assert self.u.reg_read(UC_ARM_REG_PC)==STOP
  return self.u.reg_read(UC_ARM_REG_R0)
 def decision(self,mode,kind,tag,mask,enabled,matched,blocked,controller,name,configured,vector_kind=None):
  if vector_kind is None:vector_kind=kind
  self.active={COMP:TYPES[kind],CHANNEL:TYPES[vector_kind],CHANNEL+0x4000:TYPES[vector_kind],SETTINGS:0x41ad38};
  if controller==2:self.active[COMP]=0x1595b4
  self.controller=controller;self.configured=configured;self.missing=-999
  self.w(OBJ+8,mask);self.w(OBJ+12,MIX);self.u.mem_write(OBJ+4,bytes([enabled]));self.w(MIX+0x2dc,SETTINGS);self.w(MIX+0x120,VECTOR);self.w(MIX+0x124,2 if matched==2 else int(bool(matched)));self.w(VECTOR,CHANNEL);self.w(VECTOR+4,CHANNEL+0x4000);self.w(CHANNEL+0xf4,PAR+4 if matched>=2 else PAR);self.w(CHANNEL+0x4000+0xf4,PAR);self.u.mem_write(MIX+0x364,bytes([blocked]));self.w(PAR+12,INFO);self.w(INFO+4,tag)
  self.u.mem_write(COMP+8,name.encode()+b'\0');self.u.mem_write(COMP+8+len(name)+1,bytes(64-len(name)-1))
  typeid=0x50617261 if mode=='lp' or mode=='sp' else 0x436f6d70 if mode in ['lc','sc','ls','ss'] else 42
  obj=PAR if mode.endswith('p') else SETTINGS if mode.endswith('s') else COMP
  if mode in ['ln','sn']:obj=0;typeid=0x436f6d70
  result=self.invoke(0x4f7c4 if mode[0]=='l' else 0x4fc98,[OBJ,typeid,0,obj]);assert result is not None
  assert not self.writes
  return dict(input=[mode,kind,tag,mask,enabled,matched,blocked,controller,name,configured,vector_kind],result=result,trace=self.trace)
 def refresh(self,variant,values,settings=True,cache=False,missing=-999):
  self.active={};self.values=values;self.missing=missing;self.u.mem_write(OBJ,bytes(128));self.w(OBJ+12,MIX);self.w(MIX+0x2dc,SETTINGS if settings else 0);self.w(VT+0x44,GETVALUE)
  for i in range(10):self.w(PARAMS+i*16,VT);self.w(OBJ+16+4*i,PARAMS+i*16 if cache and (cache!=2 or 7+i!=missing) else 0)
  self.u.mem_write(OBJ+4,b"\1");self.w(OBJ+8,0xffffffff);self.w(COMP+12,MIX);self.w(COMP+8,0xa55a);self.u.mem_write(COMP+4,b'\0')
  address=[0x4fe1c,0x500d4,0x501ac,0x50140,0x50210][variant]
  result=self.invoke(address,[OBJ,COMP if variant in [1,3] else MIX,0,0])
  return dict(input=[variant,values,int(settings),int(cache),missing],fault=result is None,mask=self.r(OBJ+8),enabled=int(self.u.mem_read(OBJ+4,1)[0]),cache=[self.r(OBJ+16+i*4)-PARAMS if self.r(OBJ+16+i*4) else -1 for i in range(10)],trace=self.trace,writes=self.writes)
def generate():
 n=Native();cases=[];masks=[0,1023]+[1<<i for i in range(10)]
 for k in range(len(TYPES)):
  for mask in masks:
   cases.append(n.decision('lc',k,0,mask,1,0,0,1,'ordinary',0))
  for mode in ['sc','sp','lp']:
   tags=range(-2,422) if mode=='lp' else [-1,0,1,2,306,307,308]
   for tag in tags:
    for mask in masks if mode=='lp' else [0]:
     cases.append(n.decision(mode,k,tag,mask,1,1,0,1,'ordinary',1))
 # Enabled/blocked/channel membership, noncomponent/null observers and names.
 for k,tag,enabled,matched,blocked in itertools.product(range(len(TYPES)),[14,17,38,39,40],[0,1],[0,1],[0,1]):
  for mask in [0,1,8,16,1023]:cases.append(n.decision('lp',k,tag,mask,enabled,matched,blocked,1,'ordinary',0))
 for mode in ['ln','sn','lo','so','ls','ss','lp','sp']:
  for k in [0,1]:cases.append(n.decision(mode,k,0,0,0,0,0,0,'ordinary',0))
 for k,name,configured in itertools.product(range(len(TYPES)),['mixscene','mutegroup','Mixscene','ordinary'],[0,1]):cases.append(n.decision('sc',k,0,0,1,0,0,1,name,configured))
 for mode,k,tag in itertools.product(['lp','sp'],[0,1],[0,1,14,17,307]):cases.append(n.decision(mode,k,tag,0,1,0,0,2,'ordinary',0))
 for vk,mask,enabled,matched in itertools.product([1,14,15,16,17],masks,[0,1],range(4)):cases.append(n.decision('lp',1,17,mask,enabled,matched,0,1,'ordinary',0,vk))
 refresh=[]
 vals=[0,0x80000000,0x3f800000,0xbf800000,0x7fc00000,0x7f800000,0xff800000,1,0x80000001]
 for variant in range(5):
  for value in vals:refresh.append(n.refresh(variant,[value]*10))
  for i in range(10):
   v=[0]*10;v[i]=0x3f800000;refresh.append(n.refresh(variant,v))
  refresh.append(n.refresh(variant,[0]*10,False))
 for cache,missing in itertools.product([False,True,2],range(7,17)):
  refresh.append(n.refresh(0,[0x3f800000]*10,True,cache,missing))
 return dict(elf=ELF,elf_sha256=SHA,ranges=n.ranges,rtti_records=sorted(n.records,key=lambda x:x['address']),cases=cases,refresh=refresh,boundary='Original application instructions and literal pools only. Core services and float compare intercepted at exact addresses. RTTI translated from original records to host pointer width/offset scale8 and queried by real libstdc++ __dynamic_cast; not original ARM runtime execution or ABI proof. App FilterGroup helper boundary varies independently; helper native/provider proof plus unchanged production implementation bound separately. Null/partial settings faults captured, rejected explicitly in source port. All decision writes absent; refresh object writes captured; stack writes bounded.')
if __name__=='__main__':
 j=json.loads(json.dumps(generate()));p=ROOT/BASE/'fixtures.json'
 if '--generate' in sys.argv:p.write_text(json.dumps(j,separators=(',',':'))+'\n')
 else:assert j==json.loads(p.read_text())
 print(len(j['cases']),'decision cases,',len(j['refresh']),'refresh/constructor cases; real RTTI boundary queries')
