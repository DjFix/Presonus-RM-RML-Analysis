"""Original ARM instruction oracle. Core bodies excluded; modeled boundary calls
are explicit in fixtures; portable replay uses actual pinned CCL implementations.
"""
import hashlib,json,struct,pathlib,collections
from unicorn import Uc, UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=pathlib.Path(__file__).resolve().parents[5]
PACKETS=ROOT/'temp/recovery-work/rolling200-02/implementation-plan01/packets-batch03/packets'
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
OBJ=0x400000;PARAM=0x402000;VT=0x403000;BANDS=0x410000;CURVES=0x420000;AUX=0x430000;STACK=0x500000;STOP=0x600000;HEAP=0x700000

def fb(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def bf(v):return struct.unpack('<f',struct.pack('<I',v))[0]
def f(v):return bf(fb(v))
def signed(v):return v if v<0x80000000 else v-0x100000000

def ranges():
 raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 out={}
 with ELF.open('rb') as stream:
  e=ELFFile(stream)
  for p in sorted(PACKETS.glob('*w04*')):
   j=json.load(open(p/'native-context.json'));b=j['bodies'][j['roots'][0]]
   sec=e.get_section(b['section_index']);off=sec['sh_offset']+b['address']-sec['sh_addr']
   assert off==b['file_offset'];assert hashlib.sha256(raw[off:off+b['size']]).hexdigest()==b['bytes_sha256']
   out[int(p.name[-2:])]={k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}
  for label,mangled in [('zeroParam','_ZN8Presonus9EQControl10BandParams9zeroParamEPN4Core8Portable9ParameterE'),('freqToX','_ZNK8Presonus9EQControl7freqToXEf'),('gainToY','_ZNK8Presonus9EQControl7gainToYEf')]:
   symbol=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name==mangled)
   sec=e.get_section(symbol['st_shndx']);offset=sec['sh_offset']+symbol['st_value']-sec['sh_addr']
   out[label]={'mangled':mangled,'address':symbol['st_value'],'size':symbol['st_size'],'section':sec.name,'section_index':symbol['st_shndx'],'file_offset':offset,'bytes_sha256':hashlib.sha256(raw[offset:offset+symbol['st_size']]).hexdigest()}
 return raw,out
RAW,RANGES=ranges()

# Fail closed at each UC_HOOK_CODE notification. Only this case's original
# target and already-bound application callees may execute instructions.
# Intercepted entry PCs are observed BEFORE Unicorn executes that instruction;
# every such callback sets PC=LR, so no Core/provider body instruction executes.
APPLICATION_CLOSURE={1:[1,8,'freqToX'],2:[2,'zeroParam'],3:[3,'gainToY'],
                     4:[4],5:[5,'freqToX'],6:[6,'gainToY'],7:[7],
                     8:[8,'freqToX'],9:[9]}
HELPER_BINDINGS={
 'zeroParam':(2,'_ZN8Presonus9EQControl10BandParams9zeroParamEPN4Core8Portable9ParameterE'),
 'freqToX':(5,'_ZNK8Presonus9EQControl7freqToXEf'),
 'gainToY':(6,'_ZNK8Presonus9EQControl7gainToYEf')}
