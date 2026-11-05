"""Exact ARM target and explicit hash-bound application helpers only; fail closed."""
from pathlib import Path
import json,hashlib,struct,sys,datetime
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import *
from unicorn.arm_const import *
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
OUT=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling200-02/agent-repos02/resolve_permissions/temp/recovery-work/rolling200-02/permissions-regression-review08')
BASE=ROOT/'temp/recovery-work/rolling200-02/implementation-plan01/packets-closeout09-01/packets'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
PACKETS={k:BASE/('rolling200_02_impl_'+k) for k in ['w03_01','w03_02','w03_03','w03_04','w03_05','w03_06','storm_01','storm_02','storm_03']}
EXTRA=[ROOT/'temp/recovery-work/rolling200-02'/n for n in ['expand-closeout09-w03_01-getAccessCodeFileName01','expand-closeout09-w03_06-getSelectedFileName01','expand-closeout09-w03_04-getDataDir01']]
BODIES={};DATA=ELF.read_bytes();assert hashlib.sha256(DATA).hexdigest()==SHA
for p in [*PACKETS.values(),*EXTRA]:
 d=json.loads((p/'native-context.json').read_text())
 for key in d['roots']:
  b=d['bodies'][key];BODIES[b['address']]=b
  assert hashlib.sha256(DATA[b['file_offset']:b['file_offset']+b['size']]).hexdigest()==b['bytes_sha256']
  with ELF.open('rb') as f:
   e=ELFFile(f);sec=e.get_section(b['section_index']);assert sec['sh_offset']+b['address']-sec['sh_addr']==b['file_offset'];assert b['address']+b['size']<=sec['sh_addr']+sec['sh_size'];m=d['nodes'][key]['metadata']['mangled'];assert any(x['st_value']==b['address'] and x['st_size']==b['size'] and x['st_shndx']==b['section_index'] for x in e.get_section_by_name('.symtab').get_symbol_by_name(m))
def rootbody(k):
 if k=='existing_helper':return BODIES[0x50c94]
 d=json.loads((PACKETS[k]/'native-context.json').read_text());return d['bodies'][d['roots'][0]]
