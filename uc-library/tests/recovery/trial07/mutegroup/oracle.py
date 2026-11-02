#!/usr/bin/env python3
"""Execute only sealed application ARM bodies. Explicit boundary stubs are not Core recovery."""
import argparse,hashlib,json,struct,io,math,itertools,multiprocessing,os,time,datetime,copy
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[5]
ELF='rootfs/RML16AI_Rack_13731/home/root/mixer'
HASH='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
BASE=0x1000000; SELF=BASE; GROUPS=BASE+0x1000; PARAMS=BASE+0x8000; ARR=BASE+0x20000; VT=BASE+0x30000; STOP=BASE+0x40000; STUB=BASE+0x41000; REMOTE=BASE+0x42000; MIX=BASE+0x43000; OBS=BASE+0x44000; MSG=BASE+0x45000; TIMERS=BASE+0x46000

def specs():
 out=[]
 for i in range(1,11):
  p=ROOT/f'temp/recovery-work/graph-live-trial-07/trial07_mutegroup_{i}-packet';d=json.loads((p/'context.json').read_text());o=d['originals'][0]['original'];out.append(o)
 return out

def run(case,raw,sp):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);e=ELFFile(io.BytesIO(raw));mapped=set()
 for seg in e.iter_segments():
  if seg['p_type']!='PT_LOAD':continue
  a=seg['p_vaddr'];n=seg['p_memsz'];lo=a&~4095;hi=(a+n+4095)&~4095
  for p in range(lo,hi,4096):
   if p not in mapped:u.mem_map(p,4096);mapped.add(p)
  u.mem_write(a,seg.data())
 u.mem_map(BASE,0x100000);u.mem_map(BASE+0x200000,0x20000)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def b(a,v):u.mem_write(a,bytes([v]))
 def floats(v):return struct.unpack('<I',struct.pack('<f',v))[0]
 def fval(v):return struct.unpack('<f',struct.pack('<I',v))[0]
 def ps(i):return PARAMS+i*0x100
 def gi(a):return (a-GROUPS)//0x200
 def pi(a):return (a-PARAMS)//0x100
 def array(a,values):
  for i,v in enumerate(values):w(a+i*4,v)
 def vector(obj,offset,values,storage):w(obj+offset,storage);w(obj+offset+4,len(values));array(storage,values)
 trace=[];debug=[];values=case['values'][:];members=[[0,1],[1,2],[3]];unassigned=case['loose'][:]
 for i,v in enumerate(values):
  a=ps(i);w(a,VT);w(a+0xc,a+0x40);w(a+0x44,case['tag'] if i==case['param'] else i);u.mem_write(a+0x48,(case['name'] if i==case['param'] else 'p').encode()+b'\0')
 for i in range(3):
  a=GROUPS+i*0x200;w(a,VT+0x100);vector(a,0x14,[ps(j) for j in members[i]],ARR+0x100+i*0x100);b(a+0xac,case['busy']);b(a+0xad,case['stored']);w(a+4,0);w(a+0xc,ps(9+i) if case['old_remote'] else 0)
 vector(SELF,0xa0,[GROUPS+i*0x200 for i in range(3)],ARR)
 vector(SELF,0xb8,[ps(i) for i in unassigned],ARR+0x1000)
 vector(SELF,0xcc,[ps(i) for i in case['delayed']],ARR+0x1100)
 vector(SELF,0x8c,[TIMERS+i*0x100 if flag else 0 for i,flag in enumerate(case['timer_present'])],ARR+0x1200)
 w(SELF+0xb0,GROUPS+2*0x200 if case['all_group'] else 0);w(SELF+0xdc,MIX);w(SELF+0xe0,OBS if case['observer'] else 0);b(SELF+0x85,case['enabled']);b(SELF+0xe4,case['recalling'])
 vector(MIX,0x2c4,[ps(0),0,ps(2),ps(3)],ARR+0x1300)
 w(REMOTE,VT+0x200);w(OBS,VT+0x300)
 for x in [0x493968]:w(x,1)
 for off,target in [(0x44,STUB),(0x58,STUB+4)]:w(VT+off,target)
 for off,target in [(8,STUB+8),(0x10,STUB+12)]:w(VT+0x100+off,target)
 w(VT+0x200+0x14,STUB+16);w(VT+0x300,STUB+20);w(VT+0x300+4,STUB+24)
 def ret(v=None):
  if v is not None:u.reg_write(UC_ARM_REG_R0,v&0xffffffff)
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def cstr(a):
  out=bytearray()
  while a and len(out)<500:
   z=bytes(u.mem_read(a,1))[0]
   if not z:break
   out.append(z);a+=1
  return out.decode()
 def groupmembers(a):return [pi(r(r(a+0x14)+j*4)) for j in range(r(a+0x18))]
 allowed=[(o['address'],o['address']+o['size']) for o in sp]
 def hook(u,a,size,_):
  if a==STOP:u.emu_stop();return
  regs=[u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];v,x,y,z=regs
  if a==0xacf4:
   i=gi(v);ret(v if 0<=i<3 and ((y==0x339de4 and i==0) or (y==0x339dbc and i==2)) else 0)
  elif a==0x116a38:
   debug.append('recallMutes %d %s'%(x if x<2**31 else x-2**32,cstr(y)));ret()
  elif a==0x312e0:trace.append(['refreshSip']);ret()
  elif a==0x7538c:trace.append(['activate',x,int(bytes(u.mem_read(SELF+0xe4,1))[0])]);ret()
  elif a==STUB:ret(floats(values[pi(v)]))
  elif a==STUB+4:
   i=pi(v);values[i]=fval(x);trace.append(['set',i,values[i],y]);ret()
  elif a==STUB+8:trace.append(['load',gi(v)]);ret(case['load_ok'])
  elif a==STUB+12:w(v+0x18,0);ret()
  elif a==STUB+16:trace.append(['remoteLookup']);ret(REMOTE+0x100 if case['remote_component'] else 0)
  elif a==STUB+20:trace.append(['allDirty',y]);ret()
  elif a==STUB+24:trace.append(['groupDirty',y,z]);ret()
  elif a==0x74eec or a==0x747a0:ret()
  elif a==0x7486c:ret(int((not r(v+4) or values[pi(r(v+4))]!=0) and any(values[i]==0 for i in groupmembers(v))))
  elif a==0x157940:ret(int(fval(v)>fval(x)))
  elif a==0x4c1bc:
   n=r(v+4);w(r(v)+4*n,r(x));w(v+4,n+1);ret(1)
  elif a==0xad18:
   s=cstr(v);needle=cstr(x);idx=s.find(needle);ret(v+idx if idx>=0 else 0)
  elif a==0xaf70:ret((cstr(v)>cstr(x))-(cstr(v)<cstr(x)))
  elif a==0x11c2e4 or a==0x11d4f4:ret()
  elif a==0x119c4c:
   if v==SELF:ret(ps(16+x) if x in case['local_tags'] else 0)
   else:ret(ps(48+x) if x in case['remote_tags'] else 0)
  elif a==0x5dd78:trace.append(['connected']);ret(REMOTE if case['connected'] else 0)
  elif a==0xfff08:ret(MSG+0x100 if case['message_match'] else 0)
  elif a==0x1223b4:ret(case['index'])
  elif a==0x5e040:trace.append(['muteGroupStored',x if x<2**31 else x-2**32]);ret()
  elif a==0x1196a8:ret()
  elif a in (0x8c6c0,0x8c758,0x8c7f8,0x8c640):
   i=(v-TIMERS)//0x100 if v!=SELF+0x108 else 3
   if a==0x8c6c0:trace.append(['executing',i]);ret(case['executing'][i])
   elif a==0x8c758:trace.append(['elapsed',i]);ret(case['elapsed'][i])
   elif a==0x8c7f8:trace.append(['end',i]);ret()
   else:trace.append(['reset',i]);ret()
  elif a==0x775f0:w(v+4,0);ret()
  elif any(lo<=a<hi for lo,hi in allowed):return
  else:raise RuntimeError(f'unbound native execution {a:#x}')
 u.mem_write(MSG+0x100,b'presetMuteGroup\0')
 handle=u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_SP,BASE+0x21fff0);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,SELF)
 m=case['method'];u.reg_write(UC_ARM_REG_R1,ps(case['param']) if m in (2,4) else MSG if m==7 else case['index'] if m in (1,5,10) else case['flag']);u.reg_write(UC_ARM_REG_R2,case['flag'] if m==1 else case['msg'])
 try: u.emu_start(sp[m-1]['address'],STOP,count=200000)
 except Exception as ex: raise RuntimeError(f'method={m} case={case} pc={u.reg_read(UC_ARM_REG_PC):#x}') from ex
 def pid(a):return -1 if a==0 else pi(a)
 out={'trace':trace,'debug':debug,'values':values[:4],'loose':[pi(r(r(SELF+0xb8)+i*4)) for i in range(r(SELF+0xbc))],'delayed_count':r(SELF+0xd0),'members':[groupmembers(GROUPS+i*0x200) for i in range(3)],'bindings':[[pid(r(GROUPS+i*0x200+4)),pid(r(GROUPS+i*0x200+0xc))] for i in range(3)],'stored':int(bytes(u.mem_read(GROUPS+0xad,1))[0]),'recalling':int(bytes(u.mem_read(SELF+0xe4,1))[0])}
 if m==1:out['result']=u.reg_read(UC_ARM_REG_R0)
 u.hook_del(handle)
 return out

