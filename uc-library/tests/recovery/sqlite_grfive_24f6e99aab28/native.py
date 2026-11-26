"""Independent whole ARM bodies; explicit binary32 and NumericParam boundaries."""
import hashlib,json,struct,sys,math,random
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0 as R0,UC_ARM_REG_R1 as R1,UC_ARM_REG_R2 as R2,UC_ARM_REG_PC as PC,UC_ARM_REG_SP as SP,UC_ARM_REG_LR as LR
OBJ,PARAM,STACK,STOP,TABLE=0x22000000,0x23000000,0x24000000,0x25000000,0x26000000
B='_ZN8Presonus15MeterBallistics'; M='_ZN8Presonus9MeterMaid'
def pack(*x):return struct.pack('<'+'I'*len(x),*x)
def fl(x):return struct.unpack('<f',pack(x))[0]
def bits(x):
 try:return struct.unpack('<I',struct.pack('<f',x))[0]
 except OverflowError:return bits(math.copysign(math.inf,x))
def digest(x):return hashlib.sha256(x).hexdigest()
def points():
 vals=[0,0x80000000,bits(-1),bits(.0125)-1,bits(.0125),bits(.0125)+1,bits(.99)-1,bits(.99),bits(.99)+1,bits(1),bits(2),0x7f800000,0xff800000,0x7fc00000]
 rows=[]
 for bound in (0,1):
  for table in (0,1):
   for v in vals:
    for delay,hold,clip,signal in [(0,0,0,0),(4,80,1,1),(5,0xffffffff,200,10),(0x7fffffff,0x80000000,0xffffffff,0xffffffff),(0xffffffff,1,2,2)]:
     rows.append([bound,table,1,bits(.5),bits(.75),hold,clip,signal,delay,bits(.04),v,bits(.25)])
 rng=random.Random(6914)
 for _ in range(180):
  rows.append([rng.randrange(2),rng.randrange(2),rng.randrange(2),bits(rng.uniform(-.2,1.2)),bits(rng.uniform(-.2,1.2)),rng.choice([0,1,80,0xffffffff]),rng.choice([0,1,2,200]),rng.choice([0,1,2,10]),rng.choice([0,4,5,10,0xffffffff]),bits(rng.choice([0,.04,.5])),rng.choice(vals),rng.choice([0,bits(.25)])])
 return rows

