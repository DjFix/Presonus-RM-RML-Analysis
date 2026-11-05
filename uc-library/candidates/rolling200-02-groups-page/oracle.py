"""Execute only four assigned ARM bodies; all other routines are bounded captures.
Synthetic ARM state is explicit, never asserted to match portable C++ layout.
No Core binary implementation is executed or reconstructed.
"""
import datetime,hashlib,json,struct,shlex,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
BASE=Path('uc-library/candidates/rolling200-02-groups-page')
OUT=Path('evidence/recovery/2026-11-05/rolling200-02/groups-page');OUT.mkdir(parents=True,exist_ok=True)
ELF=Path('rootfs/CS18_v13840/home/root/surface');SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
TARGETS=[(0x92f18,208,'4883eb17c8652de098b2d38027f5d00fc5b9916e7a470dbb04ef5779a22c16e8'),(0x93430,584,'a7ce3f6703d335c13a5b4cd2c69ec2b5b221753af8c3e1a186b9889cfaad055e'),(0x92fe8,432,'8be167ce5b327f286ea1c6cfe33ffe9cc8914c66d4dff469a38a5dd8e4383e4e'),(0x93198,656,'73fdc6008f2e1c77e8b719cb434872b61229ed3b121f2ea259bd6bec3aca90f8')]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def number(v):return struct.unpack('<f',struct.pack('<I',v))[0]
def signed(v):return (v+2**31)%2**32-2**31
raw=ELF.read_bytes();assert sha(ELF)==SHA
with ELF.open('rb') as f:
 e=ELFFile(f);sec=e.get_section(12);assert sec.name=='.text'
 segments=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
 ranges=[]
 for address,size,digest in TARGETS:
  offset=address-sec['sh_addr']+sec['sh_offset'];assert hashlib.sha256(raw[offset:offset+size]).hexdigest()==digest
  ranges.append(dict(address=address,size=size,sha256=digest,file_offset=offset,section='.text',section_index=12))