def cases():
 for m in range(1,11):
  for k in range(24):
   yield dict(method=m,index=[0,1,2,3,-1,0x80000000][k%6],flag=k%2,param=k%4,name=['mute','status','prestatussuffix','other'][k%4],tag=5 if k%5==0 else 4,msg=[0,3,5][k%3],values=[[1,1,1,1],[0,1,0,1],[-1,0,2,0]][k%3]+[0]*80,loose=[[0,2,0],[1,2],[]][k%3],delayed=[0,2],enabled=int(k%4!=0),recalling=int(k%7==0),busy=int(k%8==0),stored=int(k%9==0),old_remote=int(k%3==0),all_group=int(k%2==0),observer=int(k%4!=0),connected=int(k%3!=0),remote_component=int(k%4!=1),local_tags=[0,2,4,6,8],remote_tags=[18,19,21,23,25],load_ok=int(k%3!=1),message_match=int(k%4!=0),timer_present=[1,int(k%2==0),1],executing=[1,int(k%3!=1),0,1],elapsed=[int(k%2==0),1,1,int(k%3==0)])

def execute_item(pair):
 n,c=pair
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
 result=run(c,(ROOT/ELF).read_bytes(),specs())
 return dict(id=n,input=c,expected=result,execution=dict(start_utc=start,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),duration_seconds=time.monotonic()-tick))

