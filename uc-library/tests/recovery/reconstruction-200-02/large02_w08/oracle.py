"""Exact ARM app instructions; deterministic external provider stubs, never Core execution."""
import json,hashlib,struct,argparse,re
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=None
# Discover repository without depending on invocation cwd.
for parent in Path(__file__).resolve().parents:
 if (parent/'AGENTS.md').exists() and (parent/'rootfs').exists():ROOT=parent;break
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def flt(x):return struct.unpack('<f',struct.pack('<I',x))[0]
def packet(n):return ROOT/f'temp/recovery-work/reconstruction-200-02/isolated-batch01/packets/large02_w08_{n:02d}'
def target(n):
 d=json.loads((packet(n)/'native-context.json').read_text());key=d['roots'][0];return d['nodes'][key]['metadata']
def run(n,args):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x300000);u.mem_map(0x500000,0x200000);u.mem_map(0x700000,0x1000)
 with ELF.open('rb') as f:
  e=ELFFile(f)
  for seg in e.iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 obj=0x500000;pa,pb=0x501000,0x502000;vt=0x503000;rect=0x504000;controller=0x505000;attr=0x506000
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def reg(i):return u.reg_read(UC_ARM_REG_R0+i)
 def ret(v=None):
  if v is not None:u.reg_write(UC_ARM_REG_R0,v&0xffffffff)
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def text(a):
  out=bytearray()
  for i in range(256):
   b=bytes(u.mem_read(a+i,1))
   if b==b'\0':break
   out+=b
  return out.decode(errors='replace')
 trace=[];state={'invalid':0,'release':0,'delete':0,'value':0,'refresh':False,'sends':0,'index':0,'valid':0};observers={pa:0,pb:0};values={pa:0,pb:bits(.25)}
 timers={};params={};attrs={};lookup={};pointers={0:0,1:pa,2:pb}
 u.mem_write(obj,bytes([0xa5])*0x200)
 for a in [pa,pb]:
  w(a,vt);w(a+12,a+0x100);w(a+0x104,0)
 w(vt+4,0x700100);w(vt+0x44,0x700108);w(vt+0x58,0x70010c);w(vt+0x60,0x700104)
 for i,v in enumerate([2,3,42,53]):w(rect+i*4,v)
 old=args[0] if args else 0;new=args[1] if len(args)>1 else 0
 if n in [2,3,4,5,9]:
  offset={2:0x68,3:0x74,4:0x6c,5:0x70,9:0x64}[n];w(obj+offset,pointers[old]);observers[pointers[old]]=int(old!=0)
 if n in [6,7,14]:w(obj+0x58,pa if old else 0)
 if n==8:state['normalized']=bits(old/100);state['param']=pa if new else 0
 if n==18:
  enabled,present,width=args;w(obj+0x5c,controller if enabled else 0);w(obj+0x58,0);w(controller,vt+0x200);w(vt+0x20c,0x700110)
  if present:attrs={'link':'l','isstereo':'s','chnum':'c'}
  lookup={'l':pa,'s':pb,'c':0x507000};state['width']=width
  for off in [0x64,0x68,0x6c]:w(obj+off,0)
 if n in [16,17,19]:
  tag,msg,value,executing=args[:4];w(pa+0x104,tag);values[pa]=bits(value/100);other=tag+8 if tag<8 else tag-8;params={tag:pa,other:pb}
  w(obj+0x88,0x508000);w(obj+0x8c,8);w(obj+0xb8,0x50b000 if len(args)>4 and args[4] else 0)
  for i in range(8):
   a=0x509000+i*64;w(0x508000+i*4,a);timers[a]=bool(executing and i==tag)
  timers[obj+0x98]=False;state['refresh']=False
 def hook(uc,a,size,data):
  if a==0x700000:uc.emu_stop();return
  if a in [0xfb6f4,0xfaef0,0xfb15c,0xfb028,0x11c87c,0x11a74c,0xf8000]:trace.append([hex(a),reg(0),reg(1),reg(2)]);ret(reg(0));return
  if a in [0x11e2e0,0x11f4f0]:observers[reg(0)]=observers.get(reg(0),0)+(1 if a==0x11f4f0 else -1);trace.append([hex(a),reg(0),reg(1)]);ret();return
  if a==0x10e9fc:state['invalid']+=1;trace.append(['invalidate']);ret();return
  if a==0x700100:state['release']+=1;trace.append(['release',reg(0)]);ret();return
  if a==0xad5c:state['delete']+=1;trace.append(['delete',reg(0)]);ret();return
  if a==0xf6cf8:ret(state['param']);return
  if a==0x700104:ret(state['normalized']);return
  if a==0x656e0:state['value']=reg(1);trace.append(['setValue',reg(1)]);ret();return
  if a==0x124200:
   name=text(reg(1));v=attrs.get(name,'');ptr=0x50c000+len(trace)*128;u.mem_write(ptr,v.encode()+b'\0');trace.append(['getString',name]);ret(ptr);return
  if a==0x124324:trace.append(['getInt',text(reg(1))]);ret(state['width']);return
  if a==0x700110:trace.append(['lookup',text(reg(1)),text(reg(2))]);ret(lookup.get(text(reg(1)),0));return
  if a==0xf940c:w(reg(0),0);trace.append(['bitmap',text(reg(2))]);ret(reg(0));return
  if a==0x700108:trace.append(['getValue',reg(0)]);ret(values.get(reg(0),0));return
  if a==0x70010c:values[reg(0)]=reg(1);trace.append(['paramSet',reg(0),reg(1),reg(2)]);ret();return
  if a==0x11acf0:ret(params.get(reg(1),0));return
  if a==0x12078:ret(int(timers.get(reg(0),False)));return
  if a==0x12110:ret(1);return
  if a in [0x12228,0x11ff8,0x121b0]:timers[reg(0)]=a==0x12228;trace.append([hex(a),reg(0)]);ret(1);return
  if a==0x1877e0:ret(int(flt(reg(0))>flt(reg(1))));return
  if a==0x187780:ret(int(flt(reg(0))==flt(reg(1))));return
  if a==0x4fe0c:state['id']=text(reg(1));trace.append(['MessageAttributes',text(reg(1))]);ret(reg(0));return
  if a==0x4fdac:state['url']=text(reg(1));trace.append(['setURL',text(reg(1))]);ret();return
  if a==0x124ae8:trace.append(['lookupOrAdd',text(reg(1))]);ret(0x50d000);return
  if a==0x1259c8:state['messageIndex']=reg(2);trace.append(['setIndex',reg(2),reg(3)]);ret();return
  if a==0x50208:state['type']=reg(2);trace.append(['MutableMessageEvent',reg(2),reg(3)]);ret(reg(0));return
  if a==0x4ef38:state['sends']+=1;state['index']=state['messageIndex'];state['valid']=int(state['id']=='presetMuteGroup' and state['url']=='mutegroup' and state['type']==0x4a4d);trace.append(['sendEvent',reg(0),reg(1)]);ret(1);return
  if a in [0xe5c24,0x124690]:trace.append(['cleanup',hex(a)]);ret();return
  if a==0x11fc24:trace.append(['changed',reg(0)]);ret();return
  # Reject execution outside exact app target bodies (plus assigned app callees).
  if not (entry<=a<end or n==18 and any(lo<=a<lo+84 for lo in [0x678a8,0x67854,0x677ac]) or n==19 and 0x9ded0<=a<0x9dff4):
   raise RuntimeError(f'unmodeled call {a:x} trace {trace[-6:]}')
 m=target(n);entry=m['address'];end=entry+m['size'];u.reg_write(UC_ARM_REG_SP,0x6ff000);u.reg_write(UC_ARM_REG_LR,0x700000);u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,rect);u.reg_write(UC_ARM_REG_R2,0)
 if n in [2,3,4,5,9]:u.reg_write(UC_ARM_REG_R1,pointers[new])
 if n==8:u.reg_write(UC_ARM_REG_R1,state['param'])
 if n==18:u.reg_write(UC_ARM_REG_R1,attr)
 if n==16:u.reg_write(UC_ARM_REG_R1,pa);u.reg_write(UC_ARM_REG_R2,args[1])
 if n==17:u.reg_write(UC_ARM_REG_R1,args[0])
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(entry,0x700000,count=10000)
 assert u.reg_read(UC_ARM_REG_PC)==0x700000, "native execution did not return"
 if n in [1,10]:out=[int(r(obj+0x58)==0),int(r(obj+0x5c)==0)]
 elif n in [2,3,4,5,9]:out=[{0:0,pa:1,pb:2}[r(obj+offset)],observers[pa],observers[pb],state['invalid']]
 elif n in [6,7,14]:out=[state['release'],state['delete']]
 elif n in [11,12]:out=[sum(r(obj+x)==0 for x in [0x68,0x64,0x6c,0x70,0x74]),1]
 elif n in [13,15]:
  out=[sum(r(obj+x)==0 for x in [0x5c,0x60,0x64,0x68,0x6c,0x70])+sum(bytes(u.mem_read(obj+x,1))==b'\0' for x in [0x58,0x59,0x5a])+int(bytes(u.mem_read(obj+0x74,16))==bytes(16))+int(bytes(u.mem_read(obj+0x84,16))==bytes(16))]
 elif n==8:out=[int(state['param']!=0),int(flt(state['value'])*100)]
 elif n==18:out=[int(r(obj+0x64)==pa),int(r(obj+0x68)==pb),int(r(obj+0x6c)==0x507000),r(obj+0x60),0];out[3]=struct.unpack('<i',struct.pack('<I',out[3]))[0]
 else:out=[int(flt(values[pa])*100),int(flt(values[pb])*100),int(timers.get(0x509000+args[0]*64,False)),int(timers[obj+0x98])]
 if n in [17,19]:out += [state['sends'],state['index'],state['valid']]
 return {'argv':[n,*args],'expected':out,'native_trace':trace}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
 assert hashlib.sha256(ELF.read_bytes()).hexdigest()==SHA
 ranges=[]
 with ELF.open('rb') as f:
  e=ELFFile(f)
  for n in range(1,20):
   m=target(n);sec=e.get_section(m['section']);offset=sec['sh_offset']+m['address']-sec['sh_addr'];raw=sec.data()[m['address']-sec['sh_addr']:m['address']-sec['sh_addr']+m['size']]
   assert hashlib.sha256(raw).hexdigest()==re.search(r'section \.text; SHA256 `([0-9a-f]+)`',(packet(n)/'ELF_CONTEXT.md').read_text()).group(1)
   ranges.append({'packet':n,'metadata':m,'file_offset':offset,'range_sha256':hashlib.sha256(raw).hexdigest()})
 cases=[]
 for n in range(1,20):
  if n in [2,3,4,5,9]:inputs=[[old,new] for old in range(3) for new in range(3)]
  elif n in [6,7,14]:inputs=[[0],[1]]
  elif n==8:inputs=[[v,p] for v in [0,25,100] for p in [0,1]]
  elif n==18:inputs=[[c,p,w] for c in [0,1] for p in [0,1] for w in [0,7,-3]]
  elif n==16:inputs=[[tag,msg,v,ex] for tag in [0,7,8,15] for msg in [0,1,2,3,4] for v in [0,100] for ex in [0,1]]
  elif n==17:inputs=[[tag,0,v,0,c] for tag in [0,7] for v in [0,100] for c in [0,1]]
  elif n==19:inputs=[[tag,0,v,ex,c] for tag in [0,7] for v in [0,100] for ex in [0,1] for c in [0,1]]
  else:inputs=[[]]
  for inp in inputs:cases.append(run(n,inp))
 Path(a.out).write_text(json.dumps({'oracle':'original ARM instructions in Unicorn; Core/provider boundary stubs only','elf_sha256':SHA,'unicorn_version':unicorn.__version__,'ranges':ranges,'cases':cases},indent=2)+'\n');print(len(cases),'native executions')
if __name__=='__main__':main()
