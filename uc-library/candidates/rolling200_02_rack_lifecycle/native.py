"""Independent exact ARM application-body oracle. Original Core never executes.
Named boundaries model source-port providers, with real host operator new/delete backing
for private guest allocations. No guest syscall/network/device passthrough.
"""
import ctypes, hashlib, json, pathlib, struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_LR
R=pathlib.Path.cwd(); E=R/'rootfs/RML16AI_Rack_13731/home/root/mixer'; SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
PACK=R/'temp/recovery-work/rolling200-02/next-implementation08/prepared09-rack_lifecycle08/packets'
raw=E.read_bytes(); assert hashlib.sha256(raw).hexdigest()==SHA
lib=ctypes.CDLL("libstdc++.so.6");opnew=lib._Znwm;opnew.argtypes=[ctypes.c_size_t];opnew.restype=ctypes.c_void_p;opdelete=lib._ZdlPv;opdelete.argtypes=[ctypes.c_void_p]
with E.open('rb') as f:
 elf=ELFFile(f); loads=[(s['p_vaddr'],s.data(),s['p_memsz']) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
 def data(a,n):
  for sec in elf.iter_sections():
   if sec['sh_type']!='SHT_NOBITS' and sec['sh_addr']<=a and a+n<=sec['sh_addr']+sec['sh_size']:return sec.data()[a-sec['sh_addr']:a-sec['sh_addr']+n]
  raise ValueError(hex(a))
 def string(a):
  if not a:return None
  return data(a,128).split(b'\0')[0].decode()
 params=[]
 for i in range(5):
  b=data(0x355dc8+i*84,84); w=struct.unpack('<21I',b)
  params.append(dict(type=w[0],tag=w[1],name=b[8:40].split(b'\0')[0].decode(),values=list(struct.unpack('<5f',b[40:60])),flags=w[15],unit=string(w[16]),curve=string(w[17]),strings=[string(x) for x in struct.unpack('<2I',data(w[18],8))],title=string(w[19]),short_title=string(w[20])))
 ranges=[];cases=[]
 for i in range(14,19):
  packet=PACK/f'rolling200_02_rack_lifecycle_{i}';req=json.loads((packet/'request.json').read_text());t=req['targets'][0];a=t['address'];n=t['size'];ctor=i<16
  sym=next(s for s in elf.get_section_by_name('.symtab').get_symbol_by_name(t['mangled']) if s['st_value']==a and s['st_size']==n)
  sec=elf.get_section(sym['st_shndx']);off=sec['sh_offset']+a-sec['sh_addr'];h=hashlib.sha256(raw[off:off+n]).hexdigest();assert h in (packet/'ELF_CONTEXT.md').read_text()
  ranges.append(dict(task=i,mangled=t['mangled'],address=a,size=n,section=sec.name,file_offset=off,sha256=h))
  for filled in ([False] if ctor else [False,True]):
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
   mapped=set()
   for va,b,memsize in loads:
    for page in range(va&~4095,(va+memsize+4095)&~4095,4096):
     if page not in mapped:u.mem_map(page,4096);mapped.add(page)
    u.mem_write(va,b)
   SELF=0x1000000;STACK=0x1100000;STOP=0x1200000;MIX=0x1300000;REG=0x1300100
   u.mem_map(SELF,4096);u.mem_map(STACK,0x10000);u.mem_map(STOP,4096)
   u.mem_write(SELF,bytes([0xa5])*0x1e8)
   alloc={};trace=[];writes=[];frees=[]
   def new(key,size):
    assert key not in alloc
    p=opnew(size);assert p;alloc[key]=p
   def free(key):
    assert key in alloc
    opdelete(alloc.pop(key));frees.append(key)
   new('object',0x1e8)
   if filled:
    for x in [0xf4,0x108,0x11c,0x130]:new(hex(x),20)
   def w(p,v,n=4):u.mem_write(p,int(v).to_bytes(n,'little'))
   def read(p,n=4):return int.from_bytes(u.mem_read(p,n),'little')
   def ret():u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   def write_guard(uc,access,p,n,v,unused):
    assert SELF<=p and p+n<=SELF+0x1e8 or STACK<=p and p+n<=STACK+0x10000,('private write',hex(p))
    if SELF<=p<SELF+0x1e8:writes.append([p-SELF,n,v&((1<<(8*n))-1)])
   def read_guard(uc,access,p,n,v,unused):
    assert SELF<=p and p+n<=SELF+0x1e8 or STACK<=p and p+n<=STACK+0x10000 or any(va<=p and p+n<=va+memsize for va,b,memsize in loads),('private read',hex(p))
   def hook(uc,pc,size,unused):
    if pc==STOP:uc.emu_stop();return
    if a<=pc<a+n:return
    r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2);d=r0-SELF
    if pc==0x52ae0:
     assert ctor and (r0,r1,r2)==(SELF,MIX,REG);trace.append(['base_ctor']);ret()
    elif pc==0x7f1e8:
     assert ctor and d in [0xf4,0x108,0x11c] and (r1,r2)==(0,5);trace.append(['vector_ctor',d,0,5]);ret()
    elif pc==0x7efbc:
     assert ctor and d==0x130;trace.append(['task_resize',d,0,5]);ret()
    elif pc==0x8c59c:
     assert ctor and d in [0x150,0x170,0x190,0x1b0] and r1==0x3f800000;trace.append(['timer_ctor',d,r1]);ret()
    elif pc==0x11ec54:
     assert ctor and (d,r1,r2)==(0x28,0x355dc8,5);trace.append(['parameters',d,r1,r2]);ret()
    elif pc==0x8c630:
     assert not ctor and d in [0x150,0x170,0x190,0x1b0];trace.append(['timer_dtor',d]);ret()
    elif pc in [0x7f150,0x7f180]:
     assert not ctor and d in ([0x130] if pc==0x7f150 else [0xf4,0x108,0x11c]);trace.append(['vector_dtor',d])
     if filled:free(hex(d))
     ret()
    elif pc==0x5292c:
     assert not ctor and r0==SELF;trace.append(['base_dtor']);ret()
    elif pc==0xac10:
     assert i==16 and r0==SELF;free('object');trace.append(['object_delete']);ret()
    else:raise RuntimeError('unbound PC '+hex(pc))
   u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write_guard);u.hook_add(UC_HOOK_MEM_READ,read_guard)
   for reg,v in [(UC_ARM_REG_R0,SELF),(UC_ARM_REG_R1,MIX),(UC_ARM_REG_R2,REG),(UC_ARM_REG_SP,STACK+0xf000),(UC_ARM_REG_LR,STOP)]:u.reg_write(reg,v)
   u.emu_start(a,STOP,count=1000);assert u.reg_read(UC_ARM_REG_PC)==STOP
   state={hex(x):read(SELF+x,1 if x==0x28 else 4) for x in [0x28,0x144,0x148,0x14c,0x1d4,0x1d8,0x1dc,0x1e0,0x1e4]} if ctor else {}
   assert ('object' not in alloc)==(i==16)
   cases.append(dict(task=i,filled=filled,trace=trace,writes=writes,state=state,actual_host_frees=frees.copy(),live_allocations=sorted(alloc)))
   for key in list(alloc):free(key)
 print(json.dumps(dict(elf_sha256=SHA,ranges=ranges,table_sha256=hashlib.sha256(data(0x355dc8,420)).hexdigest(),parameters=params,cases=cases,limitations='Normal application bodies only. External named provider boundaries modeled; original Core bodies never execute. Actual host operator new/delete back private guest allocation identities, not ARM allocator implementation. Native unwind/throwing destructors not exercised. Constructor body writes and call arguments captured; original layout and inheritance unresolved.'),indent=2))
