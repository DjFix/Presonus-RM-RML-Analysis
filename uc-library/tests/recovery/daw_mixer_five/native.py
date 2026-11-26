"""Independent ARM execution of the five assigned DAWMixerHandler ranges.
Synthetic component/provider boundaries are explicit; no decompiler oracle.
"""
import hashlib, io, json, pathlib, struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
PACKETS=pathlib.Path('temp/recovery-work/sqlite-issued/packet-readfreeze-sol61')
H,C,G,A,V,S,END=0x10000000,0x11000000,0x12000000,0x13000000,0x14000000,0x15008000,0x16000000
P=0x18000000

def sha(b): return hashlib.sha256(b).hexdigest()
def context(task): return json.loads((PACKETS/task/'CONTEXT.json').read_text())
def method(o):
 import subprocess
 return subprocess.check_output(['c++filt',o['mangled']],text=True).split('::')[3].split('(')[0]
def cases(m):
 if m=='getMainChannel': return [dict(client=c,group=g,used=u,first=t) for c,g,u,t in [(0,1,1,1),(1,0,1,1),(1,1,0,1),(1,1,-1,1),(1,1,1,0),(1,1,1,1),(1,1,2,2)]]
 if m=='assignControlLinkTargets':return [dict(client=c,control=p,meters=e,populated=z) for c,p,e,z in [(0,1,1,1),(1,0,1,1),(1,1,0,1),(1,1,1,0),(1,1,1,1)]]
 if m=='assignSelectedChannelTargets':return [dict(client=c,controller=k,focus=f,locked=l) for c,k,f,l in [(0,1,1,1),(1,0,1,1),(1,1,0,1),(1,1,1,1),(1,1,1,0)]]
 if m=='assignChannels':return [dict(client=c,controller=k,radio=r,bank=b,modifiers=m,selection=q) for c,k,r,b,m,q in [(0,1,0,0,0,0),(1,0,0,0,0,0)]+[(1,1,r,b,m,q) for r in (-1,0,3,4,6) for b in (0,2) for m in (0,1,2,3) for q in (0,4,5,6)]]
 return [dict(group=g,offset=o,filter=f,shift=s,meters=me,mix=mi,meterMode=mm) for g,o,f,s,me,mi,mm in [(0,0,'',0,0,33,34),(1,0,'',0,0,33,34),(1,1,'',1,0,33,36),(1,0,'AudioGroup',0,1,13,35),(1,1,'not AudioEffect',0,0,33,34),(1,0,'AudioEffect',1,0,33,36),(1,2,'not AudioGroupAudioEffect',0,0,33,34)]]

def observe(task):
 d=context(task); original=d['originals'][0]['original'];data=pathlib.Path(original['elf_path']).read_bytes();assert sha(data)==original['elf'];elf=ELFFile(io.BytesIO(data));syms={s.name:s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name};sym=syms[original['mangled']];sec=elf.get_section(sym['st_shndx']);off=sec['sh_offset']+sym['st_value']-sec['sh_addr'];body=data[off:off+sym['st_size']];assert sha(body)==original['range_sha256'];assert body.hex()==original['range_hex'];m=method(original)
 result=[]
 for spec in cases(m):result.append(execute(data,elf,syms,original,m,spec))
 return dict(task=task,method=m,original={k:v for k,v in original.items() if k!='range_hex'},file_offset=off,cases=result)

