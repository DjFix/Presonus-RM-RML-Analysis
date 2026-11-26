"""Run exact selected application lifecycle bodies, preserving Core boundaries.
No Core binary implementation executes. App/provider allocations and clock/libm
are explicit fixture boundaries; native deallocation unmaps real fixture memory.
"""
import ctypes,hashlib,json,re,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UcError,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0 as R0,UC_ARM_REG_R1 as R1,UC_ARM_REG_R2 as R2,UC_ARM_REG_R3 as R3,UC_ARM_REG_PC as PC,UC_ARM_REG_LR as LR,UC_ARM_REG_SP as SP
ROOT=Path(__file__).resolve().parents[4]
PACKETBASE=Path('temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/sl_channel49_sol61/packet-r4/tasks')
OBJ,PEER,MIXER,PARAM,INFO,VT,STACK,STOP,HEAP=0x22000000,0x22001000,0x22002000,0x22003000,0x22004000,0x22005000,0x23000000,0x24000000,0x25000000
POW=ctypes.CDLL('libm.so.6').powf;POW.argtypes=[ctypes.c_float,ctypes.c_float];POW.restype=ctypes.c_float

def pack(*v):return struct.pack('<'+'I'*len(v),*[i&0xffffffff for i in v])
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def fl(v):return struct.unpack('<f',pack(v))[0]
def digest(b):return hashlib.sha256(b).hexdigest()
class Image:
 def __init__(self,original):
  self.path=ROOT/original['elf_path'];self.sha=original['elf']
  with self.path.open('rb') as f:
   assert hashlib.file_digest(f,'sha256').hexdigest()==self.sha;f.seek(0);e=ELFFile(f);self.segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD'];self.symbols={};self.at={};self.rows={}
   for s in e.get_section_by_name('.symtab').iter_symbols():
    if not s.name or not isinstance(s['st_shndx'],int):continue
    self.symbols[s.name]=s['st_value'];self.at.setdefault(s['st_value'],[]).append(s.name)
    sec=e.get_section(s['st_shndx']);off=s['st_value']-sec['sh_addr']
    if s['st_size'] and sec['sh_type']!='SHT_NOBITS' and 0<=off<=sec['sh_size']-s['st_size']:
     self.rows[s.name]=dict(address=s['st_value'],size=s['st_size'],section=s['st_shndx'],file_offset=sec['sh_offset']+off,sha256=digest(sec.data()[off:off+s['st_size']]))
   rel=e.get_section_by_name('.rel.plt');dyn=e.get_section(rel['sh_link']);plt=e.get_section_by_name('.plt');self.imports={dyn.get_symbol(r['r_info_sym']).name:plt['sh_addr']+20+12*i for i,r in enumerate(rel.iter_relocations()) if r['r_info_type']==22};self.import_at={v:k for k,v in self.imports.items()}
 def verify(self,o):
  r=self.rows[o['mangled']];assert [r[k] for k in ['address','size','section','file_offset','sha256']]==[o[k] for k in ['address','size','section','file_offset','range_sha256']]
 def cpu(self):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);lo=min(a for a,_,_ in self.segments)&~4095;hi=max(a+n for a,n,_ in self.segments);u.mem_map(lo,(hi-lo+4095)&~4095)
  for a,_,d in self.segments:u.mem_write(a,d)
  for a,n in [(OBJ,0x10000),(STACK,0x10000),(STOP,4096),(HEAP,0x10000)]:u.mem_map(a,n)
  return u

