"""Independent original ARM execution; typed parameter and I/O boundaries are explicit."""
import ctypes,hashlib,io,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
BASE=Path('temp/recovery-work/sqlite-issued/packet-sol61')
PREFIX='_ZN8Presonus5Panel17MeterLevelControl'
TASKS=sorted(BASE.glob('*/CONTEXT.json'))

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def signed(v):return ctypes.c_int32(v).value

def generate():
 packets=[json.loads(p.read_text()) for p in TASKS]; roles={}; records=[]
 for p in packets:
  for row in p['originals']:
   o=row['original'];roles.setdefault(o['role'],[]).append(o)
 for role,originals in roles.items():
  path=Path(originals[0]['elf_path']); raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==originals[0]['elf']
  elf=ELFFile(io.BytesIO(raw)); symbols=elf.get_section_by_name('.symtab')
  sym={s.name:s['st_value'] for s in symbols.iter_symbols()}
  for o in originals:
   s=elf.get_section(o['section']);off=s['sh_offset']+o['address']-s['sh_addr'];body=raw[off:off+o['size']]
   assert body.hex()==o['range_hex'] and hashlib.sha256(body).hexdigest()==o['range_sha256'] and off==o['file_offset']
  image=[]
  for seg in elf.iter_segments():
   if seg['p_type']=='PT_LOAD':image.append((seg['p_vaddr'],seg.data()))
  global_count=0x243098 if role=='client' else 0x491f08
  table0=0x250f00 if role=='client' else 0x49f138
  table1=0x250f8c if role=='client' else 0x49f1c4
  # Resolve table/static identities by ELF symbols rather than relocated guesses.
  global_count=sym['_ZN8Presonus5Panel12MeterControl13numMeterStepsE']
  table0=sym['_ZN8Presonus5Panel12MeterControl10inputTableE'];table1=sym['_ZN8Presonus5Panel12MeterControl11outputTableE']
  disabled=0x250ed4 if role=='client' else 0x49f130
  queue=0x250ed8 if role=='client' else 0x49f134
  # transmit literal pool determines exact shared globals.
  target=next(o for o in originals if '8transmit' in o['mangled'])
  def literal(addr):
   s=next(s for s in elf.iter_sections() if s['sh_addr']<=addr<s['sh_addr']+s['sh_size']);off=s['sh_offset']+addr-s['sh_addr'];return struct.unpack('<I',raw[off:off+4])[0]
  disabled=literal(target['address']+0x22c);queue=literal(target['address']+0x234)
  methods={o['mangled']:o['address'] for o in originals}
  lib=ctypes.CDLL('libm.so.6');lib.powf.argtypes=[ctypes.c_float,ctypes.c_float];lib.powf.restype=ctypes.c_float
  db=[-60.,-30.,-12.,0.]; gains=[lib.powf(10.,ctypes.c_float(x*ctypes.c_float(.05).value).value) for x in db]
  cases=[]
  for mode in range(14):
   for value in [0.,.0005,.001,.01,.1,.25,.5,.9,.99,1.]:
    for direction in [0,1]:cases.append(dict(op='changed',mode=mode,value=value,direction=direction,alt=1,clip=0.,enabled=1,disabled=0,meter=0,custom=0,action=3,tag=7,offset=2))
  for op in ['broadcast','transmit','steps','set','clip']:
   for mode in [0,2,6,7,9,10,12,13]:
    for clip in [0.,1.]:cases.append(dict(op=op,mode=mode,value=2.,direction=0,alt=1,clip=clip,enabled=1,disabled=0,meter=0,custom=0,action=3,tag=7,offset=2))
  for setting,values in [('alt',[0]),('enabled',[0]),('disabled',[1]),('meter',[1]),('custom',[1]),('action',[0,4]),('tag',[-1])]:
   for mode in [0,1,6,7,9,12,13]:
    for value in values:
     c=dict(op='changed',mode=mode,value=.5,direction=0,alt=1,clip=1.,enabled=1,disabled=1 if setting=='meter' else 0,meter=0,custom=0,action=3,tag=7,offset=2);c[setting]=value;cases.append(c)
  for mode in range(14):
   cases.append(dict(op='setmode',mode=mode,value=.5,direction=0,alt=1,clip=0.,enabled=1,disabled=0,meter=0,custom=0,action=3,tag=7,offset=2))
  for base in list(cases[:20]):
   for flag in ['primary','notifyalt','repeat']:
    c=dict(base);c[flag]=0 if flag=='primary' else 1;cases.append(c)
  for case in cases:
   case.setdefault('primary',1);case.setdefault('notifyalt',0);case.setdefault('repeat',0)
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x780000);u.mem_map(0x1000000,0x10000);u.mem_map(0x5000000,0x1000)
   for a,b in image:u.mem_write(a,b)
   def put(a,*v):u.mem_write(a,struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v)))
   def word(a):return struct.unpack('<I',u.mem_read(a,4))[0]
   receiver,vt,p,alt,pvt,info,ios,ivt,custom,stack,stop=0x1000200,0x1000100,0x1000300,0x1000400,0x1000500,0x1000600,0x1000700,0x1000800,0x1000900,0x100f000,0x5000ffc
   put(receiver,vt,0xffffffff,p if case['primary'] else 0,alt if case['alt'] else 0,0,ios,case['tag'],case['offset'],custom if case['custom'] else 0,case['direction'],0 if case['op']=='setmode' else case['mode'],0 if case['op']=='setmode' else case['mode'],0,0)
   put(vt+4,methods[PREFIX+'12paramChangedEPN4Core8Portable9ParameterEi']);put(vt+24,0x5000018);put(vt+32,methods[PREFIX+'14broadcastValueEi']);put(vt+36,methods[PREFIX+'8transmitEv'])
   put(p,pvt,0,0,info);put(alt,pvt);put(info+8,*([0]*8));u.mem_write(info+8,b'meterX\0' if case['meter'] else b'gainX\0')
   put(pvt+32,0x5000020);put(pvt+68,0x5000044);put(pvt+96,0x5000060);put(ios,ivt);put(ivt+4,0x5000004)
   put(global_count,4,4);put(disabled,case['disabled']);put(queue,0,0x100b000,0,16)
   for a in [table0,table1,custom]:
    put(a,4);u.mem_write(a+4,struct.pack('<4f',*gains));u.mem_write(a+68,struct.pack('<4f',*db));u.mem_write(a+132,struct.pack('<2f',-60.,0.))
   messages=[];boundary=[];writes=[]
   def memwrite(uc,access,address,size,value,data):
    if receiver<=address<receiver+56:writes.append(dict(offset=address-receiver,size=size,value=value))
   u.hook_add(UC_HOOK_MEM_WRITE,memwrite)
   base_set=sym['_ZN8Presonus5Panel7Control12setParameterEPN4Core8Portable9ParameterEi']
   def hook(uc,pc,size,data):
    if pc==stop:uc.emu_stop();return
    if pc==(0xaa5c if role=='client' else 0xa928):
     n=uc.reg_read(UC_ARM_REG_R2);left=bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R0),n));right=bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R1),n));result=0 if left==right else 1
    elif pc==0x5000004:
     messages.append(list(uc.mem_read(uc.reg_read(UC_ARM_REG_R1),4)));result=0
    elif pc==0x5000020:result=case['enabled']
    elif pc==0x5000044:result=bits(case['clip'])
    elif pc==0x5000060:result=bits(case['value'])
    elif pc==0x5000018:boundary.append('setAltParameter');result=0
    elif pc==base_set:boundary.append('Control::setParameter unchanged');result=0
    else:return
    uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,hook)
   op=case['op'];r1=p;r2=case['action']
   if op=='changed':
    r1=alt if case['notifyalt'] else p
    name=PREFIX+'12paramChangedEPN4Core8Portable9ParameterEi'
   elif op=='broadcast':name=PREFIX+'14broadcastValueEi';r1=int(case['value'])
   elif op=='transmit':name=PREFIX+'8transmitEv'
   elif op=='steps':name='_ZNK8Presonus5Panel17MeterLevelControl16getNumMeterStepsEb';r1=1
   elif op in ['set','setmode']:name=PREFIX+'12setParameterEPN4Core8Portable9ParameterEi';r2=case['mode']
   else:name=PREFIX+'16setClipParameterEPN4Core8Portable9ParameterE';r1=alt
   for reg,val in [(UC_ARM_REG_SP,stack),(UC_ARM_REG_LR,stop),(UC_ARM_REG_R0,receiver),(UC_ARM_REG_R1,r1),(UC_ARM_REG_R2,r2)]:u.reg_write(reg,val)
   
   try:
    u.emu_start(methods[name],stop,count=10000)
    if case['repeat']:
     for reg,val in [(UC_ARM_REG_SP,stack),(UC_ARM_REG_LR,stop),(UC_ARM_REG_R0,receiver),(UC_ARM_REG_R1,r1),(UC_ARM_REG_R2,r2)]:u.reg_write(reg,val)
     u.emu_start(methods[name],stop,count=10000)
   except Exception:
    print(role,case,hex(u.reg_read(UC_ARM_REG_PC)),hex(u.reg_read(UC_ARM_REG_LR)));raise
   assert u.reg_read(UC_ARM_REG_PC)==stop,(role,case,hex(u.reg_read(UC_ARM_REG_PC)))
   out=dict(level=signed(word(receiver+4)),mode=word(receiver+44),blank=word(receiver+48)&255,clip=word(receiver+52),queued=word(queue+8),messages=messages)
   if op in ['steps','set','setmode','clip']:out['return']=u.reg_read(UC_ARM_REG_R0)
   records.append(dict(role=role,input=case,output=out,boundaries=boundary,native_writes=writes))
 return dict(originals=[o for os in roles.values() for o in os],cases=records,boundary_policy='Genuine original ARM instructions including soft-float helpers. Parameter virtual getters and memory IPanelIO recipient modeled; unchanged Control setter and alternate setter boundaries explicitly stubbed. Table gains supplied by system powf, same API used by pinned DbTable provider.',producer_sha256=sha(__file__))
if __name__=='__main__':
 import sys
 result=generate();Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n');print(len(result['cases']),'native cases')
