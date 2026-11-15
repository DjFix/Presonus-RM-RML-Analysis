"""Original application execution with actual CCL RPC providers; no Core binary."""
import ctypes,hashlib,itertools,json,struct,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
import capstone,unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ROOT=Path(__file__).resolve().parents[4];BASE=Path(__file__).parent;TASK=BASE.name;METHOD=int(TASK[-2:]);PACKET=ROOT/'temp/recovery-work/rolling10x10-20261114/prepared06/packets'/TASK
ELFHASH='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def generate(exe):
 reads=json.loads((ROOT/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared06-rolling10_pages.json').read_text());ep=Path(reads['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path']);assert hashlib.sha256(ep.read_bytes()).hexdigest()==ELFHASH
 t=json.loads((PACKET/'request.json').read_text())['targets'][0]
 with ep.open('rb') as f:
  e=ELFFile(f);sec=e.get_section(12);sym=e.get_section_by_name('.symtab').get_symbol_by_name(t['mangled'])[0];assert (sym['st_value'],sym['st_size'],sym['st_shndx'])==(t['address'],t['size'],12)
  off=sec['sh_offset']+t['address']-sec['sh_addr'];f.seek(off);body=f.read(t['size']);syms={s['st_value']:s.name for s in e.get_section_by_name('.symtab').iter_symbols() if s['st_info']['type']=='STT_FUNC'}
  calls={int(i.op_str.lstrip('#'),16) for i in capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_ARM).disasm(body,t['address']) if i.mnemonic=='bl'}
  rodata=[(s['sh_addr'],s.data()) for s in e.iter_sections() if s.name=='.rodata']
 libc=ctypes.CDLL(None);libc.strcmp.argtypes=[ctypes.c_char_p,ctypes.c_char_p];libc.strcmp.restype=ctypes.c_int
 cases=[]
 combinations=itertools.product(range(3),range(3),(0,1) if METHOD!=2 else (0,),(0,1) if METHOD==4 else (0,))
 for pattern,alt,ignore,cancel in combinations:
  inputs=[METHOD,pattern,alt,ignore,cancel];p=subprocess.Popen([str(Path(exe).resolve()),'--provider'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True);p.stdin.write(' '.join(map(str,inputs))+'\n');p.stdin.flush()
  def rpc(s):p.stdin.write(s+'\n');p.stdin.flush();line=p.stdout.readline().strip();assert line,('provider failed',s,p.poll());return line
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);mapped=set()
  def maprange(a,n):
   for page in range(a&~4095,(a+n+4095)&~4095,4096):
    if page not in mapped:u.mem_map(page,4096);mapped.add(page)
  maprange(t['address'],len(body));u.mem_write(t['address'],body)
  for a,data in rodata:maprange(a,len(data));u.mem_write(a,data)
  for a in calls:maprange(a,4)
  maprange(0x1000000,65536);maprange(0x2000000,65536);maprange(0x494bf0,16)
  obj=0x1000000;storage=0x1001000;source=0x1002000
  u.mem_write(storage,(b'ignoreAltMemory' if ignore else b'preset')+b'\0');u.mem_write(storage+0x30,struct.pack('<I',source));u.mem_write(storage+0x2c,struct.pack('<I',0x1004000));u.mem_write(obj+0xa4,struct.pack('<I',int(rpc('COUNT '+str(obj+144)))))
  u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,source if METHOD==2 else storage);u.reg_write(UC_ARM_REG_SP,0x2008000);u.reg_write(UC_ARM_REG_LR,0x1008000)
  trace=[];pcs=[];writes=[]
  def cstring(a):
   b=bytearray()
   for i in range(512):
    x=bytes(u.mem_read(a+i,1))
    if x==b'\0':return bytes(b)
    b.extend(x)
   raise AssertionError('unterminated original literal')
  def code(uc,address,size,data):
   if t['address']<=address<t['address']+t['size']:pcs.append(address);return
   assert address in calls,hex(address)
   r=[uc.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)];name=syms[address];out=0;op=''
   if 'CoreLock4lock' in name:op='LOCK'
   elif 'CoreLock6unlock' in name:op='UNLOCK'
   elif 'AttributePoolSuspenderC1' in name:op=f'SUSPEND {r[0]}'
   elif 'AttributePoolSuspenderD1' in name:op=f'RESUME {r[0]}'
   elif 'Attributes9removeAll' in name:op=f'CLEAR {r[0]}'
   elif 'Attributes8copyFrom' in name:op=f'COPY {r[0]} {r[1]}'
   elif 'Attributes8makeReal' in name:op=f'REAL {r[0]}'
   elif 'Attributes13getAttributes' in name:assert cstring(r[1])==b'altmem';op='GET'
   elif 'Component4save' in name:op='SAVE'
   elif 'AttributesWriterC1' in name:op='WRITER'
   elif 'AttributesWriter11writeObject' in name:assert cstring(r[1])==b'altmem' and r[3]==1;op=f'WRITE {r[2]}'
   elif name.startswith('strcmp'):out=libc.strcmp(cstring(r[0]),cstring(r[1]))
   else:raise AssertionError(('unexecuted or unresolved boundary',hex(address),name))
   if op:out=int(rpc(op))
   trace.append(dict(address=address,symbol=name,args=r,provider_operation=op,return_word=out&0xffffffff));uc.reg_write(UC_ARM_REG_R0,out&0xffffffff);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,lambda uc,k,a,n,v,x:writes.append([a,n,v]))
  u.emu_start(t['address'],0x1008000,count=250);assert u.reg_read(UC_ARM_REG_PC)==0x1008000
  assert all(0x2000000<=a<0x2010000 for a,n,v in writes)
  report=rpc('REPORT');p.stdin.close();assert p.wait(timeout=5)==0
  if METHOD==4:assert int(report.split()[-1])==u.reg_read(UC_ARM_REG_R0)
  cases.append(dict(inputs=inputs,expected=report,executed=pcs,calls=trace,stack_writes=writes,application_writes=[],return_word=u.reg_read(UC_ARM_REG_R0)))
 return dict(elf_sha256=ELFHASH,mangled=t['mangled'],address=t['address'],size=t['size'],section=12,file_offset=off,range_sha256=hashlib.sha256(body).hexdigest(),unicorn_version=unicorn.__version__,cases=cases,domain='Finite empty/int/UTF8/nested Attributes states, alternate0..2 patterns, exact ignoreAltMemory bypass, save cancellation with real Component provider; original normal ARM instructions and exact call arguments/order, real CCL Attributes/lock/pool/storage operations independently executed by RPC. No binary Core instructions or exception paths.',limitations=['Provider mappings are explicit ARM-to-host source-port adapters, not original Core binary behavior/layout.','No exception/unwind paths, allocation failure, hardware or concurrent race equivalence.'])
if __name__=='__main__':
 import sys
 Path(sys.argv[2]).write_text(json.dumps(generate(sys.argv[1]),indent=2)+'\n')
