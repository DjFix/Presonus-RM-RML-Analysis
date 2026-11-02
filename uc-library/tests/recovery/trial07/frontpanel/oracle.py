#!/usr/bin/env python3
"""Execute original RM13731 ARM methods only; intercept external/provider boundaries.
No firmware/hardware operations are performed. Core implementation is excluded.
"""
import argparse,hashlib,json,math,struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_PC,UC_ARM_REG_LR,UC_ARM_REG_SP
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[5]
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
ELF_HASH='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
BASE=0x1000000;MODEL=BASE+0x1000;SETTINGS=BASE+0x2000;VT=BASE+0x3000;ARRAY=BASE+0x4000;CHARRAY=BASE+0x5000;NAME=BASE+0x6000;COPY=BASE+0x7000;PARAM=0x1100000;CHANNEL=0x1120000;HOOK=0x1200000;STOP=HOOK+0xff00
ADDRESSES={1:0x62e14,2:0x63a24,3:0x683f8,4:0x67550,5:0x64d54,6:0x687b8,7:0x6741c,8:0x67488,9:0x66030,10:0x68550}
def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def flt(x):return struct.unpack('<f',struct.pack('<I',x))[0]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def packet(i):return ROOT/f'temp/recovery-work/graph-live-trial-07/trial07_frontpanel_{i}-packet'
def verify():
 assert sha(ELF)==ELF_HASH
 with ELF.open('rb') as f:
  elf=ELFFile(f); result=[]
  for i in range(1,11):
   c=json.loads((packet(i)/'context.json').read_text());n=json.loads((packet(i)/'native-context.json').read_text());body=next(iter(n['bodies'].values()));o=c['originals'][0]['original'];section=elf.get_section(int(o['section_json']));off=section['sh_offset']+o['address']-section['sh_addr'];f.seek(off);h=hashlib.sha256(f.read(o['size'])).hexdigest();assert h==body['bytes_sha256'];assert off==body['file_offset'];result.append(dict(task=c['task_id'],mangled=o['mangled'],address=o['address'],size=o['size'],section=section.name,file_offset=off,bytes_sha256=h))
 return result
