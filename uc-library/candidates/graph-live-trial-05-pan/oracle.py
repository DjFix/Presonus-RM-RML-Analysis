import json, hashlib, struct, re, datetime, os
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
BASE=Path('uc-library/candidates/graph-live-trial-05-pan')
ELF=Path('rootfs/CS18_v13840/home/root/surface')
sha=lambda b:hashlib.sha256(b).hexdigest()
u32=lambda x:struct.pack('<I',x&0xffffffff)
f32=lambda b:struct.unpack('<f',u32(b))[0]
fb=lambda f:struct.unpack('<I',struct.pack('<f',f))[0]
raw=ELF.read_bytes(); assert sha(raw)=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
ranges=[]
with ELF.open('rb') as f:
 e=ELFFile(f); segs=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']; sec=e.get_section(12)
 for i in range(1,6):
  packet=Path(f'temp/recovery-work/graph-live-trial-05/trial05_pan_{i}-packet')
  ctx=json.loads((packet/'context.json').read_text()); task=json.loads((packet/'task.json').read_text()) if (packet/'task.json').exists() else None
  text=(packet/'ELF_CONTEXT.md').read_text(); m=re.search(r'original `([^`]+)`; address `0x([0-9a-f]+)`; size (\d+); section ([^;]+); SHA256 `([^`]+)`',text)
  name,addr,size,section,h=m.groups();addr=int(addr,16);size=int(size);off=sec['sh_offset']+addr-sec['sh_addr']; assert sha(raw[off:off+size])==h
  ranges.append(dict(task_id=ctx['task_id'],mangled=name,address=addr,size=size,section=section,file_offset=off,sha256=h,elf_sha256=sha(raw),firmware='CS18AI surface 13840',role='client'))

def run(kind, bits=0, present=True,label='', explicit=None, fallback=0, msg=0, fields=None, changed=0):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM); u.mem_map(0,0x280000)
 for a,b in segs:u.mem_write(a,b)
 u.mem_map(0x300000,0x30000);u.mem_map(0x400000,0x10000)
 obj=0x300000;p=0x301000;vt=0x302000;stack=0x408000;stop=0x320000
 def w(a,x):u.mem_write(a,u32(x))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 for off in [0x64,0x68,0x6c,0x70,0x74]:w(obj+off,0)
 w(p,vt);w(vt+0x44,0x310000);w(vt+0x70,0x310004);w(vt+0xc,0x310008)
 if kind in [1,2]:w(obj+(0x68 if kind==1 else 0x64),p if present else 0)
 if kind in [3,5]:
  w(obj+0x6c,p if present else 0)
  if explicit is not None:w(obj+0x70,p)
 if kind==4:
  for off,val in zip([0x68,0x64,0x6c,0x70,0x74],fields):w(obj+off,val)
 trace=[]
 def ret(v=None):
  if v is not None:u.reg_write(UC_ARM_REG_R0,v&0xffffffff)
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def hook(u,a,size,_):
  if a==stop:u.emu_stop();return
  rr=lambda n:u.reg_read([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3][n])
  if a==0x310000:trace.append('value');ret(explicit if explicit is not None else bits)
  elif a==0x310004:
   trace.append('string');u.mem_write(rr(1),label.encode()[:63]+b'\0');ret()
  elif a==0x310008:trace.append('original');ret(p if fallback else 0)
  elif a==0x11e1d0:trace.append('controller');ret(0)
  elif a==0xb02c:trace.append('strlen');ret(len(label))
  elif a==0xb164:
   trace.append('parse');m=re.match(r'\s*([+-]?\d+)',label)
   if m:
    n=int(m.group(1));n=max(-(1<<63),min((1<<63)-1,n));u.mem_write(rr(2),struct.pack('<q',n));ret(1)
   else:ret(0)
  elif a==0x10e9fc:trace.append('invalidate');ret()
  elif a==0xf8768:trace.append('base:'+str(rr(2)));ret()
  elif not (any(t['address']<=a<t['address']+t['size'] for t in ranges) or 0x187000<=a<0x188000):
   raise RuntimeError(f'unexpected execution {a:x}')
 u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,bits if kind==3 else changed);u.reg_write(UC_ARM_REG_R2,msg)
 target=ranges[kind-1]['address'];u.emu_start(target,stop,count=20000)
 assert u.reg_read(UC_ARM_REG_PC)==stop,hex(u.reg_read(UC_ARM_REG_PC))
 return dict(result=u.reg_read(UC_ARM_REG_R0),trace=trace,fields=[r(obj+o) for o in [0x68,0x64,0x6c,0x70,0x74]])
cases=[]
for kind in [1,2]:
 for present in [False,True]:
  for bits in [0,0x80000000,fb(1),fb(-1),0x7f800000,0xff800000,0x7fc00000,1]:
   inp=dict(kind=kind,bits=bits,present=present);cases.append(dict(input=inp,output=run(**inp)))
for present,label,explicit in [(False,'',None),(True,'',None),(True,'1',None),(True,'2',None),(True,'-3',None),(True,'-4',None),(True,'  +12tail',None),(True,'name',None),(True,'0',None),(True,'9223372036854775807',None),(True,'-9223372036854775808',None)]+[(True,'ignored',v) for v in [0,0x80000000,fb(1),fb(-1),0x7fc00000]]:
 for kind in [5,3]:
  for bits in ([fb(x) for x in [-2,-1,-0.0,0,0.25,0.5,1,2]] if kind==3 else [0]):
   inp=dict(kind=kind,bits=bits,present=present,label=label,explicit=explicit);cases.append(dict(input=inp,output=run(**inp)))
for kind in [3,5]:
 for bits in ([fb(x) for x in [-1,0,0.5,1,2]] if kind==3 else [0]):
  inp=dict(kind=kind,bits=bits,present=True,label='name',fallback=1);cases.append(dict(input=inp,output=run(**inp)))
for msg in [-1,0,3,4,5,99]:
 for fields in [[1,2,3,4,5],[7,7,7,7,7],[0,2,0,4,0]]:
  for changed in [0,1,2,3,4,5,7,9]:
   inp=dict(kind=4,msg=msg,fields=fields,changed=changed);cases.append(dict(input=inp,output=run(**inp)))
(BASE/'native.json').write_text(json.dumps(dict(ranges=ranges,cases=cases,producer=sha(Path(__file__).read_bytes()),unicorn=__import__('unicorn').__version__,limitations=['Core/libc boundary stubs recorded; no Core binary execution','Label fallback observer null path only pending app context','soft float helpers execute original ELF instructions']),indent=2)+'\n')
print('original ARM cases',len(cases))