def execute(k,args):
 b=rootbody(k);u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
 with ELF.open('rb') as f:
  for seg in ELFFile(f).iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 u.mem_map(0x1000000,0x20000);u.mem_map(0x2000000,0x20000)
 obj=0x1000000;arr=obj+0x1000;vt=obj+0x2000;param=obj+0x3000;mix=obj+0x4000;other=obj+0x5000;stop=0x101ff00
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def rd(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def put(a,s):u.mem_write(a,s.encode()+b'\0')
 def text(a):
  if not a:return ''
  z=bytearray()
  for i in range(4096):
   c=bytes(u.mem_read(a+i,1))
   if c==b'\0':return z.decode()
   z+=c
  raise RuntimeError('unterminated native string')
 def ret(v=0):u.reg_write(UC_ARM_REG_R0,v&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 trace=[];pcs=set();writes=[];clock=[];attributes={};result={};allowed=[b]
 if k in ['w03_01','w03_04','w03_06','existing_helper']:
  for a in [0x321c4]+([0x5165c] if k=='w03_01' else [0x50c94,0x50bac] if k=='w03_06' else [0x50bac] if k=='existing_helper' else []):allowed.append(BODIES[a])
 w(obj,vt);w(param,vt+0x100);w(mix,vt+0x200);w(other,vt+0x300);w(obj+0x88,mix);w(obj+0x8c,other);w(obj+0x94,obj+0x6000);put(obj+0x6000+0x3a4,'device')
 for base in [vt+0x100,vt+0x200,vt+0x300]:
  for slot,addr in [(0x44,0x101f100),(0x70,0x101f110),(0x74,0x101f120),(0x5c,0x101f130)]:w(base+slot,addr)
 reg1=0;reg2=0;current='initial';default='default';attr=obj+0x8000;put(obj+0x8100,'code');w(param+0xc,obj+0x8100-8)
 if k in ['storm_01','w03_05']:
  reg1=args['pointer'];w(obj+(0xe0 if k=='storm_01' else 0xf8),args.get('before',args['pointer']))
 elif k=='storm_02':w(obj+0xa4,9);reg1=args['index']
 elif k=='storm_03':
  w(obj+0xa4,9);w(obj+0xa0,arr);reg1=args['needle']
  for i,members in enumerate(args['groups']):
   g=obj+0x9000+0x100*i;ma=obj+0xb000+0x100*i;w(arr+4*i,g);w(g+0x14,ma);w(g+0x18,len(members))
   for j,m in enumerate(members):w(ma+4*j,m)
 elif k=='w03_02':pass
 elif k=='w03_03':
  u.mem_write(obj+0x108,bytes([args['dirty']]));v=args['deadline']&((1<<64)-1);w(obj+0x100,v);w(obj+0x104,v>>32);clock=list(args['times'])
 elif k=='w03_04':reg1=obj+0x7000;reg2=obj+0x7100;put(reg2,args['name'])
 elif k=='w03_01':
  attributes=args['attributes'];current='initial'
 elif k in ['w03_06','existing_helper']:
  w(obj+0xf8,obj+0xc000 if args['selected'] else 0);put(obj+0xc000+0xd8,args['name'])
  if k=='existing_helper':reg1=obj+0x7000;put(reg1,'keep');u.mem_write(obj+0x108,b'\0')
 providers={0x1a134:'CString128 ctor',0x119c4c:'Component getParameterByTag',0x157928:'runtime float greater-or-equal (__aeabi_fcmpge)',0x101f100:'Parameter getValue',0x101f110:'Parameter toString',0x101f120:'Parameter fromString',0x101f130:'Parameter resetValue',0x116908:'GetAbsoluteTime',0x157a08:'runtime signed division',0x11dbd4:'Parameter changed',0x11dc28:'Parameter rangeChanged',0x127a08:'FileUtils getDataDir',0x129ba4:'FileName ctor',0x1289f4:'FileName descend',0x1279b4:'FileUtils makeDirectory',0xae68:'runtime strncpy',0xae98:'runtime strlen',0xae08:'runtime strncat',0x121dbc:'AttributeAllocator getDefault',0x121a68:'Attributes ctor',0x1228b0:'Attributes dtor',0x117fa8:'ArchiveUtils loadFromFile',0x121d4c:'Attributes lookup',0x117950:'AttributesBuilder ctor',0x11973c:'Component save',0x118ec8:'ArchiveUtils saveInBackground',0x2f178:'Vector State dtor'}
 def code(uc,a,n,user):
  nonlocal current
  if a==stop:u.emu_stop();return
  if any(x['address']<=a<x['address']+x['size'] for x in allowed):pcs.add(a);return
  if a not in providers:raise RuntimeError(f'unknown PC {a:#x}')
  r=[uc.reg_read(reg) for reg in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];name=providers[a];trace.append([name,r])
  if a==0x1a134:put(r[0],'');ret(r[0])
  elif a==0x119c4c:ret(param if args.get('present',True) else 0)
  elif a==0x101f100:ret(struct.unpack('<I',struct.pack('<f',args['value']))[0])
  elif a==0x157928:ret(int(struct.unpack('<f',struct.pack('<I',r[0]))[0]>=struct.unpack('<f',struct.pack('<I',r[1]))[0]))
  elif a==0x101f110:put(r[1],args['text'][:r[2]-1]);ret()
  elif a==0x101f120:
   current=text(r[1]);put(param+0x2c,current);result.setdefault('events',[]).append(['from',current,r[2]]);ret()
  elif a==0x101f130:current=default;put(param+0x2c,current);result.setdefault('events',[]).append(['reset',r[1]]);ret()
  elif a==0x116908:
   v=clock.pop(0)*1000000;uc.reg_write(UC_ARM_REG_R1,(v>>32)&0xffffffff);ret(v)
  elif a==0x157a08:
   v=r[0]|r[1]<<32;v=v-(1<<64) if v>>63 else v;d=r[2]|r[3]<<32;v=(abs(v)//d)*(-1 if v<0 else 1);uc.reg_write(UC_ARM_REG_R1,(v>>32)&0xffffffff);ret(v)
  elif a in [0x11dbd4,0x11dc28]:result.setdefault('events',[]).append(['changed' if a==0x11dbd4 else 'range',int(r[0]==other)]);ret()
  elif a==0x127a08:put(obj+0xd000,args.get('root','ROOT'));ret(obj+0xd000)
  elif a==0x129ba4:put(r[0],text(r[1])[:255]);ret(r[0])
  elif a==0x1289f4:
   v=text(r[0]);put(r[0],(v+('' if v.endswith('/') else '/')+text(r[1]))[:255]);ret(r[0])
  elif a==0x1279b4:result.setdefault('directories',[]).append(text(r[0]));ret(1)
  elif a==0xae68:
   raw=bytes(u.mem_read(r[1],r[2]));u.mem_write(r[0],raw.split(b'\0')[0][:r[2]].ljust(r[2],b'\0'));ret(r[0])
  elif a==0xae98:ret(len(text(r[0])))
  elif a==0xae08:put(r[0],text(r[0])+text(r[1])[:r[2]]);ret(r[0])
  elif a==0x121dbc:ret(obj+0xe000)
  elif a in [0x121a68,0x1228b0,0x117950,0x2f178]:ret()
  elif a==0x117fa8:result['filename']=text(r[1]);ret(args['load'])
  elif a==0x121d4c:
   v=attributes.get(text(r[1]));w(attr+4,3 if isinstance(v,str) else 1);put(obj+0xf000,v if isinstance(v,str) else '');w(attr+8,obj+0xf000);ret(attr if v is not None else 0)
  elif a==0x11973c:result['saved']=True;ret(1)
  elif a==0x118ec8:result['filename']=text(r[0]);result['archive_flags']=[r[2],r[3],rd(uc.reg_read(UC_ARM_REG_SP)),rd(uc.reg_read(UC_ARM_REG_SP)+4)];ret(1)
 def write(uc,access,a,n,v,user):
  if obj<=a<obj+0x20000:writes.append([a-obj,n,v])
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 for r,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,reg1),(UC_ARM_REG_R2,reg2),(UC_ARM_REG_SP,0x201f000),(UC_ARM_REG_LR,stop)]:u.reg_write(r,v)
 u.emu_start(b['address'],stop,count=20000);assert u.reg_read(UC_ARM_REG_PC)==stop
 if k=='storm_01':result['pointer']=rd(obj+0xe0)
 elif k in ['storm_02','storm_03','w03_05']:result['return']=u.reg_read(UC_ARM_REG_R0)
 elif k in ['w03_01','w03_02']:result['text']=current
 elif k=='w03_03':
  v=rd(obj+0x100)|(rd(obj+0x104)<<32);result['deadline']=v-(1<<64) if v>>63 else v;result['dirty']=bytes(u.mem_read(obj+0x108,1))[0]
 elif k=='w03_04':result['filename']=text(reg1)
 elif k=='existing_helper':result['filename']=text(reg1);result['dirty']=bytes(u.mem_read(obj+0x108,1))[0]
 return dict(task=k,input=args,output=result,trace=trace,writes=writes,executed_pcs=sorted(pcs),allowed_ranges=[{x:b[x] for x in ['address','size','file_offset','bytes_sha256']} for b in allowed])
def main():
 scratch=str(ROOT/'temp/recovery-work/rolling200-02/closeout09-owner01/files')
 cases=[]
 for p in [0,1,0x12345678,0xfffffffc]:cases.append(execute('storm_01',dict(pointer=p,before=99)));cases.append(execute('w03_05',dict(pointer=p)))
 for i in list(range(11))+[0xfffffffe,0xffffffff,0x80000000]:cases.append(execute('storm_02',dict(index=i)))
 for place in [-1,*range(9)]:
  for needle in [0,11,22,33]:
   groups=[[] for _ in range(9)]
   if place>=0:groups[place]=[11,22,22,33] if needle==33 else [11,needle,needle,33]
   cases.append(execute('storm_03',dict(groups=groups,needle=needle)))
 for present in [False,True]:
  for v in [0.,-0.,1.,-1.]:cases.append(execute('w03_02',dict(present=present,value=v,text='1.00' if v>0 else '-1.00' if v<0 else '0.00')))
 for dirty,deadline,times in [(0,0,[10]),(0,5,[10]),(0,10,[10]),(0,11,[10]),(1,0,[10,10]),(1,0,[10,4000]),(0,-1,[0]),(0,0x100000000,[0xffffffff]),(0,0xffffffff,[0x100000000])]:cases.append(execute('w03_03',dict(dirty=dirty,deadline=deadline,times=times)))
 for root,name in [(scratch,''),(scratch,'desk'),(scratch+'/','x'*63),(scratch+'/'+'R'*(235-len(scratch)-1),'n'*63)]:cases.append(execute('w03_04',dict(root=root,name=name)))
 for present,load,attributes in [(False,False,{}),(True,False,{}),(True,True,{}),(True,True,{'code':7}),(True,True,{'code':''}),(True,True,{'code':'1234'})]:cases.append(execute('w03_01',dict(present=present,load=load,attributes=attributes,root=scratch)))
 for selected in [False,True]:cases.append(execute('w03_06',dict(selected=selected,name='desk',root=scratch)))
 fixture=dict(version=1,elf_sha256=SHA,unicorn=unicorn.__version__,producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=cases)
 (OUT/'native-fixtures.json').write_text(json.dumps(fixture,indent=2)+'\n');print('native executions',len(cases))
 historical=ROOT/'uc-library/candidates/graph-live-trial-05-permissions/native-fixtures.json'
 helpercases=[]
 for c in json.loads(historical.read_text())['cases']:
  if c['target']==0:
   args=dict(c['input'],root=scratch);observation=execute('existing_helper',args);observation['historical_case_id']=c['case_id'];helpercases.append(observation)
 helpers=dict(version=1,elf_sha256=SHA,producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),historical_input=dict(path=str(historical.relative_to(ROOT)),sha256=hashlib.sha256(historical.read_bytes()).hexdigest()),scope='Six existing helper refresh cases, no new reconstruction credit; historical no-op callback outcomes are not reused',cases=helpercases)
 (OUT/'existing-helper-fixtures.json').write_text(json.dumps(helpers,indent=2)+'\n');print('existing helper native executions',len(helpercases))
if __name__=='__main__':main()
