"""Execute only sealed target ARM bodies; all external providers are declared stubs.
No Core binary implementation executes. Synthetic memory is not an ABI claim.
"""
import hashlib, json, struct, sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
BASE=0x1000000; MIX=BASE+0x1000; REG=BASE+0x2000; SELF=BASE; GROUP=BASE+0x3000
PAR=BASE+0x10000; CTRL=BASE+0x20000; CHANNEL=BASE+0x30000; VT=BASE+0x40000; STOP=0x2000000
SLOTS={0x10:STOP+0x100,0x44:STOP+0x200,0x58:STOP+0x300}
def cases():
 out=[]
 def add(method,**kw):out.append(dict(method=method,**kw))
 for expired in [0,1]:
  for bits in [0,0x3f800000,0x3f000000,0x7fc00000,0x80000000]:
   for present in [0,1]:add(1,expired=expired,bits=bits,present=present)
 for tag in [-1,0,4,5,6]:
  for on in [0,1]:
   for present in [0,1]:add(2,tag=tag,on=on,present=present)
 for status in [-1,0,1,2,3,4]:
  for clients in [0,1,8]:add(3,status=status,clients=clients)
 for n in [0,1,3]:
  for m in [0,1,2]:
   if m<=n:add(4,n=n,m=m)
 for n in [0,1,3]:
  for mask in [0,1,7]:add(5,n=n,mask=mask)
 for present in [0,1]:add(6,present=present)
 for n in [0,1,3]:add(7,n=n)
 for n,m,k in [(0,0,0),(1,0,0),(0,2,0),(0,0,3),(1,2,3)]:add(8,n=n,m=m,k=k)
 for tag in [0,4,5,100]:
  for bits in [0,0x3f800000,0x3f000000,0x7fc00000]:add(9,tag=tag,bits=bits)
 for n in [0,1,3]:
  for mask in [0,1,7]:add(10,n=n,mask=mask)
 return out

