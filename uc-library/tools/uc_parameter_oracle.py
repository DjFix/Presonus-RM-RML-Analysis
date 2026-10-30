#!/usr/bin/env python3
"""Original ARM parameter payloads/dispatch; compact whole-state byte patches."""
import argparse,collections,hashlib,json,struct
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
import uc_meter_oracle as meter

TYPES=[('ParamEditEvent',20549),('ParamModeEvent',20557),('ParamIncrementEvent',20553),
       ('ParamColorEvent',20547),('ParamRangeEvent',20562),('ParamStringListEvent',20556)]
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
def prepare(kind,seed,length):
 event=bytearray(pattern(seed,2336));name,tag=TYPES[kind];event[:4]=struct.pack('<I',tag|((seed&1)<<16))
 n=(0,1,7,127)[length];event[16+n]=0;event[144:146]=struct.pack('<H',(0,1,32767,32768,65535,255,256,65534)[seed%8])
 raw=bytes(event[16:17+n])+bytes(event[144:146]);bounds=[0,n,n+1,n+2,n+3];strings=[(0,128)]
 bits=(0,0x80000000,0x7f800000,0xff800000,0x7fc12345,0x7f812345,0xffffffff,1)
 if kind==1:
  n=(0,1,7,63)[length];event[146+n]=0;strings.append((len(raw),64));raw+=bytes(event[146:147+n])
 elif kind==2:event[146:148]=struct.pack('<H',(0,1,32767,32768,65535,255,256,65534)[seed%8]);raw+=bytes(event[146:148])
 elif kind in (3,4,5):
  for index in range(5 if kind==4 else 1):
   event[148+index*4:152+index*4]=struct.pack('<I',bits[(seed+index)%8]);bounds.append(len(raw));raw+=bytes(event[148+index*4:152+index*4]);bounds.append(len(raw))
  if kind==4:
   for index,start in enumerate((168,200)):
    n=(0,1,7,31)[(length+index)%4];event[start+n]=0;strings.append((len(raw),32));bounds.extend([len(raw),len(raw)+n]);raw+=bytes(event[start:start+n+1])
  if kind==5:
   n=(0,1,31,1023)[length];event[152+n]=0;strings.append((len(raw),1024));raw+=bytes(event[152:153+n])
 bounds.extend([len(raw)-1,len(raw),len(raw)+1]);return event,raw,bounds,strings

def make_oracle(repository,role):
 saved=meter.METHODS;meter.METHODS=METHODS
 try:obj=meter.Oracle(repository,role)
 finally:meter.METHODS=saved
 def count(u,address,size,user):obj.calls+=1
 for symbol in obj.functions[4:12]:obj.u.hook_add(unicorn.UC_HOOK_CODE,count,begin=symbol['address'],end=symbol['address'])
 symbols=json.loads((repository/'uc-library/recovered'/role/'all-symbols.json').read_text())
 strlen=next(s for s in symbols if s['address'] and s['mangled'].startswith('strlen@@'))
 def hook(u,address,size,user):
  src=u.reg_read(arm.UC_ARM_REG_R0)
  for n in range(1024):
   assert obj.event<=src+n<obj.event+2336
   if u.mem_read(src+n,1)[0]==0:break
  else:raise AssertionError('writer lacks bounded NUL')
  u.reg_write(arm.UC_ARM_REG_R0,n);u.reg_write(arm.UC_ARM_REG_PC,u.reg_read(arm.UC_ARM_REG_LR));obj.helpers['strlen']+=1
 obj.u.hook_add(unicorn.UC_HOOK_CODE,hook,begin=strlen['address'],end=strlen['address']);return obj