def run_lifecycle(image,o,probe=None):
 image.verify(o);u=image.cpu();events=[];writes=[];trace=[];entered={};allocated=HEAP;freed=[];parameter_values={};tag_parameters={};parameter_tags={};parameter_flags={};vector_cursor=HEAP+0x8000;clock_raw=0
 u.mem_write(OBJ,b'\xa5'*4096)
 def put(a,*v):u.mem_write(a,pack(*v))
 def words(a,n):return list(struct.unpack('<'+'I'*n,u.mem_read(a,n*4)))
 def word(a):return words(a,1)[0]
 def cstr(a):return bytes(u.mem_read(a,256)).split(b'\0',1)[0].decode(errors='replace')
 def ret(v=None):
  if v is not None:u.reg_write(R0,v&0xffffffff)
  u.reg_write(PC,u.reg_read(LR))
 # Null-linker initialized native precondition for independent destruction.
 if 'D' in o['mangled'].rsplit('E',1)[0][-2:]:put(OBJ+0x1dc,0)
 def hook(machine,pc,size,user):
  nonlocal allocated,vector_cursor
  trace.append(pc);a,b,c,d=[machine.reg_read(r) for r in (R0,R1,R2,R3)]
  syms=image.at.get(pc,[]);name=next((n for n in syms if n.startswith('_ZN4Core') or n.startswith('_ZNK4Core')),'')
  if name:
   if re.match(r'_ZN4Core8Portable9ComponentC[12]EPKc$',name):
    events.append(['CCL_Component_ctor',a-OBJ,cstr(b)]);u.mem_write(a+8,cstr(b).encode()[:31]+b'\0');put(a+0x50,0);put(a+0x58,0,0);ret(a)
   elif re.match(r'_ZN4Core8Portable9ComponentD[12]Ev$',name):events.append(['CCL_Component_cleanup',a-OBJ]);ret(a)
   elif name=='_ZN4Core8Portable12NumericParam8setValueEfb':
    assert (PARAM<=a<PARAM+0x1000 or a in parameter_tags)
    parameter_values[a]=b;events.append(['CCL_numeric_set',parameter_tags.get(a,a-PARAM),b,c]);ret()
   elif name=='_ZNK4Core8Portable12NumericParam8getValueEv':ret(parameter_values[a])
   elif name=='_ZNK4Core8Portable9Parameter9isEditingEv':ret(int(probe.get('case',{}).get('editing',True)))
   elif name=='_ZNK4Core8Portable10ColorParam8getValueEv':ret(0)
   elif name=='_ZN4Core8Portable10ColorParam8setValueEfb':events.append(['CCL_color_setValue_noop',parameter_tags[a],b,c]);ret()
   elif name=='_ZNK4Core8Portable12NumericParam9isNumericEv':ret(1)
   elif name=='_ZNK4Core8Portable10ColorParam9isNumericEv':ret(0)
   elif name=='_ZNK4Core8Portable9Component17getParameterByTagEi':
    events.append(['CCL_get_tag',a-OBJ,b]);ret(tag_parameters.get((a,b),0))
   elif name=='_ZN4Core8Portable9ParamList3addEPKNS0_9ParamInfoEib':
    assert c==3 and d==0
    owner=a-0x28
    for index in range(c):
     info=b+index*84;tag=word(info+4);pointer=HEAP+0x2000+len(parameter_tags)*96
     put(pointer,image.symbols['_ZTVN4Core8Portable12NumericParamE']+8);put(pointer+12,info)
     tag_parameters[(owner,tag)]=pointer;parameter_tags[pointer]=tag;parameter_flags[pointer]=word(info+60);parameter_values[pointer]=word(info+52)
    events.append(['CCL_add_application_parameters',owner-OBJ,c]);ret(1)
   elif name=='_ZN4Core8Portable9Parameter17setFeedbackNeededEb':events.append(['CCL_feedback',parameter_tags[a],b]);ret()
   elif name=='_ZN4Core8Portable9Parameter9setPublicEb':
    parameter_flags[a]=(parameter_flags[a]&~4) if b else parameter_flags[a]|4
    events.append(['CCL_public',parameter_tags[a],b]);ret()
   elif name=='_ZN4Core8Portable9Parameter7changedEv':events.append(['CCL_changed',parameter_tags[a]]);ret()
   elif name=='_ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE':events.append(['CCL_observer_add',parameter_tags[a],b-HEAP]);ret()
   elif name=='_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE':events.append(['CCL_observer_remove',parameter_tags[a],b-HEAP]);ret()
   elif name=='_ZN4Core6VectorIPNS_8Portable9ParameterEE6resizeEi':
    if b>word(a+12):
     capacity=max(b,32);old=word(a+4);count=word(a+8);pointer=vector_cursor;vector_cursor+=256
     if old and count:u.mem_write(pointer,bytes(u.mem_read(old,count*4)))
     put(a+4,pointer);put(a+12,capacity)
    events.append(['CCL_vector_resize',b]);ret(1)
   elif re.match(r'_ZN4Core6VectorIPNS_8Portable9ParameterEED[12]Ev$',name):events.append(['CCL_vector_cleanup',word(a+8)]);ret(a)
   elif name=='_ZN4Core15GetAbsoluteTimeEv' or ('SystemClock' in name and ('getTime' in name or 'getMilliseconds' in name)):u.reg_write(R1,(clock_raw>>32)&0xffffffff);events.append(['CCL_clock',clock_raw]);ret(clock_raw&0xffffffff)
   elif name=='_ZN4Core8Portable9Component6onIdleEv':events.append(['CCL_children_idle_boundary']);ret()
   elif name=='_ZN4Core13CStringBufferILi128EE6insertEiPKc':
    old=cstr(a);u.mem_write(a,(old[:b]+cstr(c)+old[b:]).encode()[:127]+b'\0');ret(a)
   elif name=='_ZN4Core20MutableCStringTraitsINS_13CStringBufferILi128EEEE12appendFormatEPKcz':
    assert cstr(b)=='%d';number=c if c<0x80000000 else c-0x100000000;u.mem_write(a,(cstr(a)+str(number)).encode()[:127]+b'\0');ret(a)
   elif name=='_ZN4Core20MutableCStringTraitsINS_13CStringBufferILi128EEEE6appendEPKci':
    extra=cstr(b);extra=extra if c==0xffffffff else extra[:c];u.mem_write(a,(cstr(a)+extra).encode()[:127]+b'\0');ret(a)
   else:raise RuntimeError('unhandled Core boundary '+name+' '+hex(pc))
   return
  imp=image.import_at.get(pc)
  if imp:
   if imp in ('__cxa_guard_acquire','__cxa_guard_release'):
    events.append([imp]);
    if imp.endswith('acquire'):ret(int(not word(a)&1))
    else:put(a,1);ret()
   elif imp=='powf':ret(bits(POW(fl(a),fl(b))))
   elif imp.startswith('_Znwj'):
    pointer=allocated;allocated+=max(256,(a+255)&~255);events.append(['actual_fixture_new',a,pointer-HEAP]);ret(pointer)
   elif imp=='__dynamic_cast':
    assert a in parameter_tags;events.append(['CCL_typed_color_cast',parameter_tags[a]]);ret(a if parameter_tags[a]==3 else 0)
   elif imp.startswith('_ZdlPv'):
    assert a in (OBJ,HEAP);freed.append(a-OBJ);u.mem_unmap(a,4096);events.append(['actual_delete_unmap',a-OBJ]);ret()
   elif imp=='strlen':ret(len(cstr(a)))
   elif imp=='strcmp':ret((cstr(a)>cstr(b))-(cstr(a)<cstr(b)))
   elif imp=='strstr':
    where=cstr(a).find(cstr(b));ret(a+where if where>=0 else 0)
   elif imp=='strncat':u.mem_write(a,(cstr(a)+cstr(b)[:c]).encode()+b'\0');ret(a)
   elif imp in ('memcpy','memmove'):u.mem_write(a,bytes(u.mem_read(b,c)));ret(a)
   elif imp=='__cxa_end_cleanup':raise RuntimeError('unexpected exception cleanup')
   else:raise RuntimeError('unhandled import '+imp)
   return
  if '_ZN8Presonus2UC15ClientComponent12paramChangedEPN4Core8Portable9ParameterEi' in syms and probe and probe.get('callback'):
   assert a==OBJ and b in parameter_tags
   events.append(['ClientComponent_callback_boundary',parameter_tags[b],c]);ret();return
  if '_ZN8Presonus13MappableMixer23sendObjectChangeMessageENS_23IMixerComponentObserver19ObjectChangeMessageE' in syms and probe and probe.get('callback'):
   assert a in (MIXER,MIXER+0x4000)
   events.append(['Mappable_message_boundary','master' if a==MIXER+0x4000 else 'local',b]);ret();return
  if any(n in syms for n in ['_ZN8Presonus13SLChannelBase16updateColorIndexEv','_ZN8Presonus13SLChannelBase20updateColorFromIndexEv']) and probe and probe.get('callback'):
   assert a==OBJ;events.append(['prior_color_index_boundary' if '_ZN8Presonus13SLChannelBase16updateColorIndexEv' in syms else 'prior_color_from_index_boundary']);ret();return
  if '_ZN8Presonus24MixerClientComponentBase15channelSelectedEPNS_13SLChannelBaseE' in syms and probe and probe.get('callback'):
   assert a==MIXER and b==OBJ;events.append(['actual_selector_dependency_boundary']);ret();return
  if '_ZN8Presonus2UC20ClientImplementation18setLastParamChangeEPv' in syms:
   assert a==MIXER+0xb8 and b in parameter_tags
   events.append(['ClientImplementation_cache_boundary',parameter_tags[b]])
   ret();return
  # All executed application constructor/destructor helpers retain exact native
  # identities and range hashes. Arithmetic runtime helpers execute unchanged.
  for n in syms:
   if n.startswith(('_ZN8Presonus','_ZNK8Presonus')) and n in image.rows:entered[n]=image.rows[n]
 def on_write(machine,access,address,size,value,user):
  if OBJ<=address<OBJ+4096:writes.append([address-OBJ,size,value&((1<<(8*size))-1)])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,on_write)
 for reg,v in ((R0,OBJ),(SP,STACK+0x8000),(LR,STOP)):u.reg_write(reg,v)
 u.emu_start(o['address'],STOP,count=100000)
 assert (u.reg_read(PC),u.reg_read(SP))==(STOP,STACK+0x8000)
 init_cases=[]
 if probe and (probe.get('init') or probe.get('linking') or probe.get('callback') or probe.get('owned_cleanup')):
  target=probe['original'];image.verify(target)
  tags=[3,5,6,7,8,9,10,11,12,13,17,20,18,21,22,224,225,226,227,228,229,230,231,232,233,234,235,236,237,238,239,300,301,302,303,255,256,271,272,411]
  # Live peer app object is initialized by its real original C2.
  for reg,v in ((R0,PEER),(SP,STACK+0x8000),(LR,STOP)):u.reg_write(reg,v)
  u.emu_start(image.symbols['_ZN8Presonus9SLChannelC2Ev'],STOP,count=100000)
  assert u.reg_read(PC)==STOP
  for owner in [OBJ,PEER]:
   for tag in tags:
    pointer=HEAP+0x2000+len(parameter_tags)*96;info=HEAP+0xc000+len(parameter_tags)*84
    paramtype=6 if tag==3 else 3;vptr=image.symbols['_ZTVN4Core8Portable10ColorParamE' if tag==3 else '_ZTVN4Core8Portable12NumericParamE']+8
    put(pointer,vptr);put(pointer+12,info);put(info,paramtype,tag);put(info+60,0)
    tag_parameters[(owner,tag)]=pointer;parameter_tags[pointer]=tag;parameter_flags[pointer]=0;parameter_values[pointer]=bits(1. if tag in (13,21) else 0.)
  # Actual Component parent/list fixture, with the receiver in slot0 (number1).
  put(OBJ+0x50,MIXER+0x1000);put(MIXER+0x1000+0x58,MIXER+0x1100,2);put(MIXER+0x1100,OBJ,PEER)
  if probe.get('init'):
   for reg,v in ((R0,OBJ),(R1,MIXER),(R2,PEER),(SP,STACK+0x8000),(LR,STOP)):u.reg_write(reg,v)
   u.emu_start(target['address'],STOP,count=100000)
   assert (u.reg_read(PC),u.reg_read(SP))==(STOP,STACK+0x8000)
   linker=word(OBJ+0x1dc)
   init_cases.append(dict(number=1,source_peer='distinct',rates=[word(OBJ+off+12) for off in [0x84,0xc4,0x104,0x144,0x184]],right_rate=word(OBJ+0x218) if probe['stereo'] else None,linker_present=bool(linker),mixer_binding=word(OBJ+0x1d8)==MIXER,color_index_tag=parameter_tags.get(word(OBJ+0x1d4)),selection_tag=parameter_tags.get(word(OBJ+0x200)) if probe.get('channel') else None,selection_public=(parameter_flags.get(word(OBJ+0x200),4)&4)==0 if probe.get('channel') else None,neighbour_selection_tag=parameter_tags.get(word(OBJ+0x204)) if probe.get('channel') else None,on_left_bits=parameter_values[tag_parameters[(OBJ,15000)]],observed_adds=[event[1] for event in events if event[0]=='CCL_observer_add'],observed_removes=[event[1] for event in events if event[0]=='CCL_observer_remove'],core_requests=list(events)))
  if probe.get('linking'):
   operation=target['mangled'];mode=probe.get('case',{})
   link_parameter=tag_parameters[(OBJ,21)]
   parameter_values[link_parameter]=bits(mode.get('link',1.))
   source=tag_parameters[(OBJ,mode.get('tag',17))]
   parameter_values[source]=bits(.75)
   if mode.get('tag',17)==21:parameter_values[link_parameter]=bits(mode.get('link',1.))
   def invoke(name,args):
    for reg,val in zip((R0,R1,R2,R3),args):u.reg_write(reg,val)
    u.reg_write(SP,STACK+0x8000);u.reg_write(LR,STOP)
    u.emu_start(image.symbols[name],STOP,count=100000)
    assert (u.reg_read(PC),u.reg_read(SP))==(STOP,STACK+0x8000)
   ctor='_ZN8Presonus13SLChannelBase11ParamLinkerC1ERNS_24MixerClientComponentBaseERS0_S4_'
   direct_ctor='ParamLinkerC' in operation
   invoke(operation if direct_ctor else ctor,[HEAP,MIXER,OBJ,PEER])
   put(OBJ+0x1dc,HEAP)
   if mode.get('missing_link'):put(HEAP+0x24,0)
   before=len(events)
   if not direct_ctor:
    if 'ParamLinkerD' in operation:invoke(operation,[HEAP])
    elif 'ParamLinker12paramChanged' in operation:invoke(operation,[HEAP,source,mode.get('msg',3)])
    elif 'ParamLinker8isLinked' in operation:invoke(operation,[HEAP])
    elif 'getSlowLinkParams' in operation:
     put(HEAP+0x1000,0,0,0,0,5);invoke(operation,[OBJ,HEAP+0x1000])
    else:invoke(operation,[OBJ])
   returned=u.reg_read(R0)
   try:u.mem_read(HEAP,4);linker_mapped=True
   except UcError:linker_mapped=False
   slow=[]
   if 'getSlowLinkParams' in operation:
    pointer=word(HEAP+0x1004);count=word(HEAP+0x1008);slow=[parameter_tags[word(pointer+i*4)] for i in range(count)]
   init_cases.append(dict(input=mode,observed_adds=[e[1] for e in events if e[0]=='CCL_observer_add'],observed_removes=[e[1] for e in events[before:] if e[0]=='CCL_observer_remove'],cache_calls=[e[1] for e in events[before:] if e[0]=='ClientImplementation_cache_boundary'],peer_value_bits=parameter_values[tag_parameters[(PEER,mode.get('tag',17))]],linked_boolean=returned if '8isLinked' in operation else None,neighbour_matches=returned==PEER if 'getLinkNeighbour' in operation else None,getter_tag=parameter_tags.get(returned) if 'getLinkParameter' in operation or 'getLinkMasterParameter' in operation else None,slow_tags=slow,linker_mapped_after=linker_mapped,events=events[before:]))
  if probe.get('callback'):
   mode=probe.get('case',{});operation=target['mangled']
   def invoke(name,args):
    for reg,val in zip((R0,R1,R2,R3),args):u.reg_write(reg,val)
    u.reg_write(SP,STACK+0x8000);u.reg_write(LR,STOP)
    u.emu_start(image.symbols[name],STOP,count=100000)
    assert (u.reg_read(PC),u.reg_read(SP))==(STOP,STACK+0x8000)
   invoke('_ZN8Presonus9SLChannel4initERNS_24MixerClientComponentBaseERNS_13SLChannelBaseE',[OBJ,MIXER,PEER])
   parameter_values[tag_parameters[(OBJ,13)]]=bits(mode.get('selection',1.))
   parameter_values[tag_parameters[(OBJ,21)]]=bits(mode.get('link',1.))
   parameter_values[tag_parameters[(PEER,13)]]=0
   if mode.get('master'):put(MIXER+0x678,MIXER+0x4000)
   if mode.get('missing_linked'):put(OBJ+0x204,0)
   before=len(events)
   if 'updateLinkedSelection' in operation:args=[OBJ,mode['notify']]
   else:args=[OBJ+4 if operation.startswith('_ZThn4_') else OBJ,tag_parameters[(OBJ,mode['tag'])],mode['msg']]
   invoke(operation,args)
   init_cases.append(dict(input=mode,events=events[before:],selection_bits=parameter_values[tag_parameters[(OBJ,13)]],linked_selection_bits=parameter_values[tag_parameters[(PEER,13)]],original_thunk_adjustment=4 if operation.startswith('_ZThn4_') else None))
  if probe.get('owned_cleanup'):
   def invoke(name,args):
    for reg,val in zip((R0,R1,R2,R3),args):u.reg_write(reg,val)
    u.reg_write(SP,STACK+0x8000);u.reg_write(LR,STOP);u.emu_start(image.symbols[name],STOP,count=100000)
    assert (u.reg_read(PC),u.reg_read(SP))==(STOP,STACK+0x8000)
   initializer='_ZN8Presonus13SLChannelBase4initERNS_24MixerClientComponentBaseERS0_' if probe.get('base') else '_ZN8Presonus9SLChannel4initERNS_24MixerClientComponentBaseERNS_13SLChannelBaseE'
   invoke(initializer,[OBJ,MIXER,PEER]);before=len(events);invoke(target['mangled'],[OBJ])
   init_cases.append(dict(owned_cleanup=True,events=events[before:],observed_removes=[e[1] for e in events[before:] if e[0]=='CCL_observer_remove']))
 meter_cases=[]
 if probe and not probe.get('init') and not probe.get('linking') and not probe.get('callback') and not probe.get('owned_cleanup'):
  target=probe['original'];image.verify(target)
  offsets=[0x84,0xc4,0x104,0x144,0x184]
  if probe['stereo']:offsets.append(0x20c)
  numeric_vptr=image.symbols['_ZTVN4Core8Portable12NumericParamE']+8
  for i,off in enumerate(offsets):
   for j in range(2):
    pointer=PARAM+(i*2+j)*64;put(pointer,numeric_vptr);parameter_values[pointer]=0;put(OBJ+off+0x30+j*4,pointer)
  def call(mangled,args):
   for reg,v in zip((R0,R1,R2,R3),(OBJ,*args)):u.reg_write(reg,v)
   u.reg_write(SP,STACK+0x8000);u.reg_write(LR,STOP)
   u.emu_start(image.symbols[mangled],STOP,count=100000)
   assert (u.reg_read(PC),u.reg_read(SP))==(STOP,STACK+0x8000)
  def reset():
   for off in offsets:
    for reg,v in ((R0,OBJ+off),(SP,STACK+0x8000),(LR,STOP)):u.reg_write(reg,v)
    u.emu_start(image.symbols['_ZN8Presonus15MeterBallistics5resetEv'],STOP,count=10000)
    assert u.reg_read(PC)==STOP
   for pointer in parameter_values:parameter_values[pointer]=0
  keys=[1818588780,1919247477,1668441444,1735550308,1819436388,0]
  if 'SLCascadeMeteringChannel' in target['mangled']:
   aggregate='_ZN8Presonus24SLCascadeMeteringChannel20updateAggregateMeterEif'
   slave_set='_ZN8Presonus24SLCascadeMeteringChannel23updateSlaveChannelLevelEf'
   operation=target['mangled']
   scenarios=[(master,key,level,slave) for master in [False,True] for key in keys for level in [-.25,.25,1.25] for slave in [-.125,.5]] if 'updateAggregateMeter' in operation else [(False,keys[0],value,.5) for value in [-.25,0.,.5,1.25]] if 'updateSlaveChannelLevel' in operation else [(False,keys[0],.25,.5)]
   for master,key,level,slave in scenarios:
    reset();put(OBJ+0x20c,0);call(slave_set,[bits(slave)]);call(aggregate,[0,bits(0.)]);put(PEER+0x214,bits(.5));put(OBJ+0x20c,PEER if master else 0)
    if 'updateAggregateMeter' in operation:call(operation,[key,bits(level)])
    elif 'updateSlaveChannelLevel' in operation:call(operation,[bits(level)])
    else:call(operation,[])
    meter_cases.append(dict(input=[int(master),key,bits(level),bits(slave)],local_bits=word(OBJ+0x210),slave_bits=word(OBJ+0x214),peer_slave_bits=word(PEER+0x214),values=[parameter_values[PARAM+i*64] for i in range(len(offsets)*2)]))
  elif 'updateStereoMeters' in target['mangled']:
   for key in keys:
    reset();call(target['mangled'],[key,bits(.25),bits(.75)])
    meter_cases.append(dict(input=[key,bits(.25),bits(.75)],values=[parameter_values[PARAM+i*64] for i in range(len(offsets)*2)]))
  elif 'updateMeter' in target['mangled']:
   for key in keys:
    for level in [-.25,0.,.25,1.25]:
     reset();call(target['mangled'],[key,bits(level)])
     meter_cases.append(dict(input=[key,bits(level)],values=[parameter_values[PARAM+i*64] for i in range(len(offsets)*2)]))
  elif '6onIdle' in target['mangled']:
   reset()
   for key in keys[:5]:call('_ZN8Presonus13SLChannelBase11updateMeterEif',[key,bits(.25)])
   for reg,v in ((R0,OBJ+0x1e0),(R1,bits(-1.)),(SP,STACK+0x8000),(LR,STOP)):u.reg_write(reg,v)
   u.emu_start(image.symbols['_ZN8Presonus10DelayTimer11beginActionEf'],STOP,count=20000);assert u.reg_read(PC)==STOP
   for milliseconds in [0,24,25,49,50,75,100,125,150,175,200,225,250]:
    clock_raw=milliseconds*1000000;call(target['mangled'],[])
    meter_cases.append(dict(input=[milliseconds],values=[parameter_values[PARAM+i*64] for i in range(len(offsets)*2)]))
  elif 'idleMeters' in target['mangled']:
   reset()
   if probe['stereo']:call('_ZN8Presonus15SLStereoChannel18updateStereoMetersEiff',[keys[0],bits(.25),bits(.75)])
   else:
    for key in keys[:5]:call('_ZN8Presonus13SLChannelBase11updateMeterEif',[key,bits(.25)])
   for frame in range(10):
    call(target['mangled'],[])
    meter_cases.append(dict(input=[frame],values=[parameter_values[PARAM+i*64] for i in range(len(offsets)*2)]))
 default_name=None;name_cases=[]
 if not probe and re.search(r'C[12]Ev$',o['mangled']):
  name_method='_ZNK8Presonus13SLChannelBase14getDefaultNameERN4Core13CStringBufferILi128EEE'
  for prefix in ['', 'pre-', 'Aux', 'Ch', 'FX', 'a'*126]:
   for number in [0,1,2,3,4]:
    if number:
     put(OBJ+0x50,PEER);put(PEER+0x58,PEER+0x100,4)
     for i in range(4):put(PEER+0x100+i*4,OBJ if i==number-1 else PEER+0x200+i*0x100)
    else:put(OBJ+0x50,0)
    u.mem_write(OBJ+0x800,prefix.encode()+b'\0')
    for reg,v in ((R0,OBJ),(R1,OBJ+0x800),(SP,STACK+0x8000),(LR,STOP)):u.reg_write(reg,v)
    u.emu_start(image.symbols[name_method],STOP,count=20000)
    assert (u.reg_read(PC),u.reg_read(SP))==(STOP,STACK+0x8000)
    value=cstr(OBJ+0x800);name_cases.append(dict(prefix=prefix,number=number,value=value))
    if not prefix and not number:default_name=value
  put(OBJ+0x50,0)
 try:after=bytes(u.mem_read(OBJ,0x260));mapped=True
 except UcError:after=b'';mapped=False
 return dict(original=o,operation_original=probe['original'] if probe else None,meter_cases=meter_cases,init_cases=init_cases,native_app_ranges=entered,events=events,writes=writes,receiver_mapped_after=mapped,receiver_after_hex=after.hex(),default_name=default_name,name_cases=name_cases,trace_count=len(trace))