def observe(target):
 with open(target['elf_path'],'rb') as f:
  assert hashlib.file_digest(f,'sha256').hexdigest()==target['elf']; f.seek(0);e=ELFFile(f);sy=e.get_section_by_name('.symtab')
  def span(n):
   s,=sy.get_symbol_by_name(n);sec=e.get_section(s['st_shndx']);off=s['st_value']-sec['sh_addr'];b=sec.data()[off:off+s['st_size']];return dict(mangled=n,address=s['st_value'],size=s['st_size'],section=s['st_shndx'],file_offset=sec['sh_offset']+off,range_sha256=digest(b)),b
  extent,body=span(target['mangled']); assert all(extent[k]==target[k] for k in ('address','size','section','file_offset','range_sha256'));assert body.hex()==target['range_hex']
  names=[B+'8setLevelEf',B+'12idleSetLevelEf','_ZN8Presonus11GRMeterMaid8setLevelEf','_ZNK8Presonus9MeterMaid9isClippedEv',M+'10setClippedEb',M+'9setSignalEb',M+'8setMeterEf',M+'7setPeakEf']
  providers={n:span(n)[0] for n in names};helpers={n:span(n)[0] for n in ('__aeabi_fsub','__aeabi_fmul','__aeabi_fcmplt','__aeabi_fcmpgt','__aeabi_ui2f')}
  vtable,vbytes=span('_ZTVN8Presonus11GRMeterMaidE');base_vtable,bbytes=span('_ZTVN8Presonus15MeterBallisticsE');numeric,nbytes=span('_ZTVN4Core8Portable12NumericParamE')
  setp=span('_ZN4Core8Portable12NumericParam8setValueEfb')[0];getp=span('_ZNK4Core8Portable12NumericParam8getValueEv')[0]
  assert struct.unpack_from('<I',nbytes,8+88)[0]==setp['address'];assert struct.unpack_from('<I',nbytes,8+68)[0]==getp['address']
  segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
 cpu=Uc(UC_ARCH_ARM,UC_MODE_ARM);low=min(x[0] for x in segments)&~4095;high=max(a+n for a,n,b in segments);cpu.mem_map(low,(high-low+4095)&~4095)
 for a,n,b in segments:cpu.mem_write(a,b)
 for a in (OBJ,PARAM,STACK,STOP,TABLE):cpu.mem_map(a,4096)
 for s in [extent,vtable,base_vtable,numeric,setp,getp,*providers.values(),*helpers.values()]:assert digest(bytes(cpu.mem_read(s['address'],s['size'])))==s['range_sha256']
 def word(a):return struct.unpack('<I',cpu.mem_read(a,4))[0]
 def write(a,*v):cpu.mem_write(a,pack(*v))
 # Original constructor's independently observed actual default-table words.
 prior=json.loads(Path('uc-library/tests/recovery/cycle20_g02_s08/fixtures.json').read_text());tw=prior['originals'][0]['cases'][0]['output'][10:20];write(TABLE,*tw)
 helper={r['address']:n for n,r in helpers.items()};effects={providers[n]['address']:n for n in names[3:]};active={}
 def hook(c,pc,size,user):
  x,y=c.reg_read(R0),c.reg_read(R1)
  if pc in helper:
   n=helper[pc];a,b=fl(x),fl(y)
   if n.endswith('ui2f'):r=bits(x)
   elif n.endswith('fsub'):r=bits(a-b)
   elif n.endswith('fmul'):r=bits(a*b)
   elif n.endswith('fcmplt'):r=int(a<b)
   else:r=int(a>b)
   active['helpers'].append([n,x,y,r]);c.reg_write(R0,r);c.reg_write(PC,c.reg_read(LR));return
  if pc in effects:
   name=effects[pc];tag=next(k for k in ['isClipped','setClipped','setSignal','setMeter','setPeak'] if k in name)
   active['effects'].append([tag,y if tag not in ('isClipped',) else 0]);active['entries'].append(name)
  if pc==setp['address']:
   assert x in [PARAM+64*i for i in range(4)] and c.reg_read(R2)==0
   idx=(x-PARAM)//64;active['params'][idx]=y;active['parameter_calls'].append(['set',idx,y,False]);c.reg_write(PC,c.reg_read(LR));return
  if pc==getp['address']:
   assert x==PARAM+3*64;v=active['params'][3];active['parameter_calls'].append(['get',3,v]);c.reg_write(R0,v);c.reg_write(PC,c.reg_read(LR));return
  assert any(s['address']<=pc<s['address']+s['size'] for s in providers.values()),hex(pc)
 def writes(c,a,addr,size,val,u):
  if OBJ<=addr<OBJ+64:active['writes'].append([c.reg_read(PC),addr-OBJ,size,val])
 cpu.hook_add(UC_HOOK_CODE,hook);cpu.hook_add(UC_HOOK_MEM_WRITE,writes);cases=[]
 for p in points():
  bound,table,enabled,amp,peak,hold,clip,signal,delay,rate,value,initial=p
  cpu.mem_write(OBJ,bytes(96));write(OBJ,vtable['address']+8);write(OBJ+8,bits(1),rate,enabled,amp,peak,hold,clip,signal,delay,TABLE if table else 0)
  for i in range(4):write(OBJ+0x30+4*i,PARAM+64*i if bound else 0);write(PARAM+64*i,numeric['address']+8)
  active.update(effects=[],parameter_calls=[],params=[initial]*4,helpers=[],writes=[],entries=[])
  for r,v in [(R0,OBJ),(R1,value),(SP,STACK+2048),(LR,STOP)]:cpu.reg_write(r,v)
  cpu.emu_start(extent['address'],STOP,count=10000);assert cpu.reg_read(PC)==STOP and cpu.reg_read(SP)==STACK+2048
  output=[cpu.reg_read(R0),*struct.unpack('<6I',cpu.mem_read(OBJ+20,24)),*active['params']]
  cases.append(dict(input=p,output=output,effects=active['effects'],parameter_calls=active['parameter_calls'],writes=active['writes'],helpers=active['helpers'],entries=active['entries']))
 return dict(target=target,extent=extent,providers=providers,helpers=helpers,vtable=vtable,base_vtable=base_vtable,base_vtable_words=list(struct.unpack('<10I',bbytes)),numeric=numeric,numeric_set=setp,numeric_get=getp,table_fixture_sha256=digest(Path('uc-library/tests/recovery/cycle20_g02_s08/fixtures.json').read_bytes()),cases=cases)
if __name__=='__main__':
 d=json.loads(Path(sys.argv[1]).read_text()); print(json.dumps(dict(originals=[observe(x['original']) for x in d['originals']]),indent=2))
