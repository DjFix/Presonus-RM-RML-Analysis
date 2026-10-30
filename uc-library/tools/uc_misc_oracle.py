#!/usr/bin/env python3
"""Original ARM timecode/music/debug/short-sysex codecs with compact fixtures."""
import argparse,collections,hashlib,json,struct
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
from core_uc_oracle import Oracle as Loader
from uc_meter_oracle import patch
EVENT_SIZE=2336
TYPES=[('TimeCodeEvent',21571),('MusicInputEvent',19785),('DebugEvent',17474),('MidiShortSysexEvent',21331)]
METHODS=[]
for name,tag in TYPES:
 codec=name+'Class';prefix=f'_ZNK8Presonus2UC{len(codec)}{codec}'
 METHODS.extend([(prefix+f'5writeERNS0_12BufferWriterERKNS0_{len(name)}{name}E',name+'Write'),
                 (prefix+f'4readERNS0_{len(name)}{name}ERNS0_12BufferReaderE',name+'Read')])
for name,tag in TYPES:
 prefix=f'_ZNK8Presonus2UC19PrimitiveEventClassINS0_{len(name)}{name}ELi{tag}EE'
 METHODS.extend([(prefix+'5writeERNS0_12BufferWriterERKNS0_5EventE',name+'DispatchWrite'),
                 (prefix+'4readERNS0_5EventERNS0_12BufferReaderE',name+'DispatchRead')])
def pattern(seed,size):return bytes((i*29+seed*17)%255+1 for i in range(size))

