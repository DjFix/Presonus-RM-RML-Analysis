#!/usr/bin/env python3
"""Original ARM no-member and file-control wire codecs, never device/file IO."""
import argparse,collections,hashlib,json,struct
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
import uc_parameter_oracle as parameter

TYPES=[('NoOpEvent',20047),('DiscoveryLeaveEvent',17484),('DiscoveryQueryEvent',17489),('KeepAliveEvent',19265),
       ('FileRequestEvent',18002),('FileDataRateEvent',18003),('FileAbortEvent',17985)]
METHODS=[]
for kind,(name,tag) in enumerate(TYPES):
 if kind<4:
  prefix=f'_ZNK8Presonus2UC28PrimitiveEventClassNoMembersINS0_{len(name)}{name}ELi{tag}EE'
  METHODS.extend([(prefix+'5writeERNS0_12BufferWriterERKS2_',name+'Write'),(prefix+'4readERS2_RNS0_12BufferReaderE',name+'Read')])
 else:
  codec=name+'Class';prefix=f'_ZNK8Presonus2UC{len(codec)}{codec}'
  METHODS.extend([(prefix+f'5writeERNS0_12BufferWriterERKNS0_{len(name)}{name}E',name+'Write'),(prefix+f'4readERNS0_{len(name)}{name}ERNS0_12BufferReaderE',name+'Read')])
for name,tag in TYPES:
 prefix=f'_ZNK8Presonus2UC19PrimitiveEventClassINS0_{len(name)}{name}ELi{tag}EE'
 METHODS.extend([(prefix+'5writeERNS0_12BufferWriterERKNS0_5EventE',name+'DispatchWrite'),(prefix+'4readERNS0_5EventERNS0_12BufferReaderE',name+'DispatchRead')])
pattern=parameter.pattern
def prepare(kind,seed,length):
 event=bytearray(pattern(seed,2336));event[:4]=struct.pack('<I',TYPES[kind][1]|((seed&1)<<16));raw=b'';bounds=[0];strings=[]
 if kind>=4:
  idbits=(0,1,32768,65535,0x12345678,0xffffffff,0x80000000,0x7f812345)[seed%8];event[16:20]=struct.pack('<I',idbits);raw=struct.pack('<H',idbits&65535);bounds+=[1,2]
  bits=(0,0x80000000,0x7f800000,0xff800000,0x7fc12345,0x7f812345,0xffffffff,1)
  if kind==4:
   event[20:24]=struct.pack('<I',bits[seed%8]);raw+=struct.pack('>I',bits[seed%8]);bounds.append(6)
   for index,start in enumerate((24,280)):
    n=(0,1,31,255)[(length+index)%4];event[start+n]=0;strings.append((len(raw),256));bounds.extend([len(raw),len(raw)+n]);raw+=bytes(event[start:start+n+1])
  if kind==5:
   for index in range(3):event[20+index*4:24+index*4]=struct.pack('<I',bits[(seed+index)%8]);bounds.append(len(raw));raw+=bytes(event[20+index*4:24+index*4]);bounds.append(len(raw))
 bounds.extend([len(raw)-1,len(raw),len(raw)+1]);return event,raw,bounds,strings

def make_oracle(repository,role):
 saved=parameter.METHODS;parameter.METHODS=METHODS
 try:obj=parameter.make_oracle(repository,role)
 finally:parameter.METHODS=saved
 def count(u,address,size,user):obj.calls+=1
 for symbol in obj.functions[12:14]:obj.u.hook_add(unicorn.UC_HOOK_CODE,count,begin=symbol['address'],end=symbol['address'])
 return obj

