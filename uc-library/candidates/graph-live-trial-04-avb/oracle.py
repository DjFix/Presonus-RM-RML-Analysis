"""Execute only five verified native method ranges; named external calls are boundaries."""
import hashlib,json,struct,itertools,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
BASE=Path('uc-library/candidates/graph-live-trial-04-avb')
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def pack(*x):return struct.pack('<'+'I'*len(x),*x)
def generate():
 raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 bodies=[]; originals=[]
 for i in range(1,6):
  p=Path(f'temp/recovery-work/graph-live-trial-04/trial04_avb_{i}-packet')
  d=json.loads((p/'native-context.json').read_text());b=next(iter(d['bodies'].values()));bodies.append(b)
  assert hashlib.sha256(raw[b['file_offset']:b['file_offset']+b['size']]).hexdigest()==b['bytes_sha256']
  originals.append(json.loads((p/'context.json').read_text())['originals'])
 with ELF.open('rb') as f:
  elf=ELFFile(f)
  for b in bodies:
   s=elf.get_section(b['section_index']);assert s.name==b['section'];assert b['file_offset']==s['sh_offset']+b['address']-s['sh_addr']
 cases=[]
 # Cartesian branch coverage plus high-bit stream identities and old/null slots.
 for target,clock,disable,mode,old,link in itertools.product(range(1,6),range(2),range(2),[-1,1,2],range(2),[0,1,2]):
  ident=[0,0x1122334455667788,0xffffffffffffffff,0x8000000000000000][(target+mode+link)%4]
  types=[0,1,2,3,-1,4] if target==1 else [0]
  for typ in types:
   args=[target,typ,ident,clock,mode,disable,old,link,0x76543210]
   cases.append({'input':args,'expected':execute(raw,bodies,args)})
 out={'version':1,'oracle':'original ELF ARM Unicorn','elf_sha256':SHA,'ranges':bodies,'cases':cases,'exclusions':['Native class memory is synthetic; no original layout claim.','Manager/routing/debug and indirect packet sender calls are boundary stubs.','Manager returns distinct non-null listeners; allocation failure/native null dereference outside domain.','Core native debug body excluded; actual pinned Core used in C++ source port.','Packet padding bytes uninitialized; only explicit initialized fields compared.']}
 (BASE/'fixtures.json').write_text(json.dumps(out,indent=2)+'\n');print(len(cases),'native executions')
def execute(raw,bodies,args):
 target,typ,ident,clock,mode,disable,old,link,source=args
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x1000,0x500000)
 for b in bodies:u.mem_write(b['address'],raw[b['file_offset']:b['file_offset']+b['size']])
 obj=0x400000;owner=0x401000;manager=0x402000;sender=0x403000;vtable=0x404000;send=0x405000;stop=0x406000;sp=0x4f0000
 def put(a,*v):u.mem_write(a,pack(*v))
 def get(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 put(obj+0x98,owner,manager);put(owner+0x380,sender);put(owner+0x174,source);put(sender,vtable);put(vtable,send);put(obj+0xb0,link)
 handles={};slots=[]
 for i in range(4):
  a=0x410000+i*0x100;u.mem_write(a,bytes([10+i]));handles[a]=10+i;slots.append(a if old else 0)
 put(obj+0xa0,*slots)
 trace=[];writes=[];nextid=40
 def hook(uc,a,size,data):
  nonlocal nextid
  r=[uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
  if a==stop:uc.emu_stop();return
  if a==0xa6f28:trace.append(['remove',handles[r[1]]])
  elif a==0xa70c8:
   n=nextid;nextid+=1;p=0x420000+n*0x100;handles[p]=n;uc.mem_write(p,bytes([n]));trace.append(['add',r[2],r[3],get(uc.reg_read(UC_ARM_REG_SP)),get(uc.reg_read(UC_ARM_REG_SP)+4),n]);uc.reg_write(UC_ARM_REG_R0,p)
  elif a==0xa6c40:trace.append(['clock',handles[r[1]]])
  elif a in [0xa988,0x116a38]:trace.append(['debug',r[1],r[2]])
  elif a==0xa7fd0:trace.append(['configureStaticTalkerStreams'])
  elif a==0xa854c:trace.append(['routeLink'])
  elif a==send:
   p=r[1];magic=get(p);size=get(p+4);words=[get(p+i*4) for i in range(size//4-1)];enabled=uc.mem_read(p+size-4,1)[0];trace.append(['packet']+words+[enabled])
  elif any(b['address']<=a<b['address']+b['size'] for b in bodies):return
  else:raise RuntimeError(f'unexpected execute {a:x}')
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 def write(uc,access,a,size,value,data):
  if obj+0xa0<=a<obj+0xb0:writes.append([a-obj,handles.get(value,0)])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,typ&0xffffffff);u.reg_write(UC_ARM_REG_R2,ident&0xffffffff);u.reg_write(UC_ARM_REG_R3,ident>>32);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop);put(sp,clock,mode&0xffffffff,disable)
 u.emu_start(bodies[target-1]['address'],stop,count=10000)
 assert u.reg_read(UC_ARM_REG_PC)==stop
 return {'trace':trace,'state':[handles.get(get(obj+0xa0+i*4),0) for i in range(4)],'writes':writes}
if __name__=='__main__':generate()
