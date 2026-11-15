"""Exact ARM range execution; host subprocess executes real base/free boundaries."""
import hashlib,json,struct,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR,UC_ARM_REG_SP
R=Path(__file__).resolve().parents[4]
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
SNAP=ROOT/'temp/recovery-work/trial10x2-20261115/prepared01/snapshot'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
ELF=SNAP/'rootfs/RML16AI_Rack_13731/home/root/mixer'
COUNTS=[1,3,17]

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def packet(variant):return R/'temp/recovery-work/trial10x2-20261115/prepared01/packets'/('trial10x2_storm_'+variant)
def generate(exe,variant):
 raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 req=json.loads((packet(variant)/'request.json').read_text());t=req['targets'][0]
 with ELF.open('rb') as f:
  elf=ELFFile(f);symbols={s.name:s for s in elf.get_section_by_name('.symtab').iter_symbols()}
  s=symbols[t['mangled']];sec=elf.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];body=raw[off:off+s['st_size']]
  assert (s['st_value'],s['st_size'],s['st_shndx'])==(t['address'],t['size'],t['section'])
  assert sec.name=='.text'
  expected={'d2':(0x6ac78,76,'0577d76ef1b52ce94e58c6cdb658de2e6866445ed103543883a87ec13ed2b3f0'),'d0':(0x6accc,84,'98027dc86def50b3081504de51eb1cc6ab71c4446c58e891767ed2f873b6fb41')}
  assert (off,len(body),hashlib.sha256(body).hexdigest())==expected[variant]
 cases=[]
 for count in COUNTS:
  bridge_argv=[str(exe),'--boundary',variant,str(count)]
  bridge=subprocess.Popen(bridge_argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  assert bridge.stdout.readline().strip()=='READY'
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x2000000);u.mem_write(t['address'],body)
  obj=0x400000;sentinel=bytes((i*29+count)%256 for i in range(0x500));u.mem_write(obj,sentinel)
  trace=[];sites=[];writes=[];responses=[]
  def command(c):
   bridge.stdin.write(c+'\n');bridge.stdin.flush();return bridge.stdout.readline().strip()
  def hook(u,a,n,_):
   if a==0x1f00000:u.emu_stop();return
   if t['address']<=a<a+n<=t['address']+t['size']:sites.append(a);return
   assert u.reg_read(UC_ARM_REG_R0)==obj
   if a==0x2dd94:
    assert not trace
    result=command('B');assert result=='BASE 1';responses.append(result);trace.append('actual-source-base-destructor')
   elif a==0xac10:
    assert variant=='d0' and trace==['actual-source-base-destructor']
    result=command('F');assert result=='FREE 1';responses.append(result);trace.append('actual-unsized-delete')
   else:raise AssertionError(hex(a))
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook)
  u.hook_add(UC_HOOK_MEM_WRITE,lambda u,ac,a,n,v,_:writes.append([a,n,v]))
  for reg,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_SP,0x8ff000),(UC_ARM_REG_LR,0x1f00000)]:u.reg_write(reg,v)
  try:
   u.emu_start(t['address'],0x1f00000,count=100)
   assert u.reg_read(UC_ARM_REG_PC)==0x1f00000 and u.reg_read(UC_ARM_REG_SP)==0x8ff000
   assert u.reg_read(UC_ARM_REG_R0)==obj
   final=command('E');assert final.startswith('RESULT ')
   bridge.stdin.close();assert bridge.wait(timeout=10)==0,bridge.stderr.read()
  finally:
   if bridge.poll() is None:bridge.kill();bridge.wait()
  ow=[[a-obj,n,v] for a,n,v in writes if obj<=a<obj+len(sentinel)]
  assert ow==[[4,4,0x32f968+0xe0],[0x88,4,0x32f968+0xf0],[0x104,4,0x32f968+0x130],[0x45c,4,0x32f968+0x144],[0,4,0x32f968]]
  want=bytearray(sentinel)
  for a,n,v in ow:struct.pack_into('<I',want,a,v)
  assert bytes(u.mem_read(obj,len(sentinel)))==want
  cases.append(dict(count=count,bridge_arguments=['--boundary',variant,str(count)],boundary_commands=['B']+(['F'] if variant=='d0' else [])+['E'],trace=trace,boundary_responses=responses,result=final,sites=sites,object_writes=ow,terminal_pc=u.reg_read(UC_ARM_REG_PC),terminal_sp=u.reg_read(UC_ARM_REG_SP),return_object_preserved=True))
 return dict(elf_sha256=SHA,mangled=t['mangled'],range=dict(address=t['address'],size=t['size'],section='.text',section_index=t['section'],file_offset=off,sha256=hashlib.sha256(body).hexdigest()),cases=cases,boundary='Original ARM target only. At original base call invoke real qualified canonical MixerComponent destructor in live host subprocess; at original unsized delete call invoke genuine global delete there. ARM object dispatch writes stay in emulator. No original base/Core execution or original layout/ARM ABI claim. Host base borrows nonempty real Core vectors and application service resources containing CCL parameters/owned child; child cleanup occurs only at external owner destruction.')
