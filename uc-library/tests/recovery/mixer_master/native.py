"""Execute original application ARM instructions; Core calls are explicit boundary stubs.
No Core firmware reconstruction. Float equality uses original compiler runtime.
"""
import hashlib,json,struct,random
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
NAME='_ZN8Presonus5Mixer18MixerComponentBase8isMasterEv'
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
if not ELF.exists(): ELF=Path('/home/rs/projects/opencs/ai-line-analysis')/ELF
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
KIND='master'
def inputs():
 if KIND=='collect':
  return list(dict.fromkeys(list(range(-32,33))+[-2147483648,2147483647,-65536,65536]+[random.Random(i).randrange(-2147483648,2147483648) for i in range(256)]))
 if KIND=='master':
  return [0,0x80000000,0x3f800000,0x3f7fffff,0x3f800001,0x40000000,0xbf800000,0x7f800000,0xff800000,0x7fc00000,0xffc00001,0x7f800001,1,0x807fffff,0x7f7fffff]+[random.Random(i).getrandbits(32) for i in range(128)]
 return [[n,capacity,fail,duplicate] for n,capacity in [(0,0),(0,3),(1,1),(2,2),(2,5)] for fail in [0,1] for duplicate in [0,1]]
def generate():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 with ELF.open('rb') as f:
  e=ELFFile(f);s=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==NAME);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];rang=dict(mangled=NAME,address=s['st_value'],size=s['st_size'],section=sec.name,section_index=s['st_shndx'],file_offset=off,sha256=hashlib.sha256(data[off:off+s['st_size']]).hexdigest());segments=[(p['p_vaddr'],p.data()) for p in e.iter_segments() if p['p_type']=='PT_LOAD']
 expected_ranges={'delegate':(198792,100,'e2b6215ecd5f24531d2159473c231fde138ec9218a351580de0bf7b5767c370a'),'collect':(195276,48,'6068392bf0af6a060aa8cf6f967154d4c991868fe1992b712a1836718b2b69ee'),'master':(200608,64,'0941d63c80909f38bd2005c92d9af545da48ebb13c95ab799ee722afbdf552d6')}
 assert (rang['address'],rang['size'],rang['sha256'])==expected_ranges[KIND]
 runtime_ranges=[]
 if KIND=='master':
  with ELF.open('rb') as f:
   e=ELFFile(f)
   for name in ['__aeabi_fcmpeq','__aeabi_cfcmpeq','__eqsf2']:
    z=next(z for z in e.get_section_by_name('.symtab').iter_symbols() if z.name==name);section=e.get_section(z['st_shndx']);offset=section['sh_offset']+z['st_value']-section['sh_addr']
    runtime_ranges.append(dict(mangled=name,address=z['st_value'],size=z['st_size'],section=section.name,file_offset=offset,sha256=hashlib.sha256(data[offset:offset+z['st_size']]).hexdigest()))
 cases=[]
 for value in inputs():
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
  for a,b in segments:u.mem_write(a,b)
  def put(a,n):u.mem_write(a,struct.pack('<I',n&0xffffffff))
  def get(a):return struct.unpack('<I',u.mem_read(a,4))[0]
  trace=[];writes=[];sites=[];runtime_sites=[]
  if KIND=='master':put(0x4002dc,0x500000);put(0x510000,0x520000);put(0x520044,0xe00000)
  if KIND=='delegate':
   n,capacity,fail,duplicate=value;put(0x400370,0x600000);put(0x400374,n);put(0x400378,capacity)
   for i in range(n):put(0x600000+4*i,0x700000+i*16)
   target=0x700000 if duplicate else 0x710000
  def hook(u,a,size,_):
   if a==0xf00000:u.emu_stop();return
   if rang['address']<=a<rang['address']+rang['size']:sites.append(a);return
   if KIND=='master' and a==0x119c4c:
    assert u.reg_read(UC_ARM_REG_R0)==0x500000 and u.reg_read(UC_ARM_REG_R1)==5
    trace.append(['lookup',5]);u.reg_write(UC_ARM_REG_R0,0x510000)
   elif KIND=='master' and a==0xe00000:
    assert u.reg_read(UC_ARM_REG_R0)==0x510000
    trace.append(['getValue',value]);u.reg_write(UC_ARM_REG_R0,value)
   elif KIND=='master' and any(x['address']<=a<x['address']+x['size'] for x in runtime_ranges):runtime_sites.append(a);return
   elif KIND=='delegate' and a==0x388b4:
    assert u.reg_read(UC_ARM_REG_R0)==0x40036c
    required=u.reg_read(UC_ARM_REG_R1);trace.append(['resize',required,not bool(fail)])
    if not fail:put(0x400378,required)
    u.reg_write(UC_ARM_REG_R0,0 if fail else 1)
   else:raise RuntimeError(hex(a))
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook)
  u.hook_add(UC_HOOK_MEM_WRITE,lambda u,access,a,n,v,_:writes.append([a,n,v]))
  for reg,val in [(UC_ARM_REG_R0,0x400000),(UC_ARM_REG_R1,target if KIND=='delegate' else (value&0xffffffff if KIND=='collect' else 0)),(UC_ARM_REG_SP,0x8ff000),(UC_ARM_REG_LR,0xf00000)]:u.reg_write(reg,val)
  u.emu_start(rang['address'],0xf00000,count=10000);assert u.reg_read(UC_ARM_REG_PC)==0xf00000
  if KIND=='delegate':expected=[get(0x600000+4*i) for i in range(get(0x400374))];expected=[(x-0x700000)//16 if x!=0x710000 else 99 for x in expected]
  else:expected=u.reg_read(UC_ARM_REG_R0)
  nonstack=[w for w in writes if not 0x8fe000<=w[0]<0x8ff000]
  if KIND!='delegate':assert not nonstack
  cases.append(dict(input=value,expected=expected,trace=trace,writes=nonstack,sites=sorted(set(sites)),runtime_sites=sorted(set(runtime_sites))))
 return dict(elf_sha256=SHA,ranges=[rang],runtime_ranges=runtime_ranges,cases=cases,stubs='Core lookup returns configured borrowed Parameter; virtual getValue returns controlled IEEE bits; Core resize success/failure boundary only, capacity policy intentionally not compared; actual compiler float helper executes original instructions')
def fixture(observations):
 return {**{k:observations[k] for k in ['elf_sha256','ranges','runtime_ranges']},'cases':[{'input':c['input'],'expected':c['expected']} for c in observations['cases']]}
if __name__=='__main__':
 import sys
 observations=generate()
 Path(sys.argv[1]).write_text(json.dumps(fixture(observations),indent=2)+'\n')
 if len(sys.argv)>2:Path(sys.argv[2]).write_text(json.dumps(observations,indent=2)+'\n')
