"""Execute exact original ARM destructor; RPC calls real Channel/CCL destruction and real free."""
import hashlib,json,struct,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ROOT=Path(__file__).resolve().parents[4];BASE=Path(__file__).resolve().parent;TASK=BASE.name
PREFIX=Path('temp/recovery-work/trial10x2-20261115');PACKET=ROOT/PREFIX/'prepared01/packets'/TASK

def generate(exe):
 t=json.loads((PACKET/'request.json').read_text())['targets'][0]
 reads=json.loads((ROOT/PREFIX/'READ_INPUTS-prepared01-trial10x2_tape.json').read_text())
 ep=Path(reads['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path'])
 assert hashlib.sha256(ep.read_bytes()).hexdigest()==t['original_elf_sha256']
 with ep.open('rb') as f:
  elf=ELFFile(f);sec=elf.get_section(12);sym=elf.get_section_by_name('.symtab').get_symbol_by_name(t['mangled'])[0]
  assert (sym['st_value'],sym['st_size'],sym['st_shndx'])==(t['address'],t['size'],12)
  offset=sec['sh_offset']+t['address']-sec['sh_addr'];f.seek(offset);body=f.read(t['size'])
  sections=[(s['sh_addr'],s.data()) for s in elf.iter_sections() if s['sh_flags']&2 and s['sh_type']=='SHT_PROGBITS']
 deleting=int('D0Ev' in t['mangled'])
 expected_hash='c074ebcecbd5e0c3d6e33e9bc20cfc903f5b6b1c7ce6420bea282208a95f43c2' if deleting else '320fe3e45e4c61857f73a58b6d70b20e9e987cf9867e8c272ea27391ccb5d522'
 assert hashlib.sha256(body).hexdigest()==expected_hash
 cases=[]
 for count in (1,2,4,8):
  p=subprocess.Popen([str(Path(exe).resolve()),'--provider'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
  p.stdin.write(f'{count} {deleting}\n');p.stdin.flush();assert p.stdout.readline().strip()=='READY'
  def rpc(op):
   p.stdin.write(op+'\n');p.stdin.flush();assert p.stdout.readline().strip()=='OK'
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);mapped=set()
  def mapping(a,n):
   for page in range(a&~4095,(a+n+4095)&~4095,4096):
    if page not in mapped:u.mem_map(page,4096);mapped.add(page)
  for a,data in sections:mapping(a,len(data));u.mem_write(a,data)
  obj=0x1000000;stop=0x2000000;stack=0x3000000
  for a,n in ((obj,4096),(stop,4096),(stack,65536)):mapping(a,n)
  u.mem_write(obj,b'\xa5'*128);u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_SP,stack+32768)
  calls=[];writes=[];executed=[]
  def code(uc,a,n,_):
   if a==stop:uc.emu_stop();return
   if t['address']<=a<t['address']+t['size']:executed.append(a);return
   assert uc.reg_read(UC_ARM_REG_R0)==obj
   if a==0x3f418:
    assert not calls;calls.append('actual_ChannelComponent_destructor');rpc('BASE')
   elif a==0xac10:
    assert deleting and calls==['actual_ChannelComponent_destructor'];calls.append('actual_unsized_global_delete');rpc('FREE')
   else:raise AssertionError(('unbound execution',hex(a)))
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  def write(uc,access,a,n,value,_):
   if obj<=a<obj+128:writes.append([a-obj,n,value])
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
  u.emu_start(t['address'],stop+4,count=100)
  assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_R0)==obj
  assert writes==[[0,4,0x174230],[4,4,0x1742b0]],writes
  assert bytes(u.mem_read(obj+8,120))==b'\xa5'*120
  p.stdin.write('END\n');p.stdin.flush();observed=p.stdout.readline().strip();p.stdin.close();assert p.wait()==0
  assert observed==f'{count} {count} 1 {deleting} 1',observed
  cases.append(dict(inputs=[count,deleting],expected=observed,calls=calls,writes=writes,native_instructions=executed,original_return='same ARM this pointer; ABI-specific, not portable C++ destructor return'))
 return dict(elf_sha256=t['original_elf_sha256'],address=t['address'],size=t['size'],section=12,file_offset=offset,range_sha256=expected_hash,domain='Normal valid source-port TapeInput/Channel lifecycle with 1,2,4,8 owned CCL children, owned real float parameter/vector state; borrowed ChannelState/environment/parameter preserved; no exception/concurrency/hardware/ARM layout claim.',cases=cases)
