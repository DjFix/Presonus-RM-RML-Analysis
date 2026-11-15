import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ELF=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared05/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer')
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
NAME='_ZN8Presonus5Panel7GEQPage6recallEv'
def generate():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA;ranges=[]
 with ELF.open('rb') as f:
  e=ELFFile(f)
  for name,expected in [(NAME,(447688,32,'54d43cc61b30c6b09e7654c4bc019c7c683acc6869f0ce6f511590bcad916d04')),('_ZN8Presonus5Panel14GeqUIComponent17flattenCurrentGeqEv',(461988,212,'668295244f7a8174a7fcc62046968ba5486ce630bacbe948dff5e53c02a156d6'))]:
   s=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name==name);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];body=data[off:off+s['st_size']];assert (s['st_value'],s['st_size'],hashlib.sha256(body).hexdigest())==expected
   ranges.append(dict(mangled=name,address=s['st_value'],size=s['st_size'],section=sec.name,file_offset=off,sha256=hashlib.sha256(body).hexdigest()))
 cases=[]
 for present in [0,1]:
  for selection in [-2147483648,-1,0,1,2,2147483647]:
   for count in [0,2]:
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
    for r in ranges:u.mem_write(r['address'],data[r['file_offset']:r['file_offset']+r['size']])
    def put(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
    put(0x400118,0x410000 if present else 0);put(0x410084,selection);put(0x410090,0x420000);put(0x4202b0,0x430000);put(0x4202b4,count)
    # Native Core vector error sentinel is zero-initialized NOBITS, as are null entries.
    put(4799616,0);trace=[];writes=[]
    def hook(u,a,n,_):
     assert any(r['address']<=a<r['address']+r['size'] for r in ranges),hex(a)
     trace.append(a)
    u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,a,n,v,_:writes.append([a,n,v]))
    for reg,val in [(UC_ARM_REG_R0,0x400000),(UC_ARM_REG_SP,0x801000),(UC_ARM_REG_LR,0xf00000)]:u.reg_write(reg,val)
    before=bytes(u.mem_read(0x400000,0x40000));u.emu_start(447688,0xf00000,count=100);assert u.reg_read(UC_ARM_REG_PC)==0xf00000
    assert bytes(u.mem_read(0x400000,0x40000))==before
    nonstack=[w for w in writes if not 0x800000<=w[0]<0x801000];assert not nonstack
    cases.append(dict(present=present,selection=selection,count=count,provider_entered=461988 in trace,flatten_calls=0,writes=nonstack,sites=trace))
 return dict(elf_sha256=SHA,ranges=ranges,cases=cases,domain='24 recall cases: null/present borrowed component; six signed selections incl INT_MIN/MAX; vector size zero/two with null entries and zero error sentinel; actual native provider executes, no deeper calls; memory unchanged',external_calls=[])
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
