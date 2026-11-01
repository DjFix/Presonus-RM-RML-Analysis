"""Original ARM targets only; explicit boundary stubs, never Core recovery."""
import json,hashlib,struct,itertools,pathlib,datetime
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=pathlib.Path(__file__).resolve().parents[3];C=pathlib.Path(__file__).parent
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
sha=lambda b:hashlib.sha256(b).hexdigest()
raw=ELF.read_bytes();assert sha(raw)=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
ranges=[]
with ELF.open('rb') as f:
 e=ELFFile(f)
 for i in range(1,6):
  m=json.loads((ROOT/f'temp/recovery-work/graph-live-trial-05/trial05_scenes_{i}-packet/context.json').read_text())
  o=m['originals'][0]['original'];print(o) if False else None
  name=o.get('mangled',o.get('original_mangled'))
  sym=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==name)
  assert sym['st_value']==o['address'] and sym['st_size']==o['size']
  s=e.get_section(sym['st_shndx']);off=s['sh_offset']+sym['st_value']-s['sh_addr'];body=raw[off:off+sym['st_size']]
  ranges.append({'target':i,'mangled':name,'address':sym['st_value'],'size':sym['st_size'],'section':s.name,'file_offset':off,'sha256':sha(body)})
base=0x200000;params=0x210000;vt=0x220000;dele=0x230000;tbase=0x240000;stack=0x300000;stop=0x400000
getparam=0x119c4c;getvalue=0x400100;setvalue=0x400104;entry=0x400108;leave=0x40010c
f32=lambda u:struct.unpack('<f',struct.pack('<I',u))[0]
def execute(v):
 target,store,mask,state,recall,index,delegate,present,running,longer=v
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x70000,0x5000);u.mem_map(0x119000,0x1000);u.mem_map(0x157000,0x1000);u.mem_map(0x8c000,0x1000);u.mem_map(0x200000,0x60000);u.mem_map(stack,0x10000);u.mem_map(stop,0x1000)
 for r in ranges:u.mem_write(r['address'],raw[r['file_offset']:r['file_offset']+r['size']])
 def w(a,n):u.mem_write(a,struct.pack('<I',n&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 w(vt+0x44,getvalue);w(vt+0x58,setvalue)
 vals=[(store if i==0 else 0x3e800000) if mask&(1<<i) else None for i in range(8)]
 for i in range(8):w(params+i*0x100,vt);w(params+i*0x100+12,params+i*0x100+32);w(params+i*0x100+36,i)
 w(base+0xa0,0xffffffff);w(base+0xa8,dele if delegate else 0);w(dele,dele+16);w(dele+16,entry);w(dele+20,leave)
 w(base+0x90,tbase);w(base+0x94,4)
 for i in range(4):w(tbase+4*i,tbase+0x100+0x10*i if present&(1<<i) else 0)
 trace=[];lookups=[]
 def hook(u,pc,size,_):
  a=u.reg_read(UC_ARM_REG_R0);b=u.reg_read(UC_ARM_REG_R1);d=u.reg_read(UC_ARM_REG_R2)
  ret=None
  if pc==stop:u.emu_stop();return
  if pc==getparam:
   lookups.append(b);ret=params+b*0x100 if b<8 and vals[b] is not None else 0
  elif pc==getvalue:
   i=(a-params)//0x100;trace.append('g'+str(i));ret=vals[i]
  elif pc==setvalue:
   i=(a-params)//0x100;trace.append(f's{i}:{b}:{d}');vals[i]=b;ret=0
  elif pc==0x157940:ret=int(f32(a)>f32(b))
  elif pc in (entry,leave):trace.append('enter' if pc==entry else 'leave');ret=0
  elif pc==0x73dd8:trace.append('r'+str(b));ret=recall
  elif pc==0x1196a8:trace.append('idle');ret=0
  elif pc in (0x8c6c0,0x8c758,0x8c7f8):
   i=(a-tbase-0x100)//0x10
   if pc==0x8c6c0:trace.append('e'+str(i));ret=int(bool(running&(1<<i)))
   elif pc==0x8c758:trace.append('l'+str(i));ret=int(bool(longer&(1<<i)))
   else:trace.append('end'+str(i));ret=0
  if ret is not None:u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook)
 u.reg_write(UC_ARM_REG_SP,stack+0x8000);u.reg_write(UC_ARM_REG_R0,base);u.reg_write(UC_ARM_REG_R1,index if target==4 else state);u.reg_write(UC_ARM_REG_LR,stop)
 u.emu_start(ranges[target-1]['address'],stop+4,count=20000)
 assert u.reg_read(UC_ARM_REG_PC)==stop
 result=u.reg_read(UC_ARM_REG_R0) if target==1 else -1
 observation=f'{result} {r(base+0xa0)} '+' '.join('-' if x is None else str(x) for x in vals)+' |'+(' '+' '.join(trace) if trace else '')
 return observation,lookups
cases=[]
def add(v):
 observation,lookup=execute(v);cases.append({'inputs':v,'observation':observation,'native_lookup_tags':lookup})
# Store value class boundaries include signed zeros, subnormals, infinities, NaNs.
for store,mask in itertools.product([0,0x80000000,1,0x80000001,0x3f800000,0xbf800000,0x7f800000,0xff800000,0x7fc00000,0x7f800001],[0,1,255]):add([1,store,mask,0,0,0,0,0,0,0])
for target,state,mask,delegate in itertools.product([2,3],[0,1],[0,3,7,15,255,0b11010101],[0,1]):add([target,0,mask,state,0,0,delegate,0,0,0])
for rec,index,mask in itertools.product([0,1],[0,1,2,6,7,0xffffffff,0xfffffffe],[0,3,7,255]):add([4,0,mask,0,rec,index,0,0,0,0])
for store,mask,present,running,longer,rec in itertools.product([0,0x3f800000],[1,255],[0,15,5],[0,15,10],[0,15,5],[0,1]):add([5,store,mask,0,rec,0,0,present,running,longer])
(C/'fixtures.json').write_text(json.dumps({'oracle':'original ARM Unicorn with explicit provider/app stubs','ranges':ranges,'cases':cases},indent=2)+'\n')
print('Original executions',len(cases))