def observe_lifecycle():
 images={};out=[]
 for contextpath in sorted((ROOT/PACKETBASE).glob('*/CONTEXT.json')):
  c=json.loads(contextpath.read_text())
  for row in c['originals']:
   o=row['original']
   if not re.search(r'[CD][012]Ev$',o['mangled']):continue
   if 'ParamLinker' in o['mangled']:continue
   if o['elf'] not in images:images[o['elf']]=Image(o)
   image=images[o['elf']];out.append(run_lifecycle(image,o))
 return dict(kind='Exact native application lifecycle execution; CCL Component ctor/destructor and libm/guard/delete boundaries explicit. Original complete fields and ABI unresolved.',originals=out)
def observe_metering():
 images={};out=[]
 for contextpath in sorted((ROOT/PACKETBASE).glob('*/CONTEXT.json')):
  c=json.loads(contextpath.read_text())
  for row in c['originals']:
   o=row['original'];name=o['mangled']
   if not any(key in name for key in ['13SLChannelBase11updateMeter','13SLChannelBase10idleMeters','15SLStereoChannel18updateStereoMeters','15SLStereoChannel10idleMeters','13SLChannelBase6onIdle','24SLCascadeMeteringChannel20updateAggregateMeter','24SLCascadeMeteringChannel23updateSlaveChannelLevel','24SLCascadeMeteringChannel17slaveMixerChanged']):continue
   if o['elf'] not in images:images[o['elf']]=Image(o)
   image=images[o['elf']];stereo='SLStereoChannel' in name;ctor='_ZN8Presonus25SLRackStereoMainComponentC2Ev' if stereo else ('_ZN8Presonus24SLCascadeMeteringChannelC2Ev' if 'SLCascadeMeteringChannel' in name else '_ZN8Presonus13SLChannelBaseC2Ev');r=image.rows[ctor]
   constructor=dict(o,mangled=ctor,address=r['address'],size=r['size'],section=r['section'],file_offset=r['file_offset'],range_sha256=r['sha256'])
   out.append(run_lifecycle(image,constructor,dict(original=o,stereo=stereo)))
 return dict(kind='Real original selected meter routing/idle methods, real native MeterMaid/GR/Ballistics providers and original floating helpers; exact CCL NumericParam setValue boundaries captured.',originals=out)
