import json,hashlib,struct,ctypes,random
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
CONFIG={'task': 'rolling10_next100_avb_idle', 'cls': 'AvbComponent', 'sha': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07', 'elf': '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer', 'name': '_ZN8Presonus3AVB12AvbComponent6onIdleEv', 'body': {'address': 690980, 'size': 96, 'section': '.text', 'section_index': 12, 'file_offset': 658212, 'bytes_sha256': '63c37c0e8400693c1ba1500d1d4bf51fdfce6a1af795b5e7cf20238549d902b7', 'storage': 'file', 'instructions': [{'address': 690980, 'bytes': '0dc0a0e1', 'mnemonic': 'mov', 'operands': 'ip, sp'}, {'address': 690984, 'bytes': '10d82de9', 'mnemonic': 'push', 'operands': '{r4, fp, ip, lr, pc}'}, {'address': 690988, 'bytes': '04b04ce2', 'mnemonic': 'sub', 'operands': 'fp, ip, #4'}, {'address': 690992, 'bytes': '04d04de2', 'mnemonic': 'sub', 'operands': 'sp, sp, #4'}, {'address': 690996, 'bytes': '73b701eb', 'mnemonic': 'bl', 'operands': '#0x116908'}, {'address': 691000, 'bytes': '3c209fe5', 'mnemonic': 'ldr', 'operands': 'r2, [pc, #0x3c]'}, {'address': 691004, 'bytes': '0030a0e3', 'mnemonic': 'mov', 'operands': 'r3, #0'}, {'address': 691008, 'bytes': 'b0bb02eb', 'mnemonic': 'bl', 'operands': '#0x157a08'}, {'address': 691012, 'bytes': '34e09fe5', 'mnemonic': 'ldr', 'operands': 'lr, [pc, #0x34]'}, {'address': 691016, 'bytes': '7d3fa0e3', 'mnemonic': 'mov', 'operands': 'r3, #0x1f4'}, {'address': 691020, 'bytes': '01c0a0e1', 'mnemonic': 'mov', 'operands': 'ip, r1'}, {'address': 691024, 'bytes': '0040a0e3', 'mnemonic': 'mov', 'operands': 'r4, #0'}, {'address': 691028, 'bytes': '06009ee8', 'mnemonic': 'ldm', 'operands': 'lr, {r1, r2}'}, {'address': 691032, 'bytes': '031091e0', 'mnemonic': 'adds', 'operands': 'r1, r1, r3'}, {'address': 691036, 'bytes': '0420a2e0', 'mnemonic': 'adc', 'operands': 'r2, r2, r4'}, {'address': 691040, 'bytes': '02005ce1', 'mnemonic': 'cmp', 'operands': 'ip, r2'}, {'address': 691044, 'bytes': '020000ca', 'mnemonic': 'bgt', 'operands': '#0xa8b74'}, {'address': 691048, 'bytes': '10a89d19', 'mnemonic': 'ldmibne', 'operands': 'sp, {r4, fp, sp, pc}'}, {'address': 691052, 'bytes': '010050e1', 'mnemonic': 'cmp', 'operands': 'r0, r1'}, {'address': 691056, 'bytes': '10a89d99', 'mnemonic': 'ldmibls', 'operands': 'sp, {r4, fp, sp, pc}'}, {'address': 691060, 'bytes': '01108ee8', 'mnemonic': 'stm', 'operands': 'lr, {r0, ip}'}, {'address': 691064, 'bytes': '10a89de9', 'mnemonic': 'ldmib', 'operands': 'sp, {r4, fp, sp, pc}'}], 'coverage': 'static decoded instruction ranges; indirect dispatch explicit'}, 'static': {'mangled': '_ZZN8Presonus3AVB12AvbComponent6onIdleEvE15lastMaintenance', 'address': 4805568, 'size': 8, 'section_index': 24, 'section': '.bss', 'storage': 'SHT_NOBITS', 'initialization': 'zero-initialized8bytes, nofilebytes'}}
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
SHA=CONFIG['sha'];NAME=CONFIG['name'];PROVIDER=R/'temp/recovery-work'/CONFIG['task']/'runtime.so'
GCC=Path('/usr/lib/x86_64-linux-gnu/libgcc_s.so.1');GCC_SHA='d93224d2b0dab4247598be683adca02f5cf00586f99c187579cd7e92058fb7cb'
def inputs():
 rows=[]
 lasts=[0,1,499,500,501,2147483647,4294966795,4294966796,4294966797,4294967295,4294967296,4294967396,1<<48,9223372036854775307]
 for last in lasts:
  now=[0,1,499,500,501,1000,4294967295,4294967296,9223372036854]
  for d in [499,500,501]:
   if last+d<=9223372036854:now.append(last+d)
  for q in sorted(set(now)):
   for remainder in [0,1,999999]:
    ticks=q*1000000+remainder
    if ticks<=9223372036854775807:rows.append((last,ticks,len(rows)%2))
 rows.extend([(0,9223372036854775807,0),(4294967296,9223372036854775807,1),(9223372036854775307,9223372036854775807,0)])
 rng=random.Random(710)
 for _ in range(96):rows.append((rng.randrange(0,9223372036854775308),rng.randrange(0,9223372036854775808),rng.randrange(2)))
 return rows

def generate():
 data=Path(CONFIG['elf']).read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 assert hashlib.sha256(GCC.read_bytes()).hexdigest()==GCC_SHA
 lib=ctypes.CDLL(str(PROVIDER));lib.divideRawClock.argtypes=[ctypes.c_int64,ctypes.POINTER(ctypes.c_int64),ctypes.POINTER(ctypes.c_int64)];lib.divideRawClock.restype=None
 with Path(CONFIG['elf']).open('rb') as f:
  e=ELFFile(f);syms=list(e.get_section_by_name('.symtab').iter_symbols());s=next(s for s in syms if s.name==NAME);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];body=data[off:off+s['st_size']]
  assert (s['st_value'],s['st_size'],off,hashlib.sha256(body).hexdigest())==(CONFIG['body']['address'],CONFIG['body']['size'],CONFIG['body']['file_offset'],CONFIG['body']['bytes_sha256'])
  st=next(x for x in syms if x.name==CONFIG['static']['mangled']);stsec=e.get_section(st['st_shndx']);assert (st['st_value'],st['st_size'],stsec.name,stsec['sh_type'])==(CONFIG['static']['address'],8,'.bss','SHT_NOBITS')
  clock_site=s['st_value']+16;div_site=s['st_value']+28
  def branch(pc):
   ins=struct.unpack_from('<I',body,pc-s['st_value'])[0];delta=ins&0xffffff
   if delta&0x800000:delta-=1<<24
   return pc+8+4*delta
  clock=branch(clock_site);divide=branch(div_site);assert struct.unpack_from('<I',body,88)[0]==1000000 and struct.unpack_from('<I',body,92)[0]==st['st_value']
 cases=[]
 for last,ticks,receiver in inputs():
  q=ctypes.c_int64();rem=ctypes.c_int64();lib.divideRawClock(ticks,ctypes.byref(q),ctypes.byref(rem))
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000);u.mem_write(s['st_value'],body);u.mem_write(st['st_value'],struct.pack('<q',last));obj=0x600000+receiver*0x1000;u.mem_write(obj,b'\xa5'*128);sites=[];trace=[];writes=[]
  def reg64(lo,hi):return (u.reg_read(lo)|(u.reg_read(hi)<<32))
  def set64(lo,hi,val):u.reg_write(lo,val&0xffffffff);u.reg_write(hi,(val>>32)&0xffffffff)
  def code(u,pc,n,_):
   if s['st_value']<=pc<s['st_value']+s['st_size']:sites.append(pc);return
   if pc==clock:
    trace.append(['source_clock',ticks]);set64(UC_ARM_REG_R0,UC_ARM_REG_R1,ticks)
   elif pc==divide:
    assert reg64(UC_ARM_REG_R0,UC_ARM_REG_R1)==ticks and reg64(UC_ARM_REG_R2,UC_ARM_REG_R3)==1000000
    trace.append(['actual_GCC_signed128',ticks,q.value,rem.value]);set64(UC_ARM_REG_R0,UC_ARM_REG_R1,q.value);set64(UC_ARM_REG_R2,UC_ARM_REG_R3,rem.value)
   else:raise RuntimeError(hex(pc))
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,a,n,v,_:writes.append([a,n,v]))
  for reg,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_SP,0x8ff000),(UC_ARM_REG_LR,0xf00000),(UC_ARM_REG_R4,0x12345678),(UC_ARM_REG_R11,0x87654321)]:u.reg_write(reg,v)
  u.emu_start(s['st_value'],0xf00000,count=100);assert u.reg_read(UC_ARM_REG_PC)==0xf00000 and u.reg_read(UC_ARM_REG_SP)==0x8ff000 and u.reg_read(UC_ARM_REG_R4)==0x12345678 and u.reg_read(UC_ARM_REG_R11)==0x87654321
  assert bytes(u.mem_read(obj,128))==b'\xa5'*128 and len(trace)==2
  ns=[w for w in writes if not 0x8fe000<=w[0]<0x8ff000];assert all(st['st_value']<=w[0]<st['st_value']+8 for w in ns)
  after=struct.unpack('<q',u.mem_read(st['st_value'],8))[0]
  cases.append(dict(last=last,ticks=ticks,receiver=receiver,after=after,quotient=q.value,remainder=rem.value,trace=trace,sites=sites,nonstack_writes=ns))
 return dict(elf_sha256=SHA,ranges=[dict(mangled=NAME,address=s['st_value'],size=s['st_size'],section=sec.name,file_offset=off,sha256=hashlib.sha256(body).hexdigest())],original_process_static=CONFIG['static'],original_helper=dict(address=divide,identity='__aeabi_ldivmod',original_size=0,executed=False),clock_address=clock,cases=cases,provider=dict(library=str(GCC),sha256=GCC_SHA,adaptation='Independently compiled RuntimeProvider.cpp directly calls actual __divti3/__modti3 after widening signed64 dividend, fixed divisor1e6; observed64 quotient/remainder translated to ARM register pairs. No original helper/Core execution, Python division, or new-product oracle. Deterministic clock input is explicit existing gateway test boundary.'))
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
