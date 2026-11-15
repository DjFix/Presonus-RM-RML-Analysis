"""Execute exact original app bodies; typed source-provider boundary observations only."""
import json,hashlib,struct,subprocess,io,itertools
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
B=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114')
PREP=B/'prepared-remaining14-phaseb-proposed01';SNAP=PREP/'snapshot'
ELF_SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
TASKS={'fader':'frontpanel_fader','led':'frontpanel_meter_led','switch':'frontpanel_meter_switch','predicate':'panel_copy_predicate','init':'panel_init'}
CONTRACT={}
EVID={}
for k,t in TASKS.items():
 r=json.load(open(PREP/'packets'/('rolling10_next100_'+t)/'request.json'));CONTRACT[k]=r['reconstruction_contract'];c=json.load(open(SNAP/CONTRACT[k]['path']));EVID[k]=next(e for e in c['requirements']['state']['evidence'] if e['kind']=='native_observation')
def sha(x):return hashlib.sha256(x).hexdigest()
def call(exe,args,stdin=''):
 p=subprocess.run([str(exe),*map(str,args)],input=stdin,text=True,capture_output=True,check=True);return p.stdout
class Oracle:
 def __init__(self,key):
  self.key=key;raw=(SNAP/'rootfs/RML16AI_Rack_13731/home/root/mixer').read_bytes();assert sha(raw)==ELF_SHA
  self.elf=ELFFile(io.BytesIO(raw));self.raw=raw;self.data=json.load(open(SNAP/EVID[key]['path']));assert sha((SNAP/EVID[key]['path']).read_bytes())==EVID[key]['sha256'];self.body=self.data['verified_body'];self.start=self.body['address'];self.end=self.start+self.body['size'];sections=[s for s in self.elf.iter_sections() if s['sh_flags']&2 and s['sh_type']!='SHT_NOBITS']
  def read(a,n):
   s=next(s for s in sections if s['sh_addr']<=a and a+n<=s['sh_addr']+s['sh_size']);o=s['sh_offset']+a-s['sh_addr'];return raw[o:o+n],o
  self.read=read;body,off=read(self.start,self.body['size']);assert sha(body)==self.body['bytes_sha256'] and off==self.body['file_offset']
  t=self.data['target'];assert any(s.name==t['mangled'] and s['st_value']==self.start and s['st_size']==self.body['size'] and s['st_shndx']==12 for s in self.elf.get_section_by_name('.symtab').iter_symbols())
  if key=='fader':
   v=self.data['numeric22_interface'];d,o=read(v['address'],v['size']);assert sha(d)==v['sha256'] and o==v['file_offset'];self.vptr=v['address']+8;self.setter=v['slots']['22'];assert struct.unpack_from('<I',d,8+22*4)[0]==self.setter
  if key in ['led','switch']:
   v=self.data['control_vtable'];d,o=read(v['address'],v['size']);assert sha(d)==v['sha256'];self.vptr=v['address']+8;self.setter=v['slot4_entry'];assert struct.unpack_from('<I',d,8+16)[0]==self.setter
  if key=='init':
   v=self.data['string29_vtable'];d,o=read(v['address'],v['size']);assert sha(d)==v['sha256'];self.vptr=v['address']+8;self.setter=v['entry'];assert struct.unpack_from('<I',d,8+29*4)[0]==self.setter
   f=self.data['format_literal'];d,o=read(f['address'],3);assert sha(d)==f['sha256'] and d==b'%d\0'
 def execute(self,args,desc,exe):
  mu=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  # Original PT_LOAD bytes are mapped read-only as inputs. Hooks reject any
  # instruction outside the assigned exact body or named boundary entry.
  for seg in self.elf.iter_segments():
   if seg['p_type']!='PT_LOAD':continue
   base=seg['p_vaddr']&~4095;end=(seg['p_vaddr']+seg['p_memsz']+4095)&~4095;mu.mem_map(base,end-base);mu.mem_write(seg['p_vaddr'],seg.data())
  mu.mem_map(0x10000000,0x100000);mu.mem_map(0x20000000,4096)
  PANEL=0x10001000;MIXER=0x10002000;REGISTRAR=0x10003000;CTRL=0x10004000;PARAM=0x10005000;META=0x10006000;CONTROLLER=0x10007000
  STOP=0x20000000;STACK=0x100f0000
  def word(a,v):mu.mem_write(a,struct.pack('<I',v&0xffffffff))
  def get(r):return mu.reg_read(r)
  def signed(v):return struct.unpack('<i',struct.pack('<I',v))[0]
  def ret(v=None):
   if v is not None:mu.reg_write(UC_ARM_REG_R0,v&0xffffffff)
   mu.reg_write(UC_ARM_REG_PC,get(UC_ARM_REG_LR))
  word(PANEL+0x8c,MIXER);word(PANEL+0x90,REGISTRAR)
  target=self.key;ops=[];events=[];sites=[];writes=[]
  mu.reg_write(UC_ARM_REG_SP,STACK);mu.reg_write(UC_ARM_REG_LR,STOP);mu.reg_write(UC_ARM_REG_R0,PANEL);mu.reg_write(UC_ARM_REG_FP,0x55aabbcc)
  if target=='fader':
   shape,index,fbits=map(int,args);mu.reg_write(UC_ARM_REG_R1,index&0xffffffff);mu.reg_write(UC_ARM_REG_R2,fbits)
   for name,offset,array in [('input',0x134,0x10010000),('bank',0x198,0x10011000),('main',0x1ac,0x10012000)]:
    vec=desc[name];word(MIXER+offset,array);word(MIXER+offset+4,len(vec))
    for i,c in enumerate(vec):word(array+4*i,0x10020000+c*0x1000 if c else 0)
   for i,present in enumerate(desc['locate'],1):
    channel=0x10020000+i*0x1000;param=0x10030000+i*0x1000;word(channel+0x114,param if present else 0);word(param,self.vptr)
  elif target in ['led','switch']:
   kind,present,old,argument=map(int,args);mu.reg_write(UC_ARM_REG_R1,CTRL if kind else 0);mu.reg_write(UC_ARM_REG_R2,argument&0xffffffff);word(CTRL,self.vptr)
  elif target=='predicate':
   key,object,controller,tag=map(int,args);mu.reg_write(UC_ARM_REG_R1,key&0xffffffff);mu.reg_write(UC_ARM_REG_R2,1);mu.reg_write(UC_ARM_REG_R3,PARAM if object==1 else 1 if object else 0);word(PARAM+0xc,META);word(META+4,desc['tag'])
  elif target=='init':
   number,present=map(int,args);word(REGISTRAR+0xa4,desc['number']);word(MIXER+0x2dc,0x10008000);word(PARAM,self.vptr)
  def code(uc,pc,n,_):
   if self.start<=pc<self.end:sites.append(pc);return
   if target=='fader' and pc==self.setter:
    identifier=(get(UC_ARM_REG_R0)-0x10030000)//0x1000;assert 1<=identifier<=5;ops.append(f'numeric:{identifier}:{get(UC_ARM_REG_R1)}:{get(UC_ARM_REG_R2)}');events.append({'boundary':'real NumericParam::setValue','r0_identity':identifier,'bits':get(UC_ARM_REG_R1),'edit':get(UC_ARM_REG_R2)});ret();return
   if target in ['led','switch','predicate'] and pc==0xacf4:
    if target in ['led','switch']:
     assert get(UC_ARM_REG_R1)==3508996 and get(UC_ARM_REG_R2)==3508616 and get(UC_ARM_REG_R3)==0
     ops.append('cast');ret(CTRL if desc['cast'] else 0)
    else:
     assert get(UC_ARM_REG_R1)==1414580 and get(UC_ARM_REG_R2)==1521044 and get(UC_ARM_REG_R3)==4;ret(CONTROLLER if desc['cast'] else 0)
    events.append({'boundary':'intentional real type-ID cast adaptation','actual_provider_result':desc['cast']});return
   if target in ['led','switch'] and pc==0x8fbb4:
    ops.append('match:'+str(signed(get(UC_ARM_REG_R1))));events.append({'boundary':'LEDControl::setmatchvalue','match':signed(get(UC_ARM_REG_R1))});ret();return
   if target in ['led','switch','init'] and pc==0x119c4c:
    tag=signed(get(UC_ARM_REG_R1));ops.append('lookup:'+str(tag));events.append({'boundary':'real Component::getParameterByTag','tag':tag,'actual_result':desc['lookup']});ret(PARAM if desc['lookup'] else 0);return
   if target in ['led','switch'] and pc==self.setter:
    assert get(UC_ARM_REG_R0)==CTRL;which=int(get(UC_ARM_REG_R1)!=0);ops.append(f'set:{which}:{get(UC_ARM_REG_R2)}');events.append({'boundary':'Control::setParameter','actual_lookup_identity':which,'mode':get(UC_ARM_REG_R2)});ret();return
   if target=='predicate' and pc==0x11c1d4:
    assert get(UC_ARM_REG_R0)==PARAM;events.append({'boundary':'real Parameter::getController','actual_result':desc['controller']});ret(CONTROLLER if desc['controller'] else 0);return
   if target=='init' and pc==0x4e974:
    assert bytes(mu.mem_read(get(UC_ARM_REG_R1),3))==b'%d\0';number=signed(get(UC_ARM_REG_R2));text=call(exe,['format',number]);assert len(text)<64;ptr=get(UC_ARM_REG_R0);assert STACK-1000<ptr<STACK;mu.mem_write(ptr,text.encode()+b'\0');ops.append('format');events.append({'boundary':'actual CString64.appendFormat','format_hex':'256400','signed_number':number,'bytes_with_nul_hex':(text.encode()+b'\0').hex()});ret();return
   if target=='init' and pc==self.setter:
    assert get(UC_ARM_REG_R0)==PARAM;ptr=get(UC_ARM_REG_R1);text=bytes(mu.mem_read(ptr,64)).split(b'\0')[0];ops.append(f'text:{text.hex()}:{get(UC_ARM_REG_R2)}');events.append({'boundary':'actual StringParam::fromString','text_hex':text.hex(),'edit':get(UC_ARM_REG_R2)});ret();return
   raise AssertionError((target,hex(pc),'outside original exact body/approved boundary'))
  def write(uc,access,a,n,v,_):
   assert STACK-4096<=a<a+n<=STACK;writes.append([a-STACK,n,v])
  mu.hook_add(UC_HOOK_CODE,code);mu.hook_add(UC_HOOK_MEM_WRITE,write)
  mu.emu_start(self.start,STOP,count=1000);assert get(UC_ARM_REG_PC)==STOP and get(UC_ARM_REG_SP)==STACK and get(UC_ARM_REG_FP)==0x55aabbcc
  return {'ops':ops,'events':events,'sites':sites,'stack_writes':writes,'r0':get(UC_ARM_REG_R0) if target=='predicate' else None,'nonstack_app_writes':[]}