def run(case, bodies, image, loads):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 ranges=[]
 for va,data,memsz in loads:
  lo=va&~4095; hi=(va+memsz+4095)&~4095
  if ranges and lo<=ranges[-1][1]:ranges[-1][1]=max(hi,ranges[-1][1])
  else:ranges.append([lo,hi])
 for lo,hi in ranges:u.mem_map(lo,hi-lo)
 for va,data,memsz in loads:u.mem_write(va,data)
 u.mem_map(BASE,0x80000);u.mem_map(STOP,0x1000);u.mem_map(0x3000000,0x10000)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def obj(a):w(a,VT)
 for off,target in SLOTS.items():w(VT+off,target)
 obj(SELF)
 for i in range(128):obj(PAR+i*0x100);obj(CTRL+i*0x100);obj(CHANNEL+i*0x400)
 w(SELF+0x8c,MIX);w(SELF+0x90,REG);w(MIX+0x2d8,CHANNEL+0x8000)
 n=case.get('n',3);m=case.get('m',2);k=case.get('k',3)
 if case['method']==7:k=n
 for off,count,start in [(0xf8,n,0),(0x10c,m,16),(0x120,k,32)]:
  arr=BASE+0x50000+start*0x10;w(SELF+off,arr);w(SELF+off+4,count)
  for i in range(count):w(arr+i*4,CTRL+(start+i)*0x100)
 arr=BASE+0x58000;w(MIX+0x134,arr);w(MIX+0x138,n)
 for i in range(n):w(arr+i*4,CHANNEL+i*0x400);w(CHANNEL+i*0x400+0x170,10+i)
 w(SELF+0x1d4,case.get('status',0));w(SELF+0x1e0,case.get('bits',0));w(SELF+0x1e4,PAR if case.get('present',1) else 0)
 w(SELF+0x14c,PAR if case.get('present',1) else 0)
 trace=[]; lookup={}; values={PAR:case.get('bits',0)}; attached=True
 def paddr(owner,tag):
  if case['method']==2 and not case['present']:return 0
  key=(owner,tag)
  if key not in lookup:lookup[key]=PAR+(len(lookup)+1)*0x100
  return lookup[key]
 def labelpar(a):
  if a==0:return 'null'
  if a==PAR:return 'monitor'
  for (o,t),p in lookup.items():
   if p==a:
    owner='self' if o==SELF else ('source' if o==CHANNEL+0x8000 else 'ch'+str((o-CHANNEL)//0x400))
    return owner+':'+str(t)
  raise ValueError(hex(a))
 def labelctrl(a):return str((a-CTRL)//0x100)
 def ret(v=0):u.reg_write(UC_ARM_REG_R0,v&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def hook(uc,a,size,data):
  nonlocal attached
  if a==STOP:uc.emu_stop();return
  a0=uc.reg_read(UC_ARM_REG_R0);a1=uc.reg_read(UC_ARM_REG_R1);a2=uc.reg_read(UC_ARM_REG_R2)
  if a==0x8c758:ret(case.get('expired',0))
  elif a==0x1578e0:
   f=lambda b:struct.unpack('<f',struct.pack('<I',b))[0]
   ret(int(f(a0)==f(a1)))
  elif a==0x119c4c:ret(paddr(a0,a1))
  elif a==0x8e4ac:ret(GROUP+a1*0x100)
  elif a==0x8d9ec:
   if case['method'] in [5,10] and not (case['mask']&(1<<(a1-10))):ret(0)
   else:ret(CTRL+(a1 if case['method']==3 else (a1-10 if case['method'] in [5,10] else 60))*0x100)
  elif a==0x8f580:ret(PAR)
  elif a==0xacf4:ret(a0)
  elif a==0x8fbc8:trace.append('blink '+labelctrl(a0)+' '+str(a1));ret()
  elif a==0x2f464:ret(case.get('clients',0))
  elif a==0x116a38:ret() # Diagnostic only; no production side effect.
  elif a==0x2f31c:
   assert a0==MIX and a1==SELF+0x84
   trace.append('removeDelegate');ret()
  elif a==0x11c2e4:
   assert a0==PAR and a1==SELF+4
   attached=False;ret()
  elif a==0x11dc28:trace.append('changed '+labelpar(a0));ret()
  elif a==SLOTS[0x10]:trace.append('bind '+labelctrl(a0)+' '+labelpar(a1)+' '+str(a2));ret(1)
  elif a==SLOTS[0x44]:ret(values.get(a0,0))
  elif a==SLOTS[0x58]:
   trace.append('set '+labelpar(a0)+' '+str(a1)+' '+str(a2));values[a0]=a1;ret()
  elif not (bodies[case['method']]['address']<=a<bodies[case['method']]['address']+bodies[case['method']]['size']):
   raise RuntimeError('unbound execution '+hex(a))
 u.hook_add(UC_HOOK_CODE,hook)
 u.reg_write(UC_ARM_REG_SP,0x300f000);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,SELF)
 u.reg_write(UC_ARM_REG_R1,case.get('tag',BASE+0x60000));u.reg_write(UC_ARM_REG_R2,case.get('on',0))
 u.emu_start(bodies[case['method']]['address'],STOP,count=10000)
 assert u.reg_read(UC_ARM_REG_PC)==STOP
 if case['method']==1:trace.append('return '+str(u.reg_read(UC_ARM_REG_R0)))
 if case['method']==6:trace.append('attached '+str(int(attached)))
 if case['method']==9:trace.append('saved '+str(r(SELF+0x1e0)));trace.append('monitor '+str(int(r(SELF+0x1e4)!=0)))
 return trace

def main():
 image=ELF.read_bytes();assert hashlib.sha256(image).hexdigest()==SHA
 bodies={};checks=[]
 with ELF.open('rb') as f:
  e=ELFFile(f);loads=[(s['p_vaddr'],s.data(),s['p_memsz']) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
  for i in range(1,11):
   p=Path(f'temp/recovery-work/graph-live-trial-07/trial07_rackpanel_{i}-packet/native-context.json');d=json.loads(p.read_text());b=d['bodies'][d['roots'][0]];bodies[i]=b
   sec=e.get_section(b['section_index']);assert sec.name==b['section'];off=sec['sh_offset']+b['address']-sec['sh_addr'];assert off==b['file_offset']
   assert hashlib.sha256(image[off:off+b['size']]).hexdigest()==b['bytes_sha256'];checks.append(dict(method=i,address=b['address'],size=b['size'],section=b['section'],file_offset=off,sha256=b['bytes_sha256']))
 result=[dict(input=c,trace=run(c,bodies,image,loads)) for c in cases()]
 Path(sys.argv[1]).write_text(json.dumps(dict(version=1,elf_sha256=SHA,ranges=checks,cases=result),indent=2)+'\n')
 print('Native ARM executions',len(result))
if __name__=='__main__':main()
