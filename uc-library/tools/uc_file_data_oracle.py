#!/usr/bin/env python3
"""Original ARM fixed4096 FileData codecs; no Core allocation or file/device IO."""
import argparse,collections,hashlib,json,struct
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
from core_uc_oracle import Oracle as Loader
from uc_meter_oracle import patch
EVENT_SIZE=8192
METHODS=[
('_ZNK8Presonus2UC18FileDataEventClass5writeERNS0_12BufferWriterERKNS0_13FileDataEventE','FileDataWrite'),
('_ZNK8Presonus2UC18FileDataEventClass4readERNS0_13FileDataEventERNS0_12BufferReaderE','FileDataRead'),
('_ZNK8Presonus2UC19PrimitiveEventClassINS0_13FileDataEventELi17988EE5writeERNS0_12BufferWriterERKNS0_5EventE','FileDataDispatchWrite'),
('_ZNK8Presonus2UC19PrimitiveEventClassINS0_13FileDataEventELi17988EE4readERNS0_5EventERNS0_12BufferReaderE','FileDataDispatchRead')]
def pattern(seed,size):return bytes((i*29+seed*71)&255 for i in range(size))

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
  self.u.mem_map(self.io,0x40000);self.u.mem_map(self.event,8192);self.io_size=64;self.calls=0
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
   assert n<=4096 and allowed(src,n) and allowed(dst,n,True)
   assert n==0 or dst+n<=src or src+n<=dst
   if n:u.mem_write(dst,bytes(u.mem_read(src,n)))
   u.reg_write(arm.UC_ARM_REG_R0,dst);u.reg_write(arm.UC_ARM_REG_PC,u.reg_read(arm.UC_ARM_REG_LR));self.helpers['memcpy']+=1
  symbol=next(s for s in symbols if s['address'] and s['mangled'].startswith('memcpy@@'))
  self.u.hook_add(unicorn.UC_HOOK_CODE,memcpy,begin=symbol['address'],end=symbol['address'])
  def count(u,address,size,user):self.calls+=1
  for symbol in self.functions[:2]:self.u.hook_add(unicorn.UC_HOOK_CODE,count,begin=symbol['address'],end=symbol['address'])
  def override(u,address,size,user):
   self.calls+=1;u.reg_write(arm.UC_ARM_REG_R0,int(address==self.stop+8));u.reg_write(arm.UC_ARM_REG_PC,u.reg_read(arm.UC_ARM_REG_LR))
  for address in (self.stop+4,self.stop+8):self.u.hook_add(unicorn.UC_HOOK_CODE,override,begin=address,end=address)

 def call(self,op,capacity,offset,mode,io,event):
  u=self.u;self.calls=0;self.io_size=len(io)
  table=[0]*8;kind=0
  table[6]=self.functions[2*kind]['address'] if mode==0 else self.stop+4*mode
  table[7]=self.functions[2*kind+1]['address'] if mode==0 else self.stop+4*mode
  event=bytearray(event);event[EVENT_SIZE-32:EVENT_SIZE]=struct.pack('<8I',*table);before_event=bytes(event)
  u.mem_write(self.obj,struct.pack('<IIi',self.io,self.io+offset,capacity));u.mem_write(self.io,bytes(io));u.mem_write(self.event,before_event)
  u.mem_write(self.codec,struct.pack('<I',self.event+EVENT_SIZE-32)+bytes(12))
  for i in range(13):u.reg_write(getattr(arm,f'UC_ARM_REG_R{i}'),0)
  u.reg_write(arm.UC_ARM_REG_CPSR,0x10);u.reg_write(arm.UC_ARM_REG_SP,self.stack+0xff00);u.reg_write(arm.UC_ARM_REG_LR,self.stop)
  u.reg_write(arm.UC_ARM_REG_R0,self.codec);u.reg_write(arm.UC_ARM_REG_R1,self.event if op%2 else self.obj);u.reg_write(arm.UC_ARM_REG_R2,self.obj if op%2 else self.event)
  u.emu_start(self.functions[op]['address'],self.stop,count=100000)
  assert u.reg_read(arm.UC_ARM_REG_PC)==self.stop and u.reg_read(arm.UC_ARM_REG_SP)==self.stack+0xff00
  result=u.reg_read(arm.UC_ARM_REG_R0);assert result in (0,1)
  base,cursor,size=struct.unpack('<IIi',u.mem_read(self.obj,12));assert base==self.io and size==capacity
  assert self.calls==(1 if op<2 or capacity-offset>=(4 if op%2 else 6) else 0)
  return result,cursor-self.io,before_event,bytes(u.mem_read(self.io,len(io))),bytes(u.mem_read(self.event,EVENT_SIZE))

