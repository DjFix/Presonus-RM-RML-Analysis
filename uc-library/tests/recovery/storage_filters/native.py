"""Execute exact app ELF ranges; CCL/controller/RTTI and libc are explicit boundaries."""
import hashlib,json,pathlib,struct,itertools
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
CLASSES=['FxPresetFilter','GEQPresetFilter','ChannelParamTagFilter','AltMemoryFilter','SmaartStoreFilter']
def name(c,m):return '_ZNK'+('15AltMemoryFilter' if c=='AltMemoryFilter' else '8Presonus5Mixer'+str(len(c))+c)+'10'+m+'EiPKcPv'
NAMES=[name(c,m) for m in ['shouldLoad','shouldSave'] for c in CLASSES]
def generate():
 blob=ELF.read_bytes();assert hashlib.sha256(blob).hexdigest()==SHA
 f=ELF.open('rb');e=ELFFile(f);sy=e.get_section_by_name('.symtab');ranges=[]
 for n in NAMES:
  s=sy.get_symbol_by_name(n)[0];sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];ranges.append(dict(mangled=n,address=s['st_value'],size=s['st_size'],section=sec.name,file_offset=off,sha256=hashlib.sha256(blob[off:off+s['st_size']]).hexdigest()))
 def execute(c,args,save=False):
  typ,nm,present,tag,flags,controller,index,filtertag,filterindex,pname=args
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
  for seg in e.iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
  u.mem_map(0x1000000,0x20000);u.mem_map(0x9000000,0x10000)
  obj=0x1000000;param=obj+0x1000;info=obj+0x2000;ctrl=obj+0x3000;string=obj+0x4000;vt=obj+0x5000;stop=obj+0x1f000;override=obj+0x1e000
  def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
  def rd(a):return struct.unpack('<I',u.mem_read(a,4))[0]
  def text(a):return bytes(u.mem_read(a,512)).split(b'\0')[0]
  w(obj,vt);w(vt,override);w(obj+4,filtertag);w(obj+8,filterindex);w(param+12,info);w(info+4,tag);w(info+0x3c,flags);u.mem_write(info+8,pname.encode()+b'\0');w(param+0x50,ctrl if controller else 0);w(ctrl+0x16c,index)
  if nm is not None:u.mem_write(string,nm.encode()+b'\0')
  trace=[];pcs=[];writes=[]
  target=next(r for r in ranges if r['mangled']==name(c,'shouldSave' if save else 'shouldLoad'))
  def code(uc,pc,n,_):
   if pc==stop:uc.emu_stop();return
   if pc==override:
    assert [uc.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]==[obj,typ,0 if nm is None else string,param if present else 0]
    trace.append('virtual shouldLoad: arguments preserved');uc.reg_write(UC_ARM_REG_R0,tag&1)
   elif pc==0xaf70:
    a=text(uc.reg_read(UC_ARM_REG_R0));b=text(uc.reg_read(UC_ARM_REG_R1));trace.append(['strcmp',a.hex(),b.hex()]);uc.reg_write(UC_ARM_REG_R0,int(a!=b))
   elif pc==0xad18:
    a=uc.reg_read(UC_ARM_REG_R0);needle=text(uc.reg_read(UC_ARM_REG_R1));pos=text(a).find(needle);trace.append(['strstr',needle.hex(),pos]);uc.reg_write(UC_ARM_REG_R0,0 if pos<0 else a+pos)
   elif pc==0x18224:
    a=text(rd(uc.reg_read(UC_ARM_REG_R0)));b=text(uc.reg_read(UC_ARM_REG_R1));trace.append(['CCL ConstString eq',a.hex(),b.hex()]);uc.reg_write(UC_ARM_REG_R0,int(a==b))
   elif pc==0x11c1d4:
    trace.append('CCL Parameter getController');uc.reg_write(UC_ARM_REG_R0,ctrl if controller else 0)
   elif pc==0xacf4:
    trace.append(['RTTI ChannelComponent',controller]);uc.reg_write(UC_ARM_REG_R0,ctrl if controller==2 else 0)
   else:
    assert target['address']<=pc<target['address']+target['size'],hex(pc)
    pcs.append(pc);return
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  def write(uc,access,a,n,v,_):
   assert 0x9000000<=a<a+n<=0x9010000,hex(a)
   writes.append([a,n,v])
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for r,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],[obj,typ,0 if nm is None else string,param if present else 0]):u.reg_write(r,v)
  u.reg_write(UC_ARM_REG_SP,0x9008000);u.reg_write(UC_ARM_REG_LR,stop);u.emu_start(target['address'],stop+4,count=1000);assert u.reg_read(UC_ARM_REG_PC)==stop
  return dict(result=u.reg_read(UC_ARM_REG_R0),trace=trace,executed_pcs=pcs,stack_writes=writes)
 para=0x50617261;comp=0x436f6d70;cases=[]
 def add(c,a,save=False):cases.append(dict(kind=c,save=save,args=a,**execute(c,a,save)))
 base=[para,None,1,0,0,0,0,7,-1,'']
 for c in CLASSES:
  if c=='FxPresetFilter':domains=itertools.product([para,comp,0],[0,1],['','loaded_num','Loaded_num','loaded_numx','xloaded_num','é'])
  elif c=='GEQPresetFilter':domains=itertools.product([para,comp,0],[0,1],[None,'','gain','gain2','xgain','on','onx','On','é'])
  elif c=='ChannelParamTagFilter':domains=itertools.product([para,comp,0],[0,1],[0,1,2],[-1,0,1,2147483647],[-2,0,1],[7,8])
  elif c=='AltMemoryFilter':domains=itertools.product([para,comp,0],[0,1],[0,1,32,64,65,128,0xffffffff])
  else:domains=itertools.product([para,comp,0],[0,1],[None,'eq','EQ','other'],[0,400,420,421],[0,1,2],[-1,0,1])
  for row in domains:
   a=base[:]
   if c in ['FxPresetFilter','GEQPresetFilter']:
    a[0],a[2],val=row;a[9 if c=='FxPresetFilter' else 1]=val
   elif c=='ChannelParamTagFilter':a[0],a[2],a[5],a[6],a[8],a[3]=row
   elif c=='AltMemoryFilter':a[0],a[2],a[4]=row
   else:
    a[0],a[2],a[1],a[3],a[5],a[6]=row
    if a[0]==comp and a[1]=='eq' and not a[2]:continue
   add(c,a)
  for typ,nm,present,result in itertools.product([para,comp,0],[None,'eq'],[0,1],[0,1]):
   a=base[:];a[0]=typ;a[1]=nm;a[2]=present;a[3]=result;add(c,a,True)
 f.close();return dict(elf_path=str(ELF.relative_to(ROOT)),elf_sha256=SHA,ranges=ranges,cases=cases,scope='Exact original app ARM execution only; libc, pinned CCL and RTTI are explicit boundary observations. Stack writes captured, no nonstack writes. Invalid eq/null component domain excluded. Original declarations/layout/ABI/hardware unproven.')
if __name__=='__main__':
 import sys
 pathlib.Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
