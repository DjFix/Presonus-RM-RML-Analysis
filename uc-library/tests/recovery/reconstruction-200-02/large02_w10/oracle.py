"""Execute only assigned original ARM application ranges; external calls are traced boundaries."""
import hashlib,json,struct,sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[12] if False else Path.cwd()
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
with ELF.open('rb') as f:
 e=ELFFile(f);segments=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD'];symbol_rows={s.name:dict(s.entry) for s in e.get_section_by_name('.symtab').iter_symbols()};sections=[dict(s.header) for s in e.iter_sections()];symbols={s.name:s['st_value'] for s in e.get_section_by_name('.symtab').iter_symbols()}
b=ROOT/'temp/recovery-work/reconstruction-200-02/isolated-batch01/packets'
import re
specs=[]
for n in range(1,24):
 text=(b/f'large02_w10_{n:02}'/'ELF_CONTEXT.md').read_text()
 m=re.search(r'original `([^`]+)`; address `0x([0-9a-f]+)`; size (\d+); section ([^;]+); SHA256 `([^`]+)`',text)
 offset=int(re.search(r'file offset `0x([0-9a-f]+)`',text).group(1),16)
 name,address,size,section,digest=m.groups();address=int(address,16);size=int(size)
 assert hashlib.sha256(raw[offset:offset+size]).hexdigest()==digest
 row=symbol_rows[name];assert row['st_value']==address and row['st_size']==size
 section_header=sections[row['st_shndx']];assert address+size<=section_header['sh_addr']+section_header['sh_size'];assert section_header['sh_offset']+address-section_header['sh_addr']==offset
 specs.append(dict(n=n,mangled=name,address=address,size=size,offset=offset,sha256=digest,section=section))

helper_name='_ZN8Presonus7Surface19PageHeaderComponent16updateFocusParamEPN4Core8Portable9ParameterE'
helper_row=symbol_rows[helper_name];assert helper_row['st_value']==0x908e8 and helper_row['st_size']==344
helper_section=sections[helper_row['st_shndx']];helper_offset=helper_section['sh_offset']+0x908e8-helper_section['sh_addr'];assert helper_offset==0x888e8
helper_digest=hashlib.sha256(raw[helper_offset:helper_offset+344]).hexdigest();assert helper_digest=='9c7d4f6368dfe24ed30af80ff25e47d441e02471f0623700424b95f4dd40c4db'
helper_dependency=dict(mangled=helper_name,address=0x908e8,size=344,offset=helper_offset,sha256=helper_digest,section='.text',readiness_claim=False)


typed_data_dependencies=[]
for name,address,size in [('_ZTIN4Core8Portable9ComponentE',0x204e28,32),('_ZTIN8Presonus7Surface19MainScreenComponentE',0x1a0434,12)]:
 row=symbol_rows[name];assert row['st_value']==address and row['st_size']==size
 section=sections[row['st_shndx']];offset=section['sh_offset']+address-section['sh_addr']
 typed_data_dependencies.append(dict(mangled=name,address=address,size=size,section_index=row['st_shndx'],offset=offset,sha256=hashlib.sha256(raw[offset:offset+size]).hexdigest(),interpretation='Identity/range binding only; no layout or provider behavior claim'))

