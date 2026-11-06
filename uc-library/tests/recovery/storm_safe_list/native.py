"""Execute only the seven sealed app ranges. No Core firmware execution or syscall passthrough."""
import hashlib,json,pathlib,struct,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
BASE=pathlib.Path('uc-library/tests/recovery/storm_safe_list')
PACKETS=pathlib.Path('temp/recovery-work/rolling200-02/next-implementation122/prepared122/packets')
ELF='rootfs/RML16AI_Rack_13731/home/root/mixer'; SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
OBJ=0x1000000; MIX=OBJ+0x1000; PAR=OBJ+0x2000; VT=OBJ+0x3000; ARR=OBJ+0x4000; MAN=OBJ+0x5000; OUT=OBJ+0x6000; HEAP=OBJ+0x7000;STACK=0x1100000;SP=STACK+0x8000;STOP=0x1200000
FOLDER='temp/recovery-work/rolling200-02/storm-safe122/files'
def verified():
 raw=(ROOT/ELF).read_bytes(); assert hashlib.sha256(raw).hexdigest()==SHA
 bodies=[];segments=[]
 with (ROOT/ELF).open('rb') as f:
  elf=ELFFile(f)
  for seg in elf.iter_segments():
   if seg['p_type']=='PT_LOAD': segments.append((int(seg['p_vaddr']),int(seg['p_memsz']),seg.data()))
  for i in range(1,8):
   j=json.loads((ROOT/PACKETS/f'rolling200_02_storm_safe122_{i:02d}/native-context.json').read_text());b=j['bodies'][j['roots'][0]];sec=elf.get_section(b['section_index']);off=sec['sh_offset']+b['address']-sec['sh_addr'];assert off==b['file_offset'] and sec.name==b['section']; assert hashlib.sha256(raw[off:off+b['size']]).hexdigest()==b['bytes_sha256'];bodies.append({k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']})
 return bodies,segments

def execute(bodies,segments,mode,args):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
 for a,n,data in segments:
  for pg in range(a&~4095,(a+n+4095)&~4095,4096):
   if pg not in pages:u.mem_map(pg,4096);pages.add(pg)
  u.mem_write(a,data)
 for a,n in [(OBJ,0x10000),(STACK,0x10000),(STOP,4096)]:u.mem_map(a,n)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def s(a):
  b=bytearray()
  if not a:return ''
  while u.mem_read(a,1)!=b'\0':b+=u.mem_read(a,1);a+=1
  return b.decode()
 def put(a,t):u.mem_write(a,t.encode()+b'\0')
 def regs():return [u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
 def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 enabled=1; cache=True; saved=True; loaded=True; bits=0; notified=[];trace=[];loose=3;resize=[];app_writes=[]
 if mode=='filename':cache=int(args[0])>0;slot=int(args[1])
 if mode=='store':saved=bool(int(args[0]))
 if mode=='all':enabled=int(args[0]);incoming=int(args[1]);saved=bool(int(args[2]))
 if mode=='startup':bits=int(args[0]);loaded=bool(int(args[1]));enabled=0
 w(OBJ+0x85,enabled);u.mem_write(OBJ+0x85,bytes([enabled]));w(OBJ+0xdc,MIX);w(OBJ+0xb8,loose);w(MIX,VT);w(VT+0x24,STOP+4);w(VT+0x20,STOP+8);w(PAR,VT+0x100);w(VT+0x144,STOP+12);w(MIX+0x2c4,ARR);w(MIX+0x2c8,3)
 for i,p in enumerate([PAR,PAR+0x100,PAR]):w(ARR+4*i,p)
 # Original Singleton<T>::theInstance cell from literal pool, not inferred layout.
 manager_cell=r(0x75550);w(manager_cell,0 if mode=='filename' and args[0]=='-1' else MAN)
 def hook(uc,a,size,user):
  nonlocal loose
  R=regs();sp=uc.reg_read(UC_ARM_REG_SP)
  if a==STOP:return
  if a==0xacd0:
   assert mode=='manager-unwind';trace.append('rethrow-boundary');uc.reg_write(UC_ARM_REG_PC,STOP);return
  if a==0x121dbc:trace.append('allocator');ret(HEAP);return
  if a==0x121a68:trace.append('attributes');ret(R[0]);return
  if a==0x117950:assert R[2]==1;trace.append('builder:1');ret(R[0]);return
  if a==STOP+4:assert R[0]==MIX;trace.append('save');ret(int(saved));return
  if a==STOP+8:assert R[0]==MIX;trace.append('load');loose=2;ret(1);return
  if a==STOP+12:ret(bits);return
  if a==0x118ec8:
   assert R[2:]==[0,0] and r(sp)==0 and r(sp+4)==0;trace.append('background:'+s(R[0]));ret(HEAP);return
  if a==0x117fa8:
   assert R[2:]==[0,0] and r(sp)==0 and r(sp+4)==0;trace.append('read:'+s(R[1]));ret(int(loaded));return
  if a==0x1228b0:trace.append('destroy-attributes');ret();return
  if a==0x2f178:trace.append('destroy-builder');ret();return
  if a==0x775f0:assert R[0]==OBJ+0xb8;loose=0;w(R[0],0);ret();return
  if a==0x119c4c:assert R[1]==0;ret(PAR);return
  if a==0x157940:
   value=struct.unpack('<f',struct.pack('<I',R[0]))[0];ret(int(value>0));return
  if a==0x116a38:ret();return
  if a==0x11dc28:notified.append([int((R[0]-PAR)//0x100),int(u.mem_read(OBJ+0x85,1)[0])]);ret();return
  if a==0x84b08:trace.append('lookup');ret(HEAP if cache else 0);return
  if a==0x85764:
   assert s(R[3])=='mutegroup' and s(r(sp))=='' and r(sp+4)==0 and r(sp+8)==1
   put(R[0],FOLDER+'/'+('%02d'%struct.unpack('<i',struct.pack('<I',(R[2]+1)&0xffffffff))[0])+'.mutegroup.muteGroup');ret(R[0]);return
  if a==0x129ba4:put(R[0],s(R[1]));ret(R[0]);return
  if a==0xae68:u.mem_write(R[0],bytes(u.mem_read(R[1],R[2])));ret(R[0]);return
  if a==0xb030:ret(1);return
  if a==0xaa3c:w(R[0],1);ret();return
  if a==0x127acc:put(R[1],s(R[0]).split('/')[-1]);ret();return
  if a==0xad18:
   idx=s(R[0]).find(s(R[1]));ret(R[0]+idx if idx>=0 else 0);return
  if a==0xae98:ret(len(s(R[0])));return
  if a==0x1279b4:trace.append('mkdir:'+s(R[0]));ret(1);return
  if a==0x1289f4:put(R[0],s(R[0])+('' if s(R[0]).endswith('/') else '/')+s(R[1]));ret(R[0]);return
  if a==0xa7e4:assert R[0]==24;trace.append('allocate-manager');ret(MAN);return
  if a==0x126cfc:assert R[0]==MAN;trace.append('register-deletable');ret();return
  if a==0x85e94:
   assert R[1]==10;resize.append([R[1],r(R[0]+0x10),r(R[0]+8)]);w(R[0]+0xc,R[1]);ret(1);return
  assert any(b['address']<=a<a+size<=b['address']+b['size'] for b in bodies),(hex(a),R)
 def write(uc,access,a,size,v,user):
  if not STACK<=a<a+size<=SP:app_writes.append([a,size,v])
 u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.hook_add(UC_HOOK_CODE,hook)
 if mode in ['manager','manager-unwind']:idx=5+int(args[0]);r0=OBJ;r1=0;r2=0
 elif mode=='filename':idx=4;r0=OUT;r1=OBJ;r2=slot
 elif mode=='safe':idx=0;r0=OUT;r1=OBJ;r2=0
 else:idx={'store':1,'all':2,'startup':3}[mode];r0=OBJ;r1=incoming if mode=='all' else 0;r2=0
 for reg,v in [(UC_ARM_REG_SP,SP),(UC_ARM_REG_LR,STOP),(UC_ARM_REG_R0,r0),(UC_ARM_REG_R1,r1),(UC_ARM_REG_R2,r2)]:u.reg_write(reg,v)
 start=bodies[idx]['address']
 if mode=='manager-unwind':
  w(r(start+0x84),OBJ if args[1]=='1' else MAN);u.reg_write(UC_ARM_REG_R4,OBJ);start+=0x50
 u.emu_start(start,STOP,count=20000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 if mode=='safe':
  cached=s(OUT);cache=False
  for reg,v in [(UC_ARM_REG_SP,SP),(UC_ARM_REG_LR,STOP),(UC_ARM_REG_R0,OUT),(UC_ARM_REG_R1,OBJ+0x800)]:u.reg_write(reg,v)
  u.emu_start(bodies[0]['address'],STOP,count=20000);assert s(OUT)==cached and trace.count('lookup')==1
 if mode=='manager-unwind':expected=str(int(r(r(bodies[idx]['address']+0x84))!=0))
 elif mode=='manager':expected=f'{r(OBJ+0x10)} {r(OBJ+0xc)} {r(OBJ+0x14)}';assert resize==[[10,5,0]],resize
 elif mode in ['filename','safe']:expected=s(OUT)
 elif mode in ['store','all']:expected=str(trace.count('save'))+' '+str(sum(t.startswith('background:') for t in trace))
 else:expected=f'{u.mem_read(OBJ+0x85,1)[0]} {loose} '+','.join(str(n[0])+':'+str(n[1]) for n in notified)+f' {trace.count("load")}'
 return dict(argv=[mode,*args],expected=expected.strip(),trace=trace,notifications=notified,loose=loose,app_writes=app_writes)
def generate():
 bodies,segments=verified();cases=[]
 for variant in ['0','1']:cases.append(execute(bodies,segments,'manager',[variant]))
 for variant in ['0','1']:
  for own in ['0','1']:cases.append(execute(bodies,segments,'manager-unwind',[variant,own]))
 for cache in ['-1','0','1']:
  for slot in ['0','7','4294967295']:cases.append(execute(bodies,segments,'filename',[cache,slot]))
 cases.append(execute(bodies,segments,'safe',[]))
 for saved in ['0','1']:cases.append(execute(bodies,segments,'store',[saved]))
 for enabled in ['0','1']:
  for incoming in ['0','1']:
   for saved in ['0','1']:cases.append(execute(bodies,segments,'all',[enabled,incoming,saved]))
 for bits in ['0','2147483648','3212836864','2143289344','1065353216','2139095040']:
  for loaded in ['0','1']:cases.append(execute(bodies,segments,'startup',[bits,loaded]))
 return dict(elf=ELF,elf_sha256=SHA,ranges=bodies,cases=cases,boundaries='Only sealed application instructions execute. CCL and already recovered lookup/build filename calls are explicit fixture boundaries, not firmware Core execution. Save/load return and membership are controlled boundary inputs; host replay additionally uses actual CCL tree and files. Native exceptional unwinder and allocator failure not executed; host exception cleanup separately bounded. No original layouts/return declarations/ARM interoperability claim.')
if __name__=='__main__':
 j=generate();p=ROOT/BASE/'fixtures.json'
 if '--generate' in sys.argv:p.write_text(json.dumps(j,indent=2)+'\n')
 else:assert j==json.loads(p.read_text())
 print(len(j['cases']),'exact ARM observations')