# These entries are modeled, not instruction-executed arithmetic ranges.
# Any PC in a libgcc body other than an intercepted entry is rejected.
INTERCEPTS={
 0x1877e0:('libgcc-arithmetic-entry','__aeabi_fcmpgt'),
 0x1877f8:('libgcc-arithmetic-entry','__aeabi_f2iz / __fixsfsi'),
 0x18714c:('libgcc-arithmetic-entry','__aeabi_fsub'),
 0x187150:('libgcc-arithmetic-entry','__aeabi_fadd / __addsf3'),
 0x11e2e0:('Core-provider-entry','Parameter::removeObserver'),
 0xf8768:('Core-provider-entry','Control::paramChanged'),
 0x6f280:('Core-provider-entry','Vector<BandParams>::resize'),
 0xf02b8:('Core-provider-entry','Bitmap::Bitmap(int,int,BitmapPixelFormat,int)'),
 0xe8a70:('Core-provider-entry','LogInterpolator::rangeToNormalized; explicit linear source-port binding'),
 0xe8238:('Core-provider-entry','LinearInterpolator::rangeToNormalized'),
 0xe81b0:('Core-provider-entry','LinearInterpolator::normalizedToRange'),
 0x10e9bc:('Core-provider-entry','View::getClientRect'),
 0x6f0d8:('Core-provider-entry','Vector<SortedBand>::resize'),
 0x6f250:('Core-provider-entry','Vector<SortedBand>::~Vector'),
 0xac60:('runtime-provider-entry','operator new[] PLT'),
 0xa90c:('runtime-provider-entry','operator new PLT'),
 0xaec4:('runtime-provider-entry','operator delete[] PLT'),
 0xaba0:('runtime-provider-entry','memset PLT'),
 STOP+0x1000:('synthetic-virtual-boundary','Parameter::getValue'),
 STOP+0x1004:('synthetic-virtual-boundary','Parameter::getMin'),
 STOP+0x1008:('synthetic-virtual-boundary','Parameter::setValue'),
 STOP+0x100c:('synthetic-virtual-boundary','Graphics::drawLine'),
 STOP+0x1010:('synthetic-virtual-boundary','Bitmap deleting destructor boundary')}
HELPER_PROVENANCE={}
for label,(number,mangled) in HELPER_BINDINGS.items():
 packet=PACKETS/f'rolling200_02_impl_w04_{number:02}'/'native-context.json'
 context=json.loads(packet.read_text())
 node_id,node=next((k,v) for k,v in context['nodes'].items()
                   if v.get('metadata',{}).get('mangled')==mangled)
 metadata=node['metadata'];body=RANGES[label]
 assert metadata['elf_sha256']==SHA
 assert metadata['core_source_boundary'] is False
 assert metadata['address']==body['address'] and metadata['size']==body['size']
 assert int(metadata['section'])==body['section_index']
 HELPER_PROVENANCE[label]={'packet':str(packet.relative_to(ROOT)),
   'packet_sha256':hashlib.sha256(packet.read_bytes()).hexdigest(),
   'bound_node':node_id,'mangled':mangled,'range':body}
PC_AUDIT={'version':1,'policy':'Every executed PC must be in the per-target bound application closure or an intercepted entry; unexpected PC fails before execution.',
 'elf_sha256':SHA,'helper_provenance':HELPER_PROVENANCE,
 'application_closures':{str(k):[str(x) for x in v] for k,v in APPLICATION_CLOSURE.items()},
 'allowed_application_ranges':{str(k):RANGES[k] for k in list(range(1,10))+list(HELPER_BINDINGS)},
 'intercepted_entry_allowlist':{hex(k):{'kind':v[0],'name':v[1]} for k,v in INTERCEPTS.items()},
 'executed_libgcc_body_ranges':[],
 'executed_Core_body_ranges':[],
 'case_count':0,'observed_instruction_pcs':{},'observed_intercepted_entries':{},
 'unexpected_pc_count':0}

def audit_pc(target,address,size):
 if address in INTERCEPTS:
  key=f'{target}:{address:#x}'
  counts=PC_AUDIT['observed_intercepted_entries']
  counts[key]=counts.get(key,0)+1
  return 'intercept'
 for label in APPLICATION_CLOSURE[target]:
  body=RANGES[label]
  if body['address']<=address and address+size<=body['address']+body['size']:
   assert address%4==0 and size==4,(target,hex(address),size)
   key=f'{target}:{address:#x}'
   counts=PC_AUDIT['observed_instruction_pcs']
   counts[key]=counts.get(key,0)+1
   return 'application'
 PC_AUDIT['unexpected_pc_count']+=1
 raise RuntimeError(f'Unbound executed PC before instruction execution: target={target}, pc={address:#x}, size={size}; request exact bound range from Root')

def write_audit(path):
 path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 assert PC_AUDIT['unexpected_pc_count']==0
 path.write_text(json.dumps(PC_AUDIT,indent=2)+'\n')