def observe_initialization():
 images={};out=[]
 for contextpath in sorted((ROOT/PACKETBASE).glob('*/CONTEXT.json')):
  c=json.loads(contextpath.read_text())
  for row in c['originals']:
   o=row['original'];name=o['mangled']
   if '4initERNS_24MixerClientComponentBaseE' not in name:continue
   if o['elf'] not in images:images[o['elf']]=Image(o)
   image=images[o['elf']];stereo='SLStereoChannel' in name
   ctor='_ZN8Presonus25SLRackStereoMainComponentC2Ev' if stereo else ('_ZN8Presonus13SLChannelBaseC2Ev' if '13SLChannelBase4init' in name else '_ZN8Presonus9SLChannelC2Ev')
   r=image.rows[ctor];constructor=dict(o,mangled=ctor,address=r['address'],size=r['size'],section=r['section'],file_offset=r['file_offset'],range_sha256=r['sha256'])
   out.append(run_lifecycle(image,constructor,dict(original=o,stereo=stereo,init=True,channel='13SLChannelBase4init' not in name)))
 return dict(kind='Original app init chains, three genuine table metadata rows, real app ParamLinker and DelayTimer; CCL parameter/vector/controller/clock APIs captured as explicit provider boundaries.',originals=out)
def observe_linking():
 images={};out=[]
 for contextpath in sorted((ROOT/PACKETBASE).glob('*/CONTEXT.json')):
  c=json.loads(contextpath.read_text())
  for row in c['originals']:
   o=row['original'];name=o['mangled']
   if not ('ParamLinker' in name or 'getLinkNeighbour' in name or '13SLChannelBase8isLinked' in name or '9SLChannel16getLinkParameter' in name or '9SLChannel22getLinkMasterParameter' in name or '9SLChannel17getSlowLinkParams' in name):continue
   if o['elf'] not in images:images[o['elf']]=Image(o)
   image=images[o['elf']];ctor='_ZN8Presonus9SLChannelC2Ev';r=image.rows[ctor]
   constructor=dict(o,mangled=ctor,address=r['address'],size=r['size'],section=r['section'],file_offset=r['file_offset'],range_sha256=r['sha256'])
   if 'paramChanged' in name:cases=[dict(msg=msg,link=link,tag=tag) for msg,link,tag in [(3,1.,17),(3,0.,17),(2,1.,17),(3,1.,3),(0,1.,17),(1,1.,17),(4,1.,17),(5,1.,17)]]+[dict(msg=3,link=1.,tag=17,editing=False)]
   elif '8isLinked' in name:cases=[dict(link=v) for v in [-.25,0.,.75]]+[dict(missing_link=True)]
   else:cases=[{}]
   for case in cases:out.append(run_lifecycle(image,constructor,dict(original=o,stereo=False,linking=True,case=case)))
 return dict(kind='Exact original ParamLinker variants/getters/forwarders with actual native class bodies and float helpers; genuine CCL vector/parameter/observer operations explicit provider boundaries.',originals=out)
