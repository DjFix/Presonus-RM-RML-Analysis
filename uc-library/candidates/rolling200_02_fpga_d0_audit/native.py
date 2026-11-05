"""Independent bounded ARM lifecycle execution; standard call boundaries only."""
import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_INTR
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
BASE=Path('uc-library/candidates/rolling200_02_fpga_d0_audit')
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
A=0x1000000;S=A+0x1000;STACK=0x2000000;STOP=0x3000000;CELL=0x495368
cases=[];ranges=[]
with ELF.open('rb') as f:
 e=ELFFile(f);table=e.get_section_by_name('.symtab')
 for variant in ['D0','D1','D2']:
  name='_ZN8Presonus4NOAA16TCardFPGAUpdater'+variant+'Ev'
  syms=table.get_symbol_by_name(name);assert len(syms)==1
  sym=syms[0];sec=e.get_section(sym['st_shndx']);addr=int(sym['st_value']);size=int(sym['st_size']);off=int(sec['sh_offset'])+addr-int(sec['sh_addr']);body=raw[off:off+size]
  r=dict(original_mangled=name,demangled='Presonus::NOAA::TCardFPGAUpdater::~TCardFPGAUpdater()',elf_sha256=SHA,firmware_version='RM/RML mixer 13731',address=addr,size=size,section_index=int(sym['st_shndx']),section=sec.name,file_offset=off,range_sha256=hashlib.sha256(body).hexdigest());ranges.append(r)
  if variant=='D0':assert (addr,size,r['range_sha256'])==(677416,148,'309152f685cbb2f6347a2cf9e2ee9370ca8860370619a1be48a2276e8cd91273')
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  u.mem_map(addr&~4095,8192);u.mem_write(addr,body)
  u.mem_map(CELL&~4095,4096);u.mem_write(CELL,struct.pack('<I',S))
  u.mem_map(A,8192);u.mem_map(STACK,65536);u.mem_map(STOP,4096)
  for boundary in [0xa2fe0,0xac10]:
   page=boundary&~4095
   # unregister lies outside target page; allocator is separately trapped.
   u.mem_map(page,4096)
  state=dict(registered=True,live=True,trace=[],stopped=False,writes=[])
  def code(uc,pc,n,_):
   if pc==STOP:state['stopped']=True;uc.emu_stop();return
   if pc==0xa2fe0:
    assert uc.reg_read(UC_ARM_REG_R0)==S and uc.reg_read(UC_ARM_REG_R1)==A
    assert state['registered'];state['registered']=False;state['trace'].append('unregister-boundary')
    uc.reg_write(UC_ARM_REG_R0,0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   if pc==0xac10:
    assert variant=='D0' and uc.reg_read(UC_ARM_REG_R0)==A
    assert not state['registered'] and state['live'];state['live']=False;state['trace'].append('operator-delete-boundary')
    uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   assert addr<=pc<addr+size,(variant,'outside allowed instruction range',hex(pc))
  def write(uc,access,a,n,v,_):
   assert (A<=a and a+n<=A+4) or (STACK<=a and a+n<=STACK+65536),(hex(a),n)
   state['writes'].append(dict(address=a,size=n,value=v))
  def interrupt(*_):raise AssertionError('No guest syscall/interrupt permitted')
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write);u.hook_add(UC_HOOK_INTR,interrupt)
  u.reg_write(UC_ARM_REG_R0,A);u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP)
  u.emu_start(addr,STOP+4,count=1000)
  assert state['stopped'] and u.reg_read(UC_ARM_REG_R0)==A and not state['registered']
  assert state['live']==(variant!='D0')
  assert state['trace']==(['unregister-boundary','operator-delete-boundary'] if variant=='D0' else ['unregister-boundary'])
  assert struct.unpack('<I',u.mem_read(A,4))[0]==3519248
  cases.append(dict(variant=variant,return_this=True,**state))
result=dict(ranges=ranges,cases=cases,unicorn_version=__import__('unicorn').__version__,domain='Each exact original D0/D1/D2 range verified independently. Existing nonnull singleton, normal-return path; guest unregister and standard delete boundaries captured independently. No original Core, allocator, constructor, device, update, erase, syscall or exception instructions executed. Boundary live-state models call identity/order only; host real deallocation is separately proven by executable C++ replay.')
(BASE/'fixtures.json').write_text(json.dumps(result,indent=2)+'\n');print('Native D0/D1/D2: exact ranges; guarded unregister/delete/this return observations passed')
