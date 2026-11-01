"""Execute original ARM ranges; callback stubs model only external boundaries."""
import hashlib,json,random,struct,pathlib,datetime,sys,time
START=datetime.datetime.now(datetime.timezone.utc).isoformat();T0=time.monotonic()
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
BASE=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path('uc-library/candidates/graph-live-trial-04-linkable')
BASE.mkdir(parents=True,exist_ok=True)
ELF=pathlib.Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(ELF)=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
raw=ELF.read_bytes(); ranges=[];targets=[]
for n in range(1,6):
 p=pathlib.Path(f'temp/recovery-work/graph-live-trial-04/trial04_linkable_{n}-packet/context.json')
 c=json.loads(p.read_text());o=c['originals'][0]['original'];targets.append(o)
 with ELF.open('rb') as f:
  e=ELFFile(f);s=e.get_section(int(o['section_json']));off=s['sh_offset']+o['address']-s['sh_addr'];b=raw[off:off+o['size']]
  native=json.loads(p.with_name('native-context.json').read_text());bound=native['bodies'][native['roots'][0]]
  assert bound['address']==o['address'] and bound['size']==o['size'] and bound['file_offset']==off and bound['bytes_sha256']==hashlib.sha256(b).hexdigest()
  r=dict(o,file_offset=off,range_sha256=hashlib.sha256(b).hexdigest(),section_name=s.name);ranges.append(r)
A=0x200000;V=0x210000;ARR=0x220000;STACK=0x300000;STOP=0x400000;QUERY=0x400100;REMOVE=0x400200;SET=0x400300;MASTER=0x82bd8
addr=lambda i:0 if i<0 else A+0x100*i
idx=lambda a:-1 if a==0 else (a-A)//0x100
cases=[];rng=random.Random(82334)
for method in range(5):
 for k in range(96):
  nodes=[]
  for i in range(4):
   nodes.append({'partner':rng.randrange(-1,4),'slave':rng.choice([0,1,2,127,255]),'enabled':rng.choice([0,1,255]),'query':rng.randrange(2),'children':[rng.choice([-1]+list(range(i+1,4))) for _ in range(rng.randrange(5))] if i<3 else []})
  peer=k%4;flag=k%2
  if k%4==0:nodes[0]['partner']=peer
  if k%4==1:nodes[0]['partner']=-1
  uc=Uc(UC_ARCH_ARM,UC_MODE_ARM);uc.mem_map(0x80000,0x10000);uc.mem_map(A,0x30000);uc.mem_map(STACK,0x10000);uc.mem_map(STOP,0x1000)
  for r in ranges:uc.mem_write(r['address'],raw[r['file_offset']:r['file_offset']+r['size']])
  def w(a,v):uc.mem_write(a,struct.pack('<I',v))
  for i,n in enumerate(nodes):
   a=addr(i);v=V+i*0x100;ar=ARR+i*0x100
   w(a,v);w(v,QUERY);w(v+0x40,REMOVE);w(v+0x3c,SET);w(a+0x88,addr(n['partner']));w(a+0x58,ar);w(a+0x5c,len(n['children']));uc.mem_write(a+0x8c,bytes([n['slave'],n['enabled']]))
   for j,x in enumerate(n['children']):w(ar+j*4,addr(x))
  trace=[];writes=[];stopped=[False]
  def hook(u,a,size,data):
   if a==STOP:stopped[0]=True;u.emu_stop();return
   if a not in (QUERY,REMOVE,SET,MASTER):return
   r0=u.reg_read(UC_ARM_REG_R0);r1=u.reg_read(UC_ARM_REG_R1);r2=u.reg_read(UC_ARM_REG_R2)
   if a==QUERY:
    trace.extend([0,idx(r0),r1,0]);ret=r0 if nodes[idx(r0)]['query'] else 0
   elif a==REMOVE:trace.extend([1,idx(r0),0,0]);ret=0xd00d
   elif a==SET:trace.extend([2,idx(r0),idx(r1),r2]);ret=0xd00d
   else:trace.extend([3,idx(r0),idx(r1),0]);ret=0xd00d
   for j in range(4):
    ja=addr(j);trace.extend([idx(struct.unpack('<I',u.mem_read(ja+0x88,4))[0]),*u.mem_read(ja+0x8c,2)])
   u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  def mem(u,access,a,size,value,data):
   if A<=a<A+0x400:writes.append([a-A,size,value])
  uc.hook_add(UC_HOOK_CODE,hook);uc.hook_add(UC_HOOK_MEM_WRITE,mem);uc.reg_write(UC_ARM_REG_SP,STACK+0xf000);uc.reg_write(UC_ARM_REG_LR,STOP);uc.reg_write(UC_ARM_REG_R0,A);uc.reg_write(UC_ARM_REG_R1,flag if method==3 else addr(peer));uc.reg_write(UC_ARM_REG_R2,flag)
  uc.emu_start(targets[method]['address'],STOP+4,count=10000);assert stopped[0]
  after=[]
  for i in range(4):
   a=addr(i);after.extend([idx(struct.unpack('<I',uc.mem_read(a+0x88,4))[0]),*uc.mem_read(a+0x8c,2)])
  ret=uc.reg_read(UC_ARM_REG_R0)
  cases.append(dict(method=method,peer=peer,flag=flag,before=nodes,after=after,trace=trace,writes=writes,r0=ret))
lines=[]
for c in cases:
 vals=[c['method'],c['peer'],c['flag']]
 for n in c['before']:vals += [n['partner'],n['slave'],n['enabled'],n['query'],len(n['children'])]+n['children']
 vals+=c['after']+[c['r0'] if c['method']==4 else -1,len(c['trace'])]+c['trace']
 lines.append(' '.join(map(str,vals)))
(BASE/'fixtures.txt').write_text('\n'.join(lines)+'\n');(BASE/'native-observations.json').write_text(json.dumps(dict(elf_sha256=sha(ELF),ranges=ranges,cases=cases,oracle='Unicorn original ARM instructions; query/set/remove/master boundary hooks; no Core instructions executed'),indent=2)+'\n')
print(f'original ARM executions: {len(cases)}; 96 per target')

(BASE/'oracle-run.json').write_text(json.dumps({'start_utc':START,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seconds':time.monotonic()-T0,'argv':sys.argv,'executions':len(cases),'unicorn_version':__import__('unicorn').__version__},indent=2)+'\n')
