"""Bound original ARM instructions; Core/libc calls are explicit test boundaries.
No Core implementation is recovered. Hooks supply bounded observations for host
providers; app control flow, member writes, token/category selection and dispatch
are executed from the original ELF. Output fixtures never use reconstructed C++.
"""
import argparse, hashlib, json, pathlib, struct, time
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[5]
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
ADDR={'parse':0x851c4,'static':0x85600,'member':0x85764,'canDelete':0x84708,'cache':0x857d4,'rebuild':0x859b8,'category':0x85040,'observer':0x56ea8,'info':0x85bac,'file':0x85ae0}
def sha(b):return hashlib.sha256(b).hexdigest()
def signed(n):return n if n<0x80000000 else n-0x100000000
class Native:
 def __init__(self,case):
  self.case=case;self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);self.u.mem_map(0x8000,0x600000)
  with ELF.open('rb') as f:
   e=ELFFile(f)
   for s in e.iter_segments():
    if s['p_type']=='PT_LOAD':self.u.mem_write(s['p_vaddr'],s.data())
  self.u.mem_map(0x1000000,0x400000);self.u.mem_map(0x9000000,0x200000)
  self.heap=0x1010000;self.obj=0x1000000;self.trace=[];self.writes=[];self.events='';self.tok=0;self.iterindex=0
  self.entries=self.alloc(3*96);self.observers=self.alloc(128);self.cats=self.alloc(32*16)
  self.string(self.obj+4,'preset',64);self.string(self.obj+0x45,case['argv'][-1],256)
  self.word(self.obj+0x148,2);self.word(self.obj+0x150,self.observers);self.word(self.obj+0x154,2);self.word(self.obj+0x158,32)
  self.word(self.obj+0x164,self.entries);self.word(self.obj+0x16c,3)
  self.word(self.obj+0x178,self.cats);self.word(self.obj+0x17c,2);self.word(self.obj+0x180,16)
  for i in range(3):self.string(self.entries+96*i,'* Empty Location *',64)
  for i,t in enumerate(['Vocal','Drums']):self.string(self.cats+32*i,t,32)
  for i in range(2):
   d=self.alloc(4);v=self.alloc(8);self.word(d,v);self.word(v,0x1007000);self.word(v+4,0x1007004);self.word(self.observers+i*4,d)
  self.delegate_ids={self.readword(self.observers+i*4):i+1 for i in range(2)}
  self.bodyranges=[];self.hooks={}
  for n in range(1,11):
   j=json.loads((ROOT/f'temp/recovery-work/graph-live-trial-07/trial07_presetcache_{n}-packet/native-context.json').read_text())
   for b in j['bodies'].values():self.bodyranges.append((b['address'],b['address']+b['size']))
   for edge in j['edges']:
    if edge['kind']=='ELF_CALLS' and 'target_address' in edge['metadata']:
     node=j['nodes'].get(edge['dst'],{});label=node.get('label','')
     if label!='$a':self.hooks[edge['metadata']['target_address']]=label
  self.u.hook_add(UC_HOOK_CODE,self.hook)
  self.u.hook_add(UC_HOOK_MEM_WRITE,self.writehook)
 def alloc(self,size):
  p=self.heap;self.heap+=(size+15)//16*16;return p
 def word(self,p,n):self.u.mem_write(p,struct.pack('<I',n&0xffffffff))
 def readword(self,p):return struct.unpack('<I',self.u.mem_read(p,4))[0]
 def string(self,p,s,cap=None):
  b=s.encode() if isinstance(s,str) else s
  if cap:b=b[:cap-1]
  self.u.mem_write(p,b+b'\0')
 def text(self,p):
  if not p:return None
  b=bytearray()
  for i in range(16384):
   v=self.u.mem_read(p+i,1)
   if v==b'\0':return bytes(b).decode('utf8')
   b+=v
  raise RuntimeError('unterminated')
 def ptr(self,s):
  if s is None:return 0
  p=self.alloc(len(s.encode())+1);self.string(p,s);return p
 def writehook(self,u,access,address,size,value,data):
  if self.obj<=address<self.obj+0x184 or self.entries<=address<self.entries+288:
   self.writes.append([address-self.obj,size,value])
 def resize(self,obj,cap,stride):
  old=self.readword(obj+4);total=self.readword(obj+8);new=self.alloc(max(1,cap)*stride)
  if old:self.u.mem_write(new,bytes(self.u.mem_read(old,min(total,cap)*stride)))
  self.word(obj+4,new);self.word(obj+12,cap);return 1
 def hook(self,u,a,size,data):
  if a==0x1006000:u.emu_stop();return
  if any(lo<=a<hi for lo,hi in self.bodyranges):return
  r=[u.reg_read(x) for x in REGS];sp=u.reg_read(UC_ARM_REG_SP)
  label=self.hooks.get(a,'')
  self.trace.append({'address':a,'label':label,'args':r})
  ret=r[0]
  if a in (0x1007000,0x1007004):
   ident=self.delegate_ids[r[0]]
   if a==0x1007000:self.events+=f'change,{ident},{signed(r[2])},{hx(self.text(r[3]))},{hx(self.text(self.readword(sp)))};'
   else:self.events+=f'rebuild,{ident};'
  elif a==0xae98:ret=len(self.text(r[0]))
  elif a==0xaf70:
   x=self.text(r[0]);y=self.text(r[1]);ret=(x>y)-(x<y)
  elif a in (0xae68,0xafe8):self.u.mem_write(r[0],bytes(self.u.mem_read(r[1],r[2])))
  elif a==0xabe0:self.string(r[0],self.text(r[1]))
  elif a==0xae08:self.string(r[0],self.text(r[0])+self.text(r[1])[:r[2]])
  elif a==0xa9dc:
   p=r[0] or self.tok
   while p and self.u.mem_read(p,1)==b'.':p+=1
   if not p or self.u.mem_read(p,1)==b'\0':ret=0;self.tok=0
   else:
    ret=p
    while self.u.mem_read(p,1) not in (b'.',b'\0'):p+=1
    if self.u.mem_read(p,1)==b'.':self.u.mem_write(p,b'\0');self.tok=p+1
    else:self.tok=0
  elif a==0xafdc:
   import re
   m=re.match(r'\s*([+-]?\d+)',self.text(r[0]))
   if m:self.u.mem_write(r[2],struct.pack('<q',int(m[1])));ret=1
   else:ret=0
  elif a in (0xab14,):ret=self.alloc(r[0])
  elif a==0xad54:pass
  elif a in (0x1cf90,0x1debc,0x129ba4):
   cap={0x1cf90:64,0x1debc:32,0x129ba4:256}[a];self.string(r[0],self.text(r[1]) or '',cap)
  elif a in (0x39574,0x85fc4):self.string(r[0],self.text(r[0]).strip(' \t\r\n\v\f'))
  elif a==0x127acc:self.string(r[1],self.text(r[0]).rsplit('/',1)[-1],256)
  elif a==0x127bf0:
   self.string(r[0],''.join('_' if c in '?*/\\<>|:"\t\r\n' else c for c in self.text(r[0])))
  elif a==0x1289f4:
   s=self.text(r[0]);self.string(r[0],s+('' if s.endswith('/') else '/')+self.text(r[1]),256)
  elif a==0x12a68:
   fmt=self.text(r[1]);s=('%02d.%s.'%(signed(r[2]),self.text(r[3]))) if fmt=='%02d.%s.' else ('%s.'%self.text(r[2]))
   self.string(r[0],self.text(r[0])+s,256)
  elif a in (0x85d34,0x86364,0x56da8):ret=self.resize(r[0],r[1],32 if a==0x86364 else 4)
  elif a==0x85e34:pass
  elif a in (0x85cdc,0x38424):self.string(r[0],self.text(r[1]) or '',64 if a==0x85cdc else 32)
  elif a==0x129d4c:self.iterindex=0
  elif a==0x129bfc:
   files=self.case.get('files',[])
   if self.iterindex>=len(files):ret=0
   else:
    f=files[self.iterindex];self.iterindex+=1;ret=self.alloc(260)
    self.string(ret,self.case['argv'][-1]+'/'+f['name'],256)
    self.u.mem_write(ret+256,bytes([f.get('directory',False),f.get('hidden',False)]))
  elif a==0x127a24:pass
  else:raise RuntimeError(f'unhandled call {a:x} {label}')
  u.reg_write(UC_ARM_REG_R0,ret&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def call(self,op,args,stack=[]):
  for reg,val in zip(REGS,args):self.u.reg_write(reg,val&0xffffffff)
  sp=0x91ff000;self.u.reg_write(UC_ARM_REG_SP,sp);self.u.reg_write(UC_ARM_REG_LR,0x1006000)
  for i,v in enumerate(stack):self.word(sp+4*i,v)
  self.u.emu_start(ADDR[op],0,count=200000)
  if self.u.reg_read(UC_ARM_REG_PC)!=0x1006000:raise RuntimeError('execution did not return')
  return self.u.reg_read(UC_ARM_REG_R0)
 def run(self):
  op,slot,n,c,extra,full,path=self.case['argv'];slot=int(slot);full=int(full);n=None if n=='~' else n;c=None if c=='~' else c;extra=None if extra=='~' else extra
  result=-999;name=self.alloc(64);category=self.alloc(32);self.string(name,'unchanged');self.string(category,'unchanged');out=self.alloc(256);self.string(out,'')
  if op=='parse':
   name=self.alloc(64);category=self.alloc(32);s=self.alloc(4);self.word(s,slot)
   result=signed(self.call(op,[self.obj,self.ptr(n or ''),name,category],[s]));slot=signed(self.readword(s))
  elif op in ('static','member'):
   if op=='static':self.call(op,[out,slot,self.ptr(path),self.ptr('preset')],[self.ptr(n),self.ptr(c),self.ptr(extra),full])
   else:self.call(op,[out,self.obj,slot,self.ptr(n)],[self.ptr(c),self.ptr(extra),full])
  elif op=='canDelete':result=self.call(op,[self.obj,slot])
  elif op=='cache':self.call(op,[self.obj,self.ptr(n),self.ptr(c),slot])
  elif op=='category':self.call(op,[self.obj,self.ptr(n)])
  elif op=='observer':
   d=next((k for k,v in self.delegate_ids.items() if v==slot),0)
   if not d:d=self.alloc(4);self.delegate_ids[d]=slot
   self.call(op,[self.obj,d])
  elif op=='info':result=self.call(op,[self.obj,name,category,slot])
  elif op=='file':self.call(op,[out,self.obj,slot,full])
  elif op=='rebuild':
   self.u.mem_write(self.obj+0x145,b'\1');self.call(op,[self.obj]);self.call(op,[self.obj])
  lines=[f'result={result}',f'slot={slot}',f'name={hx(self.text(name))}',f'category={hx(self.text(category))}',f'path={hx(self.text(out))}',f'events={self.events}']
  entries=self.readword(self.obj+0x164)
  for i in range(3):lines.append('entry='+hx(self.text(entries+96*i))+','+hx(self.text(entries+96*i+64)))
  cats=self.readword(self.obj+0x178)
  for i in range(self.readword(self.obj+0x17c)):lines.append('cat='+hx(self.text(cats+32*i)))
  obs=self.readword(self.obj+0x150)
  for i in range(self.readword(self.obj+0x154)):lines.append('observer='+str(self.delegate_ids[self.readword(obs+4*i)]))
  return '\n'.join(lines)+'\n'
def hx(s):return 'null' if s is None else s.encode().hex()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);a=parser.parse_args()
 assert sha(ELF.read_bytes())==SHA
 checks=[]
 for n in range(1,11):
  j=json.loads((ROOT/f'temp/recovery-work/graph-live-trial-07/trial07_presetcache_{n}-packet/native-context.json').read_text())
  with ELF.open('rb') as f:
   elf=ELFFile(f)
   for ident,b in j['bodies'].items():
    sec=elf.get_section(b['section_index']);offset=sec['sh_offset']+b['address']-sec['sh_addr'];f.seek(offset);raw=f.read(b['size'])
    assert offset==b['file_offset'] and sha(raw)==b['bytes_sha256'];checks.append(dict(packet=n,identity=ident,**{k:v for k,v in b.items() if k in ('address','size','section','section_index','file_offset','bytes_sha256')}))
 cases=[]
 def add(op,slot=0,name='~',category='~',extra='~',full=0,files=None):
  cases.append({'argv':[op,str(slot),name,category,extra,str(full),'temp/recovery-work/graph-live-trial-07/presetcache-worker/replay-files'],'files':files or []})
 for s in [-3,0,1,2,3,100]:add('canDelete',s)
 for op in ['static','member']:
  for s,n,c,e,f in [(0,' Alpha ',' Vocal ','~',0),(9,'?A/B','Drums','sub',1),(-1,'','~','~',0),(100,'x'*90,'y'*50,'',1)]:add(op,s,n,c,e,f)
 for n in ['', '01.Alpha.preset','01.Alpha.Vocal.preset','02.a.b.Drums.preset','03.a.Other.preset','xx.Name.preset','-2.Name.preset','..01...a..Vocal..preset..','one.two','01.'+'x'*90+'.Vocal.preset']:add('parse',name=n)
 for s,n,c in [(-1,'a','b'),(3,'a','b'),(0,'Alpha','Vocal'),(1,'~','~'),(2,'* Empty Location *',''),(0,'x'*100,'y'*50)]:add('cache',s,n,c)
 for n in ['Vocal','New','x'*60,'~']:add('category',name=n)
 for s in [1,2,3,0]:add('observer',s)
 for s in [0,2,3]:add('info',s)
 for s in [0,2]:add('file',s,full=1)
 add('rebuild');add('rebuild',files=[{'name':'01.Alpha.Vocal.preset'}]);add('rebuild',files=[{'name':'02.Hidden.preset','hidden':True},{'name':'folder','directory':True}])
 for c in cases:
  native=Native(c);c['expected']=native.run();c['native_trace']=native.trace;c['native_writes']=native.writes
 pathlib.Path(a.out).write_text(json.dumps({'version':1,'elf_sha256':SHA,'range_checks':checks,'oracle':'original ARM instructions with explicit Core/libc/observer boundary hooks','cases':cases},indent=2)+'\n')
 print('native cases',len(cases))
if __name__=='__main__':main()