def observe_callbacks():
 images={};out=[]
 for contextpath in sorted((ROOT/PACKETBASE).glob('*/CONTEXT.json')):
  c=json.loads(contextpath.read_text())
  for row in c['originals']:
   o=row['original'];name=o['mangled']
   if not ('13SLChannelBase12paramChanged' in name or '9SLChannel12paramChanged' in name or '13SLChannelBase21updateLinkedSelection' in name or (name.startswith('_ZThn4_') and '15ClientComponent12paramChanged' in name)):continue
   if o['elf'] not in images:images[o['elf']]=Image(o)
   image=images[o['elf']];ctor='_ZN8Presonus9SLChannelC2Ev';r=image.rows[ctor];constructor=dict(o,mangled=ctor,address=r['address'],size=r['size'],section=r['section'],file_offset=r['file_offset'],range_sha256=r['sha256'])
   if name.startswith('_ZThn4_'):cases=[dict(tag=13,msg=2)]
   elif 'updateLinkedSelection' in name:cases=[dict(notify=notify,link=link,missing_linked=missing) for notify in [0,1] for link in [0.,1.] for missing in [False,True]]
   else:
    pairs=[(13,2),(21,2),(22,2),(17,2),(21,3),(22,3),(3,3),(15002,3),(17,3),(13,0),(13,4),(411,3),(255,2),(256,2),(271,2),(272,2)]
    cases=[dict(tag=tag,msg=msg,master=master) for tag,msg in pairs for master in ([False,True] if tag in [3,256] else [False])]+[dict(tag=21,msg=3,selection=0.)]
   for case in cases:out.append(run_lifecycle(image,constructor,dict(original=o,stereo=False,callback=True,case=case)))
 return dict(kind='Exact channel callback/updateLinkedSelection and sub4 thunk execution with real app getter/linker/float bodies; prior Client/color/Mappable/selector bodies are explicit dependency boundaries. Source/CCL full integrations are replayed separately.',originals=out)