def cases(key):
 if key=='fader':return [[s,i,b] for s,i,b in itertools.product(range(4),[-2147483648,-1,0,1,2,6,7,30,31,32,33,35,36,37,38,39,2147483647],[0,0x80000000,0xbf800000,0x3f000000,0x40000000])]
 if key in ['led','switch']:return [list(c) for c in itertools.product(range(4),range(2),range(3),[-2147483648,-1,0,1,12,13,2147483647])]
 if key=='predicate':return [[k,o,c,t] for k,o,c,t in itertools.product([0,1348563553,-1],[0,1],[0,1,2],[-2147483648,-1,0,217,218,219,220,221,222,223,224,2147483647])]+[[k,2,0,0] for k in [0,-1,1348563552]]
 if key=='init':return [[n,p] for n,p in itertools.product([-2147483648,-2147483647,-1000,-1,0,1,42,2147483646,2147483647],range(2))]
def generate(key,exe):
 oracle=Oracle(key);rows=[]
 for args in cases(key):
  desc=json.loads(call(exe,['describe',key,*args]));obs=oracle.execute(args,desc,exe)
  rows.append({'args':args,'provider_input_description':desc,'original':obs})
 return {'elf_sha256':ELF_SHA,'task':'rolling10_next100_'+TASKS[key],'target':oracle.data['target'],'range':{k:v for k,v in oracle.body.items() if k!='instructions'},'evidence':EVID[key],'contract':CONTRACT[key],'cases':rows,'scope':'Exact original non-Core instructions execute; external boundaries use independently observed actual source-provider identities/results. Original ARM private state is seeded explicitly from actual typed descriptors. No Core body execution, original RTTI/return/layout/ABI or hardware claim.'}