class Oracle:
 def __init__(self,repository,role):
  original=unicorn.Uc.hook_add;handles=[]
  def capture(u,*args,**kwargs):
   h=original(u,*args,**kwargs);handles.append(h);return h
  unicorn.Uc.hook_add=capture
  try:loader=Loader(repository,role)
  finally:unicorn.Uc.hook_add=original
  self.u=loader.u;self.manifest=loader.manifest
  for h in handles:self.u.hook_del(h)
  self.obj=loader.obj;self.codec=self.obj+0x4000;self.io=0x11000000;self.event=0x12000000;self.stack=loader.stack;self.stop=loader.stop
  self.u.mem_map(self.io,0x40000);self.u.mem_map(self.event,4096);self.io_size=64;self.calls=0
  symbols=json.loads((repository/'uc-library/recovered'/role/'all-symbols.json').read_text());by_name={s['mangled']:s for s in symbols}
  self.functions=[by_name[name] for name,_ in METHODS]
  def allowed(address,size,write=False):
   regions=[(self.obj,self.obj+12),(self.codec,self.codec+16),(self.io,self.io+self.io_size),(self.event,self.event+EVENT_SIZE),(self.stack,self.stack+0x10000)]
   return any(a<=address and address+size<=b for a,b in (regions if write else regions+loader.loads))
  def guard(u,access,address,size,value,user):assert allowed(address,size,access==unicorn.UC_MEM_WRITE),(hex(address),size)
  self.u.hook_add(unicorn.UC_HOOK_MEM_READ|unicorn.UC_HOOK_MEM_WRITE,guard)
  self.helpers=collections.Counter()
  def memcpy(u,address,size,user):
   dst,src,n=[u.reg_read(r) for r in (arm.UC_ARM_REG_R0,arm.UC_ARM_REG_R1,arm.UC_ARM_REG_R2)]
   assert n<=2048 and allowed(src,n) and allowed(dst,n,True)
   assert n==0 or dst+n<=src or src+n<=dst
   if n:u.mem_write(dst,bytes(u.mem_read(src,n)))
   u.reg_write(arm.UC_ARM_REG_R0,dst);u.reg_write(arm.UC_ARM_REG_PC,u.reg_read(arm.UC_ARM_REG_LR));self.helpers['memcpy']+=1
  symbol=next(s for s in symbols if s['address'] and s['mangled'].startswith('memcpy@@'))
  self.u.hook_add(unicorn.UC_HOOK_CODE,memcpy,begin=symbol['address'],end=symbol['address'])
  strlen=next(s for s in symbols if s['address'] and s['mangled'].startswith('strlen@@'))
  def strlen_hook(u,address,size,user):
   src=u.reg_read(arm.UC_ARM_REG_R0)
   for n in range(1024):
    assert self.event<=src+n<self.event+EVENT_SIZE
    if u.mem_read(src+n,1)[0]==0:break
   else:raise AssertionError('writer lacks bounded NUL')
   u.reg_write(arm.UC_ARM_REG_R0,n);u.reg_write(arm.UC_ARM_REG_PC,u.reg_read(arm.UC_ARM_REG_LR));self.helpers['strlen']+=1
  self.u.hook_add(unicorn.UC_HOOK_CODE,strlen_hook,begin=strlen['address'],end=strlen['address'])
  def count(u,address,size,user):self.calls+=1
  for symbol in self.functions[:8]:self.u.hook_add(unicorn.UC_HOOK_CODE,count,begin=symbol['address'],end=symbol['address'])
  def override(u,address,size,user):
   self.calls+=1;u.reg_write(arm.UC_ARM_REG_R0,int(address==self.stop+8));u.reg_write(arm.UC_ARM_REG_PC,u.reg_read(arm.UC_ARM_REG_LR))
  for address in (self.stop+4,self.stop+8):self.u.hook_add(unicorn.UC_HOOK_CODE,override,begin=address,end=address)

 def call(self,op,capacity,offset,mode,io,event):
  u=self.u;self.calls=0;self.io_size=len(io)
  table=[0]*8;kind=(op%8)//2
  table[6]=self.functions[2*kind]['address'] if mode==0 else self.stop+4*mode
  table[7]=self.functions[2*kind+1]['address'] if mode==0 else self.stop+4*mode
  event=bytearray(event);event[2304:2336]=struct.pack('<8I',*table);before_event=bytes(event)
  u.mem_write(self.obj,struct.pack('<IIi',self.io,self.io+offset,capacity));u.mem_write(self.io,bytes(io));u.mem_write(self.event,before_event)
  u.mem_write(self.codec,struct.pack('<I',self.event+2304)+bytes(12))
  for i in range(13):u.reg_write(getattr(arm,f'UC_ARM_REG_R{i}'),0)
  u.reg_write(arm.UC_ARM_REG_CPSR,0x10);u.reg_write(arm.UC_ARM_REG_SP,self.stack+0xff00);u.reg_write(arm.UC_ARM_REG_LR,self.stop)
  u.reg_write(arm.UC_ARM_REG_R0,self.codec);u.reg_write(arm.UC_ARM_REG_R1,self.event if op%2 else self.obj);u.reg_write(arm.UC_ARM_REG_R2,self.obj if op%2 else self.event)
  u.emu_start(self.functions[op]['address'],self.stop,count=100000)
  assert u.reg_read(arm.UC_ARM_REG_PC)==self.stop and u.reg_read(arm.UC_ARM_REG_SP)==self.stack+0xff00
  result=u.reg_read(arm.UC_ARM_REG_R0);assert result in (0,1)
  base,cursor,size=struct.unpack('<IIi',u.mem_read(self.obj,12));assert base==self.io and size==capacity
  assert self.calls==(1 if op<8 or capacity-offset>=(4 if op%2 else 6) else 0)
  return result,cursor-self.io,before_event,bytes(u.mem_read(self.io,len(io))),bytes(u.mem_read(self.event,EVENT_SIZE))

