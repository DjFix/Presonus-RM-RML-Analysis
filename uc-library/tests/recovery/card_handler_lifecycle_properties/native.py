"""Execute original Handler app bodies only in private Unicorn memory.
Every provider boundary is explicit. No Core binary or guest syscall executes.
"""
import hashlib,json,struct,sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import *
from unicorn.arm_const import *
EXCEPTION=0x1900000
BASE=Path('uc-library/tests/recovery/card_handler_lifecycle_properties')
PACKETS=Path('temp/recovery-work/rolling200-02/next-implementation132/prepared132/packets')
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
with ELF.open('rb') as f:
 e=ELFFile(f); segments=[(int(s['p_vaddr']),s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD'];symbols={s.name:s for s in e.get_section_by_name('.symtab').iter_symbols()}
 ranges=[]
 for i in range(1,7):
  p=PACKETS/f'rolling200_02_handler132_{i:02}';req=json.loads((p/'request.json').read_text());t=req['targets'][0];s=symbols[t['mangled']];sec=e.get_section(s['st_shndx']);a=int(s['st_value']);n=int(s['st_size']);off=int(sec['sh_offset'])+a-int(sec['sh_addr'])
  assert (a,n)==(t['address'],t['size']);native=json.loads((p/'native-context.json').read_text());body=next(v for v in native['bodies'].values() if v['address']==a);h=hashlib.sha256(raw[off:off+n]).hexdigest();assert h==body['bytes_sha256'] and off==body['file_offset']
  ranges.append(dict(mangled=t['mangled'],address=a,size=n,file_offset=off,section=sec.name,range_sha256=h,elf_sha256=SHA,firmware='RM/RML mixer 13731',role='server'))
ROUTES={0xa1110:('setGEQToFWRoute',2),0xa0e50:('setMixerCustomInputRoute',4),0xa0744:('setAvbTapeRxToDigitalReturnRoute',3),0xa0abc:('setDspToAvbTxRoute',5),0xa049c:('setDspToDanteTxRoute',4),0xa0658:('setLinkBusToAvbRoute',4),0xa0bb0:('setAvbStageBoxMainRoute',3),0xa0e00:('setMixerMuteInputRoute',2),0xa06bc:('setAvbToLinkBusRoute',4),0xa0f50:('setAVS48Route',4),0xa05b0:('setAvbToSlaveFwRecordRoute',4),0xa1144:('setGEQTDMSlotInsert',3),0xa07d8:('setAvbTapeLRToAvbTxRoute',3),0xa0a40:('setTalkbackToAvbTxRoute',3),0xa0968:('setInputToDanteTxRoute',5),0xa08e0:('setInputToAvbTxRoute',4),0xa0db4:('set2TrackInputRoute',2),0xa129c:('setAvbToDacBypassRoute',5),0xa1040:('setSPDIFRoute',3),0xa1c54:('setMixerInputRoute',3),0x9dcd0:('setClockSource',1)}
A=0x1000000;P=A+0x1000;CARD=A+0x2000;ROUTER=A+0x3000;STACK=0x2000000;STOP=0x3000000
signed=lambda v:v-0x100000000 if v&0x80000000 else v

def execute(c):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000);u.mem_map(A,0x100000);u.mem_map(STACK,65536);u.mem_map(STOP,4096)
 for a,d in segments:u.mem_write(a,d)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def ret(v=0):u.reg_write(UC_ARM_REG_R0,v&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 trace=[];writes=[];freed=[];pcs=[];heap=A+0x10000;pops=0;allocations={}
 def alloc(n):
  nonlocal heap
  p=heap;heap+=(n+15)&~15;assert heap<A+0xf0000;return p
 def label(p):return 'handler' if p==A else allocations.get(p,'card' if p==CARD else 'router' if p==ROUTER else 'other')
 def unwind(delete_storage=False):
  assert c['kind'] in ['C1','C2'];delta=ranges[1 if c['kind']=='C1' else 2]['address']-0x9fd68
  u.reg_write(UC_ARM_REG_R0,EXCEPTION);u.reg_write(UC_ARM_REG_PC,(0x9fe88 if delete_storage else 0x9fee8)+delta)
 def hook(uc,pc,n,_):
  nonlocal pops
  if pc==STOP:uc.emu_stop();return
  args=[uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];sp=uc.reg_read(UC_ARM_REG_SP)
  if pc in ROUTES:
   name,count=ROUTES[pc];v=args[1:]+[r(sp),r(sp+4)];trace.append([name,*map(signed,v[:count])]);ret();return
  if pc in [0x10e384,0x10e460]:trace.append([('main.' if args[0]==A+0x70 else 'queue.')+('lock' if pc==0x10e384 else 'unlock')]);ret();return
  if pc==0x5479c:
   lock=r(args[0]);trace.append([('main.' if lock==A+0x70 else 'queue.')+'unlock']);ret();return
  if pc==0x9e9b0:trace.append(['purge']);ret();return
  if pc in [0x9da98,0x9e588,0xa3c64,0x9ce10,0xa13d8,0x9dfb8,0x10ea88,0x9e1f8]:
   name={0x9da98:'programSerialReset',0x9e588:'eraseFirmware',0xa3c64:'routeScript',0x9ce10:'card.open',0xa13d8:'router.open',0x9dfb8:'card.start',0x10ea88:'thread.start',0x9e1f8:'updateFirmware'}[pc]
   extra=[signed(args[2])] if name=='updateFirmware' else [args[1]] if name=='card.start' else []
   trace.append([name,*extra]);ret(c.get('provider_result',0));return
  if pc==0x1167c0:
   pops+=1;pool={0x4952f8:0,0x495318:1,0x495338:2}[args[0]];trace.append(['pool.pop',pool]);ret(0 if pops<=c.get('starve',0) else A+0x8000);return
  if pc==0xae68:u.mem_write(args[0],bytes(u.mem_read(args[1],args[2])));trace.append(['copy',args[2]]);ret(args[0]);return
  if pc==0x10e948:trace.append(['sleep',args[0]]);ret();return
  if pc==0x116a38:ret();return
  if pc==0xa7e4:
   name={352:'card',2360:'router',456:'spi'}.get(args[0],'other')
   if c.get('fail')==name+'_alloc':unwind();return
   p=alloc(args[0]);allocations[p]=name;ret(p);return
  if pc==0xacd0:
   assert args[0]==EXCEPTION;trace.append(['resume']);uc.reg_write(UC_ARM_REG_PC,STOP);return
  if pc==0xac10:
   assert args[0] not in freed;freed.append(args[0]);trace.append(['delete',label(args[0])]);ret();return
  if pc in [0x10e988,0xa4b38,0x10e5e8,0x9d534,0xa1a10,0xa30d4,0x10e6b4,0xa2e64,0x126cfc,0x10e800,0xa2fe0,0x9d370,0xa1eb4,0xa0018,0x10e4cc,0x10e1d0]:
   name={0x10e988:'thread.ctor',0xa4b38:'receiver.ctor',0x10e5e8:'lock.ctor',0x9d534:'card.ctor',0xa1a10:'router.ctor',0xa30d4:'register',0x10e6b4:'priority',0xa2e64:'spi.ctor',0x126cfc:'deletable.add',0x10e800:'terminate',0xa2fe0:'unregister',0x9d370:'card.D0',0xa1eb4:'router.D1',0xa0018:'list.dtor',0x10e4cc:'lock.dtor',0x10e1d0:'thread.dtor'}[pc]
   trace.append([name,*([args[1]] if name=='priority' else [])]);
   if (name=='card.ctor' and c.get('fail')=='card_ctor') or (name=='router.ctor' and c.get('fail')=='router_ctor'):
    unwind(True);return
   if name=='register' and c.get('fail')=='register':unwind();return
   if name=='card.ctor':w(args[0],0x35a638)
   if name=='card.D0':assert args[0] not in freed;freed.append(args[0])
   ret();return
  assert any(x['address']<=pc<x['address']+x['size'] for x in ranges),(c,hex(pc),'outside exact target/provider allowlist')
  pcs.append(pc)
 def write(uc,access,a,n,v,_):
  if A<=a<A+0xb0:writes.append([a-A,n,v])
 def reject(*a):raise AssertionError('guest syscall/interrupt/unmapped access rejected')
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write);u.hook_add(UC_HOOK_INTR,reject);u.hook_add(UC_HOOK_MEM_INVALID,reject)
 w(A+0x68,CARD);w(A+0x6c,ROUTER);w(CARD,0x35a638);w(CARD+0x14,c.get('mode',0));assert r(0x35a638+0x10)==0x9d370
 assert int(symbols['_ZN8Presonus4NOAA5TCardD0Ev']['st_value'])==0x9d370
 # Exact updateFirmware primary table slot recorded by native virtual call.
 update=symbols['_ZN8Presonus4NOAA5TCard14updateFirmwareEPNS_2UC23IFirmwareUpdateListenerEi']['st_value'];assert r(0x35a638+0x1c)==update
 for cell in [0x4952f8,0x495318,0x495338]:w(cell,cell);w(cell+12,0)
 w(4805480,0 if c.get('spi_absent') else A+0x4000);w(4805464,A if c.get('singleton_equal',True) else A+0x7000)
 if c.get('nonempty'):
  w(A+0xa4,A+0x9000);w(A+0xa8,A+0x9000);w(A+0x9000,P+0x400)
 w(P,c.get('id',0));w(P+4,c.get('size',28))
 for i,v in enumerate(c.get('words',[1,2,3,4,1])):w(P+8+4*i,v)
 kind=c['kind']
 if kind.startswith('C'):w(A+0x68,0);w(A+0x6c,0)
 idx={'property':0,'C1':1,'C2':2,'D0':3,'D1':4,'D2':5}[kind]
 u.reg_write(UC_ARM_REG_R0,A);u.reg_write(UC_ARM_REG_R1,P);u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP)
 u.emu_start(ranges[idx]['address'],STOP+4096,count=20000);assert u.reg_read(UC_ARM_REG_PC)==STOP,(c,'instruction budget')
 return dict(trace=trace,writes=writes,executed_addresses=pcs,pool_counts=[r(cell+12) for cell in [0x4952f8,0x495318,0x495338]],retained_dependencies=[name for pointer,name in allocations.items() if pointer not in freed and name in ['card','router']],retained_fifo_head=(r(A+0xa4)==A+0x9000) if c.get('nonempty') else None,handler_deallocated=A in freed,card_deallocated=CARD in freed,singleton=r(4805464),fifo_count=int(r(A+0xa4)!=0),copied=bytes(u.mem_read(A+0x8000,c.get('size',28))).hex() if kind=='property' and any(t[0]=='copy' for t in trace) else None)