class Oracle:
 def __init__(self,case):
  self.c=case;self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);self.trace=[];self.calls=[];self.writes=[];self.params={};self.allowed=[];self.executed=set()
  # A single mapped image includes zero-initialized bss. Core bodies cannot run.
  self.u.mem_map(0x8000,0x800000)
  with ELF.open('rb') as f:
   e=ELFFile(f)
   for s in e.iter_segments():
    if s['p_type']=='PT_LOAD':self.u.mem_write(s['p_vaddr'],s.data())
  self.u.mem_map(BASE,0x300000);self.u.mem_map(0x2000000,0x20000)
  self.w(BASE+0x8c,MODEL);self.w(MODEL+0x2dc,SETTINGS);self.w(BASE,VT);self.w(BASE+0x90,BASE+0x8000);self.w(BASE+0x100,BASE+0x9000)
  self.w(BASE+0x158,case['active']);self.w(BASE+0x1b8,case['held']);self.w(BASE+0x120,ARRAY);self.w(BASE+0x124,len(case['selections']));self.w(MODEL+0x120,CHARRAY);self.w(MODEL+0x124,len(case['channels']))
  for slot,hook in [(0x44,HOOK+0x44),(0x4c,HOOK+0x4c),(0x50,HOOK+0x50),(0x58,HOOK+0x58),(0x20,HOOK+0x20),(0x6c,HOOK+0x6c),(0x70,HOOK+0x70)]:self.w(VT+slot,hook)
  for tag,value in case['params'].items():self.makeparam(int(tag),value)
  for i,value in enumerate(case['selections']):self.w(ARRAY+4*i,self.makeparam(100+i,value))
  for i,present in enumerate(case['channels']):
   address=CHANNEL+0x100*i;self.w(address,VT);self.w(CHARRAY+i*4,address if present else 0)
  self.u.mem_write(NAME,case['page'].encode()+b'\0')
  for i in range(1,11):
   b=next(iter(json.loads((packet(i)/'native-context.json').read_text())['bodies'].values()));self.allowed.append((b['address'],b['address']+b['size']))
  self.u.hook_add(UC_HOOK_CODE,self.code);self.u.hook_add(UC_HOOK_MEM_WRITE,self.write)
 def makeparam(self,tag,value):
  addr=PARAM+tag*0x100;self.w(addr,VT);self.params[addr]={'tag':tag,'value':value,'min':bits(-100),'max':bits(100)};return addr
 def w(self,addr,value):self.u.mem_write(addr,struct.pack('<I',value&0xffffffff))
 def r(self,addr):return struct.unpack('<I',self.u.mem_read(addr,4))[0]
 def string(self,addr):
  data=bytearray()
  while True:
   b=self.u.mem_read(addr+len(data),1)
   if b==b'\0':return data.decode()
   data+=b
 def event(self,*args):self.trace.append(' '.join(map(str,args)))
 def ret(self,value=None):
  if value is not None:self.u.reg_write(UC_ARM_REG_R0,value&0xffffffff)
  self.u.reg_write(UC_ARM_REG_PC,self.u.reg_read(UC_ARM_REG_LR))
 def write(self,u,access,address,size,value,user):
  if BASE<=address<BASE+0x400 or 0x494000<=address<0x495000:self.writes.append([address,size,value])
 def code(self,u,pc,size,user):
  if pc==STOP:u.emu_stop();return
  if any(a<=pc<b for a,b in self.allowed):self.executed.add(pc);return
  a=u.reg_read(UC_ARM_REG_R0);b=u.reg_read(UC_ARM_REG_R1);c=u.reg_read(UC_ARM_REG_R2)
  self.calls.append([pc,a,b,c])
  if pc in [0xb030,0xaa3c]:
   if pc==0xaa3c:self.w(a,1)
   self.ret(1);return
  if pc==0x119c4c:self.ret(PARAM+b*0x100 if str(b) in self.c['params'] else 0);return
  if pc==0x157940:self.ret(int(flt(a)>flt(b)));return
  if pc==0x1578e0:self.ret(int(flt(a)==flt(b)));return
  if pc==0x157958:self.ret(int(flt(a)));return
  if pc==HOOK+0x44:
   p=self.params[a];self.event('@G',p['tag'],p['value']);self.ret(p['value']);return
  if pc in [HOOK+0x4c,HOOK+0x50,HOOK+0x58]:
   p=self.params[a];kind={HOOK+0x4c:'min',HOOK+0x50:'max',HOOK+0x58:'value'}[pc];self.event({'min':'@N','max':'@M','value':'@V'}[kind],p['tag'],b,*([c] if kind=='value' else []));p[kind]=b
   # CCL NumericParam setter contract. Inputs avoid clipping except toggles.
   if kind=='value':p[kind]=bits(min(max(flt(b),flt(p['min'])),flt(p['max'])))
   elif (kind=='min' and flt(p['value'])<flt(b)) or (kind=='max' and flt(p['value'])>flt(b)):
    self.event('@V',p['tag'],b,0);p['value']=b
   self.ret();return
  if pc in [0x11697c,0x116a38]:self.ret();return
  if pc==0x66668:self.event('@F',self.c['faders']);self.ret(self.c['faders']);return
  if pc==0x8c668:self.event('@T',self.c['long']);self.ret(self.c['long']);return
  if pc==0x8e4ac:assert b==12;self.ret(BASE+0xa000);return
  if pc==0x96274:self.ret(BASE+0xb000);return
  if pc==0x980c8:self.event('@A',self.c['page_exists']);self.ret(BASE+0xc000 if self.c['page_exists'] else 0);return
  if pc==0x97894:self.ret(NAME);return
  if pc==0x1cf90:self.u.mem_write(a,self.string(b).encode()[:63]+b'\0');self.ret(a);return
  if pc==0xaf70:self.ret(0 if self.string(a)==self.string(b) else 1);return
  if pc==HOOK+0x20:
   flag=self.string(b);assert flag=='ignoreAltMemory';assert self.r(b+0x30)==BASE+0x144
   self.event('@X',(a-CHANNEL)//0x100+1,1,flag);self.ret();return
  events={0x62cc8:(0,0,0),0x631e4:(1,0,0),0x8c7f8:(2,0,0),0x52624:(3,12,0),0x667e0:(4,b,0),0x63f38:(5,b,0),0x65a9c:(6,b,0),0x524e0:(7,0,0),HOOK+0x6c:(8,0,0),0x64fa4:(9,0,0),0x641cc:(10,b,0),0x62a00:(11,b,0),0x52764:(12,b,c),HOOK+0x70:(13,0,0)}
  if pc in events:self.event('@E',*events[pc]);self.ret();return
  raise RuntimeError(f'Unapproved instruction boundary {pc:x}, args {a:x} {b:x} {c:x}')
 def run(self):
  for op,a,b in self.c['ops']:
   self.u.reg_write(UC_ARM_REG_SP,0x201f000);self.u.reg_write(UC_ARM_REG_LR,STOP)
   for reg,val in [(UC_ARM_REG_R0,BASE),(UC_ARM_REG_R1,a),(UC_ARM_REG_R2,b)]:self.u.reg_write(reg,val&0xffffffff)
   self.u.emu_start(ADDRESSES[op],STOP,count=50000)
   assert self.u.reg_read(UC_ARM_REG_PC)==STOP,'instruction budget exhausted'
   if op in [4,9]:self.event('@R',self.u.reg_read(UC_ARM_REG_R0))
  held=self.r(BASE+0x1b8);self.event('@H',held if held<2**31 else held-2**32)
  for p in self.params.values():
   if p['tag']<100:self.event('@P',p['tag'],p['value'],p['min'],p['max'])
  return {'expected':self.trace,'native_calls':self.calls,'native_writes':self.writes,'passcode_cursor':self.r(4802516),'executed_target_pcs':sorted(self.executed)}
def cases():
 default={str(t):bits(v) for t,v in [(30,1),(31,1),(32,2),(33,3),(34,4),(35,5),(36,0),(37,0),(38,0.25),(39,0.5),(40,1)]}
 def c(name,ops,**changes):
  x={'name':name,'held':7,'active':1,'long':0,'faders':0,'page_exists':1,'page':'System_SysLock','params':default.copy(),'selections':[],'channels':[],'ops':ops};x.update(changes);return x
 result=[]
 for active in [0,1]:
  for selections in [[],[0],[1],[1,-1,0,0.5],[0.5,1,1]]:
   for channels in [[],[1],[0,1,1],[1,0,1,1]]:result.append(c(f'paste-{len(result)}',[[1,0,0]],active=active,selections=list(map(bits,selections)),channels=channels))
 for lock in [0,1,-1,0.5]:
  for master in [0,1,-1,0.25]:
   params=default.copy();params.update({'36':bits(lock),'37':bits(master)})
   for op in [4,9,10]:result.append(c(f'locks-{len(result)}',[[op,0,0]],params=params))
 for op in [4,6,9,10]:
  for absent in ([36],[37] if op==4 else [30]):
   params=default.copy()
   for t in absent:params.pop(str(t))
   result.append(c(f'missing-{len(result)}',[[op,0,0]],params=params))
 for group in [-1,0,3,4,5]:
  for button in [-1,7,8]:
   for duration in [0,1]:result.append(c(f'button-{len(result)}',[[5,group,button]],long=duration))
 for faders in [0,1]:
  result += [c(f'update-{faders}',[[3,0,0]],faders=faders),c(f'lockfaders-{faders}',[[7,faders,0]])]
 result.append(c('activate',[[8,0,0]]))
 for seq in [[0,1,2,3,4],[0,0,1,2,3,4],[0,9,0,1,2,3,4],[-1,0,1,2,3,4],[0,1,2,3,4,0,1,2,3,4],[2147483647,0,1,2,3,4]]:
  for locked in [0,1]:
   params=default.copy();params['36']=bits(locked);result.append(c(f'code-{len(result)}',[[2,d,0] for d in seq],params=params))
 for page in ['System_SysLock','Other','System_SysLockSuffix','a'*80]:
  for exists in [0,1]:
   for enabled in [0,1,-1]:
    params=default.copy();params['30']=bits(enabled);result.append(c(f'check-{len(result)}',[[6,d,0] for d in [0,1,2,3,4,9]],params=params,page=page,page_exists=exists))

 for absent in [31,36]:
  params=default.copy();params.pop(str(absent));result.append(c(f'code-missing-{absent}',[[2,d,0] for d in [0,1,9,0]],params=params))
 for value in [0,1.5,-1]:
  params=default.copy();params.update({str(t):bits(value) for t in range(31,36)});digit=int(value)-1;result.append(c(f'code-conversion-{value}',[[2,digit,0]]*5,params=params))
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();ranges=verify();rows=[]
 for case in cases():
  try:rows.append({'input':case,**Oracle(case).run()})
  except Exception:print('CASE',case,file=sys.stderr);raise
 a.out.write_text(json.dumps({'version':1,'producer_sha256':sha(Path(__file__)),'elf_sha256':ELF_HASH,'ranges':ranges,'cases':rows},indent=2)+'\n');print(f'original ARM executions captured: {len(rows)} scenarios')