def prepare(kind,seed,value):
 event=bytearray(pattern(seed,EVENT_SIZE));event[:4]=struct.pack('<I',TYPES[kind][1]|((seed&1)<<16));bounds=[0];raw=b''
 bits=(0,0x80000000,0x7f800000,0xff800000,0x7fc12345,0x7f812345,0xffffffff,1)
 if kind==0:
  event[16:20]=struct.pack('<I',bits[seed%8]);event[20]=value;raw=struct.pack('>I',bits[seed%8])+bytes([value]);bounds.extend([4,5])
  wide=(0,0x8000000000000000,0x7ff0000000000000,0xfff0000000000000,0x7ff8000012345678,0x7ff0000012345678,0xffffffffffffffff,1)
  for index in range(4):
   start=24+16*index;event[start]=(seed*17+index*41)&255;event[start+1]=(255-seed*13-index*29)&255;event[start+8:start+16]=struct.pack('<Q',wide[(seed+index)%8])
   if index<value:bounds.extend([len(raw),len(raw)+1,len(raw)+2,len(raw)+10]);raw+=bytes(event[start:start+2])+bytes(event[start+8:start+16])
 elif kind==1:
  idbits=(0,1,32768,65535,0x12345678,0xffffffff,0x80000000,0x7f812345)[seed%8];event[16:20]=struct.pack('<I',idbits);event[20]=(0,1,127,128,255,0x90,0xf0,0xf7)[seed%8];event[24:28]=struct.pack('<I',bits[seed%8]);raw=struct.pack('>H',idbits&65535)+bytes(event[20:21])+bytes(event[24:28]);bounds.extend([2,3,7])
 elif kind==2:event[16+value]=0;raw=bytes(event[16:17+value]);bounds.extend([value,value+1])
 else:
  event[16:18]=struct.pack('<H',value);event[18:530]=bytes((i*29+seed*71)&255 for i in range(512));raw=struct.pack('<H',value)+bytes(event[18:18+min(value,512)]);bounds.extend([2,2+min(value,512),2+value])
 logical=2+value if kind==3 else len(raw);bounds.extend([logical-1,logical,logical+1]);return event,raw,bounds

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('repository',type=Path);a=p.parse_args();target=a.repository/'uc-library/validation/uc-misc';target.mkdir(parents=True,exist_ok=True)
 vectors=target/'arm-vectors.bin';assert not vectors.exists(),'preserve previous fixtures'
 records=0;counts=collections.Counter();partials=collections.Counter();originals=[];cache={}
 def base(seed,size):
  if (seed,size) not in cache:cache[seed,size]=pattern(seed,size)
  return cache[seed,size]
 with vectors.open('wb') as output:
  output.write(b'UCMIv001'+struct.pack('<I',0))
  for role_id,role in enumerate(('client','server')):
   obj=Oracle(a.repository,role)
   def emit(op,remaining,offset,seed,event,raw,mode=0):
    nonlocal records
    capacity=remaining+offset;size=max(capacity+16,64);raw_io=base(seed+11,size);raw_event=base(seed+1,EVENT_SIZE);io=bytearray(raw_io)
    if op%2:
     wire=(b'\x34\x12\x78\x56' if op>=8 else b'')+raw;io[offset:min(size,offset+len(wire))]=wire[:size-offset]
    result,cursor,before_event,out_io,out_event=obj.call(op,capacity,offset,mode,io,event)
    output.write(struct.pack('<BBBBiiiii',role_id,op,result,mode,capacity,offset,cursor,size,seed));patch(output,raw_io,io);patch(output,raw_event,before_event);patch(output,io,out_io);patch(output,before_event,out_event)
    key=role+':'+METHODS[op][1]+':override'+str(mode);counts[key]+=1
    if not result and (cursor!=offset or out_io!=bytes(io) or out_event!=before_event):partials[key]+=1
    records+=1
   for op in range(16):
    kind=(op%8)//2
    values=((0,1,3,4,5,255) if op%2 else (0,1,3,4)) if kind==0 else (0,) if kind==1 else (0,1,31,1023) if kind==2 else (0,1,2,511,512,513,32767,32768,65535)
    for seed in range(8):
     for value in values:
      wire,raw,bounds=prepare(kind,seed,value)
      oldvalue=(0,1,3,4,5,255,2,0)[seed] if kind==0 else (value+1)%1024 if kind==2 else (0,1,511,512,513,65535,32768,2)[seed] if kind==3 else 0
      event=wire if not op%2 else prepare(kind,(seed+1)%8,oldvalue)[0];prefix=(4 if op%2 else 6) if op>=8 else 0
      cuts=set(range(15))|{2048}
      for bound in bounds:cuts.update([prefix+bound-1,prefix+bound,prefix+bound+1])
      for remaining in sorted(n for n in cuts if 0<=n<=65544):
       if kind==3 and not op%2 and value>512 and remaining>512:continue
       for offset in (0,7):
        emit(op,remaining,offset,seed,event,raw)
        if op>=8 and seed in (0,7) and value==values[0]:emit(op,remaining,offset,seed,event,raw,1);emit(op,remaining,offset,seed,event,raw,2)
    if op%2 and kind==2:
     event,_,_=prepare(kind,0,0);prefix=4 if op>=8 else 0
     for remaining in (prefix+1023,prefix+1024,prefix+1025,2048):
      for offset in (0,7):emit(op,remaining,offset,0,event,bytes([0xa5])*1026)
   originals.append(dict(role=role,elf_sha256=obj.manifest['sha256'],functions=obj.functions,helpers=dict(obj.helpers)));print(role,records,'ARM misc fixtures',flush=True)
  output.seek(8);output.write(struct.pack('<I',records))
 report=dict(records=records,cases=dict(counts),partial_mutation_failures=dict(partials),originals=originals,
             vectors_sha256=hashlib.sha256(vectors.read_bytes()).hexdigest(),unicorn_version=unicorn.__version__,
             vector_format='UCMIv001;LEcount;24metadata+4patches asUCPAv001;pattern(i,seed)=(29*i+17*seed)%255+1;IOseed+11/EVENTseed+1,2336bytes.',
             domain='Valid disjointIOthrough65567bytes/event2336bytes,cursors0/7,exactheader/byte/raw8/string/data/skip boundaries. Timecodewriter count0/1/3/4 only; reader0/1/3/4/5/255, retainedcounts andignoredpartialrecord transfers. Musicfull32ID lowBE16zeroextends on success andunchangedonshortfirstread,u8+rawLE32. DebugNULlength0/1/31/1023 ormissingreaderNUL1024. Sysexcounts0/1/2/511/512/513/32767/32768/65535; writer>512 only withpre-copycapacityrejection; readerscapcopy512thenskip. Arbitrarybytes/raw32+64bitNaNpatterns,noFPmath; typedandfalse/trueoverridetargets/callcountschecked. Invalidpointer/overflow/alias/concurrency excluded.',
             dependencies='ActualoriginalARMmisc/commonheader/primitive/bufferfunctions; onlymemcpy/strlenstandardcontracts andexplicitvirtualoverridecallbacksmodeled. NoCore,pools,resize,allocators,device/MIDI IO orhardwareexecution.',
             limitations=['Portablefixedstorage/fieldnames/numericsemantictypes/callbackhierarchy/returnspelling; originalconstructors/registration/ownership/layout/vtable/ARMABI unresolved.','Timecodereaderclamps4withoutskippingextra; writer>4unsafeandexcluded. Bothignoretransferfailuresandreturn1.','Sysexreadretainsunclampedcount; successfuloversizedwriterdataaccessunsafeandexcluded,ratherthansilentlyclamped.','IndependentFactoryCodecrequiresbind/unbind ofreturneditems. Hardwaretestingdeferred.'])
 (target/'oracle.json').write_text(json.dumps(report,indent=2)+'\n');print(records,'ARM misc cases complete',flush=True)

if __name__=='__main__':main()
