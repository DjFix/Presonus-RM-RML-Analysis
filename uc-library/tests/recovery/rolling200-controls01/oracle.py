"""Execute exact original app ARM ranges; Core call hooks are trace boundaries only."""
import hashlib,io,json,struct,sys,itertools
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[4]
PACKETS=ROOT/'temp/recovery-work/rolling200-implementation01/packets-batch04/packets'
IDS=['c11_01','c10_01','c10_03','c10_04']
OBJ=0x4000000;STACK=0x5000000;STOP=0x6000000
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]
def sha(b):return hashlib.sha256(b).hexdigest()
def word(v):return struct.pack('<I',v&0xffffffff)
def ptr(i):return 0 if i==0 else OBJ+0x1000*i
def generate():
 out=[];ranges=[];executed={};provider=[]
 for target,n in enumerate(IDS):
  c=json.loads((PACKETS/('rolling200_impl_'+n)/'context.json').read_text());b=next(iter(c['native_context']['bodies'].values()))
  server=target==0;p=ROOT/('rootfs/RML16AI_Rack_13731/home/root/mixer' if server else 'rootfs/CS18_v13840/home/root/surface');blob=p.read_bytes();assert sha(blob)==c['originals'][0]['original']['elf'];elf=ELFFile(io.BytesIO(blob));sec=elf.get_section(b['section_index']);off=int(sec['sh_offset'])+b['address']-int(sec['sh_addr']);assert off==b['file_offset'];assert sha(blob[off:off+b['size']])==b['bytes_sha256'];ranges.append(dict(task=n,elf=str(p.relative_to(ROOT)),elf_sha256=sha(blob),address=b['address'],size=b['size'],file_offset=off,section=sec.name,sha256=b['bytes_sha256']))
  if target==0:cases=([target,old,new,0,0] for old,new in itertools.product([0,1,2,0xffffffff],repeat=2))
  elif target==1:cases=([target,style,dot,p,msg] for style,dot,p,msg in itertools.product(range(3),range(3),range(4),[0,1,2,3,4,5,6,99,-1]))
  else:cases=([target,old,new,0,0] for old,new in itertools.product(range(3),repeat=2))
  for case in cases:
   u=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM);u.mem_map(b['address']&~4095,8192);u.mem_write(b['address'],blob[off:off+b['size']]);u.mem_map(OBJ,0x10000);u.mem_map(STACK,0x10000);u.mem_map(STOP,4096)
   for addr in [0x11e2e0,0x11f4f0,0x10e9fc,0xf8768]:
    page=addr&~4095
    try:u.mem_map(page,4096)
    except unicorn.UcError:pass
   state=bytearray([0xa5]*512);old,new,arg,msg=case[1:];offset=0x94 if target==0 else (0x60 if target in [1,3] else 0x64)
   if target==0:state[offset:offset+4]=word(old);args=[OBJ,new,0]
   elif target==1:state[0x60:0x68]=word(ptr(old))+word(ptr(new));args=[OBJ,ptr(arg),msg]
   else:state[offset:offset+4]=word(ptr(old));args=[OBJ,ptr(new),0]
   u.mem_write(OBJ,bytes(state));u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP)
   for r,v in zip(REGS,args):u.reg_write(r,v&0xffffffff)
   trace=[];pcs=[];writes=[]
   def code(uc,a,size,data):
    if a==STOP:return
    if a in [0x11e2e0,0x11f4f0,0x10e9fc,0xf8768]:
     r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1)
     if a in [0x11e2e0,0x11f4f0]:assert r1==OBJ+0x44;trace.append(('remove:' if a==0x11e2e0 else 'add:')+str((r0-OBJ)//0x1000))
     elif a==0x10e9fc:assert r0==OBJ;trace.append('invalidate')
     else:assert r0==OBJ and r1==ptr(arg) and uc.reg_read(UC_ARM_REG_R2)==msg&0xffffffff;trace.append('base')
     uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
    assert b['address']<=a<b['address']+b['size'],hex(a);pcs.append(a)
   def mem(uc,access,a,size,value,data):
    if OBJ<=a<OBJ+512:writes.append([a-OBJ,size,value])
   u.hook_add(unicorn.UC_HOOK_CODE,code);u.hook_add(unicorn.UC_HOOK_MEM_WRITE,mem);u.emu_start(b['address'],STOP,count=1000);assert u.reg_read(UC_ARM_REG_PC)==STOP
   result=bytes(u.mem_read(OBJ,512));allowed=[0x94] if target==0 else [0x60,0x64] if target==1 else [offset]
   for i in range(512):
    if not any(a<=i<a+4 for a in allowed):assert result[i]==state[i]
   values=[struct.unpack('<I',result[a:a+4])[0] for a in allowed]
   if target!=0:values=[0 if v==0 else (v-OBJ)//0x1000 for v in values]
   out.append(dict(input=case,expected=dict(values=values,trace=trace,writes=writes,r0=u.reg_read(UC_ARM_REG_R0),state=result.hex())))
   executed.setdefault(n,set()).update(pcs)
 return dict(version=1,oracle='Exact ARM app instructions; Core boundaries traced, not executed or substituted as behavior evidence. Pinned providers independently executed in C++ replay.',unicorn=unicorn.__version__,ranges=ranges,cases=out,executed={n:sorted(v) for n,v in executed.items()})
if __name__=='__main__':Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