def observe_owned_cleanup():
 images={};out=[]
 for contextpath in sorted((ROOT/PACKETBASE).glob('*/CONTEXT.json')):
  for row in json.loads(contextpath.read_text())['originals']:
   o=row['original'];name=o['mangled']
   if not re.match(r'_ZN8Presonus(?:13SLChannelBase|9SLChannel)D[012]Ev$',name):continue
   if o['elf'] not in images:images[o['elf']]=Image(o)
   image=images[o['elf']];base='13SLChannelBase' in name;ctor='_ZN8Presonus13SLChannelBaseC2Ev' if base else '_ZN8Presonus9SLChannelC2Ev';r=image.rows[ctor];constructor=dict(o,mangled=ctor,address=r['address'],size=r['size'],section=r['section'],file_offset=r['file_offset'],range_sha256=r['sha256'])
   out.append(run_lifecycle(image,constructor,dict(original=o,stereo=False,owned_cleanup=True,base=base)))
 return dict(kind='Exact original base/channel destructor variants after genuine native initialization/owned ParamLinker allocation; actual observer cleanup/vector boundaries and real receiver/linker unmapping at original delete calls.',originals=out)
if __name__=='__main__':
 import sys
 mode=sys.argv[1] if len(sys.argv)>1 else 'lifecycle'
 print(json.dumps({'metering':observe_metering,'init':observe_initialization,'linking':observe_linking,'callbacks':observe_callbacks,'owned':observe_owned_cleanup,'lifecycle':observe_lifecycle}[mode](),indent=2))