def expanded_cases():
 initial=list(cases())
 yield from initial
 base=copy.deepcopy(initial[1]);base.update(index=0,enabled=1,recalling=0,observer=1,busy=0,stored=0,old_remote=0)
 for method in (1,5,10):
  for flag,busy,stored,loose in itertools.product((0,1),(0,1),(0,1),([], [0,1,0])):
   c=copy.deepcopy(base);c.update(method=method,flag=flag,busy=busy,stored=stored,loose=loose);yield c
 for name,value,recalling in itertools.product(('mute','other','status'),(-1,0,1),(0,1)):
  c=copy.deepcopy(base);c.update(method=2,name=name,param=4,tag=5,msg=3,recalling=recalling,flag=1);c['values'][4]=value;yield c
 for value,enabled in itertools.product((-1,0,1),(0,1)):
  c=copy.deepcopy(base);c.update(method=4,name='mute',param=4,enabled=enabled,loose=[4,0,4]);c['values'][4]=value;yield c

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args();raw=(ROOT/ELF).read_bytes();assert hashlib.sha256(raw).hexdigest()==HASH;sp=specs();ranges=[]
 e=ELFFile(io.BytesIO(raw))
 for o in sp:
  s=e.get_section(int(o['section_json']));off=s['sh_offset']+o['address']-s['sh_addr'];data=raw[off:off+o['size']];ranges.append(dict(mangled=o['mangled'],section=s.name,file_offset=off,address=o['address'],size=o['size'],sha256=hashlib.sha256(data).hexdigest()))
 out=[];metrics=[]
 with multiprocessing.get_context('spawn').Pool(1,maxtasksperchild=1) as pool:
  for item in pool.imap(execute_item,enumerate(expanded_cases())):
   metrics.append(dict(id=item['id'],method=item['input']['method'],**item.pop('execution')))
   out.append(item)
   print('observed',item['id'],flush=True)
 (ROOT/'uc-library/candidates/graph-live-trial-07-mutegroup/oracle-metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
 Path(args.out).write_text(json.dumps({'version':1,'elf':ELF,'elf_sha256':HASH,'ranges':ranges,'oracle':'original ARM instructions with explicit Core/libc and unresolved app boundary stubs; no provider binary decompilation','cases':out},indent=2)+'\n');print('original ARM cases',len(out))
if __name__=='__main__':main()
