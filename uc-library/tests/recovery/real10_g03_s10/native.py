"""Original app ARM execution; Core and allocator calls are explicit boundaries."""
import hashlib,json,pathlib,struct,subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
SNAP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/prepared-main/snapshot')
BASE=pathlib.Path(__file__).parent
TASK=BASE.name
PACKET=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/prepared-main/packets')/TASK
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def generate(exe):
 req=json.loads((PACKET/'request.json').read_text());target=req['targets'][0]
 ev=SNAP/('temp/recovery-work/reconstruction10x10-20261116/native/'+TASK+'.json');body=json.loads(ev.read_text())['body']
 elf=SNAP/'rootfs/CS18_v13840/home/root/surface';assert sha(elf)==target['original_elf_sha256'];raw=elf.read_bytes()
 with elf.open('rb') as f:
  sec=ELFFile(f).get_section(body['section_index']);assert sec.name==body['section'];assert sec['sh_offset']+body['address']-sec['sh_addr']==body['file_offset']
 assert hashlib.sha256(raw[body['file_offset']:body['file_offset']+body['size']]).hexdigest()==body['bytes_sha256']
 inputs=[0,1,3,8];provider=subprocess.check_output([str(exe),'provider'],input=''.join(str(n)+'\n' for n in inputs).encode()).decode().splitlines();cases=[]
 for n,line in zip(inputs,provider):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for addr in [body['address']&~4095,0x11b000,0xa000,0x1000000,0x1100000,0x1200000]:u.mem_map(addr,4096)
  u.mem_write(body['address'],raw[body['file_offset']:body['file_offset']+body['size']]);obj=0x1000000;stop=0x1200000;trace=[];writes=[];sites=[]
  def hook(uc,a,size,user):
   if a in [0x11b5e0,0xad5c]:
    assert uc.reg_read(UC_ARM_REG_R0)==obj;trace.append('Core::Portable::Component::~Component' if a==0x11b5e0 else 'operator delete(void*)');uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   assert body['address']<=a<a+size<=body['address']+body['size'];sites.append(a)
  def write(uc,access,a,size,value,user):
   if obj<=a<a+size<=obj+4096:writes.append([a-obj,size,value])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for r,v in [(UC_ARM_REG_SP,0x1100800),(UC_ARM_REG_LR,stop),(UC_ARM_REG_R0,obj)]:u.reg_write(r,v)
  u.emu_start(body['address'],stop,count=100);assert u.reg_read(UC_ARM_REG_PC)==stop
  assert trace==['Core::Portable::Component::~Component','operator delete(void*)'];assert u.reg_read(UC_ARM_REG_R0)==obj
  cases.append(dict(input=[n],expected=line,provider=line,native_calls=trace,native_object_writes=writes,native_instructions=sites,native_return='original receiver'))
 return dict(producer={'path':str(BASE.relative_to(ROOT)/'native.py'),'sha256':sha(__file__),'unicorn_version':__import__('unicorn').__version__,'method':'independent original ARM instruction execution and separately observed source providers'},case_count=len(cases),elf_sha256=target['original_elf_sha256'],target_range={k:body[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']},cases=cases,scope='Valid receiver, 0/1/3/8 actual owned CCL children. Original application executes all instructions; native Core destructor and allocator are boundary stubs only. Actual pinned source provider and product independently destroy children and invoke the wrapped real unsized delete. Vtable writes recorded as ARM layout observations, not portable layout equality. No hardware, exceptions, child arrays, concurrency or ARM ABI claim.')
