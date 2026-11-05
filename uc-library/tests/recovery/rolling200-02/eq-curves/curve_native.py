"""Native application execution driven independently from new C++.
Only hash-bound expanded application ranges execute. Exact external entries are
modeled with compiler/host libc semantics; Core firmware bodies never execute.
"""
from pathlib import Path
import json,hashlib,struct,sys,bisect
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_INTR
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[5]
PKT=ROOT/'temp/recovery-work/rolling200-02/implementation-plan01/packets-current-eq01/packets'
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface';SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
OBJ,PARAM,VT,BANDS,CURVES,OUT,SUM,PIXEL,STACK,STOP=0x400000,0x402000,0x403000,0x410000,0x420000,0x430000,0x440000,0x450000,0x500000,0x600000
fb=lambda x:struct.unpack('<I',struct.pack('<f',x))[0]
bf=lambda x:struct.unpack('<f',struct.pack('<I',x))[0]
f=lambda x:bf(fb(x))
db=lambda lo,hi:struct.unpack('<d',struct.pack('<II',lo,hi))[0]
signed=lambda x:x if x<2**31 else x-2**32

def contexts():
 paths=list((ROOT/'temp/recovery-work/rolling200-02/eq-native-expansion01').glob('*/native-context.json'))
 return [PKT/f'rolling200_02_current_eq_{i:02d}'/'native-context.json' for i in [3,4]]+paths+[ROOT/'temp/recovery-work/rolling200-02/flush-reuse-packet01/native-context.json']

