#!/usr/bin/env python3
"""Original ARM primitive/header/payload dispatch and discovery-alive fixtures."""
import argparse,collections,hashlib,json,struct
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
from uc_event_oracle import make_oracle

TYPES=[('UDPMappingEvent',21837,'UDPMappingEventClass'),('MidiMessageEvent',19789,'MidiMessageEventClass'),
       ('ExtensionQueryEvent',17745,'ExtensionQueryEventClass'),('ParamValueEvent',20566,'ParamValueEventClass'),
       ('ParamStringEvent',20563,'ParamStringEventClass'),('DiscoveryAliveEvent',17473,'DiscoveryAliveEventClass')]
METHODS=[]
for name,tag,_ in TYPES:
 prefix=f'_ZNK8Presonus2UC19PrimitiveEventClassINS0_{len(name)}{name}ELi{tag}EE'
 METHODS.extend([(prefix+'5writeERNS0_12BufferWriterERKNS0_5EventE',name+'Write'),
                 (prefix+'4readERNS0_5EventERNS0_12BufferReaderE',name+'Read')])
METHODS.extend([('_ZNK8Presonus2UC24DiscoveryAliveEventClass5writeERNS0_12BufferWriterERKNS0_19DiscoveryAliveEventE','DiscoveryPayloadWrite'),
                ('_ZNK8Presonus2UC24DiscoveryAliveEventClass4readERNS0_19DiscoveryAliveEventERNS0_12BufferReaderE','DiscoveryPayloadRead')])

