"""Execute only sealed six application ARM ranges. No Core binary executes.
Clock, signed division, real-CCl interfaces and existing detach helper are
explicit intercepted boundaries; all unexpected PCs fail before execution.
Synthetic objects are test memory, not recovered declarations or layouts.
"""
import hashlib,json,pathlib,struct,collections
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
PACKETS=ROOT/'temp/recovery-work/rolling200-02/next-implementation15/prepared-rack-network15/packets'
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
MASK=(1<<64)-1
SELF=0x1000000;MIX=SELF+0x1000;NET=SELF+0x2000;PARAM=SELF+0x40000;VT=SELF+0x4000
ARRAY=SELF+0x5000;TASK=SELF+0x10000;QUEUE=SELF+0x20000;HEAP=SELF+0x30000
STACK=0x2000000;STOP=0x3000000;SET=STOP+4;EDIT=STOP+8;CONTROL=STOP+12;BROADCAST=STOP+16
IDS=[1,2,3,4,6,13]
def signed64(n):return n-(1<<64) if n>>63 else n
def milliseconds(n):
 n=signed64(n);return (abs(n)//1000000)*(-1 if n<0 else 1)
def read_inputs():
 raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 ranges={};loads=[]
 with ELF.open('rb') as f:
  e=ELFFile(f)
  for s in e.iter_segments():
   if s['p_type']=='PT_LOAD':loads.append((s['p_vaddr'],s.data(),s['p_memsz']))
  for i in IDS:
   p=PACKETS/f'rolling200_02_rack_network15_{i:02}'
   d=json.loads((p/'native-context.json').read_text());b=d['bodies'][d['roots'][0]]
   sec=e.get_section(b['section_index']);off=sec['sh_offset']+b['address']-sec['sh_addr']
   assert off==b['file_offset'];assert hashlib.sha256(raw[off:off+b['size']]).hexdigest()==b['bytes_sha256']
   ranges[i]={k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}
 return ranges,loads
RANGES,LOADS=read_inputs()
BOUNDARIES={0x116908:'legacy Core::GetAbsoluteTime entry',0x157a08:'signed division runtime entry',0x119c4c:'CCL Component::getParameterByTag entry',0x7d064:'existing detachLEDs helper entry',0xa7e4:'operator new entry',0x7f0f4:'CCL Vector::add entry',0x7efbc:'CCL Vector::resize entry',0x7f150:'CCL Vector destructor entry',SET:'Parameter::setValue virtual boundary',EDIT:'Parameter::performEdit virtual boundary',CONTROL:'Control::setParameter virtual boundary',BROADCAST:'Control::broadcastValue virtual boundary'}
AUDIT={'elf_sha256':SHA,'ranges':RANGES,'boundary_allowlist':{hex(k):v for k,v in BOUNDARIES.items()},'executed_core_body_pcs':[],'unexpected_pcs':[],'observed_pcs':{},'intercept_counts':{},'cases':0,'scope':'Only sealed target bodies execute. detachLEDs semantics are modeled from the existing canonical helper; real helper/provider regression required separately.'}
def run(c):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);maps=[]
 for va,data,size in LOADS:
  lo=va&~4095;hi=(va+size+4095)&~4095
  if maps and lo<=maps[-1][1]:maps[-1][1]=max(maps[-1][1],hi)
  else:maps.append([lo,hi])
 for lo,hi in maps:u.mem_map(lo,hi-lo)
 for va,data,size in LOADS:u.mem_write(va,data)
 u.mem_map(SELF,0x80000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
 def w(a,n):u.mem_write(a,struct.pack('<I',n&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def w64(a,n):w(a,n);w(a+4,n>>32)
 def r64(a):return r(a)|(r(a+4)<<32)
 def reg(n):return u.reg_read([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3][n])
 def ret(n=None):
  if n is not None:u.reg_write(UC_ARM_REG_R0,n&0xffffffff)
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 trace=[];created=[];allocated=HEAP;appended=False
 w(SELF+0x8c,MIX);w(MIX+0x2e0,NET if c['mask']&1 else 0);w(SELF+0x1dc,c['flags'])
 # Native reset literal points to a process-shared 64-bit millisecond cell.
 # Read literal instruction's bound actual cell rather than invent global address.
 reset_global=r(0x7eee8);w64(reset_global,c['start'])
 w(VT+0x58,SET);w(VT+0x1c,EDIT);w(VT+0x10,CONTROL);w(VT+0x20,BROADCAST)
 for tag in [1,12,17]:w(PARAM+tag*0x100,VT)
 for offset,count,index in [(0xf4,c['n'],0),(0x108,c['m'],16),(0x11c,c['k'],32)]:
  w(SELF+offset+4,ARRAY+index*4);w(SELF+offset+8,count)
  for j in range(count):
   a=SELF+0x6000+(index+j)*0x100;w(a,VT);w(ARRAY+(index+j)*4,a)
 for i,t in enumerate(c['tasks']):
  a=TASK+i*0x100;w(a,VT+0x100+i*4);w(VT+0x100+i*4,RANGES[1 if t[0]==0 else 2]['address'])
  w(a+4,PARAM+0x100 if t[1] else 0);w64(a+8,t[2]);w64(a+16,t[3])
 def writequeue(q):
  w(SELF+0x134,QUEUE);w(SELF+0x138,len(q))
  for j,i in enumerate(q):w(QUEUE+j*4,TASK+i*0x100)
 writequeue(c['queue'])
 def cid(a):return (a-(SELF+0x6000))//0x100
 def emitdetach():
  for count,start in [(c['n'],0),(c['m'],16),(c['k'],32)]:
   for i in range(count):trace.append(f'control:{start+i}:0')
 def hook(uc,pc,size,user):
  nonlocal allocated,appended
  AUDIT['observed_pcs'][hex(pc)]=AUDIT['observed_pcs'].get(hex(pc),0)+1
  if pc==STOP:u.emu_stop();return
  if pc in BOUNDARIES:
   AUDIT['intercept_counts'][hex(pc)]=AUDIT['intercept_counts'].get(hex(pc),0)+1
   if pc==0x116908:
    trace.append('clock');u.reg_write(UC_ARM_REG_R0,c['ns']&0xffffffff);u.reg_write(UC_ARM_REG_R1,c['ns']>>32);ret()
   elif pc==0x157a08:
    numerator=reg(0)|(reg(1)<<32);denominator=reg(2)|(reg(3)<<32);assert denominator==1000000
    value=milliseconds(numerator)&MASK;u.reg_write(UC_ARM_REG_R0,value&0xffffffff);u.reg_write(UC_ARM_REG_R1,value>>32);ret()
   elif pc==0x119c4c:
    tag=reg(1);owner=reg(0)
    assert tag in [1,12,17]
    present=bool(c['mask']&(8 if owner==SELF else (2 if tag==12 else 4)))
    ret(PARAM+tag*0x100 if present else 0)
   elif pc==SET:
    tag=(reg(0)-PARAM)//0x100;trace.append(f'set:{tag}:{reg(1)}:{reg(2)}')
    if tag==17 and c['mutate']:w(SELF+0x1dc,c['mutate'])
    ret()
   elif pc==EDIT:
    trace.append('edit:1')
    if c['append'] and not appended:
     n=r(SELF+0x138);w(QUEUE+n*4,TASK+c['append']*0x100);w(SELF+0x138,n+1);appended=True
    ret()
   elif pc==0x7d064:emitdetach();ret()
   elif pc==CONTROL:trace.append(f'control:{cid(reg(0))}:{reg(1)}');ret()
   elif pc==BROADCAST:trace.append(f'value:{cid(reg(0))}:{reg(1)}');ret()
   elif pc==0xa7e4:
    assert reg(0)==24;created.append(allocated);ret(allocated);allocated+=0x100
   elif pc==0x7efbc:
    # CCL resize(0) on temporary vector: storage remains empty.
    assert reg(1)==0;ret(1)
   elif pc==0x7f150:ret()
   elif pc==0x7f0f4:
    vector=reg(0);task=r(reg(1));count=r(vector+4)
    if not r(vector):w(vector,HEAP+0x4000)
    w(r(vector)+count*4,task);w(vector+4,count+1);ret(1)
   return
  allowed=([c['target']] if c['target'] in [1,2] else ([6,3,4] if c['target']==6 else [13,1,2] if c['target']==13 else [c['target']]))
  if not any(RANGES[i]['address']<=pc<RANGES[i]['address']+RANGES[i]['size'] for i in allowed):
   AUDIT['unexpected_pcs'].append(hex(pc));raise AssertionError(('Unexpected PC',hex(pc),c))
 u.hook_add(UC_HOOK_CODE,hook)
 u.reg_write(UC_ARM_REG_R0,TASK if c['target'] in [1,2] else SELF)
 u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP)
 try: u.emu_start(RANGES[c['target']]['address'],STOP,count=50000)
 except Exception:
  print('FAILED',c,'PC',hex(u.reg_read(UC_ARM_REG_PC)));raise
 assert u.reg_read(UC_ARM_REG_PC)==STOP,hex(u.reg_read(UC_ARM_REG_PC))
 out={'trace':trace,'flags':r(SELF+0x1dc),'queue':[],'created':[]}
 if c['target'] in [1,2]:out['result']=reg(0)
 count=r(SELF+0x138)
 for j in range(count):
  p=r(QUEUE+j*4)
  out['queue'].append((p-TASK)//0x100 if TASK<=p<TASK+0x10000 else 100+created.index(p))
 for a in created:out['created'].append([bool(r(a+4)),r64(a+8),r64(a+16)])
 AUDIT['cases']+=1
 return out

def inputs():
 cases=[]
 def add(t,**kw):
  d=dict(target=t,ns=501000000,start=0,delay=500,flags=0,mask=15,n=2,m=1,k=1,tasks=[[1,1,500,0]],queue=[],append=0,mutate=0);d.update(kw);cases.append(d)
 add(1,tasks=[[0,0,0,0]])
 for ns in [0,499999999,500000000,500999999,501000000,-1&MASK,-1000000&MASK,(1<<63)-1,1<<63]:
  for start,delay in [(0,500),(500,0),(MASK,1),((1<<63)-2,5),(1<<63,0),(0,MASK)]:
   for present in [0,1]:add(2,ns=ns,tasks=[[1,present,delay,start]])
 for t in [3,4]:
  for mask in range(16):
   for n,m,k in [(0,0,0),(1,2,1),(3,1,2),(8,7,6)]:add(t,mask=mask,n=n,m=m,k=k)
 for ns in [0,999000000,1000000000,1001000000,(1<<63)-1,1<<63]:
  for start in [0,1,MASK,(1<<63)-1]:
   for flags in [0,1,2,4,5,7,8,16,26]:add(6,ns=ns,start=start,flags=flags)
 for mutate in [18,20]:add(6,ns=1001000000,flags=2,mutate=mutate)
 for q in [[],[0],[1],[2],[0,1,2],[2,1,0],[1,1,0],[0,2,0,2],[1]*8,[0,1,2,1,0,2,1,0]]:
  for ns in [500000000,501000000]:add(13,ns=ns,tasks=[[0,0,0,0],[1,1,500,0],[1,0,499,0],[1,1,0,0]],queue=q)
 add(13,tasks=[[1,1,0,0],[1,0,0,0]],queue=[0],append=1)
 return cases

def produce():
 return {'elf_sha256':SHA,'ranges':RANGES,'boundaries':BOUNDARIES,'cases':[{'input':c,'expected':run(c)} for c in inputs()]}
if __name__=='__main__':
 out=produce();path=ROOT/'uc-library/tests/recovery/rack_network_tasks/fixtures.json';path.write_text(json.dumps(out,indent=2)+'\n')
 (ROOT/'evidence/recovery/2026-11-05/rolling200-02/rack-network15/native-pc-audit.json').write_text(json.dumps(AUDIT,indent=2)+'\n')
 print('Original executions',AUDIT['cases'])