lookup_name='_ZN8Presonus22AssignmentHandlerTable17getParamFocusInfoERNS_22MixerAssignmentHandler9FocusInfoEPN4Core8Portable9ParameterE'
lookup_row=symbol_rows[lookup_name];assert lookup_row['st_value']==0x75d34 and lookup_row['st_size']==140
lookup_section=sections[lookup_row['st_shndx']];lookup_offset=lookup_section['sh_offset']+0x75d34-lookup_section['sh_addr'];assert lookup_offset==0x6dd34
lookup_digest=hashlib.sha256(raw[lookup_offset:lookup_offset+140]).hexdigest();assert lookup_digest=='dd0f24298f54bae2a50e6e0e5669bd7677c10bfe0b79afcebdee5db17c76aa2e'
lookup_dependency=dict(mangled=lookup_name,address=0x75d34,size=140,offset=lookup_offset,sha256=lookup_digest,section='.text',readiness_claim=False)
def bits(f):return struct.unpack('<I',struct.pack('<f',f))[0]
def execute(n,arg,enabled=0):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x400000)
 for address,data in segments:u.mem_write(address,data)
 u.mem_map(0x1000000,0x20000);u.mem_map(0x2000000,0x20000)
 obj=0x1000000;vt=obj+0x1000;port=obj+0x2000;param=obj+0x3000;msg=obj+0x4000
 wr=lambda a,v:u.mem_write(a,struct.pack('<I',v&0xffffffff))
 rd=lambda a:struct.unpack('<I',u.mem_read(a,4))[0]
 wr(obj,vt);wr(obj+0x1cc,port);wr(port,vt+0x100);wr(param,vt+0x200)
 for slot,target in [(0x80,0x2000100),(0x68,0x2000200),(0x50,0x2000300)]:wr(vt+slot,target)
 wr(vt+0x104,0x2000400);wr(vt+0x258,0x2000500)
 u.mem_write(obj+0x158,bytes([0,0,9,0,enabled]));u.mem_write(obj+0x160,b'\x77'*88);u.mem_write(obj+0x1b8,b'\x77'*19)
 u.mem_write(msg,bytes([arg&255,0,0,0]))
 state={'params':{str(t):bits(7.) for t in [900,901,903,1000,2000,2001]},'packets':[],'flags':[0,0,0,9,enabled],'timers':[0,0,0],'values':[0x77777777]*22,'switches':[119]*19,'result':0,'sets':[],'mode':[],'durations':[0,0,0],'faderCalls':[],'brightnessLifecycle':[],'forwarded':[],'focus':{'alias':900 if n in [6,10,17] and arg&8 else -1,'text':'initial'},'handlerTrace':[]}
 allocation=[obj+0x6000];group_info=[]
 chosen=[1000];timer_offsets=[176,208,240]
 extern={a:name for name,a in symbols.items() if a}
 own={s['address']:s['n'] for s in specs}
 active={n}
 if n in [6,17]:active.add(10)
 if n==23:active|={4,21}
 if n==20:active.add(9)
 if n==2:active|={4,5,7,11,12,18,19,21,23}
 ranges=[(s['address'],s['address']+s['size']) for s in specs if s['n'] in active]
 if n in [6,10,17]:ranges.extend([(0x908e8,0x908e8+344),(0x75d34,0x75d34+140)])
 def hook(u,pc,size,data):
  if any(lo<=pc<hi for lo,hi in ranges):return
  regs=[u.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];r0,r1,r2,r3=regs
  ret=0;name=extern.get(pc,'')
  if pc==0x2000100:state['packets'].append(list(u.mem_read(r1,4)))
  elif pc==0x2000200:state['mode'].append(r1)
  elif pc==0x2000300:ret=0
  elif pc==0x2000400:state['packets'].append(list(u.mem_read(r1,4)))
  elif pc==0x2000500:
   state['params'][str(chosen[0])]=r1;state['sets'].append([chosen[0],r1,r2])
  elif 'ParamList5byTag' in name:chosen[0]=r1;ret=param if r1!=999 else 0
  elif 'ParamList4find' in name:ret=param if arg else 0
  elif name.startswith('__floatunsisf'):ret=bits(float(r0))
  elif 'DelayTimer11beginAction' in name:
   ix=timer_offsets.index(r0-obj);state['timers'][ix]=1;state['durations'][ix]=int(struct.unpack('<f',struct.pack('<I',r1))[0]*1000)
  elif 'DelayTimer9endAction' in name:state['timers'][timer_offsets.index(r0-obj)]=0
  elif 'DebugPrintf' in name:pass
  elif name.startswith('_Znwj'):
   ret=allocation[0];allocation[0]+=0x1000;wr(ret,vt+0x400);wr(vt+0x408,0x2000700)
  elif 'ControlGroupC' in name:group_info.append({'id':r1,'tags':[]})
  elif 'SwitchControlC' in name:group_info[0]['tags'].append(r1)
  elif 'Control5setIO' in name:pass
  elif pc==0x2000700:pass
  elif 'OutputPinC' in name:state['brightnessLifecycle'].append([0,r1])
  elif 'OutputPin3set' in name:
   state['result']=int(r1!=0);state['brightnessLifecycle'].append([1,r1 if r1<0x80000000 else r1-0x100000000])
  elif 'OutputPinD' in name:state['brightnessLifecycle'].append([2,0])
  elif 'Control12getParameter' in name:ret=param if arg&4 else 0
  elif pc==0x2000900:
   ret=param if r0==param else obj+0x8000 if r0==obj+0x8000 else {900:param,901:obj+0x8000,-1:0}[state['focus']['alias']]
  elif pc in [0x2000b00,0x2000b10]:
   assert r1==0x4d784173
   ret=r0 if pc==0x2000b10 else 0
  elif pc in [0x2000c00,0x2000c10,0x2000c20]:
   ordinal=(pc-0x2000c00)//16;state['handlerTrace'].append(ordinal);assert r2==param
   if ordinal==0:
    u.mem_write(r1+32,b'ignored\0')
    if arg&16:wr(r1+64,obj+0x8000)
    ret=0
   elif ordinal==1:
    u.mem_write(r1+32,b'focus\0');ret=0 if arg&32 else 1
   else:
    assert arg&32,'dispatcher failed to stop after successful handler';ret=0
  elif 'AliasParam11setOriginal' in name:
   state['focus']['alias']={param:900,obj+0x8000:901,0:-1}[r1]
  elif pc==0x2000a00:
   assert r2==0
   state['focus']['text']=bytes(u.mem_read(r1,32)).split(b'\0')[0].decode('ascii')
  elif pc==0x2000800:
   assert bytes(u.mem_read(r1,11))==b'mainscreen\0';ret=msg if enabled else 0
  elif '__dynamic_cast' in name:
   assert r1==0x204e28 and r2==0x1a0434 and r3==0,(hex(r1),hex(r2),r3)
   ret=msg if arg==1 else 0
  elif 'bumpFaderSpeed' in name or 'bumpFaderTouchSensitivity' in name:
   assert r0==obj+0x5000;state['forwarded'].append([0 if 'bumpFaderSpeed' in name else 1,r1]);ret=7
  elif 'adjustLcdBrightness' in name:state['result']=int(r1!=0)
  elif 'handleTouchscreen' in name:state['result']=1
  elif 'invokeFaderCalibration' in name:
   state['faderCalls'].append(r1)
  elif name.startswith('__aeabi_f2iz'):ret=int(struct.unpack('<f',struct.pack('<I',r0))[0])&0xffffffff
  elif pc==0x2000600:ret=bits(float(arg))
  else:raise RuntimeError(f'unmodeled boundary {pc:x} {name} method {n}')
  u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook)
 sp=0x2010000;u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,0x201f000)
 u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,arg&0xffffffff);u.reg_write(UC_ARM_REG_R2,enabled)
 if n==1:u.reg_write(UC_ARM_REG_R1,enabled);u.reg_write(UC_ARM_REG_R2,arg)
 if n==14:u.reg_write(UC_ARM_REG_R1,msg)
 if n==15:u.reg_write(UC_ARM_REG_R1,msg)
 if n in [3,13]:wr(obj+0x114,obj+0x5000 if enabled else 0)
 if n in [6,10,17]:
  wr(obj+0x12c,obj+0x5000 if arg&2 else 0)
  wr(obj+0x5000+0xc8,0 if arg&64 else obj+0x6000);wr(obj+0x5000+0xcc,0 if arg&128 else obj+0x7000)
  wr(param,vt+0x200);wr(vt+0x20c,0x2000900)
  wr(obj+0x6000,vt+0x300);wr(vt+0x30c,0x2000900)
  wr(obj+0x7000,vt+0x400);wr(vt+0x474,0x2000a00)
  wr(obj+0x8000,vt+0x200);wr(0x2697cc,1)
  wr(0x2697d0,obj+0x9000);wr(0x2697d4,0 if arg&256 else 2 if arg&512 else 5)
  for index in range(5):wr(obj+0x9000+index*4,0 if index==0 else obj+0x9000+index*0x1000)
  for index in range(1,5):
   handler=obj+0x9000+index*0x1000;table=obj+0xd000+index*0x1000
   wr(handler,table);wr(table,0x2000b00 if index==1 else 0x2000b10)
   wr(table+0x3c,0x2000c00+(index-2)*16)
  control=msg if arg&1 else 0
  if n==10:u.reg_write(UC_ARM_REG_R1,control)
  if n==6:wr(sp,control)
  if n==17:wr(sp,enabled);wr(sp+4,control)
 if n==16:wr(vt+0x14,0x2000800)
 if n==8:
  wr(obj+0x18,obj+0x5000);wr(obj+0x1c,0)
  for i in range(max(0,arg)):wr(msg+i*84+4,10+i)
  u.reg_write(UC_ARM_REG_R1,42);u.reg_write(UC_ARM_REG_R2,msg);u.reg_write(UC_ARM_REG_R3,arg&0xffffffff)
 if n==20:
  wr(obj+0x114,obj+0x5000);wr(param,vt+0x300);wr(vt+0x344,0x2000600);u.reg_write(UC_ARM_REG_R1,param)
 u.emu_start(specs[n-1]['address'],0x201f000,count=20000)
 assert u.reg_read(UC_ARM_REG_PC)==0x201f000,'native instruction budget exhausted'
 state['flags']=[u.mem_read(obj+off,1)[0] for off in [0x158,0x159,0x15b,0x15a,0x15c]]
 state['values']=list(struct.unpack('<22I',u.mem_read(obj+0x160,88)));state['switches']=list(u.mem_read(obj+0x1b8,19))
 if n in [3,13]:state['result']=u.reg_read(UC_ARM_REG_R0)
 if n in [15,16,22]:state['result']=int(u.reg_read(UC_ARM_REG_R0)!=0)
 if n==8:state['group']=group_info[0]
 # 48v initializes only prefix3; its fourth stack byte is outside comparison.
 if n==11 or (n==2 and arg==110):state['packets']=[p[:3] for p in state['packets']]
 return state
cases=[]
for n in [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]:
 args=([0,1,32767,65535] if n==1 else list(range(98,113)) if n==2 else [0,1,127,255] if n==4 else [99,100,101,104,105] if n==7 else [0,1] if n in [5,11,12,18,19,21,23,15] else [83,84] if n==14 else list(range(64))+[71,135,263,519] if n in [6,10,17] else list(range(6)) if n==16 else [-1,0,1,3] if n==8 else [-1,0,1,123] if n==9 else [900,999] if n==22 else [0,3,7])
 for arg in args:
  for enabled in ([0,1] if n in [1,2,3,7,13,14,16,17] else [0]):
   cases.append(dict(n=n,arg=arg,enabled=enabled,expected=execute(n,arg,enabled)))
Path(sys.argv[1]).write_text(json.dumps(dict(typed_data_dependencies=typed_data_dependencies,helper_dependencies=[helper_dependency,lookup_dependency],covered_targets=sorted(set(c['n'] for c in cases)),method='original ARM Unicorn target execution; external calls stubbed, no Core body execution',ranges=specs,cases=cases),indent=2)+'\n')
print(len(cases),'independent native observations')