def word(value):return struct.pack('<I',value)
def pattern(seed):return bytes((i*29+seed*17)%255+1 for i in range(512))
def prepare(kind,seed,length):
 event=bytearray(pattern(seed));event[:4]=word(TYPES[kind][1]|((seed&1)<<16))
 payload=b'';boundaries=[]
 if kind==0:payload=bytes(event[16:18])
 elif kind==1:payload=bytes(event[16:20])
 elif kind==2:payload=bytes(event[16:20])[::-1]
 elif kind in (3,4):
  n=(0,1,7,127)[length];event[16+n]=0;payload=bytes(event[16:17+n])+bytes(event[144:146]);boundaries=[n,n+1,n+2,n+3]
  if kind==3:event[148:152]=word((0x80000000,0x7fc12345,0x7f812345,0xffffffff)[seed%4]);payload+=bytes(event[148:152])
  else:
   n=(0,1,31,255)[length];event[146+n]=0;payload+=bytes(event[146:147+n])
 else:
  version=(0,1,0x80000000,0xffffffff)[seed%4];event[16:20]=word(version);payload=word(version)
  if version&0x80000000:payload+=bytes(event[20:36]);boundaries+=[4,8,10,12,20]
  for index,start in enumerate((36,100,164,228)):
   n=(0,1,7,63)[(length+index)%4];event[start+n]=0;boundaries.extend([len(payload),len(payload)+n]);payload+=bytes(event[start:start+n+1])
 boundaries.extend([0,1,2,3,4,len(payload)-1,len(payload),len(payload)+1])
 return event,payload,boundaries

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('repository',type=Path);a=p.parse_args()
 target=a.repository/'uc-library/validation/uc-dispatch';target.mkdir(parents=True,exist_ok=True)
 vectors=target/'arm-vectors.bin';assert not vectors.exists(),'preserve existing fixtures'
 records=0;counts=collections.Counter();partials=collections.Counter();originals=[]
 with vectors.open('wb') as output:
  output.write(b'UCDSv001'+struct.pack('<I',0))
  for role_id,role in enumerate(('client','server')):
   obj=make_oracle(a.repository,role);u=obj.u
   symbols=json.loads((a.repository/'uc-library/recovered'/role/'all-symbols.json').read_text());by_name={s['mangled']:s for s in symbols}
   functions=[by_name[n] for n,_ in METHODS]
   targets=[]
   for _,_,codec in TYPES:
    targets.append([next(s['address'] for s in symbols if s.get('demangled','').startswith('Presonus::UC::'+codec+'::'+method+'(')) for method in ('write','read')])
   state={'calls':0,'mode':0}
   def count_payload(u,address,size,user):state['calls']+=1
   for pair in targets:
    for address in pair:u.hook_add(unicorn.UC_HOOK_CODE,count_payload,begin=address,end=address)
   def override(u,address,size,user):
    state['calls']+=1;u.reg_write(arm.UC_ARM_REG_R0,1 if address==obj.stop+8 else 0)
    u.reg_write(arm.UC_ARM_REG_PC,u.reg_read(arm.UC_ARM_REG_LR))
   for address in (obj.stop+4,obj.stop+8):u.hook_add(unicorn.UC_HOOK_CODE,override,begin=address,end=address)
   def emit(op,capacity,offset,mode,event,io):
    nonlocal records
    kind=min(op//2,5);event=bytearray(event);before_io=bytes(io)
    table=[0]*8;table[6]=targets[kind][0] if mode==0 else obj.stop+4*mode;table[7]=targets[kind][1] if mode==0 else obj.stop+4*mode
    event[448:480]=struct.pack('<8I',*table);before_event=bytes(event)
    u.mem_write(obj.obj,struct.pack('<IIi',obj.data,obj.data+offset,capacity));u.mem_write(obj.data,before_io);u.mem_write(obj.event,before_event)
    u.mem_write(obj.codec,struct.pack('<I',obj.event+448)+bytes(12));state['calls']=0
    for i in range(13):u.reg_write(getattr(arm,f'UC_ARM_REG_R{i}'),0)
    u.reg_write(arm.UC_ARM_REG_CPSR,0x10);u.reg_write(arm.UC_ARM_REG_SP,obj.stack+0xff00);u.reg_write(arm.UC_ARM_REG_LR,obj.stop)
    u.reg_write(arm.UC_ARM_REG_R0,obj.codec);u.reg_write(arm.UC_ARM_REG_R1,obj.event if op%2 else obj.obj);u.reg_write(arm.UC_ARM_REG_R2,obj.obj if op%2 else obj.event)
    u.emu_start(functions[op]['address'],obj.stop,count=100000)
    assert u.reg_read(arm.UC_ARM_REG_PC)==obj.stop and u.reg_read(arm.UC_ARM_REG_SP)==obj.stack+0xff00
    result=u.reg_read(arm.UC_ARM_REG_R0);assert result in (0,1)
    base,cursor,size=struct.unpack('<IIi',u.mem_read(obj.obj,12));assert base==obj.data and size==capacity
    assert state['calls']==(1 if op>=12 or capacity-offset>=(4 if op%2 else 6) else 0)
    out_io=bytes(u.mem_read(obj.data,512));out_event=bytes(u.mem_read(obj.event,512));next_offset=cursor-obj.data
    output.write(struct.pack('<BBBBiii',role_id,op,result,mode,capacity,offset,next_offset)+before_io+before_event+out_io+out_event)
    key=role+':'+METHODS[op][1]+':override'+str(mode);counts[key]+=1
    if not result and (next_offset!=offset or out_io!=before_io or out_event!=before_event):partials[key]+=1
    records+=1
   for op in range(14):
    kind=min(op//2,5)
    for seed in range(4):
     for length in range(4):
      wire,payload,bounds=prepare(kind,seed,length);header=bytes(wire[8:10])+bytes(wire[12:14])
      raw=(header if op<12 else b'')+payload
      for offset in (0,7):
       cuts={0,1,2,3,4,5,6,7,len(raw)-1,len(raw),len(raw)+1,505}
       cuts.update(b+(4 if op<12 and op%2 else 6 if op<12 else 0) for b in bounds)
       for remaining in sorted(n for n in cuts if 0<=n<=505):
        for mode in ((0,1,2) if op<12 else (0,)):
         event=wire if not op%2 else prepare(kind,seed+1,(length+1)%4)[0]
         io=bytearray(pattern(seed+11));io[offset:offset+len(raw)]=raw
         emit(op,offset+remaining,offset,mode,event,io)
    if op%2 and kind>=3:
     for offset in (0,7):
      for capacity in (offset+63,offset+64,offset+127,offset+128,512):
       event=prepare(kind,0,0)[0];io=bytearray(pattern(10))
       if kind==5:io[offset+(4 if op<12 else 0):offset+(4 if op<12 else 0)+4]=word(0)
       emit(op,capacity,offset,0,event,io)
   originals.append(dict(role=role,elf_sha256=obj.manifest['sha256'],functions=functions,typed_targets=targets,helpers=dict(obj.helpers)))
   print(role,records,'ARM dispatch fixtures',flush=True)
  output.seek(8);output.write(struct.pack('<I',records))
 report=dict(records=records,cases=dict(counts),partial_mutation_failures=dict(partials),originals=originals,
             vectors_sha256=hashlib.sha256(vectors.read_bytes()).hexdigest(),unicorn_version=unicorn.__version__,
             domain='Valid disjoint512-byte IO/event images with cursors0/7 and capacities through512; exactheader/payload/string/extension boundaries, nonnegative/negative version bits, retained initial read fields, arbitrary byte strings, max path127/text255/discoverystrings63 and missing reader NUL. Primitive wrappers dispatch original typed ARM methods or contract overrides returningfalse/true unchanged. Everypayloadcallcount checked. Invalid pointers/alias/overflow/concurrency excluded.',
             dependencies='Original ARM primitive wrapper, commonheader, typedpayload and buffer instructions execute. Only imported memcpy/strlen standardcontracts and explicitvirtualoverridecallbacks are modeled. Syntheticvalidvtable slots24/28 initialize dispatch; no original constructor/pool/Core recovery.',
             limitations=['Portable callbacks replace original class hierarchy/vtable layout; non-template return spelling and original layout/ownership/constructors unresolved.','TypedFactoryCodec ownership/binding/registration are independent wrappers, not original addClass/DataItem/pool recovery.','Header read expects consumed tag. Original EventClass(EventItem) virtualwrapper remains pending.','Hardware testing deferred.'])
 (target/'oracle.json').write_text(json.dumps(report,indent=2)+'\n');print(records,'ARM dispatch cases complete',flush=True)

if __name__=='__main__':main()
