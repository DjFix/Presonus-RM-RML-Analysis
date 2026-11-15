"""Exact ARM app-range execution with a persistent real source-provider bridge.
Core binary bodies never execute; host layout/vptr equivalence is not claimed.
"""
from pathlib import Path
import hashlib,json,struct,subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
TASK=T.name;VARIANT=TASK.rsplit('_',1)[1].upper()
P=R/'temp/recovery-work/trial10x2-20261115/prepared01/packets'/TASK
READ=json.loads((R/'temp/recovery-work/trial10x2-20261115/READ_INPUTS-prepared01-trial10x2_gambit.json').read_text())
ELF=Path(READ['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path'])
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
NAME='_ZN8Presonus5Panel20GambitPanelComponent'+VARIANT+'Ev'
OBJ=0x1000000;STACK=0x1100000;STOP=0x1200000

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def range_record():
 assert sha(ELF)==SHA
 req=json.loads((P/'request.json').read_text())['targets'][0]
 with ELF.open('rb') as f:
  e=ELFFile(f);sym=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==NAME);sec=e.get_section(sym['st_shndx'])
  offset=sec['sh_offset']+sym['st_value']-sec['sh_addr'];f.seek(offset);raw=f.read(sym['st_size'])
  assert (sym['st_value'],sym['st_size'],sym['st_shndx'])==(req['address'],req['size'],12)
  body=next(b for b in json.loads((P/'native-context.json').read_text())['bodies'].values() if b['address']==req['address'])
  assert hashlib.sha256(raw).hexdigest()==body['bytes_sha256'] and offset==body['file_offset']
  plt=e.get_section_by_name('.plt');rel=e.get_section_by_name('.rel.plt');dyn=e.get_section(rel['sh_link']);idx=(0xac10-plt['sh_addr']-20)//12
  assert dyn.get_symbol(list(rel.iter_relocations())[idx]['r_info_sym']).name=='_ZdlPv'
 return dict(mangled=NAME,address=sym['st_value'],size=sym['st_size'],section=sec.name,section_index=12,file_offset=offset,sha256=hashlib.sha256(raw).hexdigest(),delete_plt_binding='_ZdlPv at 0xac10')

def execute(exe,body,n):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x800000)
 with ELF.open('rb') as f:
  for seg in ELFFile(f).iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 for a,s in [(OBJ,0x1000),(STACK,0x10000),(STOP,0x1000)]:u.mem_map(a,s)
 # Deliberately initialized valid writable native object boundary. Four vptr
 # writes are observed as native writes only, never asserted as host layout.
 u.mem_write(OBJ,bytes([0x5a])*0x1000)
 service=subprocess.Popen([str(exe),'provider',VARIANT,str(n)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=R)
 pcs=[];writes=[];calls=[];last=None
 def query(op):
  service.stdin.write(op+'\n');service.stdin.flush();line=service.stdout.readline();assert line,(op,service.poll(),service.stderr.read());return list(map(int,line.split()))
 def write(uc,access,a,size,value,unused):
  assert STACK<=a and a+size<=STACK+0x10000 or OBJ<=a and a+size<=OBJ+0x1000,(hex(a),size)
  if OBJ<=a<OBJ+0x1000:writes.append([a-OBJ,size,value])
 def code(uc,a,size,unused):
  nonlocal last
  if a==STOP:uc.emu_stop();return
  if a in (0x7e824,0xac10):
   assert uc.reg_read(UC_ARM_REG_R0)==OBJ
   op='base' if a==0x7e824 else 'free'
   last=query(op);calls.append(dict(address=a,operation=op,actual_provider_observation=last))
   if op=='free':u.mem_unmap(OBJ,0x1000)
   uc.reg_write(UC_ARM_REG_R0,OBJ);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  assert body['address']<=a<a+size<=body['address']+body['size'],('unexpected PC',hex(a))
  pcs.append(a)
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_SP,STACK+0x8000);u.reg_write(UC_ARM_REG_LR,STOP)
 try:
  u.emu_start(body['address'],STOP,count=200)
  assert u.reg_read(UC_ARM_REG_PC)==STOP
  service.stdin.close();status=service.wait(timeout=10);assert status==0,(status,service.stderr.read())
 finally:
  if service.poll() is None:service.kill();service.wait()
 assert [c['operation'] for c in calls]==(['base','free'] if VARIANT=='D0' else ['base'])
 assert writes==[[4,4,0x353aa4],[132,4,0x353ab4],[240,4,0x353ad0],[0,4,0x353a50]],writes
 return dict(n=n,native_pcs=pcs,native_writes=writes,calls=calls,observation=last)

def generate(exe):
 body=range_record()
 return dict(elf_sha256=SHA,variant=VARIANT,range=body,cases=[execute(exe,body,n) for n in [1,3,17,65]],boundary='actual RackPanelComponent source provider plus real host delete; no Core binary execution or native constructor/layout/EH claim')
