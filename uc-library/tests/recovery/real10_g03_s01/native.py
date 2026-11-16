"""Full selected app and original PageComponent getter execution."""
import hashlib,json,pathlib,struct,subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4];BASE=pathlib.Path(__file__).parent;TASK=BASE.name
SNAP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/prepared-main/snapshot')
PACKET=ROOT/'temp/recovery-work/reconstruction10x10-20261116/prepared-main/packets'/TASK
EXP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/expansions/bound-20261116T055348/g03-mainlcd-dtor/native-context.json')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def generate(exe):
 target=json.loads((PACKET/'request.json').read_text())['targets'][0];ev=SNAP/('temp/recovery-work/reconstruction10x10-20261116/native/'+TASK+'.json');body=json.loads(ev.read_text())['body'];helper=next(v for v in json.loads(EXP.read_text())['bodies'].values() if v['address']==0x73ec4)
 elf=SNAP/'rootfs/CS18_v13840/home/root/surface';assert sha(elf)==target['original_elf_sha256'];raw=elf.read_bytes();ranges=[body,helper]
 with elf.open('rb') as f:
  e=ELFFile(f)
  for b in ranges:
   sec=e.get_section(b['section_index']);assert sec.name==b['section'];assert sec['sh_offset']+b['address']-sec['sh_addr']==b['file_offset'];assert hashlib.sha256(raw[b['file_offset']:b['file_offset']+b['size']]).hexdigest()==b['bytes_sha256']
 inputs=[[count,linked,n] for count in [0,1,3] for linked in [0,1] for n in [0,1,9]];payload=''.join(' '.join(map(str,x))+'\n' for x in inputs);provider=subprocess.check_output([str(exe),'provider'],input=payload.encode()).decode().splitlines();assert len(provider)==len(inputs);cases=[]
 for inp,line in zip(inputs,provider):
  count,linked,n=inp;cleaned,pcap,vcap,borrowed=map(int,line.split());assert cleaned==count and borrowed==77
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for addr in {body['address']&~4095,helper['address']&~4095,0x74000,0x11b000,0xa000,0x1000000,0x1100000,0x1200000}:u.mem_map(addr,4096)
  for r in ranges:u.mem_write(r['address'],raw[r['file_offset']:r['file_offset']+r['size']])
  obj=0x1000000;view=obj+0x400;stop=0x1200000;sites=[];writes=[];calls=[]
  def w(p,v):u.mem_write(p,struct.pack('<I',v))
  w(obj+0x90,view if linked else 0);w(view+0x204,obj);w(obj+0xc8,obj+0x900)
  before=bytes(u.mem_read(obj,4096))
  def hook(uc,a,size,user):
   if a in [0x749b0,0x74848,0x11b5e0,0xad5c]:
    expected={0x749b0:obj+0xa8,0x74848:obj+0x94,0x11b5e0:obj,0xad5c:obj}[a];assert uc.reg_read(UC_ARM_REG_R0)==expected;calls.append([hex(a),expected-obj]);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   assert any(r['address']<=a<a+size<=r['address']+r['size'] for r in ranges),hex(a);sites.append(a)
  def write(uc,access,a,size,v,user):
   if obj<=a<a+size<=obj+4096:writes.append([a-obj,size,v])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for r,v in [(UC_ARM_REG_SP,0x1100800),(UC_ARM_REG_LR,stop),(UC_ARM_REG_R0,obj)]:u.reg_write(r,v)
  u.emu_start(body['address'],stop,count=250);assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_R0)==obj
  clear=struct.unpack('<I',u.mem_read(view+0x204,4))[0]==0;current=struct.unpack('<I',u.mem_read(obj+0xc8,4))[0]==0;deleted=sum(c[0]=='0xad5c' for c in calls)
  expected=f'{cleaned} {deleted} {int(clear)} {int(current)} {pcap} {vcap} {borrowed}'
  assert [c[0] for c in calls][:3]==['0x749b0','0x74848','0x11b5e0']
  cases.append(dict(input=inp,expected=expected,provider=line,native_calls=calls,native_object_writes=writes,native_instructions=sites,native_return='original receiver'))
 return dict(producer={'path':str(BASE.relative_to(ROOT)/'native.py'),'sha256':sha(__file__),'unicorn_version':__import__('unicorn').__version__,'method':'independent original ARM instruction execution and separately observed source providers'},case_count=len(cases),elf_sha256=target['original_elf_sha256'],target_range={k:body[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},helper_ranges=[{k:helper[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}],cases=cases,scope='18 valid lifecycle cases: 0/1/3 actual owned CCL children, absent/present borrowed observer link and 0/1/9 borrowed page/view pointer elements. Full original MainScreen variant and MainLCD D2 instructions execute, including observer/current writes and destructor ordering. Native Core vector/component and delete calls are explicit trace boundaries; real pinned CCL provider separately observes child cleanup, buffer release and borrowed page survival. Product actual D1 or D0 executes separately; actual allocator wrappers observe D0 deallocation, D1 checked before explicit storage release. No EH, native provider body execution, original layout/ARM ABI/hardware claim.')