ids=[0x67716677,0x73637270,0x73706466,0x73657269,0x73657475,0x63726f74,0x64746e70,0x64727470,0x64746174,0x6c626172,0x726f7574,0x73626d72,0x6d6d7574,0x616c6272,0x61767372,0x636c6b70,0x61736672,0x666c6576,0x67657274,0x65666972,0x74706472,0x75647461,0x74626176,0x69707464,0x69746176,0x3274726b,0x61646272]
cases=[]
for ident in ids:
 for mode in ([0,1,2,7] if ident in [0x64746e70,0x64746174] else [1]):
  for words in [[1,2,3,4,1],[0x10201,0x102,1,0,0],[0xffffffff,0x80000000,0,0xffffffff,0x100]]:
   cases.append(dict(kind='property',id=ident,mode=mode,words=words,size=28))
for n in [8,16,17,32,33,512]:
 for starve in [0,2]:cases.append(dict(kind='property',id=123,size=n,starve=starve))
for n in [16,17,33]:cases.append(dict(kind='property',id=123,size=n,nonempty=True))
for kind in ['C1','C2','D0','D1','D2']:
 for absent in [False,True]:
  for equal in [False,True]:cases.append(dict(kind=kind,spi_absent=absent,singleton_equal=equal))
for kind in ['C1','C2']:
 for fail in ['card_alloc','card_ctor','router_alloc','router_ctor','register']:
  for equal in [False,True]:cases.append(dict(kind=kind,fail=fail,singleton_equal=equal))
for c in cases:c['expected']=execute(c)
out=dict(elf_sha256=SHA,ranges=ranges,cases=cases,oracle_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),isolation='Private memory only; explicit provider boundaries; reject every other PC, interrupt and unmapped access. Native boundary numeric return values do not establish declarations.')
p=BASE/'fixtures.json'
if '--verify' in sys.argv:assert json.loads(p.read_text())==out
else:p.write_text(json.dumps(out,indent=2)+'\n')
print('Original Handler executions',len(cases),'Unicorn',__import__('unicorn').__version__)