def call(obj,op,capacity,offset,mode,io,event):
 u=obj.u;obj.calls=0;obj.io_size=len(io);kind=(op%14)//2
 table=[0]*8;table[6]=obj.functions[2*kind]['address'] if mode==0 else obj.stop+4*mode;table[7]=obj.functions[2*kind+1]['address'] if mode==0 else obj.stop+4*mode
 event=bytearray(event);event[2304:2336]=struct.pack('<8I',*table);before_event=bytes(event)
 u.mem_write(obj.obj,struct.pack('<IIi',obj.io,obj.io+offset,capacity));u.mem_write(obj.io,bytes(io));u.mem_write(obj.event,before_event);u.mem_write(obj.codec,struct.pack('<I',obj.event+2304)+bytes(12))
 for i in range(13):u.reg_write(getattr(arm,f'UC_ARM_REG_R{i}'),0)
 u.reg_write(arm.UC_ARM_REG_CPSR,0x10);u.reg_write(arm.UC_ARM_REG_SP,obj.stack+0xff00);u.reg_write(arm.UC_ARM_REG_LR,obj.stop)
 u.reg_write(arm.UC_ARM_REG_R0,obj.codec);u.reg_write(arm.UC_ARM_REG_R1,obj.event if op%2 else obj.obj);u.reg_write(arm.UC_ARM_REG_R2,obj.obj if op%2 else obj.event)
 u.emu_start(obj.functions[op]['address'],obj.stop,count=100000)
 assert u.reg_read(arm.UC_ARM_REG_PC)==obj.stop and u.reg_read(arm.UC_ARM_REG_SP)==obj.stack+0xff00
 result=u.reg_read(arm.UC_ARM_REG_R0);assert result in (0,1)
 base,cursor,size=struct.unpack('<IIi',u.mem_read(obj.obj,12));assert base==obj.io and size==capacity
 assert obj.calls==(1 if op<14 or capacity-offset>=(4 if op%2 else 6) else 0)
 out_io=bytes(u.mem_read(obj.io,len(io)));out_event=bytes(u.mem_read(obj.event,2336))
 if op<8:assert result==1 and cursor==obj.io+offset and out_io==bytes(io) and out_event==before_event,'no-member payload mutated state'
 return result,cursor-obj.io,before_event,out_io,out_event

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('repository',type=Path);a=p.parse_args();target=a.repository/'uc-library/validation/uc-file-control';target.mkdir(parents=True,exist_ok=True)
 vectors=target/'arm-vectors.bin';assert not vectors.exists(),'preserve previous fixtures'
 records=0;counts=collections.Counter();partials=collections.Counter();originals=[];cache={}
 def base(seed,size):
  if (seed,size) not in cache:cache[seed,size]=pattern(seed,size)
  return cache[seed,size]
 with vectors.open('wb') as output:
  output.write(b'UCFWv001'+struct.pack('<I',0))
  for role_id,role in enumerate(('client','server')):
   obj=make_oracle(a.repository,role)
   def emit(op,remaining,offset,seed,event,raw,mode=0):
    nonlocal records
    capacity=remaining+offset;size=max(capacity+16,64);raw_io=base(seed+11,size);raw_event=base(seed+1,2336);io=bytearray(raw_io)
    if op%2:
     wire=(b'\x34\x12\x78\x56' if op>=14 else b'')+raw;io[offset:min(size,offset+len(wire))]=wire[:size-offset]
    result,cursor,before_event,out_io,out_event=call(obj,op,capacity,offset,mode,io,event)
    output.write(struct.pack('<BBBBiiiii',role_id,op,result,mode,capacity,offset,cursor,size,seed))
    parameter.meter.patch(output,raw_io,io);parameter.meter.patch(output,raw_event,before_event);parameter.meter.patch(output,io,out_io);parameter.meter.patch(output,before_event,out_event)
    key=role+':'+METHODS[op][1]+':override'+str(mode);counts[key]+=1
    if not result and (cursor!=offset or out_io!=bytes(io) or out_event!=before_event):partials[key]+=1
    records+=1
   for op in range(28):
    kind=(op%14)//2
    for seed in range(8):
     for length in ((seed%4,(seed+1)%4) if kind==4 else (0,)):
      wire,raw,bounds,strings=prepare(kind,seed,length);event=wire if not op%2 else prepare(kind,(seed+1)%8,(length+1)%4)[0];prefix=(4 if op%2 else 6) if op>=14 else 0
      cuts=set(range(13))|{64,512,2048}
      for bound in bounds:cuts.update([prefix+bound-1,prefix+bound,prefix+bound+1])
      for remaining in sorted(n for n in cuts if 0<=n<=2048):
       for offset in (0,7):
        emit(op,remaining,offset,seed,event,raw)
        if op>=14 and seed in (0,7):emit(op,remaining,offset,seed,event,raw,1);emit(op,remaining,offset,seed,event,raw,2)
    if op<8:
     for capacity in range(33):
      for offset in range(capacity+1):
       seed=(capacity+offset+op)%8;event,raw,_,_=prepare(kind,seed,0);emit(op,capacity-offset,offset,seed,event,raw)
    if op%2 and kind==4:
     event,raw,_,strings=prepare(kind,0,0);prefix=4 if op>=14 else 0
     for start,limit in strings:
      bad=raw[:start]+bytes([0xa5])*(limit+2)
      for remaining in (prefix+start+limit-1,prefix+start+limit,prefix+start+limit+1,2048):
       for offset in (0,7):emit(op,remaining,offset,0,event,bad)
   originals.append(dict(role=role,elf_sha256=obj.manifest['sha256'],functions=obj.functions,helpers=dict(obj.helpers)));print(role,records,'ARM no-member/file-control fixtures',flush=True)
  output.seek(8);output.write(struct.pack('<I',records))
 report=dict(records=records,cases=dict(counts),partial_mutation_failures=dict(partials),originals=originals,
             vectors_sha256=hashlib.sha256(vectors.read_bytes()).hexdigest(),unicorn_version=unicorn.__version__,
             vector_format='UCFWv001;LEcount;24metadata+4patches asUCPAv001;pattern(i,seed)=(29*i+17*seed)%255+1;IOseed+11/EVENTseed+1,2336bytes.',
             domain='Disjoint valid IOthrough2071bytes/event2336bytes; no-member payloads additionally everycapacity0..32/cursor0..capacity. Cursors0/7 and exactcommonheader/idLE16/rawBE-or-LE32/string256 boundaries. Wide32-bitid inputs include highbits/0xffffffff; failedreads clearfull32id and successfulreads zeroextend. Rawwordbits include signedzero/infinities/quiet+signalingNaNs; nofloatmath. WriterstringsNUL<=255; readerabsentNUL256; actualtypedtargets and unchangedfalse/trueoverrides checked. Invalid pointers/negativecaps/alias/overflow/concurrency excluded.',
             dependencies='Actual original ARM no-member/file-control/commonheader/primitive/buffer functions; only imported memcpy/strlen standardcontracts and explicitvirtualoverride callbacks modeled. NoCore/pool/allocation/resize recovery; noactualfile/device IO.',
             limitations=['Portable header/fixedstorage/fieldnames/semantictypes/callbackhierarchy/returnspelling; originalconstructors/registration/layout/vtable/ownership/ARMABI unresolved.','NoMember payload codecs are unconditional true and state-preserving; commonheader behavior belongs separately toPrimitivewrappers.','IndependenttypedFactoryCodec requires explicitbind/unbind ofreturneditems; originalregistration/pools remainpending.','Wireverificationonly; nofileupdate/erase/flashing orhardwaretesting.'])
 (target/'oracle.json').write_text(json.dumps(report,indent=2)+'\n');print(records,'ARM no-member/file-control cases complete',flush=True)

if __name__=='__main__':main()
