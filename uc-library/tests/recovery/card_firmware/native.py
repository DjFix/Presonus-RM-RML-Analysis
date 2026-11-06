"""Hash-bound ARM bodies in private Unicorn memory; rejecting boundary traps only."""
import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import *
from unicorn.arm_const import *
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer'); SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
names=['_ZN8Presonus4NOAA5TCard13eraseFirmwareEv','_ZN8Presonus4NOAA5TCard14updateFirmwareEPNS_2UC23IFirmwareUpdateListenerEi','_ZN8Presonus5Panel14PanelRegistrar10resetBoardEii','_ZL7resetCSiib']
expected=['b32699510a8b384cd0270b6be680de5c7648015a0ca50a57ee8fd9f91936de82','d9253b8e47b6f48728a5a32717d228bfacd283eeb5d4dc7087b09656d0b28d10','ce3facdd9a180cc9a2a29bc0257f27fa2e07c643e37b940533e1f73f2c5ceb31','705931a6518ee01199d2b32749ef2c50cd2c1487853b089116451b88761ce41c']
ranges=[]
with ELF.open('rb') as f:
 e=ELFFile(f);segments=[(int(s['p_vaddr']),s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
 for name,h in zip(names,expected):
  s=e.get_section_by_name('.symtab').get_symbol_by_name(name)[0];sec=e.get_section(s['st_shndx']);a=int(s['st_value']);n=int(s['st_size']);off=int(sec['sh_offset'])+a-int(sec['sh_addr']);assert hashlib.sha256(raw[off:off+n]).hexdigest()==h
  ranges.append(dict(mangled=name,address=a,size=n,file_offset=off,section=sec.name,range_sha256=h,elf_sha256=SHA,firmware='RM/RML mixer 13731',role='server'))
A=0x1000000;STACK=0x2000000;STOP=0x3000000

def execute(c):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x500000);u.mem_map(A,65536);u.mem_map(STACK,65536);u.mem_map(STOP,4096)
 for a,b in segments:u.mem_write(a,b)
 def w(a,x):u.mem_write(a,struct.pack('<I',x&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def txt(a):return bytes(u.mem_read(a,512)).split(b'\0')[0].decode() if a else None
 def ret(x=0):u.reg_write(UC_ARM_REG_R0,x&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 trace=[];pins={};state={'stopped':False,'opens':0};counts={str(x['address']):0 for x in ranges};writes=[]
 def hook(uc,pc,n,_):
  r0,r1,r2,r3=[uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
  if pc==STOP:state['stopped']=True;uc.emu_stop();return
  if pc in [0x9ccb8,0x116a38]:ret();return # diagnostic boundary, not a Core body
  if pc==0x10e948:trace.append(['sleep',r0]);ret();return
  if pc==STOP+4:trace.append(['reset',r1,r2]);ret();return
  if pc==0xa58fc:trace.append(['programmer_construct',int(r1!=0),r2!=0,r3]);state['programmer']=r0;ret();return
  if pc==0xa5f44:
   assert r0==state['programmer'];state['opens']+=1;trace.append(['programmer_open',txt(r1)]);ret(state['opens']!=c.get('fail_open',0));return
  if pc in [0xa5e14,0xa5fe4,0xa62a4,0xa638c,0xa63bc]:
   assert r0==state['programmer'];trace.append([{0xa5e14:'unprotect',0xa5fe4:'erase',0xa62a4:'programmer_update',0xa638c:'programmer_close',0xa63bc:'programmer_destroy'}[pc]]);ret(c.get('ignored_result',0));return
  if pc==0x9dfb8:trace.append(['start',r1]);ret(c.get('start',0));return
  if pc in [0x9cec8,0x9cf9c]:trace.append(['bundle','arm' if pc==0x9cec8 else 'fpga']);ret(A+0x2000 if pc==0x9cec8 else A+0x3000);return
  if pc==0xa57d4:trace.append(['fpga_construct',int(r1!=0)]);ret();return
  if pc==0xa51e4:trace.append(['fpga_update']);ret(c.get('fpga_result',0));return
  if pc==0xa56bc:trace.append(['fpga_destroy']);ret();return
  if pc==STOP+8:trace.append(['progress',txt(r1),r2]);ret();return
  if pc==STOP+12:trace.append(['mounted']);ret(c.get('mounted',1));return
  if pc==STOP+16:trace.append(['compatible',r1]);ret(c.get('compatible',1));return
  if pc==0x10e384:trace.append(['lock']);ret();return
  if pc==0x10e460:trace.append(['unlock']);ret();return
  if pc==0xadd28:pins[r0]=r1;trace.append(['output',r1]);ret();return
  if pc==0xada3c:assert r2==0;pins[r0]=r1;trace.append(['input',r1]);ret();return
  if pc==0xaddb8:trace.append(['set',pins[r0],r1]);ret();return
  if pc in [0xad8a0,0xad7f0]:trace.append(['output_destroy' if pc==0xad8a0 else 'input_destroy',pins[r0]]);ret();return
  allowed=any(x['address']<=pc<x['address']+x['size'] for x in ranges)
  assert allowed,(c,hex(pc),'outside target and explicit boundary allowlist')
  for x in ranges:
   if pc==x['address']:counts[str(pc)]+=1
 def write(uc,access,a,n,v,_):
  if A<=a<A+256:writes.append([a-A,n,v])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 def interrupt(*args):raise AssertionError('guest interrupt/syscall rejected')
 def invalid(*args):raise AssertionError('guest invalid memory rejected')
 u.hook_add(UC_HOOK_INTR,interrupt);u.hook_add(UC_HOOK_MEM_INVALID,invalid)
 w(A,A+0x1000);w(A+0x1000+0x14,STOP+12);w(A+0x1000+0x18,STOP+16)
 w(A+0x5c,A+0x4000);w(A+0x4000,A+0x5000);w(A+0x5000,STOP+4)
 w(A+0x6000,A+0x7000);w(A+0x7000,STOP+8)
 w(A+0x20,c.get('arm',1));w(A+0x28,c.get('fpga',1));w(A+0x18,17);w(A+0x24,19)
 w(A+0x2000+0x40,1);w(A+0x2000+0x44,A+0x8000);w(A+0x2000+0x48,4);w(A+0x3000+0x40,1)
 # StaticSingleton guard preinitialized: no upstream Core execution.

 # literal0x9e548 names the guard; mapped ELF bytes determine exact pointer.
 w(r(0x9e548),1)
 kind=c['kind'];entry={'erase':ranges[0]['address'],'update':ranges[1]['address'],'reset':ranges[2]['address'],'cs':ranges[3]['address']}[kind]
 u.reg_write(UC_ARM_REG_R0,c.get('first',0) if kind=='cs' else A)
 u.reg_write(UC_ARM_REG_R1,c.get('second',0) if kind=='cs' else c.get('mode',0) if kind=='reset' else A+0x6000 if c.get('listener') else 0)
 u.reg_write(UC_ARM_REG_R2,c.get('board',0) if kind in ['cs','reset'] else c.get('mode',0));u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP)
 u.emu_start(entry,STOP+4096,count=10000);assert state['stopped'];value=u.reg_read(UC_ARM_REG_R0);value=value-(1<<32) if value&(1<<31) else value
 return dict(return_value=value if kind in ['erase','update'] else None,trace=trace,state={str(o):r(A+o) for o in [0x18,0x20,0x24,0x28,0x44]},writes=writes,instruction_counts=counts)
cases=[]
for fail in [0,1,2]:cases.append(dict(name=f'erase_{fail}',kind='erase',fail_open=fail,ignored_result=-99))
for mode in [-2147483648,-1,0,1,2,3,4,2147483647]:
 for arm,fpga in [(1,1),(0,1),(1,0),(0,0)]:
  cases.append(dict(name=f'update_{mode}_{arm}_{fpga}',kind='update',mode=mode,arm=arm,fpga=fpga,listener=1))
for fail in [1,2]:cases.append(dict(name=f'update_open_{fail}',kind='update',mode=1,arm=0,fpga=0,fail_open=fail))
for result in [2000,2003,-1,127]:cases.append(dict(name=f'fpga_error_{result}',kind='update',mode=3,fpga=0,fpga_result=result))
for mounted,compatible in [(0,1),(1,0),(1,1)]:
 for listener in [0,1]:cases.append(dict(name=f'restart_{mounted}_{compatible}_{listener}',kind='update',mode=2,arm=0,mounted=mounted,compatible=compatible,listener=listener,start=0,ignored_result=-99))
for mode in [-1,0,1,2,3,2147483647]:
 for board in [-1,0,1,2]:cases.append(dict(name=f'reset_{mode}_{board}',kind='reset',mode=mode,board=board))
for board in [0,1]:cases.append(dict(name=f'cs_{board}',kind='cs',first=103,second=108,board=board))
for c in cases:c['expected']=execute(c)
out=Path('uc-library/tests/recovery/card_firmware/fixtures.json');out.write_text(json.dumps(dict(elf_sha256=SHA,ranges=ranges,cases=cases,isolation='Unicorn private memory; every external app/Core/provider boundary explicit; interrupts, unmapped memory and other PCs reject; no guest syscall passthrough'),indent=2)+'\n');print('ARM native executions:',len(cases))
