"""Exact original ARM application oracle; Core boundaries use independent real-provider RPC."""
import pathlib,json,hashlib,struct,subprocess,itertools,datetime
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4];NAME=pathlib.Path(__file__).parent.name
NAMES=['rolling10_next_mixer_base_04','rolling10_typed_subgroup_01','rolling10_typed_digital_refresh_01','rolling10_next100_count_solos','rolling10_next100_set_channel_params','rolling10_next100_tdm_routes'];K=NAMES.index(NAME)+1
B=ROOT/'temp/recovery-work/rolling10x10-20261114/prepared-remaining14-phasea-proposed01';PACKET=B/'packets'/NAME
MAP=json.loads((ROOT/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared-remaining14-phasea-proposed01-rolling10_mixer_base.json').read_text());ELF=pathlib.Path(MAP['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path'])
SCRATCH=ROOT/'temp/recovery-work/phasea-mixer';PROVIDER=ROOT/'temp/recovery-work'/NAME/'provider';REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def fb(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def line(i):return ' '.join(map(str,[i['a'],i['b'],i['c'],i['d'],len(i['items']),*[x for it in i['items'] for x in it],i['name']]))
def inputs():
 def inp(a=0,b=0,c=0,d=1,items=(),name='!'):return dict(a=a,b=b,c=c,d=d,items=[list(x) for x in items],name=name)
 if K==1:
  return [inp(a=s,b=t,name=n) for s,t,n in itertools.product([0,1],range(5),['-','!','selch','alpha','beta','SELCH','selchx','xselch','é'])]
 if K==2:
  vals=[0.,-0.,-100.,-1.,-.25,-1e-20,1e-20,.125,1.,100.]
  return [inp(a=0,items=[(44,0,0)]),inp(a=1,items=[(44,0,0)])]+[inp(a=1,items=[(44,1,fb(v))]) for v in vals]
 if K==3:return [inp(items=[(t,1,fb(((t*7+s)%23-11)/8)) for t in range(1,12)]) for s in range(8)]
 if K==4:
  out=[]
  for count,selector,variant in itertools.product([0,1,2,6,9],[-2147483648,-1,0,1,4,7,2147483647],range(3)):
   out.append(inp(a=selector,items=[((j+variant)%5,int((j+variant)%4!=0),fb([-1.,-.25,-0.,0.,1e-20,.5,1.][(j*3+variant)%7])) for j in range(count)]))
  return out
 if K==5:
  return [inp(a=tag,b=fb(value),items=[((tag if j%3!=1 else tag+1),int((j+variant)%4!=0),fb(((j+variant)%5-2)/2)) for j in range(count)]) for count,tag,value,variant in itertools.product([0,1,2,7],[-1,0,5,1001],[-120.,-1.,-.25,-0.,0.,.5,1.,120.],range(2))]
 out=[]
 for count,config,selector in itertools.product([0,1,2,7,16],[0,2,0x7ffffffe,0x7fffffff,0x80000000,0xffffffff],[-2147483648,-3,-1,0,1,2,3,4,7,8,9,10,11,12,16,24,100,2147483647]):out.append(inp(a=selector,b=config,c=137,items=[(0,0,0)]*count))
 out += [inp(a=5,b=0,c=v,items=[]) for v in range(256)] # native table case verified after execution, not expected-output model
 return out
class Provider:
 def __init__(self,i):
  self.p=subprocess.Popen([str(PROVIDER),'--provider'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  self.p.stdin.write(line(i)+'\n');self.p.stdin.flush();s=self.p.stdout.readline().split();assert s and s[0]=='READY',s;self.count=int(s[1]);self.ops=[]
 def ask(self,s):
  self.p.stdin.write(s+'\n');self.p.stdin.flush();r=self.p.stdout.readline().strip();assert r,(s,self.p.poll());self.ops.append([s,r]);return r
 def close(self):
  self.p.stdin.write('done\n');self.p.stdin.close();assert self.p.wait(timeout=10)==0,self.p.stderr.read()
def generate():
 from elftools.elf.elffile import ELFFile
 raw=ELF.read_bytes();target=json.loads((PACKET/'request.json').read_text())['targets'][0];assert hashlib.sha256(raw).hexdigest()==target['original_elf_sha256']
 with ELF.open('rb') as stream:
  e=ELFFile(stream);section=e.get_section(target['section']);off=section['sh_offset']+target['address']-section['sh_addr'];body=raw[off:off+target['size']];segments=[(int(s['p_vaddr']),s.data(),int(s['p_memsz'])) for s in e.iter_segments() if s['p_type']=='PT_LOAD'];sym=e.get_section_by_name('.symtab');rows=list(sym.iter_symbols());symbol=next(s for s in rows if s.name==target['mangled']);assert symbol['st_value']==target['address'] and symbol['st_size']==target['size']
 ranges=[dict(mangled=target['mangled'],address=target['address'],size=target['size'],section=section.name,file_offset=off,sha256=hashlib.sha256(body).hexdigest())]
 allowed=[(target['address'],target['address']+target['size'])]
 if K in (2,4):
  ev=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-remaining14-phasea-proposed01')/'snapshot/temp/recovery-work/rolling10x10-20261114/selection/typed-getters01/b5abe743557b8938b83f1cac99e8fbd60606b81b3b5330db9d20890e767c5272.json';helpers=json.loads(ev.read_text())['original_nonCore_helper_closure']
  for h in helpers.values():
   bd=h['body'];by=raw[bd['file_offset']:bd['file_offset']+bd['size']];assert hashlib.sha256(by).hexdigest()==bd['bytes_sha256'];ranges.append(dict(mangled=h['identity']['mangled'],address=bd['address'],size=bd['size'],section=bd['section'],file_offset=bd['file_offset'],sha256=bd['bytes_sha256']));allowed.append((bd['address'],bd['address']+bd['size']))
 cases=[];all_inputs=inputs();extra=[]
 for ix,i in enumerate(all_inputs):
  provider=Provider(i);u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for addr,data,size in segments:
   lo=addr&~4095;hi=(addr+size+4095)&~4095;u.mem_map(lo,hi-lo);u.mem_write(addr,data)
  u.mem_map(0x40000000,0x40000);u.mem_map(0x50000000,0x10000);u.mem_map(0x60000000,0x4000)
  this=0x40000000;vec=this+0x1000;out=this+0x2000;params=this+0x4000;vtable=this+0x6000;channel=this+0x8000;trace=[];writes=[];route_reads=[];visited=set()
  def put(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
  def reg(n):return u.reg_read(REGS[n])
  def ret(v=0):u.reg_write(UC_ARM_REG_R0,v&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  def idparam(ptr):assert params<=ptr<params+0x1000 and (ptr-params)%0x100==0;return (ptr-params)//0x100+1
  for j,it in enumerate(i['items']):
   ptr=params+j*0x100;put(ptr,vtable);put(vec+j*4,channel+j*0x200);put(channel+j*0x200+0x16c,it[0]);put(channel+j*0x200+0xf8,ptr if it[1] else 0)
  put(vtable+0x44,0x60001000);put(vtable+0x1c,0x60002000);put(vtable+0x58,0x60003000)
  put(this+0x120,vec);put(this+0x124,provider.count);put(this+0x174,provider.count);put(this+0x19c,i['b']);put(this+0x2dc,0 if i['a']==0 else this+0x3000);put(this+0x2d8,this+0x3000);put(this+0x310,0x40030000 if i['a'] else 0)
  put(this+0x1fc,this+0x2800 if i['d'] else 0x70000000);put(this+0x2800,this+0x2a00);u.mem_write(this+0x2a00+0x234,bytes([i['c']&255]));u.mem_write(out,b'\xa5\x5a\xcc\xcc'+struct.pack('<I',0xdeadbeef))
  nameptr=0 if i['name']=='-' else this+0x2400
  if nameptr:u.mem_write(nameptr,('' if i['name']=='!' else i['name']).encode()+b'\0')
  sp=0x50008000;put(sp,out+4);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_FP,0x12345678);u.reg_write(UC_ARM_REG_LR,0x60000000);u.reg_write(UC_ARM_REG_R0,this)
  u.reg_write(UC_ARM_REG_R1,nameptr if K==1 else i['a']&0xffffffff);u.reg_write(UC_ARM_REG_R2,out if K==6 else i['b']);u.reg_write(UC_ARM_REG_R3,out+1)
  def code(uc,a,size,data):
   if a==0x60000000:uc.emu_stop();return
   if a==0xaf70:
    assert K==1;v=int(provider.ask('cmp'));trace.append(['strcmp',i['name'],'selch',v]);ret(v);return
   if a==0x119bcc:
    assert K==1;v=int(provider.ask('find'));trace.append(['findChild',i['name'],v]);ret(0 if not v else 0x40031000+v*0x100);return
   if a==0x119c4c:
    receiver=0 if K in (2,3) else (reg(0)-channel)//0x200+1;tag=reg(1);tag=tag if tag<0x80000000 else tag-0x100000000;v=int(provider.ask(f'lookup {receiver} {tag}'));trace.append(['lookup',receiver,tag,v]);ret(params+(v-1)*0x100 if v else 0);return
   if a==0x60001000:
    identity=idparam(reg(0));v=int(provider.ask(f'get {identity}'));trace.append(['getValue',identity,v]);ret(v);return
   if a==0x60002000:
    identity=idparam(reg(0));provider.ask(f'edit {identity}');trace.append(['performEdit',identity]);ret();return
   if a==0x60003000:
    identity=idparam(reg(0));v=reg(1);edit=reg(2);provider.ask(f'set {identity} {v} {edit}');trace.append(['setValue',identity,v,edit]);ret();return
   assert any(lo<=a<hi for lo,hi in allowed),hex(a);visited.add(a)
  def write(uc,access,a,size,value,data):
   if not 0x50000000<=a<0x50010000:writes.append([a-this,size,value])
  def read(uc,access,a,size,value,data):
   if a in [this+0x1fc,this+0x2800,this+0x2a00+0x234]:route_reads.append([a-this,size])
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write);u.hook_add(UC_HOOK_MEM_READ,read);u.emu_start(target['address'],0,count=10000);assert u.reg_read(UC_ARM_REG_PC)==0x60000000;assert u.reg_read(UC_ARM_REG_SP)==sp;assert u.reg_read(UC_ARM_REG_FP)==0x12345678
  result=u.reg_read(UC_ARM_REG_R0)
  if K==1:
   if result==0x40030000:result=99
   elif result:result=(result-0x40031000)//0x100
   expected=str(result)
  elif K in (2,4):expected=str(result)
  elif K in (3,5):expected=provider.ask('snapshot')
  else:
   first,second=bytes(u.mem_read(out,2));count=struct.unpack('<I',u.mem_read(out+4,4))[0];expected=f'{first} {second} {count} {provider.count}'
  provider.close();cases.append(dict(input=i,expected=expected,trace=trace,provider_operations=provider.ops,writes=writes,route_reads=route_reads,visited=sorted(visited)))
  if K==6 and i['d'] and not route_reads and ix%29==0:extra.append({**i,'d':0})
  if ix==len(all_inputs)-1 and extra:all_inputs.extend(extra);extra=[]
 return dict(version=1,task_id=NAME,elf_sha256=target['original_elf_sha256'],ranges=ranges,cases=cases,scope='Exact original ARM target plus individually verified non-Core comparison aliases. Only actual separately executed pinned CCL/libc provider observations bridge Core/libc boundaries; no original Core execution. Stable borrowed objects, finite values, distinct output references; no original return/layout/ABI or hardware claim.')
if __name__=='__main__':
 f=generate();p=ROOT/'uc-library/tests/recovery'/NAME/'fixtures.json';p.write_text(json.dumps(f,indent=2,ensure_ascii=False)+'\n');print(NAME,len(f['cases']))
