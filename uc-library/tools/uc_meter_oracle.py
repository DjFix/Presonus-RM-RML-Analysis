#!/usr/bin/env python3
"""Original ARM UC meter codecs; compact byte-patch fixtures preserve canaries."""
import argparse,collections,hashlib,json,struct
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
from core_uc_oracle import Oracle as Loader

EVENT_SIZE=2336
METHODS=[]
for name,tag in [('MeterEvent8',19778),('MeterEvent16',19795)]:
 prefix=f'_ZNK8Presonus2UC15MeterEventClassINS0_{len(name)}{name}ELi{tag}EE'
 METHODS.extend([(prefix+'5writeERNS0_12BufferWriterERKS2_',name+'Write'),(prefix+'4readERS2_RNS0_12BufferReaderE',name+'Read')])
for name,tag in [('MeterEvent8',19778),('MeterEvent16',19795)]:
 prefix=f'_ZNK8Presonus2UC19PrimitiveEventClassINS0_{len(name)}{name}ELi{tag}EE'
 METHODS.extend([(prefix+'5writeERNS0_12BufferWriterERKNS0_5EventE',name+'DispatchWrite'),(prefix+'4readERNS0_5EventERNS0_12BufferReaderE',name+'DispatchRead')])
def pattern(seed,size):return bytes((i*29+seed*71)&255 for i in range(size))
def patch(output,before,after):
 assert len(before)==len(after)
 runs=[];start=None
 for i,(a,b) in enumerate(zip(before,after)):
  if a!=b and start is None:start=i
  if a==b and start is not None:runs.append((start,after[start:i]));start=None
 if start is not None:runs.append((start,after[start:]))
 output.write(struct.pack('<I',len(runs)))
 for start,data in runs:output.write(struct.pack('<II',start,len(data))+data)

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
  def count(u,address,size,user):self.calls+=1
  for symbol in self.functions[:4]:self.u.hook_add(unicorn.UC_HOOK_CODE,count,begin=symbol['address'],end=symbol['address'])
  def override(u,address,size,user):
   self.calls+=1;u.reg_write(arm.UC_ARM_REG_R0,int(address==self.stop+8));u.reg_write(arm.UC_ARM_REG_PC,u.reg_read(arm.UC_ARM_REG_LR))
  for address in (self.stop+4,self.stop+8):self.u.hook_add(unicorn.UC_HOOK_CODE,override,begin=address,end=address)

 def call(self,op,capacity,offset,mode,io,event):
  u=self.u;self.calls=0;self.io_size=len(io)
  table=[0]*8;kind=(op//2)%2
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
  assert self.calls==(1 if op<4 or capacity-offset>=(4 if op%2 else 6) else 0)
  return result,cursor-self.io,before_event,bytes(u.mem_read(self.io,len(io))),bytes(u.mem_read(self.event,EVENT_SIZE))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('repository',type=Path);a=p.parse_args()
 target=a.repository/'uc-library/validation/uc-meter';target.mkdir(parents=True,exist_ok=True)
 vectors=target/'arm-vectors.bin';assert not vectors.exists(),'preserve previous fixtures'
 records=0;counts=collections.Counter();partials=collections.Counter();originals=[];cache={}
 def base(seed,size):
  key=(seed,size)
  if key not in cache:cache[key]=pattern(seed,size)
  return cache[key]
 with vectors.open('wb') as output:
  output.write(b'UCMRv001'+struct.pack('<I',0))
  for role_id,role in enumerate(('client','server')):
   oracle=Oracle(a.repository,role)
   def emit(op,remaining,offset,count,groups,mode=0,retained=None):
    nonlocal records
    width=1+(op//2)%2;seed=(count+groups+op)%4;capacity=remaining+offset;io_size=max(capacity+16,64)
    raw_io=base(seed,io_size);raw_event=base(seed+1,EVENT_SIZE);io=bytearray(raw_io);event=bytearray(raw_event)
    event[:4]=struct.pack('<I',19778 if width==1 else 19795);event[16:20]=struct.pack('<I',0x80ff0011+seed)
    event[20:22]=struct.pack('<H',0xffff-seed)
    old_count=(0,1,1024,65535)[seed] if retained is None else retained
    event[22:24]=struct.pack('<H',old_count if op%2 else count);event[24]=(0,35,37,255)[seed] if op%2 else groups
    def put(pos,data):
     if pos<len(io):io[pos:min(len(io),pos+len(data))]=data[:len(io)-pos]
    if op%2:
     pos=offset
     if op>=4:put(pos,b'\x34\x12\x78\x56');pos+=4
     put(pos,struct.pack('>I',0x80ff0011+seed)+struct.pack('<HH',0xffff-seed,count))
     put(pos+8+count*width,bytes([groups]));put(pos+9+count*width,bytes((i*13+seed*31)&255 for i in range(min(groups,36)*6)))
    result,next_offset,before_event,out_io,out_event=oracle.call(op,capacity,offset,mode,io,event)
    output.write(struct.pack('<BBBBiiiii',role_id,op,result,mode,capacity,offset,next_offset,io_size,seed))
    patch(output,raw_io,io);patch(output,raw_event,before_event);patch(output,io,out_io);patch(output,before_event,out_event)
    key=role+':'+METHODS[op][1]+':override'+str(mode);counts[key]+=1
    if not result and (next_offset!=offset or out_io!=bytes(io) or out_event!=before_event):partials[key]+=1
    records+=1
   for op in range(8):
    width=1+(op//2)%2
    for count in (0,1,2,7,1023,1024,1025,32767,32768,65535):
     groups_list=(0,36,255) if op%2 else (0,1,36)
     if op%2 and count in (0,1024):groups_list=(0,1,35,36,37,255)
     for groups in groups_list:
      prefix=(4 if op%2 else 6) if op>=4 else 0;data_start=prefix+8;size=count*width
      cuts=set(range(13))|{data_start+min(size,1024*width)-1,data_start+min(size,1024*width),data_start+min(size,1024*width)+1,
                          data_start+size-1,data_start+size,data_start+size+1,data_start+size+2,data_start+size+3,data_start+size+5,
                          data_start+size+7,data_start+size+1+min(groups,36)*6-1,data_start+size+1+min(groups,36)*6,data_start+size+2+min(groups,36)*6}
      for remaining in sorted(x for x in cuts if 0<=x<=131328):
       if not op%2 and count>1024 and remaining>1024*width:continue
       for offset in (0,7):
        emit(op,remaining,offset,count,groups)
        if op>=4 and count in (0,1024) and groups==0:
         emit(op,remaining,offset,count,groups,1);emit(op,remaining,offset,count,groups,2)
   originals.append(dict(role=role,elf_sha256=oracle.manifest['sha256'],functions=oracle.functions,helpers=dict(oracle.helpers)))
   print(role,records,'ARM meter fixtures',flush=True)
  output.seek(8);output.write(struct.pack('<I',records))
 report=dict(records=records,cases=dict(counts),partial_mutation_failures=dict(partials),originals=originals,
             vectors_sha256=hashlib.sha256(vectors.read_bytes()).hexdigest(),unicorn_version=unicorn.__version__,
             vector_format='UCMRv001; LEcount;24-byte metadata then4bytepatches: IOseed,EVENTseed,IOresult,EVENTresult; eachpatch has u32runcount thenu32offset/u32length/literalbytes; pattern(i,seed)=(29*i+71*seed)&255; eventseed=seed+1,2336bytes.',
             domain='Disjoint valid IO images through131351bytes and2336-byte event images. Counts0,1,2,7,1023,1024,1025,32767,32768,65535, widths1/2, exactheader/data/skip/record boundaries, cursors0/7. Readers clamp copieddata1024/2048 and recordCount36, retain originalcount; stale initialcounts and recordcounts tested. Writers count<=1024/recordCount<=36, or oversized count only when capacity rejects before sample access. Rawsamplebytes include allbytevalues. Invalid pointer/overflow/alias/concurrency excluded.',
             dependencies='Actual original ARM meter/commonheader/primitive/buffer instructions execute; imported memcpy modeled by standardcontract only. Syntheticvtable points originaltypedmethods or explicit unchangedfalse/trueoverrides. NoCore, pool, resize or originalctorimplementation.',
             limitations=['Portable boundedstorage, callbackbindings and independenttypedFactoryCodec aliases; originalclass layout/inheritance/ownership/vtable/constructorABI and non-template returnspelling unresolved.','Oversizedwriter sample access and recordCount>36 aftersuccessfulsamplecopy are potentiallyunsafe and excluded, not silentlyclamped.','Headerread expectsconsumedtag. Independentadapter requires explicitbind/unbind forreturneditems.','Hardwaretestingdeferred.'])
 (target/'oracle.json').write_text(json.dumps(report,indent=2)+'\n');print(records,'ARM meter cases complete',flush=True)

if __name__=='__main__':main()