def call(obj,op,capacity,offset,mode,io,event):
 u=obj.u;obj.calls=0;obj.io_size=len(io);kind=(op%12)//2
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
 assert obj.calls==(1 if op<12 or capacity-offset>=(4 if op%2 else 6) else 0)
 return result,cursor-obj.io,before_event,bytes(u.mem_read(obj.io,len(io))),bytes(u.mem_read(obj.event,2336))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('repository',type=Path);a=p.parse_args();target=a.repository/'uc-library/validation/uc-parameter';target.mkdir(parents=True,exist_ok=True)
 vectors=target/'arm-vectors.bin';assert not vectors.exists(),'preserve previous fixtures'
 records=0;counts=collections.Counter();partials=collections.Counter();originals=[];cache={}
 def base(seed,size):
  if (seed,size) not in cache:cache[seed,size]=pattern(seed,size)
  return cache[seed,size]
 with vectors.open('wb') as output:
  output.write(b'UCPAv001'+struct.pack('<I',0))
  for role_id,role in enumerate(('client','server')):
   obj=make_oracle(a.repository,role)
   def emit(op,remaining,offset,seed,event,raw,mode=0):
    nonlocal records
    capacity=remaining+offset;size=max(capacity+16,64);raw_io=base(seed+11,size);raw_event=base(seed+1,2336);io=bytearray(raw_io)
    if op%2:
     wire=(b'\x34\x12\x78\x56' if op>=12 else b'')+raw
     io[offset:min(size,offset+len(wire))]=wire[:size-offset]
    result,cursor,before_event,out_io,out_event=call(obj,op,capacity,offset,mode,io,event)
    output.write(struct.pack('<BBBBiiiii',role_id,op,result,mode,capacity,offset,cursor,size,seed))
    meter.patch(output,raw_io,io);meter.patch(output,raw_event,before_event);meter.patch(output,io,out_io);meter.patch(output,before_event,out_event)
    key=role+':'+METHODS[op][1]+':override'+str(mode);counts[key]+=1
    if not result and (cursor!=offset or out_io!=bytes(io) or out_event!=before_event):partials[key]+=1
    records+=1
   for op in range(24):
    kind=(op%12)//2
    for seed in range(8):
     for length in (seed%4,(seed+1)%4):
      wire,raw,bounds,strings=prepare(kind,seed,length);event=wire if not op%2 else prepare(kind,(seed+1)%8,(length+1)%4)[0]
      prefix=(4 if op%2 else 6) if op>=12 else 0
      cuts=set(range(9))|{2048}
      for bound in bounds:cuts.update([prefix+bound-1,prefix+bound,prefix+bound+1])
      for remaining in sorted(n for n in cuts if 0<=n<=2048):
       for offset in (0,7):
        emit(op,remaining,offset,seed,event,raw)
        if op>=12 and seed in (0,7) and length==seed%4:
         emit(op,remaining,offset,seed,event,raw,1);emit(op,remaining,offset,seed,event,raw,2)
    if op%2:
     event,raw,bounds,strings=prepare(kind,0,0);prefix=4 if op>=12 else 0
     for start,limit in strings:
      bad=raw[:start]+bytes([0xa5])*(limit+2)
      for remaining in (prefix+start+limit-1,prefix+start+limit,prefix+start+limit+1,2048):
       for offset in (0,7):emit(op,remaining,offset,0,event,bad)
   originals.append(dict(role=role,elf_sha256=obj.manifest['sha256'],functions=obj.functions,helpers=dict(obj.helpers)))
   print(role,records,'ARM parameter fixtures',flush=True)
  output.seek(8);output.write(struct.pack('<I',records))
 report=dict(records=records,cases=dict(counts),partial_mutation_failures=dict(partials),originals=originals,
             vectors_sha256=hashlib.sha256(vectors.read_bytes()).hexdigest(),unicorn_version=unicorn.__version__,
             vector_format='UCPAv001;LEcount;24metadata then4patches asUCMRv001. Nonzero pattern(i,seed)=(29*i+17*seed)%255+1;IOseed=seed+11,EVENTseed=seed+1,2336bytes.',
             domain='Disjoint valid IO through2071bytes/event2336bytes; cursors0/7; capacities0..2055 at exactpath/index/rawword/string boundaries; writerNULlimits path127/mode63/rangelabels31/listtext1023, missingreaderNULlimits128/64/32/1024. Index/increment edge16bits; raw32bits0/negativezero/infinities/quiet+signalingNaNs/allones; nofloatmath. Actualtypedtargets and unchangedfalse/truevirtualoverrides; everypayloadcallcountchecked. Invalid/negative-pointer/capacity/alias/overflow/concurrency excluded.',
             dependencies='Actual original ARM parameter/commonheader/primitive/buffer instructions; only imported memcpy/strlen standardcontracts and explicitvirtualoverride callbacks modeled. Fixedstringstorage only; noCore, containers, pools or resize implementation.',
             limitations=['Portablestorage/fieldnames/numericsemantictypes/returnspelling and callbackclasshierarchy; originalconstructors, ownership/layout/vtable/ARMABI unresolved.','ParamIncrement is2rawbitsbytes; StringList hasopaque32bits+1024byteCString, not an inventedparsedlist.','IndependentFactoryCodecbindings/allocations requireexplicitbind/unbind ofreturneditems; originalregistration/pools remainpending.','Hardwaretestingdeferred.'])
 (target/'oracle.json').write_text(json.dumps(report,indent=2)+'\n');print(records,'ARM parameter cases complete',flush=True)

if __name__=='__main__':main()