def execute(c):
 t=c['target'];u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000)
 with ELF.open('rb') as stream:
  for seg in ELFFile(stream).iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 u.mem_map(OBJ,0x80000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x10000);u.mem_map(HEAP,0x10000)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 w(OBJ+0x78,BANDS);w(OBJ+0x7c,c.get('count',0));w(OBJ+0x70,c.get('count',0));w(OBJ+0xf0,CURVES)
 w(OBJ+0x34,c.get('width',100));w(OBJ+0x38,c.get('height',80));w(OBJ+0x48,PARAM if c.get('primary',True) else 0)
 for i,b in enumerate(c.get('bands',[])):
  u.mem_write(CURVES+40*i+9,bytes([b[0]]));w(CURVES+40*i,fb(b[1]));w(BANDS+24*i+20,PARAM+0x100 if b[2] else 0)
 w(PARAM,VT);w(PARAM+0x100,VT+0x100);w(VT+0x44,STOP+0x1000);w(VT+0x38,STOP+0x1004);w(VT+0x58,STOP+0x1008);w(VT+0x100+0x58,STOP+0x1008)
 if t in [7,9]:w(BANDS+24*c['index']+(16 if t==7 else 0),PARAM if c['present'] else 0)
 if t==1:
  for i,present in enumerate(c['enabled_parameters']):w(BANDS+24*i+16,PARAM if present else 0)
  w(AUX,c['kind']);w(AUX+4,c['x']);w(AUX+8,c['y'])
 elif t==8:w(AUX,c['x']);w(AUX+4,c['y'])
 if t==3:
  w(AUX,PARAM);w(PARAM,VT);w(VT+0x1c,STOP+0x100c)
  for i,v in enumerate(c['clip']):w(AUX+4+4*i,v)
  u.mem_write(OBJ+0x119,bytes([c['buffered']]))
  w(OBJ+0x98,HEAP+0x8000);w(OBJ+0x9c,HEAP+0x9000)
  for i,v in enumerate(c['samples']):
   w(HEAP+0x8000+4*i,fb(v));w(HEAP+0x9000+4*i,int(v))
  for i,b in enumerate(c['bands']):u.mem_write(CURVES+40*i+8,bytes([b[3]]))
 elif t==4:
  w(OBJ+0xf0,0);w(OBJ+0x78,0);w(OBJ+0x7c,0)
  u.mem_write(OBJ+0x119,bytes([c['buffered']]))
 if t==2:
  for i,slots in enumerate(c['slots']):
   for j,v in enumerate(slots):w(BANDS+24*i+4*j,0 if v==0 else (PARAM if v==1 else PARAM+0x100))
  w(OBJ+0x48,PARAM if c['primary'] else PARAM+0x100)
  for i in range(c['count']):
   u.mem_write(CURVES+40*i+9,b'\1');u.mem_write(CURVES+40*i+20,b'\7')
 traces=[];allocations=[];next_alloc=HEAP
 def cb(uc,a,size,user):
  pc_kind=audit_pc(t,a,size)
  r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2)
  nonlocal next_alloc
  if a==0x11e2e0:
   traces.append(['remove-observer',int(r0==PARAM),r1-OBJ])
  elif a==0xf8768:traces.append(['control',int(r1==PARAM),r2])
  elif a==STOP+0x100c:
   traces.append(['line',signed(r(r1)),signed(r(r1+4)),signed(r(r2)),signed(r(r2+4))])
  elif a in [0xac60,0xa90c]:
   result=next_alloc;next_alloc+=((r0+15)//16)*16+16
   allocations.append(['new',r0]);uc.reg_write(UC_ARM_REG_R0,result)
  elif a==0xaec4:allocations.append(['delete',r0-HEAP])
  elif a==0xaba0:u.mem_write(r0,bytes([r1&255])*r2)
  elif a==0x6f280:
   w(r0+4,HEAP+0xe000);w(r0+12,r1);uc.reg_write(UC_ARM_REG_R0,1)
  elif a==0xf02b8:
   allocations.append(['bitmap',r1,r2,uc.reg_read(UC_ARM_REG_R3)])
   w(r0,VT);w(VT+4,STOP+0x1010)
  elif a==STOP+0x1010:allocations.append(['bitmap-delete'])
  elif a in [STOP+0x1000,STOP+0x1004]:
   kind='value' if a==STOP+0x1000 else 'minimum';val=c['value'] if kind=='value' else c['minimum'];traces.append([kind]);uc.reg_write(UC_ARM_REG_R0,fb(val))
  elif a==STOP+0x1008:traces.append(['set',0 if r0==PARAM else 1,r1,r2])
  elif a==0x1877e0:uc.reg_write(UC_ARM_REG_R0,int(bf(r0)>bf(r1)))
  elif a==0x1877f8:uc.reg_write(UC_ARM_REG_R0,int(bf(r0))&0xffffffff)
  elif a in [0xe8a70,0xe8238,0xe81b0]:
   arg=bf(r1)
   if a==0xe8a70: val=f(f(max(20.,min(20000.,arg))-20.)/19980.)
   elif a==0xe8238:val=f(f(max(-12.,min(12.,arg))+12.)/24.)
   else:
    lo,hi=(10.,110.) if t in [5,8,1] else (20.,220.)
    val=f(f(max(0.,min(1.,arg))*f(hi-lo))+lo)
   uc.reg_write(UC_ARM_REG_R0,fb(val))
  elif a in [0x18714c,0x187150]:uc.reg_write(UC_ARM_REG_R0,fb(bf(r0)+(-bf(r1) if a==0x18714c else bf(r1))))
  elif a==0x10e9bc:
   for i,val in enumerate([0,0,c.get('width',100),c.get('height',80)]):w(r1+4*i,val)
   uc.reg_write(UC_ARM_REG_R0,r1)
  elif a==0x6f0d8:
   # CCL vector storage/capacity boundary. App sorting runs native instructions.
   if not r(r0+4):w(r0+4,HEAP)
   w(r0+12,max(r1,16));uc.reg_write(UC_ARM_REG_R0,1)
  elif a==0x6f250:pass
  else:
   assert pc_kind=='application',(t,hex(a),'unhandled intercepted entry')
   return
  assert pc_kind=='intercept',(t,hex(a),'unlisted intercepted entry')
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  assert uc.reg_read(UC_ARM_REG_PC)==uc.reg_read(UC_ARM_REG_LR)
 u.hook_add(UC_HOOK_CODE,cb)
 u.reg_write(UC_ARM_REG_R0,OBJ)
 u.reg_write(UC_ARM_REG_R1,AUX if t in [1,3,8] else (fb(c['value']) if t in [5,6] else c.get('index',0)))
 if t==2:
  u.reg_write(UC_ARM_REG_R1,PARAM);u.reg_write(UC_ARM_REG_R2,c['message'])
 u.reg_write(UC_ARM_REG_SP,STACK+0x8000);u.reg_write(UC_ARM_REG_LR,STOP)
 for repeat in range(c.get('repeats',1)):
  u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_SP,STACK+0x8000);u.reg_write(UC_ARM_REG_LR,STOP)
  u.emu_start(RANGES[t]['address'],STOP,count=100000)
 assert u.reg_read(UC_ARM_REG_PC)==STOP,(t,c)
 PC_AUDIT['case_count']+=1
 if t==2:
  slots=[[0 if r(BANDS+24*i+4*j)==0 else (1 if r(BANDS+24*i+4*j)==PARAM else 2) for j in range(6)] for i in range(c['count'])]
  return {'slots':slots,'dirty':[u.mem_read(CURVES+40*i+20,1)[0] for i in range(c['count'])],'enabled':[u.mem_read(CURVES+40*i+9,1)[0] for i in range(c['count'])],'calls':traces}
 if t==3:return {'lines':traces}
 if t==4:
  count=c['count'];width=c['width'];height=c['height'];positive=width>0 and height>0
  bands=r(OBJ+0xf0)
  result={'band_count':count,'parameter_count':r(OBJ+0x7c),'buffer_present':int(r(OBJ+0x114)!=0),'buffer_valid':u.mem_read(OBJ+0x118,1)[0],'dirty':[u.mem_read(bands+40*i+20,1)[0] for i in range(count)] if positive else [],'enabled':[u.mem_read(bands+40*i+9,1)[0] for i in range(count)] if positive else [],'band_curve_sizes':[r(bands+40*i+16) for i in range(count)] if positive else [],'amplitude_zero':True,'pixel_zero':True,'allocations':allocations}
  if positive:
   result['amplitude_zero']=not any(u.mem_read(r(OBJ+0x98),4*width))
   if not c['buffered']:result['pixel_zero']=not any(u.mem_read(r(OBJ+0x9c),4*width))
  return result
 return {'result':signed(u.reg_read(UC_ARM_REG_R0)),'calls':traces}