def execute(c):
 raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000)
 with ELF.open('rb') as stream:
  e=ELFFile(stream)
  for seg in e.iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
  symbols=list(e.get_section_by_name('.symtab').iter_symbols())
  allowed={};providers={};bindings=[]
  for path in contexts():
   ctx=json.loads(path.read_text());bindings.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
   for key,body in ctx['bodies'].items():
    node=ctx['nodes'].get(key,{});meta=node.get('metadata',{})
    if meta.get('elf_sha256',SHA)!=SHA or meta.get('core_source_boundary') or body['address']>0x180000:continue
    sec=e.get_section(body['section_index']);offset=sec['sh_offset']+body['address']-sec['sh_addr'];assert offset==body['file_offset'];assert hashlib.sha256(raw[offset:offset+body['size']]).hexdigest()==body['bytes_sha256']
    allowed[body['address']]={k:body[k] for k in ['address','size','file_offset','bytes_sha256','section','section_index']}
   for node in ctx['nodes'].values():
    meta=node.get('metadata',{});name=meta.get('mangled','');addr=meta.get('address')
    if addr and name:providers.setdefault(addr,[]).append(name)
 # Historical helper source/proof lineage is explicit; ranges are rechecked,
 # then executed freshly as part of the current integrated target replay.
 prior=ROOT/'uc-library/tests/recovery/rolling200-02/eq-control/fixtures.json'
 history=json.loads(prior.read_text());assert history['elf_sha256']==SHA
 for key in ['7','freqToX','gainToY']:
  body=history['ranges'][key];offset=body['file_offset']
  assert hashlib.sha256(raw[offset:offset+body['size']]).hexdigest()==body['bytes_sha256']
  allowed[body['address']]=body
 bindings.append({'path':str(prior.relative_to(ROOT)),'sha256':hashlib.sha256(prior.read_bytes()).hexdigest(),'scope':'Historical helper range provenance; fresh current native execution separately recorded.'})
 for addr,size in [(OBJ,0x80000),(STACK,0x20000),(STOP,0x10000)]:u.mem_map(addr,size)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def putfloat(reg,value):u.reg_write(reg,fb(value))
 def putdouble(value):
  lo,hi=struct.unpack('<II',struct.pack('<d',value));u.reg_write(UC_ARM_REG_R0,lo);u.reg_write(UC_ARM_REG_R1,hi)
 from runtime import load
 runtime_ranges,runtime_proof=load(u,ROOT,ELF,raw)
 intervals=[]
 for start,end in sorted((v['address'],v['address']+v['size']) for v in list(allowed.values())+runtime_ranges):
  if intervals and start<=intervals[-1][1]:intervals[-1][1]=max(intervals[-1][1],end)
  else:intervals.append([start,end])
 starts=[v[0] for v in intervals]
 count=c.get('count',1);width=c.get('samples',8);t=c['target'];dirty=c.get('dirty',[1]*count)
 w(OBJ+0x70,count);w(OBJ+0x78,BANDS);w(OBJ+0x7c,count);w(OBJ+0xf0,CURVES);w(OBJ+0x34,width);w(OBJ+0x38,80);w(OBJ+0x88,fb(c.get('minimum',20.)));w(OBJ+0x8c,fb(c.get('maximum',20000.)));w(OBJ+0x98,SUM);w(OBJ+0x9c,PIXEL);u.mem_write(OBJ+0x119,bytes([c.get('buffered',0)]))
 values=[]
 for i in range(count):
  band=c.get('bands',[{}]*count)[i]
  vals=[band.get('type',c.get('type',3)),band.get('gain',c.get('gain',6.)),band.get('q',c.get('q',.7)),band.get('frequency',c.get('frequency',1000.)),band.get('on',1.),0.]
  values.extend(vals)
  for j,v in enumerate(vals):
   addr=PARAM+i*0x600+j*0x100;w(addr,VT);w(addr+8,fb(v));w(addr+12,fb(0.));w(BANDS+i*24+j*4,addr if j or c.get('present',1) else 0)
  w(CURVES+40*i+12,OUT+i*0x1000);u.mem_write(CURVES+40*i+20,bytes([dirty[i]]));u.mem_write(CURVES+40*i+8,bytes([band.get('initial_on',0)]));u.mem_write(CURVES+40*i+9,bytes([band.get('initial_enabled',0)]));u.mem_write(CURVES+40*i+36,bytes([band.get('force',0)]));w(CURVES+40*i,fb(band.get('initial_frequency',0.)));w(CURVES+40*i+4,fb(band.get('initial_gain',0.)))
  for x in range(max(width,0)):w(OUT+i*0x1000+4*x,fb(band.get('initial_curve',123.)))
 w(VT+0x44,STOP+0x1000);w(VT+0x38,STOP+0x1004)
 for x in range(max(width,0)):w(SUM+4*x,fb(99.));w(PIXEL+4*x,777)
 trace=[];pcs=set();entries={};mathops={};writes=[];appcalls=[]
 def hook(uc,pc,size,_):
  if pc==STOP:u.emu_stop();return
  if pc in allowed:appcalls.append([pc,*[uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]])
  a,b,d,e=[uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
  name=None
  if pc in [STOP+0x1000,STOP+0x1004]:
   name='Parameter::getValue' if pc==STOP+0x1000 else 'Parameter::getMin';putfloat(UC_ARM_REG_R0,bf(r(a+(8 if pc==STOP+0x1000 else 12))))
  elif pc==0xaba0:name='memset';u.mem_write(a,bytes([b&255])*d)
  elif pc==0x10e9fc:name='View::invalidate'
  elif pc in [0xe8a70,0xe8238,0xe81b0]:
   name='CCL interpolator';arg=bf(b)
   if pc==0xe8a70:val=f(f(max(20.,min(20000.,arg))-20.)/19980.)
   elif pc==0xe8238:val=f(f(max(-12.,min(12.,arg))+12.)/24.)
   else:
    lo,hi=(10.,110.) if a==OBJ+0xdc else (20.,220.)
    val=f(f(max(0.,min(1.,arg))*f(hi-lo))+lo)
   putfloat(UC_ARM_REG_R0,val)
  if name:
   entries[hex(pc)]=name;trace.append([name,a,b,d,e]);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  interval=bisect.bisect_right(starts,pc)-1
  assert interval>=0 and pc+size<=intervals[interval][1],f'unbound PC {pc:#x}'
  pcs.add(pc)
 def write_hook(uc,access,address,size,value,_):
  assert (OBJ<=address and address+size<=OBJ+0x80000) or (STACK<=address and address+size<=STACK+0x20000),f'write outside native model {address:#x}'
  if OBJ<=address<OBJ+0x80000:writes.append([address,size,value])
 def interrupt(uc,number,_):raise AssertionError(('forbidden runtime interrupt/syscall',number))
 u.hook_add(UC_HOOK_MEM_WRITE,write_hook);u.hook_add(UC_HOOK_INTR,interrupt)
 u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_SP,STACK+0x18000);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,OBJ)
 if t==3:
  u.reg_write(UC_ARM_REG_R1,OUT);u.reg_write(UC_ARM_REG_R2,c.get('index',0)&0xffffffff);u.reg_write(UC_ARM_REG_R3,width&0xffffffff)
 u.emu_start(0x6b4c0 if t==3 else 0x6c62c,STOP,count=2000000);assert u.reg_read(UC_ARM_REG_PC)==STOP,'instruction limit'
 out={'result':u.reg_read(UC_ARM_REG_R0) if t==3 else None,'curves':[[bf(r(OUT+i*0x1000+4*x)) for x in range(max(width,0))] for i in range(count)],'sum':[bf(r(SUM+4*x)) for x in range(max(width,0))],'pixels':[signed(r(PIXEL+4*x)) for x in range(max(width,0))],'bands':[{'dirty':u.mem_read(CURVES+40*i+20,1)[0],'on':u.mem_read(CURVES+40*i+8,1)[0],'enabled':u.mem_read(CURVES+40*i+9,1)[0],'frequency':bf(r(CURVES+40*i)),'gain':bf(r(CURVES+40*i+4)),'x':signed(r(CURVES+40*i+24)),'y':signed(r(CURVES+40*i+28))} for i in range(count)],'valid':u.mem_read(OBJ+0x118,1)[0],'invalidations':sum(x[0]=='View::invalidate' for x in trace),'pcs':sorted(pcs),'providers':entries,'ranges':list(allowed.values()),'bindings':bindings,'provider_trace':trace,'application_calls':appcalls,'writes':writes,'runtime_ranges':runtime_ranges,'runtime_proof':runtime_proof}
 return out
if __name__=='__main__':
 c={'target':3,'type':3,'samples':8,'q':.7,'frequency':1000.,'gain':6.}
 print(json.dumps(execute(c),indent=2))
