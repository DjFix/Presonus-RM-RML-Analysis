"""Original ARM destructor instructions, real source-provider lifecycle boundaries.
No Core binary execution: ChannelComponent boundary executes actual canonical
inline base destruction in a live portable object. Layout translation is explicit.
"""
import hashlib,json,struct,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ROOT=Path(__file__).resolve().parents[4]
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
PREFIX='_ZN8Presonus5Mixer17MonoMainComponent'
def observations(exe):
 binding=json.loads((ROOT/'temp/recovery-work/trial10x2-20261115/READ_INPUTS-prepared01-trial10x2_mono.json').read_text())
 elf=Path(binding['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path']); data=elf.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 ranges=[];cases=[]
 with elf.open('rb') as f:
  e=ELFFile(f); table=e.get_section_by_name('.symtab')
  for variant,addr,size,expected in [('D1',0x48390,48,'00c6160ffb371715c59af236e8230f315fb372d6bc4e20f9b768e4b65e87f4cf'),('D0',0x48358,56,'b0d1923ab901e992301ef284f0749d72ca2f97a8e29a3e9008dae328c27cce32')]:
   name=PREFIX+variant+'Ev'; sym=next(s for s in table.get_symbol_by_name(name) if s['st_value']==addr and s['st_size']==size);sec=e.get_section(sym['st_shndx']);off=sec['sh_offset']+addr-sec['sh_addr'];code=data[off:off+size];assert hashlib.sha256(code).hexdigest()==expected
   ranges.append(dict(mangled=name,address=addr,size=size,section=sec.name,file_offset=off,sha256=expected))
   for n in [1,2,4,8]:
    proc=subprocess.Popen([str(exe),'native',str(n)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    for page in [0x48000,0x3f000,0xa000,0x200000,0x300000,0x400000]:u.mem_map(page,4096)
    u.mem_write(addr,code);u.mem_write(0x200000,bytes([0xa5])*128)
    u.reg_write(UC_ARM_REG_R0,0x200000);u.reg_write(UC_ARM_REG_SP,0x300f00);u.reg_write(UC_ARM_REG_LR,0x400000)
    calls=[];writes=[]
    def hook(uc,pc,length,_):
     if pc==0x400000:uc.emu_stop();return
     if pc in [0x3f418,0xac10]:
      assert uc.reg_read(UC_ARM_REG_R0)==0x200000
      action='BASE' if pc==0x3f418 else 'FREE';calls.append(action)
      # Boundary has actual resource destruction/free in the persistent process.
      proc.stdin.write(action+'\n');proc.stdin.flush();assert proc.stdout.readline().strip()=='OK'
      uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
     assert addr<=pc<addr+size,hex(pc)
    def write(uc,access,address,length,value,_):
     assert 0x300000<=address<0x301000 or 0x200000<=address<0x200008
     writes.append(dict(address=address,size=length,value=value))
    u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
    u.emu_start(addr,0,count=1000)
    assert u.reg_read(UC_ARM_REG_PC)==0x400000 and u.reg_read(UC_ARM_REG_SP)==0x300f00
    assert u.reg_read(UC_ARM_REG_R0)==0x200000
    assert calls==(['BASE','FREE'] if variant=='D0' else ['BASE'])
    assert bytes(u.mem_read(0x200000,8))==struct.pack('<II',0x1764f8,0x17655c)
    assert bytes(u.mem_read(0x200008,120))==bytes([0xa5])*120
    proc.stdin.write('END\n');proc.stdin.flush();observed=proc.stdout.readline().strip();proc.stdin.close();assert proc.wait()==0
    cases.append(dict(variant=variant,children=n,calls=calls,provider_observation=observed,writes=writes,sp_restored=True,returned_receiver=True,remaining_object_bytes_unchanged=True))
 return dict(elf_sha256=SHA,ranges=ranges,cases=cases,boundary='Persistent real portable object; original ARM call to ChannelComponent runs actual inline base destruction and CCL provider; original _ZdlPv runs actual global unsized delete with real free instrumentation. No original Core execution or ARM layout equivalence.')