def run(c):
 op,tag,msg,value,own,name_id,selection,offset,match,automatic,mode,source_mode,visible,mapping,member=c
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x280000)
 for address,data in segments:u.mem_write(address,data)
 u.mem_map(0x300000,0x400000);u.mem_map(0x800000,0x10000)
 obj=0x300000;stop=0x810000;arena=0x310000;trace=[];writes=[];calls=[];params={};groups={};selection_at_doselect=-999
 def alloc(size=0x100):
  nonlocal arena
  p=arena;arena+=(size+15)&~15;return p
 def put(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def get(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def string(a):
  data=bytearray()
  while a and (b:=bytes(u.mem_read(a,1)))!=b'\0':data.extend(b);a+=1
  return data.decode('ascii')
 def text(a,s):u.mem_write(a,s.encode()+b'\0')
 vtable=alloc(0x100);mixer=alloc();mv=alloc();mp=alloc();mpv=alloc();put(mixer+0x30,mv);put(mv+0x14,0x600000);put(mp,mpv);put(mpv+0xc,0x600010)
 for slot,pc in [(0x44,0x600020),(0x58,0x600030),(0x70,0x600040),(0x74,0x600050)]:put(vtable+slot,pc)
 def param(tag,kind=3,name='other',value=0,controller=0,s=''):
  p=alloc();info=alloc();put(p,vtable);put(p+0xc,info);put(info,kind);put(info+4,tag);text(info+8,name);params[p]=dict(tag=tag,kind=kind,value=value,controller=controller,text=s);return p
 def group(name='occupied',missing=False,missing603=False):
  g=alloc();ps=[]
  if not missing:ps.append(param(600,4,'name',s=name,controller=g+4))
  if not missing603:ps.append(param(603,name='selected',value=bits(1),controller=g+4))
  ps.append(param(646,name='member',value=bits(.25),controller=g+4))
  groups[g]=ps;return g
 first=[];second=[]
 if mode not in [0,1]:
  for i in range(12):first.append(group('' if (mode==3 and i==1) or (mode==5 and i==0) else 'occupied',mode==4 and i==0,mode==8 and i==0))
  if mode!=7:second=[group(missing603=mode==8 and i==0) for i in range(3)]
 source=alloc();groups[source]=[]
 names=['copy','~copy','','1234567890123456789012345678901','~1234567890123456789012345678901','123456789012345678901234567890123456789']
 if source_mode:
  if source_mode!=7:groups[source].append(param(600,4,'name',controller=source+4,s=names[(source_mode-1)%6]))
  groups[source].extend([param(603,name='selected',value=bits(.5),controller=source+4),param(646,name='member',value=value,controller=source+4)])
  if source_mode==8:groups[source].append(param(9999,name='extra',value=bits(.8),controller=source+4))
 containers={}
 for name,children in [('filtergroup',first),('autofiltergroup',second)]:
  if mode==0 or (name=='autofiltergroup' and mode==7):containers[name]=0;continue
  container=alloc();array=alloc(4*max(1,len(children)));put(container+0x58,array);put(container+0x5c,len(children))
  for i,g in enumerate(children):put(array+4*i,g)
  containers[name]=container
 all_groups=first+second
 selected=all_groups[match] if match>=0 else 0
 names_event=['other','input_bank','input_bank_1','xinput_bank','show_auto']
 p=param(tag,name=names_event[name_id],value=value,controller=obj+4 if own else selected+4 if selected else 0)
 mode_param=param(6,name='mode',value=bits(1));edit_param=param(1009,name='editmode',value=bits(1))
 put(obj+0xcc,mixer);put(obj+0xd0,mp if mapping else 0);put(obj+0xd4,offset);put(obj+0xd8,selection);put(obj+0x134,selected)
 # updateGroups was run once in the portable setup; views include only valid names.
 lists=[]
 for children in [first,second if automatic else []]:
  valid=[g for g in children if any(params[x]['tag']==600 and params[x]['text'] for x in groups[g])];lists.append(valid)
 if mode==10:
  lists[0][1]=lists[0][0];lists[1][0]=lists[0][0]
 for index,items in enumerate(lists):
  a=alloc(4*max(1,len(items)));put(obj+0x108+index*0x14,a);put(obj+0x10c+index*0x14,len(items))
  for i,g in enumerate(items):put(a+i*4,g)
 a=alloc();put(a,p);put(obj+0xe0,a);put(obj+0xe4,member)
 root,root_size,_=TARGETS[op-1]
 boundary={0x92a14:1,0x92e94:2,0x924f4:3,0x92c80:4,0x92754:5,0x92ee4:6,0x92854:7,0x91e14:8,0x91eb8:9,0x92f18:10,0x92fe8:11,0x93198:12}
 def ret(result=None):
  if result is not None:u.reg_write(UC_ARM_REG_R0,result&0xffffffff)
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def hook(uc,pc,size,_):
  nonlocal selection_at_doselect
  if pc==stop:uc.emu_stop();return
  r=[uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
  if pc in boundary and pc!=root:
   code=boundary[pc];trace.append(code);calls.append(dict(address=pc,args=r))
   if code==3:selection_at_doselect=signed(get(obj+0xd8))
   if code==9:ret(int(selected in second));return
   ret();return
  if root<=pc<root+root_size:return
  calls.append(dict(address=pc,args=r))
  if pc==0x600000:ret(containers.get(string(r[1]),0))
  elif pc==0x600010:ret(mode_param if mapping==1 and r[1]==6 else 0)
  elif pc==0x600020:ret(params[r[0]]['value'])
  elif pc==0x600030:params[r[0]]['value']=r[1];ret()
  elif pc==0x600040:text(r[1],params[r[0]]['text'][:max(0,r[2]-1)]);ret()
  elif pc==0x600050:params[r[0]]['text']=string(r[1]);ret()
  elif pc==0x11acf0:
   ps=groups.get(r[0],[]);ret(edit_param if r[0]==obj and r[1]==1009 else next((x for x in ps if params[x]['tag']==signed(r[1])),0))
  elif pc==0x11a6c8:ret(len(groups[r[0]]))
  elif pc==0x11a6dc:ret(groups[r[0]][r[1]] if r[1]<len(groups[r[0]]) else 0)
  elif pc==0x11e1d0:ret(params[r[0]]['controller'])
  elif pc==0x11c87c:ret() # actual CCL base side effect is outside native port layout
  elif pc==0x681d4:ret(visible)
  elif pc==0xae58:ret(selected) # RTTI observation: configured controller Component or null
  elif pc==0x24268:text(r[0],string(r[1])[:31] if r[1] else '');ret(r[0])
  elif pc==0xb02c:ret(len(string(r[0])))
  elif pc==0xb260:
   s=string(r[0]);i=s.find(chr(r[1]));ret(r[0]+i if i>=0 else 0)
  elif pc==0xae7c:
   i=string(r[0]).find(string(r[1]));ret(r[0]+i if i>=0 else 0)
  elif pc==0xb0f8:ret(0 if string(r[0])==string(r[1]) else 1)
  elif pc==0xaf84:text(r[0],string(r[0])+string(r[1])[:r[2]]);ret(r[0])
  elif pc==0xacb4:uc.mem_write(r[0],bytes(uc.mem_read(r[1],r[2])));ret(r[0])
  elif pc==0x1877e0:ret(int(number(r[0])>number(r[1])))
  else:raise RuntimeError('Unexpected PC '+hex(pc))
 def write(uc,access,a,size,v,_):
  if obj<=a<obj+0x200:writes.append([a-obj,size,v])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_SP,0x808000);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R0,obj)
 arg=selected if op==1 else source if op==4 and source_mode else 0 if op==4 else p
 if op==1 and match==-2:arg=source
 u.reg_write(UC_ARM_REG_R1,arg);u.reg_write(UC_ARM_REG_R2,msg)
 u.emu_start(root,stop,count=10000);assert u.reg_read(UC_ARM_REG_PC)==stop
 out=[str(len(trace))]+list(map(str,trace))
 if op==1:out.append(str(selection_at_doselect))
 if op==2 and own:out.append(str(number(params[edit_param]['value'])))
 if op==3:
  out.extend(str(number(params[next(x for x in groups[g] if params[x]['tag']==603)]['value'])) if any(params[x]['tag']==603 for x in groups[g]) else '-99' for g in all_groups)
  if mapping:out.append(str(number(params[mode_param]['value'])) if mapping==1 else '-99')
 if op==4:
  for g in first:
   ps=groups[g];name=next((params[x]['text'] for x in ps if params[x]['tag']==600),'');out.append(json.dumps(name[:31]));out.extend(str(params[next(x for x in ps if params[x]['tag']==t)]['value']) for t in [603,646])
 return dict(input=c,output=' '.join(out),object_writes=writes,external_calls=calls)
def case(op,**kw):
 defaults=dict(tag=999,msg=3,value=bits(1),own=0,name_id=0,selection=-1,offset=0,match=-1,automatic=1,mode=2,source_mode=0,visible=0,mapping=0,member=0);defaults.update(kw);return [op,*map(int, defaults.values())]
cases=[]
for mode in [0,1,2,3,5,7]:
 for automatic in [0,1]:
  for match in [-2,-1]+([] if mode in [0,1] else [0,1,8,9,11]+([12,14] if mode!=7 else [])):
   for offset in [0,2,10]:cases.append(case(1,mode=mode,automatic=automatic,match=match,offset=offset))
for match in [0,1,12,14]:
 for offset in [0,2,10]:cases.append(case(1,mode=10,match=match,offset=offset))
for own in [0,1]:
 for msg in [0,2,3,4]:
  for tag in [600,603,645,646,685,686,999,1000,1001,1002,1003,1004,1005]:
   for value in [bits(0),bits(1),bits(-1),0x7fc00000]:cases.append(case(2,own=own,msg=msg,tag=tag,value=value,match=12))
for name in range(5):
 for value in [bits(0),bits(1),bits(-1),0x7fc00000]:
  for selection in [-1,0]:cases.append(case(2,own=1,msg=3,name_id=name,value=value,selection=selection))
for tag in [999,1002]:
 for value in [bits(0),bits(1),bits(-1),0x7fc00000]:cases.append(case(2,own=1,msg=2,tag=tag,value=value,member=1))
for msg in [2,3,4]:
 for tag in [600,603,645,646,685,686]:
  for value in [bits(0),bits(1),bits(-1),0x7fc00000]:
   for mode in [0,1,2,7,8]:
    for mapping in [0,1,2]:cases.append(case(3,msg=msg,tag=tag,value=value,mode=mode,mapping=mapping,visible=tag==600,match=-1))
for match in [0,12,-1]:cases.append(case(3,tag=603,match=match,mapping=1))
for mode in [0,1,2,3,5,7]:
 for source in range(9):
  for value in [bits(.75),0x7fc00000]:cases.append(case(4,mode=mode,source_mode=source,value=value))
records=[run(c) for c in cases]
proof=dict(elf_sha256=SHA,elf_path=str(ELF),ranges=ranges,unicorn_version=unicorn.__version__,producer_sha256=sha(__file__),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cases=records,assumptions=['Initialized synthetic ARM object and pointer lists; no layout equivalence to portable C++ asserted.','All outside-body functions are scripted bounded capture boundaries; no Core binary body executes.','Root-level method entry traces compared; portable existing providers actually execute, their nested calls are excluded from trace comparison.','Original parameter slot0x44 values and setters use captured binary32 values; string boundaries use bounded ASCII.','Every traversed group requires tag600: separately preserved exact original helper fault and portable failure chain agree on the negative input; no safe full-tree claim.'])
(OUT/'native.json').write_text(json.dumps(proof,indent=2)+'\n');(OUT/'inputs.txt').write_text(''.join(' '.join(map(str,c))+'\n' for c in cases));print('native cases',len(records))
