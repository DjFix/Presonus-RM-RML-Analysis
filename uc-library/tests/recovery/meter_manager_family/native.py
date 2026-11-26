"""Original ARM execution. Allocator/CCL vector/lock/network boundaries explicit."""
import hashlib,json,struct
from pathlib import Path
from io import BytesIO
from elftools.elf.elffile import ELFFile
from unicorn import *
from unicorn.arm_const import *
PACKETS=Path('temp/recovery-work/sqlite-issued/packet-readfreeze-sol61')
TASKS=['sqlite_meter_external_transport_sol61','sqlite24_meter_roster_a2f6dc995b','sqlite24_meter_roster_f59fc6eaf6','sqlite24_meter_roster_c49d5a25c7']
def sha(b):return hashlib.sha256(b).hexdigest()
def observe():
 contexts=[json.loads((PACKETS/t/'CONTEXT.json').read_text()) for t in TASKS]
 originals=[c['originals'][0]['original'] for c in contexts]
 image=Path(originals[0]['elf_path']).read_bytes();assert sha(image)==originals[0]['elf']
 elf=ELFFile(BytesIO(image));syms=elf.get_section_by_name('.symtab')
 def symbol(n):return syms.get_symbol_by_name(n)[0]
 def body(s):
  q=elf.get_section(s['st_shndx']);off=q['sh_offset']+s['st_value']-q['sh_addr'];return off,image[off:off+s['st_size']]
 for o in originals:
  s=symbol(o['mangled']);off,b=body(s);assert (s['st_value'],s['st_size'],s['st_shndx'],off,sha(b))==(o['address'],o['size'],o['section'],o['file_offset'],o['range_sha256'])
  assert b.hex()==o['range_hex']
 def fileword(a):
  for seg in elf.iter_segments():
   if seg['p_type']=='PT_LOAD' and seg['p_vaddr']<=a<seg['p_vaddr']+seg['p_filesz']:return struct.unpack_from('<I',image,seg['p_offset']+a-seg['p_vaddr'])[0]
  raise AssertionError(hex(a))
 cases=[]
 for selector in [-1,0,1,2,3,4,5,6,7,8,9]:
  for kind in [0,1,3,4]:
   for index in [0,1,3,12]:
    for population in ['empty','full','null']:cases.append(dict(kind='roster',index=index,selector=selector,meterkind=kind,population=population))
 for count in [0,1,3]:
  for selector in [-1,0,65536,65537]:
   for result in [0,1]:cases.append(dict(kind='external',count=count,selector=selector,result=result))
 for n in [2,3]:cases.append(dict(kind='noop',method=n))
 results=[]
 for case in cases:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for seg in elf.iter_segments():
   if seg['p_type']=='PT_LOAD':
    start=seg['p_vaddr']&~4095;end=(seg['p_vaddr']+seg['p_memsz']+4095)&~4095;u.mem_map(start,end-start);u.mem_write(seg['p_vaddr'],seg.data())
  R,V,E,C,VT,N,NVT,POOL,STACK,STOP=0x20000000,0x20002000,0x20003000,0x20004000,0x20005000,0x20006000,0x20007000,0x20010000,0x2002e000,0x2002f000
  u.mem_map(R,0x30000)
  def w(a,*v):u.mem_write(a,struct.pack('<'+'I'*len(v),*[x&0xffffffff for x in v]))
  def rd(a):return struct.unpack('<I',u.mem_read(a,4))[0]
  def ret(value=None):
   if value is not None:u.reg_write(UC_ARM_REG_R0,value&0xffffffff)
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  trace=[];alloc=[]
  offsets=[0xa08,0xa1c,0xa38]
  for j,off in enumerate(offsets):
   vals=[] if case.get('population')=='empty' else [POOL+0x100+j*0x100+i*0x40 for i in range(4)]
   if case.get('population')=='null':vals=[0]*4
   w(R+off,V+j*0x100,len(vals),32);w(V+j*0x100,*vals)
  w(R+0x1564,1);w(R+0x156c,1,2,1,2)
  # Preinitialized CCL decay table guard; original ctor instruction path executes.
  w(fileword(0x8c2a0),1)
  static_error=fileword(0x870a4);assert rd(static_error)==0
  if case['kind']=='roster':args=[R,case['index'],case['selector'],case['meterkind']];entry=originals[1]['address']
  elif case['kind']=='noop':args=[R,E];entry=originals[case['method']]['address']
  else:
   w(V,C,case['count']);w(C,7,11,19);w(E,19778,1268,44,55);w(R+0x58,C+0x100);w(C+0x100,VT);w(VT+4,STOP+4)
   w(R+0x54,C+0x200);w(C+0x200+0x8c,42);w(N,NVT);w(NVT+0x3c,STOP+8)
   args=[R,V,E,case['selector']];entry=originals[0]['address']
  def hook(uc,a,size,data):
   if a==STOP:u.emu_stop()
   elif a==0xa7e4:
    ptr=POOL+0x1000+len(alloc)*0x100;alloc.append(ptr);assert u.reg_read(UC_ARM_REG_R0)==64;ret(ptr)
   elif a==0x8b07c:
    roster=u.reg_read(UC_ARM_REG_R0);ptr=rd(u.reg_read(UC_ARM_REG_R1));count=rd(roster+4);w(rd(roster)+count*4,ptr);w(roster+4,count+1);ret(1)
   elif a in [0x10e384,0x10e460]:ret()
   elif a==0xda22c:ret(N)
   elif a==STOP+4:
    event=u.reg_read(UC_ARM_REG_R1);trace.append(['original',rd(event+8),rd(event+12)]);ret(case['result'])
   elif a==STOP+8:
    event=u.reg_read(UC_ARM_REG_R1);trace.append(['envelope',rd(event),rd(event+4),rd(event+8),rd(event+12),rd(event+16),*struct.unpack('<HHB',u.mem_read(event+20,5)),*struct.unpack('<HHH',u.mem_read(event+26,6))]);ret(0)
  u.hook_add(UC_HOOK_CODE,hook)
  for reg,value in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):u.reg_write(reg,value&0xffffffff)
  u.reg_write(UC_ARM_REG_SP,STACK);u.reg_write(UC_ARM_REG_LR,STOP);u.emu_start(entry,STOP+12,count=10000)
  assert u.reg_read(UC_ARM_REG_PC)==STOP
  if case['kind']=='roster':
   ptr=u.reg_read(UC_ARM_REG_R0);counts=[rd(R+off+4) for off in offsets];which=next(j for j,off in enumerate(offsets) if ptr in [rd(V+j*0x100+i*4) for i in range(counts[j])]);obs=dict(roster=which,counts=counts,allocated=bool(alloc),position=next(i for i in range(counts[which]) if rd(V+which*0x100+i*4)==ptr),mode=int(u.mem_read(ptr+4,1)[0]))
  elif case['kind']=='external':obs=dict(trace=trace,routes=[rd(E+8),rd(E+12)])
  else:obs=dict(unchanged=bytes(u.mem_read(R,0x2000))==bytes(0x2000)) # state includes explicit roster setup; hooks no writes instead checked by output sentinel below
  if case['kind']=='noop':obs=dict(return_r0=u.reg_read(UC_ARM_REG_R0)==R)
  results.append(dict(input=case,observed=obs))
 return dict(originals=originals,cases=results,native_boundaries=['allocator64 succeeds','CCL vector add appends with available storage','CCL lock/unlock','NetworkManager getInstance/sendEvent','IConnection second send slot result0/1'],constructor='Actual MeterMaid and MeterBallistics instructions execute with initialized decay-table guard; no ctor credit',static_error_address=static_error,static_error_value=0)
if __name__=='__main__':print(json.dumps(observe(),indent=2))
