#!/usr/bin/env python3
"""Exact original Gate body; only Core boundary effects use real CCL RPC."""
import argparse,hashlib,io,itertools,json,shlex,struct,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import *
from unicorn.arm_const import *
T=Path(__file__).resolve().parent;R=T.parents[3];TASK=T.name;BASE=R/'temp/recovery-work/rolling10x10-20261114';PACKET=BASE/'prepared-next-flow01/packets'/TASK
READ=BASE/'READ_INPUTS-prepared-next-flow01-rolling10_fx.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def cases():
 for kind,dest,previous,value,dvalue,old in itertools.product([0,1,2],[0,1],[0,1,2,3],[0.,.5,1.,-1.],[0.,.5],[0.,1.]):yield [kind,dest,previous,bits(value),bits(dvalue),bits(old)]
def generate(exe):
 target=json.loads((PACKET/'request.json').read_text())['targets'][0];raw=Path(json.loads(READ.read_text())['rootfs/CS18_v13840/home/root/surface']['frozen_read_path']).read_bytes();assert sha(raw)==target['original_elf_sha256'];elf=ELFFile(io.BytesIO(raw))
 def get(a,n):
  s=next(s for s in elf.iter_sections() if s['sh_type']!='SHT_NOBITS' and s['sh_addr']<=a<a+n<=s['sh_addr']+s['sh_size']);o=s['sh_offset']+a-s['sh_addr'];return raw[o:o+n],s.name,o
 start,size=target['address'],target['size'];body,section,offset=get(start,size);sym=next(s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name==target['mangled']);assert(sym['st_value'],sym['st_size'],sym['st_shndx'])==(start,size,target['section'])
 literals=[]
 for a,text in [(0x19f1c8,b'ch_key_listen\0'),(0x1a0440,b'key_listen\0')]:
  b,sec,off=get(a,len(text));assert b==text;literals.append(dict(address=a,size=len(b),sha256=sha(b),section=sec,file_offset=off,hex=b.hex()))
 rows=[]
 for case in cases():
  kind,dest,previous,*_=case;p=subprocess.Popen([str(exe),'--provider'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,cwd=R);p.stdin.write(' '.join(map(str,case))+'\n');p.stdin.flush();trace=[]
  def rpc(command):
   p.stdin.write(command+'\n');p.stdin.flush();result=p.stdout.readline().rstrip('\n');assert result!='',(command,p.poll());trace.append(dict(command=command,observed=result));return result
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for a in [start&~4095,0x19f000,0x1a0000,0x2000000,0x3000000,0x4000000,0x5000000]:u.mem_map(a,4096)
  u.mem_write(start,body);u.mem_write(0x2000000,b'\xa5'*4096)
  for lit in literals:u.mem_write(lit['address'],bytes.fromhex(lit['hex']))
  self=0x2000100;vtable=0x2000800;paramtable=0x2000900;addresses={i:0x2000200+0x100*i for i in range(1,5)};addresses[0]=0;ids={a:i for i,a in addresses.items()};sp=0x3000800;stop=0x4000000
  previousID=[0,1,3,2][previous]
  def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
  w(self,vtable);w(vtable+0x18,0x5000000);w(paramtable+0x44,0x5000100);w(paramtable+0xc,0x5000200);w(paramtable+0x58,0x5000300);w(self+0xc8,addresses[previousID])
  for i in range(1,5):w(addresses[i],paramtable)
  before=bytes(u.mem_read(0x2000000,4096));pcs=[];writes=[];boundary=[]
  def text(a):
   out=b''
   while True:
    b=bytes(u.mem_read(a,1));a+=1
    if b==b'\0':return out.decode()
    out+=b
  def code(uc,pc,n,d):
   if pc==stop:uc.emu_stop();return
   if start<=pc<start+size:pcs.append(pc);return
   assert pc in [0x5000000,0x5000100,0x5000200,0x5000300],hex(pc)
   a,b,c=[uc.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]]
   if pc==0x5000000:assert a==self;result=addresses[int(rpc('find '+text(b)))]
   elif pc==0x5000100:result=int(rpc('get '+str(ids[a])))
   elif pc==0x5000200:result=addresses[int(rpc('original '+str(ids[a])))]
   else:assert c in [0,1];assert rpc(f'set {ids[a]} {b} {c}')=='1';result=0
   boundary.append(dict(address=pc,args=[a,b,c],result=result));uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  def write(uc,access,a,n,v,d):
   assert sp-32<=a<a+n<=sp or a==self+0xc8 and n==4;(writes.append([a,n,v&((1<<(8*n))-1)]))
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write);u.reg_write(UC_ARM_REG_CPSR,0x10);u.reg_write(UC_ARM_REG_R0,self);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop);u.emu_start(start,stop+4,count=150);assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==sp
  final=bytes(u.mem_read(0x2000000,4096));expected=bytearray(before);expected[self+0xc8-0x2000000:self+0xcc-0x2000000]=final[self+0xc8-0x2000000:self+0xcc-0x2000000];assert final==bytes(expected)
  previousAfter=ids[struct.unpack('<I',u.mem_read(self+0xc8,4))[0]];observed=shlex.split(rpc('state'));p.stdin.write('done\n');p.stdin.flush();p.stdin.close();assert p.wait(timeout=10)==0
  rows.append(dict(input=case,expected=[str(previousAfter),*observed],provider_trace=trace,boundary_trace=boundary,pcs=pcs,writes=writes,stack_restored=True,other_memory_unchanged=True))
 return dict(task_id=TASK,elf_sha256=sha(raw),mangled=target['mangled'],address=start,size=size,section=section,file_offset=offset,range_sha256=sha(body),literals=literals,cases=rows,producer_sha256=sha(Path(__file__).read_bytes()),unicorn_version=unicorn.__version__,provider_model='Actual CCL Component registry/Numeric/Alias virtual methods and observers execute in the independent --provider branch. Native synthetic vtables map verified original slots6/3/17/22 into those actual operations; only Core memory/return transport is modeled. No original Core body executes.')
def main():
 p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(generate(a.exe.resolve()),indent=2)+'\n')
if __name__=='__main__':main()