def prepare(seed,count,background=None):
 event=bytearray(pattern(seed+1 if background is None else background,EVENT_SIZE));event[:4]=struct.pack('<I',17988|((seed&1)<<16))
 event[16:20]=struct.pack('<I',(0,1,32768,65535,0x12345678,0xffffffff,0x80000000,0x7f812345)[seed%8])
 bits=(0,0x80000000,0x7f800000,0xff800000,0x7fc12345,0x7f812345,0xffffffff,1)
 for i in range(2):event[20+4*i:24+4*i]=struct.pack('<I',bits[(seed+i)%8])
 event[28:32]=struct.pack('<HH',(0,1,32767,32768,65535,255,256,65534)[seed%8],count)
 raw=bytes(event[16:18])+bytes(event[20:32])+bytes((i*17+seed*43)&255 for i in range(min(count,4096)))
 return event,raw

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('repository',type=Path);a=p.parse_args();target=a.repository/'uc-library/validation/uc-file-data';target.mkdir(parents=True,exist_ok=True)
 vectors=target/'arm-vectors.bin';assert not vectors.exists(),'preserve previous fixtures'
 records=0;counts=collections.Counter();partials=collections.Counter();originals=[];cache={}
 def base(seed,size):
  if (seed,size) not in cache:cache[seed,size]=pattern(seed,size)
  return cache[seed,size]
 with vectors.open('wb') as output:
  output.write(b'UCFDv001'+struct.pack('<I',0))
  for role_id,role in enumerate(('client','server')):
   obj=Oracle(a.repository,role)
   def emit(op,remaining,offset,seed,event,raw,mode=0):
    nonlocal records
    capacity=remaining+offset;size=max(capacity+16,64);raw_io=base(seed,size);raw_event=base(seed+1,EVENT_SIZE);io=bytearray(raw_io)
    if op%2:
     wire=(b'\x34\x12\x78\x56' if op>=2 else b'')+raw;io[offset:min(size,offset+len(wire))]=wire[:size-offset]
    result,cursor,before_event,out_io,out_event=obj.call(op,capacity,offset,mode,io,event)
    output.write(struct.pack('<BBBBiiiii',role_id,op,result,mode,capacity,offset,cursor,size,seed));patch(output,raw_io,io);patch(output,raw_event,before_event);patch(output,io,out_io);patch(output,before_event,out_event)
    key=role+':'+METHODS[op][1]+':override'+str(mode);counts[key]+=1
    if not result and (cursor!=offset or out_io!=bytes(io) or out_event!=before_event):partials[key]+=1
    records+=1
   for op in range(4):
    for seed in range(8):
     for count in (0,1,4095,4096,4097,32767,32768,65535):
      wire,raw=prepare(seed,count);event=wire if not op%2 else prepare((seed+1)%8,(0,1,4095,4096,4097,65535,32768,2)[seed],background=seed+1)[0]
      prefix=(4 if op%2 else 6) if op>=2 else 0;bounds=[0,2,6,10,12,14,14+min(count,4096),14+count]
      cuts=set(range(23))|{8192}
      for bound in bounds:cuts.update([prefix+bound-1,prefix+bound,prefix+bound+1])
      for remaining in sorted(n for n in cuts if 0<=n<=65564):
       if not op%2 and count>4096 and remaining>4096:continue
       for offset in (0,7):
        emit(op,remaining,offset,seed,event,raw)
        if op>=2 and seed in (0,7) and count==0:emit(op,remaining,offset,seed,event,raw,1);emit(op,remaining,offset,seed,event,raw,2)
   originals.append(dict(role=role,elf_sha256=obj.manifest['sha256'],functions=obj.functions,helpers=dict(obj.helpers)));print(role,records,'ARM fixed FileData fixtures',flush=True)
  output.seek(8);output.write(struct.pack('<I',records))
 report=dict(records=records,cases=dict(counts),partial_mutation_failures=dict(partials),originals=originals,
             vectors_sha256=hashlib.sha256(vectors.read_bytes()).hexdigest(),unicorn_version=unicorn.__version__,
             vector_format='UCFDv001;LEcount;24metadata+4patches asUCMRv001;pattern(i,seed)=(29*i+71*seed)&255;IOseed/EVENTseed+1,8192bytes.',
             domain='DisjointvalidIOthrough65587bytes/event8192bytes; cursors0/7 andexactid/rawword/short/count/data/skipboundaries. Counts0/1/4095/4096/4097/32767/32768/65535; cappedcopy4096thenattemptedskipwithunclampedcount retained. FirstIDreadclearsfull32-bitfieldonfailureandzeroextendsLE16onsuccess; high32inputIDs,raw32NaNbits,rawsampleallbytevalues. Writer>4096onlyprecopycapacityrejection; successfuloversizedaccessunsafeandexcluded. Typed/false/truevirtualtargets+callcountschecked. Invalidpointers/overflow/alias/concurrency excluded.',
             dependencies='ActualoriginalARMFileData/commonheader/primitive/bufferfunctions; onlyimportedmemcpystandardcontract andexplicitvirtualoverridesmodeled. Fixed4096storage: noCorebuffer/pool/resize/allocatorimplementation oractualfile/deviceIO.',
             limitations=['Portablestorage/fieldnames/semantictypes/callbackhierarchy/returnspelling; originalconstructors/registration/ownership/layout/vtable/ARMABI unresolved.','Readerretainsoversizedcountwithprefixstorage; reencodingrequiresboundedwriterdomain, neverautomaticclamping.','IndependentFactoryCodecrequiresbind/unbindofreturneditems; originalregistration/poolsremainpending.','Noactualfileupdate/erase/programming/hardwaretests.'])
 (target/'oracle.json').write_text(json.dumps(report,indent=2)+'\n');print(records,'ARM fixed FileData cases complete',flush=True)

if __name__=='__main__':main()
