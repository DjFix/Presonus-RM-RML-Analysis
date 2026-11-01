"""Execute only sealed ARM Controller bodies; external dispatch is an explicit stub boundary."""
import hashlib,json,pathlib,struct,itertools,datetime
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=ROOT/'uc-library/candidates/graph-live-trial-04-dsp'
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def flt(v):return struct.unpack('<f',struct.pack('<I',v))[0]
def run(method,mode,index,conv,value,lo,hi,guard=1):
 p=ROOT/f'temp/recovery-work/graph-live-trial-04/trial04_dsp_{method}-packet/native-context.json'
 d=json.loads(p.read_text());b=d['bodies'][d['roots'][0]]; start=b['address'];end=start+b['size']
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x500000)
 with ELF.open('rb') as f:
  e=ELFFile(f)
  for seg in e.iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 u.mem_map(0x1000000,0x10000);u.mem_map(0x2000000,0x10000)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 obj=0x1000000;lst=obj+0x100;arr=obj+0x200;desc=obj+0x300;cv=obj+0x600;vt=obj+0x700;dv=obj+0x800
 w(obj,vt);w(obj+12,0 if mode==0 else lst);w(lst+4,arr);w(lst+8,0 if mode==6 else 3);u.mem_write(lst+20,bytes([mode in (2,3,6,7)]))
 for j in range(3):w(arr+4*j,0 if mode==4 and j==index else desc+0x90*j);w(desc+0x90*j,10+10*j);w(desc+0x90*j+0x84,cv if conv else 0)
 w(cv,dv);w(cv+4,lo);w(cv+8,hi)
 for slot,addr in [(0x14,0x1001000),(0x18,0x1001010),(0x24,0x1001020),(0x28,0x1001030)]:w(vt+slot,addr)
 w(dv+12,0x1001040);w(dv+16,0x1001050)
 w(0x4933e8,guard);w(0x497f08,desc if mode==5 else 0);w(0x497f90,0)
 trace=[];writes=[]
 def ret(v):u.reg_write(UC_ARM_REG_R0,v&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def code(uc,a,n,user):
  r=[uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]]
  if a==0x1001060:uc.emu_stop();return
  if start<=a<end:return
  if a in (0x1001000,0x1001010,0x1001020,0x1001030,0x1001040,0x1001050):
   trace.append([hex(a),r]);ret(0x3f400000 if a in (0x1001010,0x1001020,0x1001040,0x1001050) else 0x3f000000);return
  if a in (0x157940,0x1578f8):
   trace.append([hex(a),r]);ret(int(flt(r[0])>flt(r[1])) if a==0x157940 else int(flt(r[0])<flt(r[1])));return
  if a==0xb4820:trace.append(['getError',r]);ret(0x497f0c);return
  if a==0xb030:trace.append(['guard_acquire',r]);ret(1);return
  if a==0xaa3c:trace.append(['guard_release',r]);w(r[0],1);ret(0);return
  if a==0xadb4:trace.append(['atexit',r]);ret(0);return
  raise RuntimeError(f'unapproved execution {a:x}')
 def write(uc,access,a,n,v,user):
  if not 0x2000000<=a<0x2010000:writes.append([a,n,v])
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 for reg,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,index&0xffffffff),(UC_ARM_REG_R2,value),(UC_ARM_REG_SP,0x200f000),(UC_ARM_REG_LR,0x1001060)]:u.reg_write(reg,v)
 u.emu_start(start,0x1001060,count=1000)
 assert u.reg_read(UC_ARM_REG_PC)==0x1001060
 return dict(method=method,mode=mode,index=index,converter=conv,value=value,low=lo,high=hi,guard=guard,result=u.reg_read(UC_ARM_REG_R0),trace=trace,writes=writes)
def main():
 assert hashlib.sha256(ELF.read_bytes()).hexdigest()==SHA
 ranges=[]
 for i in range(1,6):
  d=json.loads((ROOT/f'temp/recovery-work/graph-live-trial-04/trial04_dsp_{i}-packet/native-context.json').read_text());b=d['bodies'][d['roots'][0]]
  with ELF.open('rb') as stream:
   ef=ELFFile(stream);sec=ef.get_section(b['section_index']);assert sec.name==b['section'];assert sec['sh_offset']+b['address']-sec['sh_addr']==b['file_offset'];assert b['address']>=sec['sh_addr'] and b['address']+b['size']<=sec['sh_addr']+sec['sh_size']
   manifest=json.loads((ROOT/f'temp/recovery-work/graph-live-trial-04/trial04_dsp_{i}-packet/context.json').read_text());mangled=manifest['originals'][0]['original']['mangled'];symbols=ef.get_section_by_name('.symtab').get_symbol_by_name(mangled);assert any(sym['st_value']==b['address'] and sym['st_size']==b['size'] and sym['st_shndx']==b['section_index'] for sym in symbols)
  raw=ELF.read_bytes()[b['file_offset']:b['file_offset']+b['size']];assert hashlib.sha256(raw).hexdigest()==b['bytes_sha256'];ranges.append({k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']})
 cases=[]
 for m in (1,2):
  for ix,v in itertools.product([-1,0,9,2147483647],[0,0x80000000,bits(.25),0x7fc12345]):cases.append(run(m,1,ix,0,v,0,bits(1)))
 for m in (3,4,5):
  for mode,ix in [(0,0),(1,0),(1,2),(1,-1),(1,3),(2,10),(2,20),(2,30),(3,99),(7,99),(4,1),(5,-1),(6,99)]:
   for c,v in itertools.product([0,1],[bits(-2),0,0x80000000,bits(.5),bits(3),0x7f800000,0xff800000,0x7fc12345]):cases.append(run(m,mode,ix,c,v,bits(-1),bits(2),guard=0 if mode==7 else 1))
 for lo,hi in [(bits(2),bits(-1)),(0x7fc54321,bits(2)),(bits(-1),0x7fc54321),(0x80000000,0),(0,0x80000000)]:
  for v in [bits(-2),0,0x80000000,bits(.5),bits(3),0x7fc12345]:cases.append(run(5,1,0,1,v,lo,hi))
 (OUT/'native-fixtures.json').write_text(json.dumps({'elf_sha256':SHA,'unicorn':unicorn.__version__,'ranges':ranges,'cases':cases},indent=2)+'\n')
 print('original ARM executions',len(cases))
if __name__=='__main__':main()
