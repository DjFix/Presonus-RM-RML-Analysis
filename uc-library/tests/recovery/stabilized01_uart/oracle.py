"""Execute exact original dspUartTest and uartTest ARM bodies offline.
UARTComm and CCL/libc calls are declared boundary contracts, never Core/native
UART execution. No expected observation is computed by reconstructed C++.
"""
import argparse,hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
BASE=Path('temp/recovery-work/stabilized-cycle01/batch02/packets')
RAWPATH=Path('rootfs/RML16AI_Rack_13731/home/root/mixer');RAW=RAWPATH.read_bytes()
STACK,STOP,OBJ=0x1000000,0x1100000,0x1200000
REG=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def ranges():
 rr=[]
 for i in [1,2]:
  c=json.loads((BASE/f'stabilized01_uart_{i:02}'/'context.json').read_text());n=c['native_context'];nid=c['native_roots'][0];m=n['nodes'][nid]['metadata'];b=n['bodies'][nid];assert hashlib.sha256(RAW).hexdigest()==m['elf']
  with RAWPATH.open('rb') as f:
   elf=ELFFile(f);syms=[s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name==m['mangled']];assert len(syms)==1;s=syms[0];sec=elf.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];assert s['st_value']==b['address'] and s['st_size']==b['size'] and off==b['file_offset'] and sec.name==b['section'];assert hashlib.sha256(RAW[off:off+b['size']]).hexdigest()==b['bytes_sha256']
  rr.append(dict(task_id=c['task_id'],original=m,address=b['address'],size=b['size'],section=b['section'],file_offset=off,bytes_sha256=b['bytes_sha256']))
 return rr

def execute(entry,scenario):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 with RAWPATH.open('rb') as f:
  pages=set()
  for s in ELFFile(f).iter_segments():
   if s['p_type']!='PT_LOAD':continue
   a,n=int(s['p_vaddr']),int(s['p_memsz'])
   for p in range(a&~4095,(a+n+4095)&~4095,4096):
    if p not in pages:u.mem_map(p,4096);pages.add(p)
   u.mem_write(a,s.data())
 u.mem_map(STACK,0x10000);u.mem_map(STOP,4096);u.mem_map(OBJ,4096)
 def string(a):
  b=bytearray()
  while u.mem_read(a+len(b),1)!=b'\0':b.extend(u.mem_read(a+len(b),1));assert len(b)<1024
  return b.decode()
 probe='PreSonus StudioLive AI';q=[list(probe.encode()),list(probe.encode())]
 if scenario=='first-mismatch':q[0][1]=ord('X')
 if scenario=='second-mismatch':q[1][1]=ord('X')
 if scenario=='sync-junk-timeout':q[0]=[0,ord('x'),0]+q[0];q[1]=[ord('z'),0]+q[1]
 if scenario=='timeout-after-sync':q[0][3]=0
 objects=[];ports={};out=dict(opens=[],writes=[],reads=[],closes=[],messages=[]);trace=[];boundaries=[];writes=[]
 def ret(v=None):
  if v is not None:u.reg_write(UC_ARM_REG_R0,v&0xffffffff)
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def hook(uc,a,n,_):
  if a==STOP:uc.emu_stop();return
  trace.append(a);x,y,z,t=[uc.reg_read(r) for r in REG]
  if a in [0x953b4,0x95f24,0x95d50,0x95400,0x96014,0x960e8,0x116a38,0xae98,0xaf70]:
   boundaries.append(dict(address=a,arguments=[x,y,z,t]))
   if a==0x953b4:objects.append(x);ret(x)
   elif a==0x95f24:
    name=string(y);port=0 if name.endswith('0') else 1;ports[x]=port;out['opens'].append(name);ret(1)
   elif a==0x95d50:out['writes'].append([ports[x],bytes(uc.mem_read(y,z)).decode()]);ret(0 if scenario=='short-write' else z)
   elif a==0x95400:
    port=ports[x];assert y==1;assert q[port],('unbounded read',scenario,port);v=q[port].pop(0);out['reads'].append([port,v]);ret(v)
   elif a==0x96014:out['closes'].append(ports[x]);ret()
   elif a==0x960e8:ret() # Actual source destructor closes invalid handle; separate provider effect.
   elif a==0xae98:ret(len(string(x)))
   elif a==0xaf70:ret((string(x)>string(y))-(string(x)<string(y)))
   elif a==0x116a38:
    fmt=string(x)
    message=fmt.replace('%s',string(y)) if '%s' in fmt else fmt.replace('%c',chr(y&255)) if '%c' in fmt else fmt
    out['messages'].append(message);ret()
  elif not (0x6a51c<=a<0x6a794):raise AssertionError(('unexpected execution',hex(a)))
 def mem(uc,access,a,n,value,_):
  if STACK<=a<STACK+0x10000:writes.append(dict(address=a,size=n,value=value))
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,mem);u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,OBJ)
 u.emu_start(entry,STOP,count=100000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 return dict(observed=out,executed_addresses=trace,boundaries=boundaries,stack_writes=writes)
def data_ranges():
 records=[]
 rawpath=Path('rootfs/CS18_v13840/home/root/surface' if 'uart'=='mapping' else 'rootfs/RML16AI_Rack_13731/home/root/mixer')
 raw=rawpath.read_bytes()
 with rawpath.open('rb') as f:
  sections=[(s.name,int(s['sh_addr']),int(s['sh_offset']),int(s['sh_size'])) for s in ELFFile(f).iter_sections() if s['sh_type']!='SHT_NOBITS']
 def data(a,n):
  sec=next(s for s in sections if s[1]<=a and a+n<=s[1]+s[3]);off=sec[2]+a-sec[1];b=raw[off:off+n];records.append(dict(address=a,size=n,section=sec[0],file_offset=off,sha256=hashlib.sha256(b).hexdigest(),hex=b.hex()));return b
 def text(a):
  sec=next(s for s in sections if s[1]<=a< s[1]+s[3]);off=sec[2]+a-sec[1];n=raw.index(b'\0',off)-off+1;return data(a,n)
 if 'uart'=='mapping':
  table=data(1690900,120)
  for i in range(0,112,8):text(struct.unpack('<I',table[i:i+4])[0])
  text(1690512)
 else:
  for i in range(0x6a748,0x6a780,4):
   sec=next(s for s in sections if s[1]<=i< s[1]+s[3]);off=sec[2]+i-sec[1];text(struct.unpack('<I',raw[off:off+4])[0])
 return records

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();rr=ranges();cc=[]
 for r in rr:
  for scenario in ['pass','first-mismatch','second-mismatch','sync-junk-timeout','timeout-after-sync','short-write']:
   cc.append(dict(task_id=r['task_id'],scenario=scenario,native=execute(r['address'],scenario)))
 Path(a.out).write_text(json.dumps(dict(version=1,ranges=rr,data_ranges=data_ranges(),cases=cc,engine='Unicorn '+unicorn.__version__,limitations='Exact helper and caller execute; UARTComm, libc and CCL calls are boundary contracts. Per-call timeout represented by returned zero, not hardware. No aggregate timeout exists in first-byte synchronization; perpetual no-response/open-failure hangs excluded. No original return declaration/layout/ARM ABI/hardware credit.'),indent=2)+'\n');print('original UART helper/caller cases',len(cc))
