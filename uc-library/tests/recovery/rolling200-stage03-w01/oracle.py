"""Independent original ARM execution; external calls are recorded boundaries, never Core bodies."""
import io,json,struct,itertools,hashlib,sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[4]
IDS=['storm_04','storm_05','w01_05','w01_06','w06_01','w06_02','w06_03']
PACK=ROOT/'temp/recovery-work/rolling200-02/implementation-plan01/packets-batch03/packets'
O=0x4000000; STACK=0x5000000; STOP=0x6000000
REG=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def word(v):return struct.pack('<I',v&0xffffffff)
def sha(b):return hashlib.sha256(b).hexdigest()
def generate():
 out=[];ranges=[];coverage={}
 for m,name in enumerate(IDS):
  p=PACK/('rolling200_02_impl_'+name);ct=json.loads((p/'context.json').read_text());nc=json.loads((p/'native-context.json').read_text());b=nc['bodies'][nc['roots'][0]];orig=ct['originals'][0]['original'];elfpath=ROOT/('rootfs/RML16AI_Rack_13731/home/root/mixer' if m<4 else 'rootfs/CS18_v13840/home/root/surface');blob=elfpath.read_bytes();assert sha(blob)==orig['elf'];elf=ELFFile(io.BytesIO(blob));sec=elf.get_section(b['section_index']);off=sec['sh_offset']+b['address']-sec['sh_addr'];assert off==b['file_offset'];assert sha(blob[off:off+b['size']])==b['bytes_sha256'];sym=next(s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name==orig['mangled']);assert(sym['st_value'],sym['st_size'],sym['st_shndx'])==(b['address'],b['size'],b['section_index'])
  ranges.append(dict(task=name,elf=str(elfpath.relative_to(ROOT)),elf_sha256=orig['elf'],mangled=orig['mangled'],address=b['address'],size=b['size'],section=sec.name,file_offset=off,sha256=b['bytes_sha256']))
  if m==0:cases=itertools.product([0,1,2,0xffffffff],[0,1,2,0xffffffff],[0],[0])
  elif m==1:cases=itertools.product([-2147483648,-1,0,1,2147483647],[0,1],[0],[0])
  elif m==2:cases=itertools.product([-2147483648,-2,-1,0,1,2,3,2147483647],[-1,0,7,2147483647],[0,1,2],[0])
  elif m in [3,5]:cases=itertools.product([0,1],[0,1,0xffffffff],[0],[0])
  elif m==4:cases=itertools.product([0,1,2,3],[0,1,7,255],[0,1,7],[0,1,7,255])
  else:cases=itertools.product([0,1,2,3],[0,1,7,255],[0],[0])
  for a,c,d,e in cases:
   u=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM);u.mem_map(0x8000,0x600000);u.mem_map(O,0x10000);u.mem_map(STACK,0x10000);u.mem_map(STOP,4096)
   for seg in elf.iter_segments():
    if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
   def w(addr,v):u.mem_write(addr,word(v))
   def r(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
   def pid(v):return 0 if v==0 else (v-O)//0x1000
   def cid(v):return (v-O)//0x1000
   u.mem_write(O,bytes([0xa5])*0x1000);args=[O,O+0x5000,0,0];trace=[];writes=[];pcs=[]
   if m==0:w(O+0xa8,a);args[1]=c
   elif m==1:args[2]=a&0xffffffff
   elif m==2:
    args=[O,a&0xffffffff,c&0xffffffff,0];w(O+0xd0,O+0x8000);w(O+0xd4,3)
    for i,v in enumerate([O+0x1000,0,O+0x2000]):w(O+0x8000+i*4,v)
    literal=r(b['address']+b['size']-4);w(literal,0 if d==0 else O+d*0x1000)
   elif m in [3,5]:args=[O,O+0x5000,(a if m==3 else c)&0xffffffff,0]
   elif m==4:
    args[1]=O+0x8000;w(O+4,O+0x7000);w(O+0xe8,O+0x6000);w(O+0x6000,O+0x1000);w(O+0x600c,O+0x2000)
    for i in range(a):
     ptr=O+0x8000+44*i;u.mem_write(ptr,bytes([65+i,0])+bytes(42));w(ptr+32,[-1,7,65535][i]);u.mem_write(ptr+36,bytes([255 if c&(1<<i) else 0,255 if e&(1<<i) else 0]));w(ptr+40,O+0x9000 if d&(1<<i) else 0)
   elif m==6:pass
   before=bytes(u.mem_read(O,0x10000))
   def ret(v=None):
    if v is not None:u.reg_write(UC_ARM_REG_R0,v&0xffffffff)
    u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   def hook(uc,pc,size,_):
    if pc==STOP:return
    if b['address']<=pc<b['address']+b['size']:pcs.append(pc);return
    x,y,z,t=[uc.reg_read(rg) for rg in REG]
    if m==1 and pc==0x73250:assert x==O and y==0;trace.append('clear');ret()
    elif m==6 and pc==0xbd63c:assert x==O and y==0;trace.append('disable');ret()
    elif m==2 and pc==0x119c4c:
     trace.append('lookup:'+str(cid(x))+':'+str(c));ret(x if c==7 else 0)
    elif m==4 and pc==0x11acf0:
     tag=y if y<0x80000000 else y-0x100000000;trace.append('lookup:'+str(cid(x))+':'+str(tag));ret(x if tag==7 else 0)
    elif m==4 and pc==0x76d0c:
     i=(y-O-0x8000)//44;assert x==O+0x7000 and t==0 and r(uc.reg_read(UC_ARM_REG_SP))==0;trace.append('connect:'+str(i)+':'+str(pid(z)));ret()
    elif m==4 and pc==0x76c6c:trace.append('color:'+str((y-O-0x8000)//44));assert z==O+0x9000;ret()
    elif m==4 and pc==0x7630c:trace.append('enabled:'+str((y-O-0x8000)//44)+':'+str(z));ret()
    else:raise RuntimeError('unbound external '+hex(pc))
   def mem(uc,access,addr,size,value,_):
    if O<=addr<O+0x10000:writes.append([addr-O,size,value])
   u.hook_add(unicorn.UC_HOOK_CODE,hook);u.hook_add(unicorn.UC_HOOK_MEM_WRITE,mem);u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP)
   for rg,v in zip(REG,args):u.reg_write(rg,v)
   u.emu_start(b['address'],STOP,count=2000);assert u.reg_read(UC_ARM_REG_PC)==STOP
   if m!=0:assert bytes(u.mem_read(O,0x10000))==before
   if m==0:
    after=bytearray(u.mem_read(O,0x10000));after[0xa8:0xac]=before[0xa8:0xac];assert bytes(after)==before;obs=str(r(O+0xa8))
   elif m in [3,5]:obs=str(u.reg_read(UC_ARM_REG_R0))+' unchanged'
   elif m==2:obs=str(pid(u.reg_read(UC_ARM_REG_R0)))+' '+(';'.join(trace) or '-')
   else:obs=';'.join(trace) or '-'
   expected=str(m)+' '+obs;out.append(dict(input=[m,a,c,d,e],expected=expected,trace=trace,writes=writes,raw_registers=[u.reg_read(rg) for rg in REG]));coverage.setdefault(name,set()).update(pcs)
 return dict(version=1,unicorn=unicorn.__version__,scope='Original exact app bodies executed. External app/Core provider calls are trace boundaries; no Core binary execution. C++ uses real providers separately.',ranges=ranges,cases=out,coverage={k:sorted(v) for k,v in coverage.items()})
if __name__=='__main__':
 p=Path(sys.argv[1]);f=generate();p.write_text(json.dumps(f,indent=2)+'\n');print('original ARM cases',len(f['cases']))