def cases():
 cs=[]
 for t,values in [(5,[-100.,20.,200.,1000.,10000.,20000.,50000.]),(6,[-50.,-12.,-6.,0.,6.,12.,50.])]:
  for value in values:cs.append(dict(target=t,value=value))
 for t in [7,9]:
  for count in [1,3]:
   for index in range(count):
    for present in [False,True]:
     for value in [-3.75,0.,0.5,1.,11.25]:cs.append(dict(target=t,count=count,index=index,present=present,value=value,minimum=0.5))
 patterns=[[],[[1,1000,1]],[[0,1000,1],[1,10000,1]],[[1,1000,0]],[[1,200,1],[1,10000,1]],[[1,10000,1],[1,200,1],[1,1000,1]],[[1,1000,1],[1,1000,1],[1,1000,1]]]
 for bands in patterns:
  for x in [-1,0,10,11,12,20,50,60,99,100,150]:
   for y in [-1,0,79,80]:
    cs.append(dict(target=8,count=len(bands),bands=bands,x=x,y=y,width=100,height=80))
 for bands in patterns:
  for primary in [False,True]:
   for kind in [0,1,2]:
    for x,y in [(10,10),(60,10),(-1,-1),(100,80)]:
     for enabled in [False,True]:cs.append(dict(target=1,count=len(bands),bands=bands,x=x,y=y,width=100,height=80,primary=primary,kind=kind,enabled_parameters=[enabled]*len(bands)))
 for count in [0,1,3]:
  for match in [-1,0,1,2,3,4,5,6]:
   for message in [0,3,4,5]:
    for primary in [False,True]:
     slots=[[2]*6 for i in range(count)]
     if count and match>=0:
      if match==6:slots[-1]=[1]*6
      else:slots[-1][match]=1
     cs.append(dict(target=2,count=count,message=message,primary=primary,slots=slots))
 for width,height in [(0,5),(5,0),(1,1),(5,4),(8,3)]:
  for count in [0,1,3]:
   for buffered in [0,1]:
    for repeats in [1,2]:cs.append(dict(target=4,width=width,height=height,count=count,buffered=buffered,repeats=repeats))
 for width in [0,1,2,5]:
  for buffered in [0,1]:
   for active in [False,True]:
    for clip in [[0,0,8,80],[1,20,4,50],[0,60,5,79]]:
     samples=([-12.,-6.,0.,6.,12.] if buffered else [0,30,70,90,40])[:width]
     cs.append(dict(target=3,width=width,height=80,count=1,buffered=buffered,bands=[[1,1000,1,int(active)]],samples=samples,clip=clip))
 return [{**c,'expected':execute(c)} for c in cs]
if __name__=='__main__':
 import sys
 out=pathlib.Path(sys.argv[1]);out.write_text(json.dumps({'elf_sha256':SHA,'ranges':RANGES,'cases':cases(),'boundaries':'Native app ranges and included native app callees execute. Parameter virtuals, Core view/vector/interpolators and ARM soft-float are modeled observation boundaries; production uses pinned actual CCL. No native Core body recovery.'},indent=2)+'\n');print(out)
 if len(sys.argv)>2:write_audit(sys.argv[2])
