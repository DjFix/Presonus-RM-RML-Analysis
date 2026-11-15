"""Execute only exact original application ranges in isolated Unicorn memory.
All CCL/runtime calls are observed boundaries, never firmware provider execution.
"""
import hashlib,json,pathlib,struct,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_INTR,UC_HOOK_MEM_INVALID
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
CANONICAL=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis')
PACKETS=ROOT/'temp/recovery-work/compact-10x20-20261113/generated-implementation40/prepared03/packets'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
ELF=CANONICAL/'rootfs/CS18_v13840/home/root/surface'
O=0x1000000;PARAM=O+0x1000;ALIASES=O+0x2000;DATA=O+0x3000;OUT=O+0x5000;STACK=0x2000000;STOP=0x3000000
H=lambda b:hashlib.sha256(b).hexdigest()
def signed(x):return x-0x100000000 if x&0x80000000 else x

def generate(task):
 packet=PACKETS/task;req=json.loads((packet/'request.json').read_text());target=req['targets'][0];native=json.loads((packet/'native-context.json').read_text());root=native['roots'][0];body=native['bodies'][root]
 blob=ELF.read_bytes();assert H(blob)==SHA
 with ELF.open('rb') as f:
  e=ELFFile(f);sym=e.get_section_by_name('.symtab').get_symbol_by_name(target['mangled'])[0];sec=e.get_section(sym['st_shndx']);a=int(sym['st_value']);size=int(sym['st_size']);off=int(sec['sh_offset'])+a-int(sec['sh_addr']);segments=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
 assert (a,size,off,H(blob[off:off+size]))==(target['address'],target['size'],body['file_offset'],body['bytes_sha256'])
 boundaries={}
 for edge in native['edges']:
  if edge['src']==root and edge['kind'] in ('ELF_CALLS','ELF_TAIL_BRANCH'):
   n=native['nodes'][edge['dst']];boundaries[n['metadata']['address']]=n['label']
 tasknum=int(task.rsplit('_',1)[1]);cases=[]
 if tasknum==12:
  for index in [0,1,2,3,-1,-2,2147483647,-2147483648]:
   for prefix in [0,7,249,255]:cases.append({'kind':'url','index':index,'prefix_length':prefix})
 elif tasknum==4:
  for types in [[],[0],[1],[2],[3],[4],[0,1,2,3,4],[2,2,4,0,3],[1,1,0]]:cases.append({'kind':'disconnect','types':types})
 else:
  for n,m,count in ([(0,0,0),(1,0,0),(3,2,2),(6,5,4)] if tasknum<=5 else [(0,0,0),(0,0,1),(0,0,4)]):cases.append({'kind':'destructor','observed_count':n,'mappable_count':m,'alias_count':count})
 def execute(c):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000);u.mem_map(O,0x10000);u.mem_map(STACK,0x10000);u.mem_map(STOP,4096)
  for start,data in segments:u.mem_write(start,data)
  def w(addr,value):u.mem_write(addr,struct.pack('<I',value&0xffffffff))
  def r(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
  def ret(value=0):u.reg_write(UC_ARM_REG_R0,value&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  def text(addr):return bytes(u.mem_read(addr,64)).split(b'\0',1)[0].decode()
  pcs=[];trace=[];writes=[];removed=[];disconnected=[];released=set();base_calls=0;object_deleted=False;originals=[PARAM,0,PARAM+0x100]
  def vector(start,count,area):
   w(start+4,area if count else 0);w(start+8,count);w(start+12,count);w(start+16,5)
  def release_vector(addr):
   ptr=r(addr+4)
   if ptr:assert ptr not in released;released.add(ptr)
   w(addr+4,0);w(addr+8,0);w(addr+12,0)
  if c['kind']=='destructor':
   if tasknum<=5:
    n,m,ac=c['observed_count'],c['mappable_count'],c['alias_count'];vector(O+0xd4,n,DATA);vector(O+0xe8,m,DATA+0x200)
    for i in range(n):w(DATA+i*4,PARAM+(i%3)*0x100)
    for i in range(m):w(DATA+0x200+i*4,PARAM+(i%3)*0x100)
   else:ac=c['alias_count']
   vector(O+0xb4,ac,DATA+0x400)
   for i in range(ac):w(DATA+0x400+i*4,ALIASES+(i%3)*0x100)
  elif c['kind']=='disconnect':
   vector(O+0xe8,len(c['types']),DATA+0x200)
   for i,t in enumerate(c['types']):w(DATA+0x200+i*4,0 if t==0 else PARAM if t==1 else ALIASES+(t-2)*0x100)
  else:w(O+0xec,c['index'])
  def code(uc,pc,n,_):
   nonlocal base_calls,object_deleted
   if pc==STOP:uc.emu_stop();return
   regs=[uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
   if pc in boundaries:
    name=boundaries[pc];trace.append({'pc':pc,'name':name,'arguments':regs})
    if name.startswith('Core::Portable::Parameter::removeObserver'):
     assert regs[1]==O+4 and PARAM<=regs[0]<PARAM+0x300;removed.append((regs[0]-PARAM)//0x100);ret()
    elif name.startswith('Core::Vector<'):
     assert regs[0] in [O+0xb4,O+0xd4,O+0xe8]
     if 'resize' in name:assert regs[1]==0
     release_vector(regs[0]);ret()
    elif name.startswith('Core::Portable::Component::~Component'):
     assert regs[0]==O;base_calls+=1;ret()
    elif name.startswith('operator delete('):
     assert regs[0]==O and not object_deleted;object_deleted=True;ret()
    elif name.startswith('__dynamic_cast'):
     assert regs[1]==0x2053b0 and regs[2]==0x2052c8
     ptr=regs[0];ret(ptr if ALIASES<=ptr<ALIASES+0x300 else 0)
    elif name.startswith('Core::Portable::AliasParam::setOriginal'):
     assert ALIASES<=regs[0]<ALIASES+0x300 and regs[1]==0;idx=(regs[0]-ALIASES)//0x100;disconnected.append(idx);originals[idx]=0;ret()
    elif 'appendFormat' in name:
     assert regs[0]==OUT and text(regs[1])=='fx/ch%d';c['observed_format']=text(regs[1]);c['observed_argument']=signed(regs[2]);ret(OUT)
    else:raise AssertionError(('unexpected provider executed',hex(pc),name))
    return
   assert a<=pc<a+size,('Outside exact application target / provider allowlist',hex(pc));pcs.append(pc)
  def write(uc,access,addr,n,value,_):
   if O<=addr<O+0x400:writes.append([addr-O,n,value])
  def reject(*args):raise AssertionError('Guest syscall/interrupt/invalid memory access rejected')
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write);u.hook_add(UC_HOOK_INTR,reject);u.hook_add(UC_HOOK_MEM_INVALID,reject)
  for reg,value in [(UC_ARM_REG_R0,O),(UC_ARM_REG_R1,OUT),(UC_ARM_REG_SP,STACK+0xf000),(UC_ARM_REG_LR,STOP)]:u.reg_write(reg,value)
  u.emu_start(a,STOP+4,count=20000);assert u.reg_read(UC_ARM_REG_PC)==STOP
  if c['kind']=='destructor':expected=[len(removed),*removed,base_calls,int(object_deleted),len(released)]
  elif c['kind']=='disconnect':expected=[len(disconnected),*disconnected,*map(lambda x:int(bool(x)),originals)]
  else:expected={'argument':c['observed_argument'],'format':c['observed_format'],'returns_destination':u.reg_read(UC_ARM_REG_R0)==OUT}
  return dict(expected=expected,executed_pcs=pcs,external_calls=trace,object_writes=writes,native_object_delete_call_observed=object_deleted,scope='Application instructions executed; Core/runtime observed as explicit boundary models. No native Core execution or original allocator-internals claim.')
 for c in cases:c['observation']=execute(c)
 return {'version':1,'task_id':task,'elf_sha256':SHA,'ranges':[dict(target,file_offset=off,section_name=sec.name,range_sha256=H(blob[off:off+size]))],'cases':cases,'oracle_source_sha256':H(pathlib.Path(__file__).read_bytes()),'unicorn_version':__import__('unicorn').__version__,'isolation':'private mapped memory; allow exact app range and named observed providers only; interrupts/syscalls/invalid accesses reject'}
if __name__=='__main__':
 task=pathlib.Path(__file__).resolve().parent.name;path=ROOT/'uc-library/tests/recovery'/task/'fixtures.json';out=generate(task)
 if '--verify' in sys.argv:assert json.loads(path.read_text())==out
 else:path.write_text(json.dumps(out,indent=2)+'\n')
 print(task,len(out['cases']),'independent original executions')
