"""Exact ARM application execution. Core boundaries use real pinned host providers.
No firmware Core body executes; source-port layout is never imposed on ARM.
"""
import hashlib, io, json, struct, subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[4]
BASE=Path(__file__).resolve().parent
PACKETS=ROOT/'temp/recovery-work/sqlite-issued/packet-sol61'
ELF=Path('/home/rs/projects/opencs/ai-line-analysis/rootfs/RML32AI_Rack_13731/home/root/mixer')
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def digest(b):return hashlib.sha256(b).hexdigest()
def load():
 data=ELF.read_bytes(); assert digest(data)==SHA
 e=ELFFile(io.BytesIO(data)); syms={s.name:s for s in e.get_section_by_name('.symtab').iter_symbols()}
 targets=[]
 for p in sorted(PACKETS.glob('*/CONTEXT.json')):
  c=json.loads(p.read_text());o=c['originals'][0]['original'];s=syms[o['mangled']];sec=e.get_section(s['st_shndx']);offset=sec['sh_offset']+s['st_value']-sec['sh_addr']
  assert (s['st_value'],s['st_size'],s['st_shndx'],offset)==(o['address'],o['size'],o['section'],o['file_offset'])
  raw=data[offset:offset+s['st_size']]; assert raw.hex()==o['range_hex'] and digest(raw)==o['range_sha256']
  targets.append(o)
 # Source-provided boundaries verified by original PLT symbol ownership.
 plt=e.get_section_by_name('.plt');rel=e.get_section_by_name('.rel.plt');dyn=e.get_section(rel['sh_link']);rels=list(rel.iter_relocations())
 for a,n in [(0xac10,'_ZdlPv'),(0xa7e4,'_Znwj'),(0xae68,'memcpy'),(0xaf70,'strcmp')]:
  assert dyn.get_symbol(rels[(a-plt['sh_addr']-20)//12]['r_info_sym']).name==n
 app=['_ZN8Presonus5Panel15PresetNameCache9CacheInfoC1Ev','_ZN8Presonus5Panel15PresetNameCache11addCategoryEPKc','_ZNK8Presonus5Panel17PresetNameManager11lookupCacheEPKc','_ZN8Presonus5Panel17PresetNameManagerC1Ev','_ZN8Presonus5Panel15PresetNameCache11cachePresetEPKcS3_i','_ZN8Presonus5Panel15PresetNameCache13getPresetInfoERN4Core13CStringBufferILi64EEERNS3_ILi32EEEi','_ZN8Presonus5Panel15PresetNameCache7rebuildEv']
 deps=[]
 for n in app:
  s=syms[n];sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];deps.append(dict(mangled=n,address=s['st_value'],size=s['st_size'],section=s['st_shndx'],file_offset=off,range_sha256=digest(data[off:off+s['st_size']])))
 return data,e,syms,targets,deps
class Machine:
 def __init__(self,exe,inputs):
  self.data,self.elf,self.syms,self.targets,self.deps=inputs
  self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);self.u.mem_map(0,0x800000)
  for s in self.elf.iter_segments():
   if s['p_type']=='PT_LOAD':self.u.mem_write(s['p_vaddr'],s.data())
  self.u.mem_map(0x1000000,0x1000000);self.u.mem_map(0x3000000,0x20000)
  self.sp=0x3010000;self.stop=0x3020000;self.u.mem_map(self.stop,4096)
  self.next=0x1000000;self.trace=[];self.calls=[];self.writes=[];self.freed=[];self.vec={};self.allocs=set()
  self.service=subprocess.Popen([str(exe)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=ROOT)
  self.allowed=[(o['address'],o['address']+o['size']) for o in self.targets+self.deps]
  self.hook=self.u.hook_add(UC_HOOK_CODE,self.code)
  self.u.hook_add(UC_HOOK_MEM_WRITE,self.write)
  # Native CacheInfo default marker pointer and independent fallback literal.
  self.marker_global=self.word(0x84cf8);self.marker=self.text(self.word(self.marker_global))
  self.singleton=self.syms['_ZN4Core8Portable9SingletonIN8Presonus5Panel17PresetNameManagerEE11theInstanceE']['st_value']
 def write(self,u,access,address,size,value,_):
  if not 0x3000000<=address<0x3020000:self.writes.append([address,size,value])
 def query(self,s):
  self.service.stdin.write(s+'\n');self.service.stdin.flush();line=self.service.stdout.readline();assert line,(s,self.service.poll(),self.service.stderr.read());return line.rstrip('\n')
 def word(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def put(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def text(self,a):
  if not a:return ''
  b=bytearray()
  while True:
   c=self.u.mem_read(a+len(b),1)[0]
   if not c:return b.decode('ascii')
   b.append(c);assert len(b)<4096
 def alloc(self,n):
  p=self.next;self.next+=(n+4095)&~4095;assert self.next<0x2000000;return p
 def string(self,s):
  p=self.alloc(len(s)+1);self.u.mem_write(p,s.encode()+b'\0');return p
 def hoststring(self,cap,p):
  return bytes.fromhex(self.query(f'string {cap} '+(self.text(p).encode().hex() if p else '-')))
 def ret(self,value=None):
  if value is not None:self.u.reg_write(UC_ARM_REG_R0,value&0xffffffff)
  self.u.reg_write(UC_ARM_REG_PC,self.u.reg_read(UC_ARM_REG_LR))
 def code(self,u,a,size,_):
  if a==self.stop:u.emu_stop();return
  r=[u.reg_read(UC_ARM_REG_R0+i) for i in range(4)]
  if a in [0x1cf90,0x1debc,0x129ba4]:
   if a==0x129ba4:b=bytes.fromhex(self.query('file '+(self.text(r[1]).encode().hex() if r[1] else '-')))
   else:b=self.hoststring(64 if a==0x1cf90 else 32,r[1])
   u.mem_write(r[0],b);self.calls.append([a,r[0],b.hex()]);self.ret(r[0]);return
  if a==0xaf70:
   result=int(self.query('compare '+(self.text(r[0]).encode().hex() or '-')+' '+(self.text(r[1]).encode().hex() or '-')))
   self.calls.append([a,self.text(r[0]),self.text(r[1]),result]);self.ret(result);return
  if a==0xae98:
   self.ret(int(self.query('length '+(self.text(r[0]).encode().hex() or '-'))));return
  if a==0xafe8:
   raw=bytes.fromhex(self.query(f'copy {r[2]} '+(self.text(r[1]).encode().hex() or '-')))
   u.mem_write(r[0],raw);self.ret(r[0]);return
  if a==0xae68:
   u.mem_write(r[0],bytes(u.mem_read(r[1],r[2])));self.ret(r[0]);return
  if a==0xa7e4:
   p=self.alloc(r[0]);self.query(f'alloc {p} {r[0]}');self.allocs.add(p);self.calls.append([a,r[0],p]);self.ret(p);return
  if a==0xac10:
   assert r[0] in self.allocs,('unowned delete',hex(r[0]))
   obs=self.query(f'free {r[0]}');assert obs.split()[0]=='1';self.allocs.remove(r[0]);self.freed.append(r[0]);self.calls.append([a,r[0],obs]);self.ret();return
  resize={0x56da8:4,0x861c4:96,0x86364:32,0x85e94:4}
  drop={0x8649c:32,0x862fc:96,0x85e64:4,0x85f94:4}
  if a in resize:
   p=r[0];stride=resize[a];n=r[1] if r[1]<0x80000000 else r[1]-0x100000000
   ok,capacity=map(int,self.query(f'resize {p} {stride} {n}').split());old=self.vec.get(p)
   data=bytes(u.mem_read(self.word(p+4),self.word(p+8)*stride)) if old and self.word(p+4) else b''
   buf=self.alloc(capacity*stride) if capacity else 0
   if buf:
    if stride==96:
     marker=self.hoststring(64,self.word(self.marker_global))
     for i in range(capacity):u.mem_write(buf+i*96,marker);u.mem_write(buf+i*96+64,b'\0')
    u.mem_write(buf,data[:capacity*stride])
   self.put(p+4,buf);self.put(p+12,capacity);self.vec[p]=(stride,buf);self.calls.append([a,p,n,capacity]);self.ret(ok);return
  if a in drop:
   p=r[0];stride=drop[a];obs=self.query(f'drop {p} {stride}');allocated,actual=map(int,obs.split());assert allocated==actual
   self.vec.pop(p);self.calls.append([a,p,obs]);self.ret();return
  assert any(lo<=a<a+size<=hi for lo,hi in self.allowed),('unexpected native PC',hex(a))
  self.trace.append(a)
 def run(self,name,args,stackargs=()):
  self.u.reg_write(UC_ARM_REG_SP,self.sp);self.u.reg_write(UC_ARM_REG_LR,self.stop)
  for i,x in enumerate(args):self.u.reg_write(UC_ARM_REG_R0+i,x&0xffffffff)
  for i,x in enumerate(stackargs):self.put(self.sp+i*4,x)
  self.u.emu_start(self.syms[name]['st_value'],self.stop,count=100000)
  assert self.u.reg_read(UC_ARM_REG_PC)==self.stop and self.u.reg_read(UC_ARM_REG_SP)==self.sp
  return self.u.reg_read(UC_ARM_REG_R0)
 def cache(self,name,slots,variant='C1'):
  p=self.alloc(0x188);self.query(f'alloc {p} 392');self.allocs.add(p)
  self.run('_ZN8Presonus5Panel15PresetNameCache'+variant+'EPKci',[p,self.string(name),slots]);return p
 def snapshot(self,p):
  cap=self.word(p+0x16c);entries=self.word(p+0x164);cats=self.word(p+0x178)
  fields=[self.text(p+4),str(self.u.mem_read(p+0x44,1)[0]),self.text(p+0x45),str(cap),str(self.word(p+0x148)),str(self.u.mem_read(p+0x145,1)[0])]
  fields += [self.text(entries+i*96)+':'+self.text(entries+i*96+64) for i in range(cap)]
  fields+=['cats']+[self.text(cats+i*32) for i in range(self.word(p+0x17c))]
  return '|'.join(fields)
 def close(self):
  assert not self.vec and not self.allocs,(self.vec,self.allocs)
  assert self.query('quit')=='0 0';self.service.stdin.close();assert self.service.wait(timeout=10)==0

def collect(exe):
 inputs=load();cases=[];lifecycle=[]
 def done(m,kind,inputs,result):
  record=dict(kind=kind,inputs=inputs,result=result,native_pcs=m.trace,native_writes=m.writes,provider_calls=m.calls,actual_deallocations=m.freed)
  m.close();return record
 m=Machine(exe,inputs);p=m.alloc(96);m.run('_ZN8Presonus5Panel15PresetNameCache9CacheInfoC1Ev',[p]);cases.append(done(m,'default',{},m.text(p)+':'+m.text(p+64)))
 for variant in ['C1','C2']:
  for slots in [-1,0,1,5,6,13]:
   m=Machine(exe,inputs);name='preset-long-type' if slots==13 else 'preset';p=m.cache(name,slots,variant);result=m.snapshot(p)
   m.run('_ZN8Presonus5Panel15PresetNameCacheD0Ev',[p])
   cases.append(done(m,'cache',dict(variant=variant,slots=slots,name=name),result))
 for text in ['', '* Empty Location *','* Empty Location * ', 'Saved preset', 'x'*90]:
  m=Machine(exe,inputs);p=m.alloc(96);m.u.mem_write(p,m.hoststring(64,m.string(text)))
  result=m.run('_ZNK8Presonus5Panel15PresetNameCache9CacheInfo7isEmptyEv',[p]);cases.append(done(m,'empty',dict(name=text),str(result)))
 for variant in ['D0','D1','D2']:
  for slots in [0,7]:
   m=Machine(exe,inputs);p=m.cache('lifecycle',slots);m.run('_ZN8Presonus5Panel15PresetNameCache'+variant+'Ev',[p]);deleted=list(m.freed)
   if variant!='D0':m.query(f'free {p}');m.allocs.remove(p)
   lifecycle.append(done(m,'cache-lifecycle',dict(variant=variant,slots=slots),dict(native_deleted=bool(deleted))))
 m=Machine(exe,inputs);p=m.cache('state',6);m.u.mem_write(p+0x145,b'\0')
 for name,category,slot in [('Saved nonempty preset','Drums',3),('second','Vocals',8),('rejected','none',-1),('rejected','none',10)]:
  m.run('_ZN8Presonus5Panel15PresetNameCache11cachePresetEPKcS3_i',[p,m.string(name),m.string(category),slot])
 result=m.snapshot(p)
 for slot in [3,10]:
  name=m.string('sentinel'+'\0'*64);category=m.string('sentinel'+'\0'*32)
  valid=m.run('_ZN8Presonus5Panel15PresetNameCache13getPresetInfoERN4Core13CStringBufferILi64EEERNS3_ILi32EEEi',[p,name,category,slot]);result+=f'\t{valid}:{m.text(name)}:{m.text(category)}'
 m.run('_ZN8Presonus5Panel15PresetNameCacheD0Ev',[p]);cases.append(done(m,'state',{},result))
 for count in [1,2,6,11,17]:
  m=Machine(exe,inputs);p=m.alloc(24);m.query(f'alloc {p} 24');m.allocs.add(p)
  m.run('_ZN8Presonus5Panel17PresetNameManagerC1Ev',[p])
  cats=['Vocals','Drums','','Vocals','012345678901234567890123456789012345'];catp=m.alloc(20)
  for i,c in enumerate(cats):m.put(catp+4*i,m.string(c))
  for i in range(count):m.run('_ZN8Presonus5Panel17PresetNameManager18registerPresetTypeEPKccS3_iiPS3_i',[p,m.string('type'+str(i)),65+i,m.string('/tmp/source-port-presets/'+str(i))],[i%9,i%4,catp,i%6])
  before=m.word(p+12);m.run('_ZN8Presonus5Panel17PresetNameManager18registerPresetTypeEPKccS3_iiPS3_i',[p,m.string('type0'),33,m.string('/duplicate')],[77,77,0,0]);assert m.word(p+12)==before==count
  result='\t'.join(m.snapshot(m.word(m.word(p+8)+i*4)) for i in range(count))
  absent=m.run('_ZNK8Presonus5Panel17PresetNameManager17getPresetTypeNameEPKc',[p,m.string('missing')]);hit=m.run('_ZNK8Presonus5Panel17PresetNameManager17getPresetTypeNameEPKc',[p,m.string('type0')]);result+=f'\t{absent}:{hit}:{m.word(p+16)}'
  # Native singleton member must clear only when this manager is installed.
  m.put(m.singleton,p)
  m.run('_ZN8Presonus5Panel17PresetNameManagerD0Ev',[p]);assert m.word(m.singleton)==0 and len(m.freed)==count+1
  cases.append(done(m,'manager',dict(count=count),result))
 for variant in ['D0','D1','D2']:
  for matching in [False,True]:
   m=Machine(exe,inputs);p=m.alloc(24);m.query(f'alloc {p} 24');m.allocs.add(p);m.run('_ZN8Presonus5Panel17PresetNameManagerC1Ev',[p])
   cache=m.cache('owned',7);items=m.word(p+8);m.put(items,cache);m.put(items+4,0);m.put(p+12,2)
   m.put(m.singleton,p if matching else 0x12345678)
   m.run('_ZN8Presonus5Panel17PresetNameManager'+variant+'Ev',[p]);assert m.word(m.singleton)==(0 if matching else 0x12345678)
   assert cache in m.freed and (p in m.freed)==(variant=='D0')
   if variant!='D0':m.query(f'free {p}');m.allocs.remove(p)
   lifecycle.append(done(m,'manager-lifecycle',dict(variant=variant,matching_singleton=matching),dict(cache_deleted=True,manager_deleted=variant=='D0',singleton=m.word(m.singleton))))
 return dict(version=1,elf_sha256=SHA,ranges=inputs[3],app_dependencies=inputs[4],cases=cases,lifecycle=lifecycle,domain='Exact selected ARM app ranges with real pinned CCL host CString/FileName/Vector providers; native virtual D0 reaches actual host operator delete, null entries and singleton writes observed. ARM layout only in emulated memory; no Core binary execution, EH/OOM/hardware claim.')