def execute(data,elf,syms,original,m,spec):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);mapped=set()
 def install(a,b):
  for page in range(a&~4095,(a+len(b)+4095)&~4095,4096):
   if page not in mapped:u.mem_map(page,4096);mapped.add(page)
  u.mem_write(a,b)
 def put(a,v):install(a,struct.pack('<I',v&0xffffffff))
 def get(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def string(a):
  if not a:return None
  b=bytearray()
  for i in range(256):
   x=u.mem_read(a+i,1)[0]
   if not x:return b.decode()
   b.append(x)
  raise ValueError(a)
 def text(a,s):install(a,s.encode()+b'\0');return a
 for seg in elf.iter_segments():
  if seg['p_type']=='PT_LOAD':install(seg['p_vaddr'],seg.data()+b'\0'*(seg['p_memsz']-seg['p_filesz']))
 install(H,b'\0'*4096);install(C,b'\0'*4096);install(G,b'\0'*4096);install(S-0x8000,b'\0'*0x10000);install(END,b'\0'*4)
 def component(i):return A+i*0x1000
 def param(i,t):return P+i*0x10000+t*16
 def identify(a):
  if not a:return '-'
  assert a>=P,hex(a)
  return f'{(a-P)//0x10000}:{((a-P)%0x10000)//16}'
 first=spec.get('first',1);children=[component(first) if first else 0,component(2),component(3),component(4)]
 for i in range(1,40):
  install(component(i),b'\0'*0x1000);put(component(i),V);put(component(i)+0x58,component(i)+0x900);put(component(i)+0x5c,0)
 put(H,C if spec.get('client',1) else 0);put(H+0x14,C if spec.get('client',1) else 0);put(H+4,0x17000000);put(H+8,V+0x1000 if spec.get('controller',1) else 0)
 install(H+0x70,bytes([spec.get('shift',0),spec.get('meters',0)]));put(C+0x680,G if spec.get('group',1) else 0);put(C+0x678,G);put(C+0x67c,G+0x100)
 put(G+0x58,G+0x800);put(G+0x5c,len(children));put(G+0x158,G+0x800);put(G+0x15c,len(children))
 for i,p in enumerate(children):put(G+0x800+i*4,p)
 hooks={};boundaries=[];trace=[]
 def hook(addr,fn):
  hooks[addr]=fn;install(addr,bytes.fromhex('1eff2fe1'))
 def regs():return [u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
 def ret(v=0):u.reg_write(UC_ARM_REG_R0,v&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def named(sub,fn):
  matches=sorted(set(s['st_value'] for n,s in syms.items() if sub in n and s['st_info']['type']=='STT_FUNC' and not n.startswith('_ZTh')))
  assert len(matches)==1,(sub,len(matches));hook(matches[0],fn)
 def bytag():
  a,t,_,_=regs();i=(a-A)//0x1000
  q=param(i,t);put(q,V+0x2000);ret(q)
 named('Component17getParameterByTag',bytag)
 named('DAWChannelGroup12getUsedCount',lambda:ret(min(spec.get('used',4),4)))
 named('DAWClientComponent14getControlLink',lambda:ret(component(30) if spec.get('control',1) else 0))
 named('DAWClientComponent15getFocusChannel',lambda:ret(component(1) if spec.get('focus',1) else 0))
 def findchild():
  a,n,_,_=regs();name=string(n)
  if a==component(30) and spec.get('populated',1):ret(component(10+int(name[1:])))
  else:ret(0)
 hook(V+0x200,findchild);put(V+0x14,V+0x200)
 def cast():
  a,t,_,_=regs();ret(a if a!=component(2) else 0)
 hook(V+0x204,cast);put(V,V+0x204)
 named('__dynamic_cast@@',cast)
 types={1:'AudioInput',2:'Wrong',3:'AudioEffect',4:'AudioGroup'}
 named('DAWChannel7getType',lambda:ret(text(V+0x400,types.get((regs()[0]-A)//0x1000,''))))
 def connect():
  _,n,p,fmt=regs();trace.append(['connect',string(n),identify(p),string(fmt),get(u.reg_read(UC_ARM_REG_SP))]);ret()
 named('MappingTable7connect',connect)
 def format32():
  out,fmt,a,b=regs();fmt=string(fmt);value=fmt%(a if fmt=='p%d' else (string(a),b));text(out,string(out)+value);ret()
 named('CStringBufferILi32EEEE12appendFormat',format32)
 named('strlen@@',lambda:ret(len(string(regs()[0]))))
 def strncpy():
  a,b,n,_=regs();v=string(b).encode()[:n];install(a,v+b'\0'*(n-len(v)));ret(a)
 named('strncpy@@',strncpy)
 def strstr():
  a,b,_,_=regs();i=string(a).find(string(b));ret(a+i if i>=0 else 0)
 named('strstr@@',strstr)
 named('DAWMixerHandler14getSelectedMix',lambda:ret(spec.get('mix',33)))
 named('DAWMixerHandler20getSelectedMeterMode',lambda:ret(spec.get('meterMode',34)))
 def mix():
  _,out,ch,mix=regs();boundaries.append(['getMixTargets', (ch-A)//0x1000 if ch else 0,mix])
  for j,t in enumerate((8,9,14,15)):put(out+j*4,param((ch-A)//0x1000,t) if ch and mix==33 else 0)
  ret()
 # Execute the original getMixTargets body; absent native folders are bounded.
 named('DAWChannel8getSends',lambda:ret(0))
 named('DAWChannel11getCueMixes',lambda:ret(0))
 def strcmp():
  a,b,_,_=regs();ret((string(a)>string(b))-(string(a)<string(b)))
 named('strcmp@@',strcmp)
 named('ColorParam8getColor',lambda:ret(0xffff0000))
 named('MappingTable8mapColorERK',lambda:ret(text(V+0x500,'blue')))
 named('MappingTable15setControlColor',lambda:(trace.append(['color',string(regs()[1]),string(regs()[2])]),ret()))
 # All generated parameter values are normal Parameters except optional color.
 # Native RTTI seam identifies tag 5 as ColorParam in this bounded domain.
 def dyn():
  a,b,c,_=regs();ret(a if a>=P else (a if a!=component(2) else 0))
 named('__dynamic_cast@@',dyn)
 def init64():a,b,_,_=regs();text(a,string(b));ret(a)
 named('CStringBufferILi64EEEE4init',init64)
 def append64():a,b,_,_=regs();text(a,string(a)+string(b));ret(a)
 named('CStringBufferILi64EEEE6append',append64)
 def page():a,b,c,_=regs();text(a,'page:'+string(b)+'.'+string(c));ret(a)
 named('PageParamC1',page)
 named('__cxa_guard_acquire@@',lambda:ret(1))
 named('__cxa_guard_release@@',lambda:(put(regs()[0],1),ret()))
 def memset():a,b,n,_=regs();install(a,bytes([b])*n);ret(a)
 named('memset@@',memset)
 named('Component11lookupChild',lambda:ret(0))
 named('DAWMixerHandler20syncAutomationParams',lambda:(boundaries.append(['sync',1 if regs()[1] else 0]),ret()))
 put(V+0x24,syms['_ZN8Presonus7Surface15DAWMixerHandler26updatePanEncoderConnectionEv']['st_value']);put(H,V)
 hook(V+0x2100,lambda:ret(1));put(V+0x2020,V+0x2100)
 ctrl=V+0x1000;put(ctrl,ctrl+0x100)
 for off,fn in [(0,lambda:ret(spec.get('modifiers',0))),(4,lambda:ret(spec.get('radio',0))),(8,lambda:ret(spec.get('bank',0))),(12,lambda:ret(P+0x800+regs()[1]*16)),(20,lambda:ret(spec.get('locked',1)))]:
  hook(ctrl+0x200+off,fn);put(ctrl+0x100+off,ctrl+0x200+off)
 for tag in (4,5,6):
  q=P+0x800+tag*16;put(q,V+0x800);put(V+0x800+0x44,V+0x900)
 hook(V+0x900,lambda:ret(struct.unpack('<I',struct.pack('<f',1.0 if (regs()[0]-P-0x800)//16==spec.get('selection',0) else 0.0))[0]))
 named('__aeabi_fcmpgt',lambda:ret(struct.unpack('<f',struct.pack('<I',regs()[0]))[0]>0))
 args=[H,G if spec.get('group',1) else 0,spec.get('offset',0),text(V+0x600,spec.get('filter',''))]
 for r,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):u.reg_write(r,v)
 u.reg_write(UC_ARM_REG_SP,S);u.reg_write(UC_ARM_REG_LR,END)
 def run(_,a,size,__):
  if a in hooks:
   hooks[a]()
 u.hook_add(UC_HOOK_CODE,run)
 writes=[]
 def write(_,access,address,size,value,__):
  if not S-0x8000<=address<S+0x8000:writes.append([address,size,value&((1<<(8*size))-1)])
 u.hook_add(UC_HOOK_MEM_WRITE,write)
 try:u.emu_start(original['address'],END,count=100000)
 except Exception as exc:raise RuntimeError((m,spec,hex(u.reg_read(UC_ARM_REG_PC)),exc))
 assert u.reg_read(UC_ARM_REG_PC)==END,(m,hex(u.reg_read(UC_ARM_REG_PC)))
 if m=='getMainChannel':trace=[['main',1 if u.reg_read(UC_ARM_REG_R0)==component(1) else 0]]
 return dict(input=spec,trace=trace,provider_boundaries=boundaries,native_nonstack_writes=writes)
if __name__=='__main__':
 import sys
 print(json.dumps(observe(sys.argv[1]),indent=2))
