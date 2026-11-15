#!/usr/bin/env python3
"""Original app instructions with executable CCL and real libc boundary bridge."""
import argparse,ctypes,hashlib,io,json,shlex,struct,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import *
from unicorn.arm_const import *
T=Path(__file__).resolve().parent;R=T.parents[3];TASK=T.name
PACKET=R/'temp/recovery-work/rolling10x10-20261114/prepared06/packets'/TASK
READ=R/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared06-rolling10_fx.json'
CASES=[[],[('custom',0)],[('ch1',1),('ch2',2)],[('ch2',2),('ch1',1)],[('chfoo',2),('aux',1),('ch002',3)],[('CH1',1),('scratch',1),('ch',0),('ch 4',2)],[('ch'+'x'*29,3),('ch1',0),('ch3',1)],[('ch000',0),('ch000',0),('other',2)]]
def sha(b):return hashlib.sha256(b).hexdigest()
def generate(exe):
 req=json.loads((PACKET/'request.json').read_text());target=req['targets'][0];raw=Path(json.loads(READ.read_text())['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path']).read_bytes();assert sha(raw)==target['original_elf_sha256'];elf=ELFFile(io.BytesIO(raw))
 def get(a,n):
  s=next(s for s in elf.iter_sections() if s['sh_type']!='SHT_NOBITS' and s['sh_addr']<=a<a+n<=s['sh_addr']+s['sh_size']);o=s['sh_offset']+a-s['sh_addr'];return raw[o:o+n],s.name,o
 start,size=target['address'],target['size'];body,section,offset=get(start,size);sym=next(s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name==target['mangled']);assert (sym['st_value'],sym['st_size'],sym['st_shndx'])==(start,size,target['section'])
 data=[]
 for a in [0x367230,0x16de6c]:
  b=get(a,32)[0].split(b'\0')[0]+b'\0';data.append(dict(address=a,size=len(b),sha256=sha(b),hex=b.hex(),section=get(a,len(b))[1],file_offset=get(a,len(b))[2]))
 libc=ctypes.CDLL(None);libc.strstr.restype=ctypes.c_void_p;libc.strstr.argtypes=[ctypes.c_void_p,ctypes.c_char_p];libc.strcmp.argtypes=[ctypes.c_char_p,ctypes.c_char_p];libc.strlen.argtypes=[ctypes.c_char_p];libc.strlen.restype=ctypes.c_size_t;libc.strncpy.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t]
 rows=[]
 boundaries=[0x3874c,0xad18,0x3987c,0xaf70,0x119638,0x11dc28,0x119624,0xae98,0xafe8,0x5c6d0,0x3884c,0xacd0]
 for inputs in CASES:
  proc=subprocess.Popen([str(exe),'--provider'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,cwd=R)
  proc.stdin.write(str(len(inputs))+'\n'+''.join(json.dumps(name)+' '+str(count)+'\n' for name,count in inputs));proc.stdin.flush()
  traces=[];events=[]
  def rpc(command):
   proc.stdin.write(command+'\n');proc.stdin.flush();out=proc.stdout.readline().rstrip('\n');assert out!='',(command,proc.poll());traces.append(dict(command=command,observed=out));return out
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages={start&~4095,*[a&~4095 for a in boundaries],0x367000,0x16d000}
  for page in pages:u.mem_map(page,4096)
  u.mem_map(0x2000000,0x10000);u.mem_map(0x3000000,4096);u.mem_map(0x4000000,4096);u.mem_write(start,body)
  for d in data:u.mem_write(d['address'],bytes.fromhex(d['hex']))
  self=0x2000000;items=0x2000800;sp=0x3000e00;stop=0x4000000;children=[0x2001000+i*0x100 for i in range(len(inputs))];changed=[];pcs=[];writes=[]
  def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
  def rd(a):return struct.unpack('<I',u.mem_read(a,4))[0]
  def text(a):
   b=bytearray()
   for i in range(1024):
    c=bytes(u.mem_read(a+i,1))
    if c==b'\0':return bytes(b)
    b+=c
   raise AssertionError('unterminated string')
  w(self+0x58,items);w(self+0x5c,len(children))
  for i,(name,count) in enumerate(inputs):w(items+i*4,children[i]);u.mem_write(children[i]+8,name.encode()+b'\0')
  def receiver(a):return children.index(a)
  def code(uc,pc,n,d):
   if pc==stop:uc.emu_stop();return
   if start<=pc<start+size:pcs.append(pc);return
   assert pc in boundaries,hex(pc)
   a,b,c=[uc.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]];result=0
   if pc==0x3874c:
    assert b==0;assert int(rpc('resize 0'))==0;w(a+4,0);w(a+8,0)
   elif pc==0xad18:
    buf=ctypes.create_string_buffer(text(a));ptr=libc.strstr(ctypes.addressof(buf),text(b));result=0 if not ptr else a+ptr-ctypes.addressof(buf)
   elif pc==0x3987c:
    assert text(b)==b'ch%d';value=shlex.split(rpc('format '+str(c)))[0];uc.mem_write(a,value.encode()+b'\0')
   elif pc==0xaf70:result=libc.strcmp(text(a),text(b))&0xffffffff
   elif pc==0xae98:result=libc.strlen(text(a))
   elif pc==0xafe8:
    dst=ctypes.create_string_buffer(c);libc.strncpy(dst,text(b),c);uc.mem_write(a,dst.raw);result=a
   elif pc==0x5c6d0:
    child=rd(b);idx=receiver(child);assert rpc('set '+str(idx)+' '+json.dumps(text(child+8).decode()))=='1';changed.append(child);assert int(rpc('add '+str(idx)))==len(changed);storage=0x2008000
    for i,p in enumerate(changed):w(storage+i*4,p)
    w(a,storage);w(a+4,len(changed));result=1
   elif pc==0x119624:result=int(rpc('count '+str(receiver(a))))
   elif pc==0x119638:
    idx=receiver(a);assert int(rpc(f'at {idx} {b}'))==b;result=0x2004000+idx*0x100+b*4
   elif pc==0x11dc28:
    idx=(a-0x2004000)//0x100;j=((a-0x2004000)%0x100)//4;events.append(shlex.split(rpc(f'changed {idx} {j}'))[0])
   elif pc==0x3884c:assert rpc('destroy')=='1'
   else:raise AssertionError('unexpected exception path')
   traces.append(dict(native_boundary=pc,args=[a,b,c],result=result));uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  def write(uc,access,a,n,v,d):
   assert 0x3000000<=a<a+n<=0x3001000 or any(p+8<=a<a+n<=p+40 for p in children),(hex(a),n)
   writes.append([a,n,v&((1<<(8*n))-1)])
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write);u.reg_write(UC_ARM_REG_CPSR,0x10);u.reg_write(UC_ARM_REG_R0,self);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop);u.emu_start(start,stop+4,count=10000);assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==sp
  names=[text(p+8).decode() for p in children];rpc('done') if False else None
  proc.stdin.write('done\n');proc.stdin.flush();proc.stdin.close();assert proc.wait(timeout=10)==0
  rows.append(dict(input=[list(x) for x in inputs],names=names,events=events,pcs=pcs,writes=writes,provider_trace=traces,stack_restored=True))
 return dict(task_id=TASK,elf_sha256=sha(raw),mangled=target['mangled'],address=start,size=size,section=section,file_offset=offset,range_sha256=sha(body),data_ranges=data,cases=rows,producer_sha256=sha(Path(__file__).read_bytes()),unicorn_version=unicorn.__version__,provider_mode='--provider actual Core Vector/Component/Parameter/CString32 calls; host libc calls via ctypes; ARM layout is a boundary memory adaptation, not recovered Core implementation')
def main():
 p=argparse.ArgumentParser();p.add_argument('--exe',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(generate(a.exe.resolve()),indent=2)+'\n')
if __name__=='__main__':main()
