"""Execute exact original app instructions and actually free the mapped host object.
The preloaded bridge observes libstdc++ unsized delete reaching real glibc free.
No Python free, reconstructed release, Core binary or device code is invoked.
"""
import ctypes,hashlib,json,os,pathlib,struct,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,__version__
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4];NAME='rolling10_next100_omap_release';TEST=pathlib.Path('uc-library/tests/recovery')/NAME;SCRATCH=pathlib.Path('temp/recovery-work')/NAME
PACKET=pathlib.Path('temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/packets')/NAME
SNAP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/snapshot')
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07';MANGLED='_ZN8Presonus3Dsp17OMAPTargetHandler7releaseEv'
def generate():
 req=json.loads((ROOT/PACKET/'request.json').read_text());binding=req['reconstruction_contract'];blob=(SNAP/binding['path']).read_bytes();assert hashlib.sha256(blob).hexdigest()==binding['sha256'];contract=json.loads(blob)
 evidence={}
 def read_refs(x):
  if isinstance(x,dict):
   if 'path' in x and 'sha256' in x:
    p=x['path'];b=(SNAP/p).read_bytes();assert hashlib.sha256(b).hexdigest()==x['sha256'];evidence[p]=json.loads(b) if p.endswith('.json') else None
   for v in x.values():read_refs(v)
  elif isinstance(x,list):
   for v in x:read_refs(v)
 read_refs(contract)
 provider=next(v for k,v in evidence.items() if k.endswith('ACTUAL_DELETE_PROVIDER.json'));runtime=pathlib.Path(provider['library']);assert hashlib.sha256(runtime.read_bytes()).hexdigest()==provider['sha256']
 elf=SNAP/'rootfs/RML16AI_Rack_13731/home/root/mixer';raw=elf.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 with elf.open('rb') as f:
  e=ELFFile(f);s=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name==MANGLED);sec=e.get_section(s['st_shndx']);offset=sec['sh_offset']+s['st_value']-sec['sh_addr'];body=raw[offset:offset+s['st_size']];assert (s['st_value'],s['st_size'],s['st_info']['bind'])==(0x86af0,20,'STB_WEAK');assert hashlib.sha256(body).hexdigest()=='1d69a0649c1059d5babb0e12a7a39634eb86c153dd0d1dd829a845585f7f78ef'
 bridge=(ROOT/SCRATCH/'native-bridge.so').resolve();assert str(bridge) in os.environ.get('LD_PRELOAD',''),'Oracle bridge must be preloaded to observe actual dynamic runtime free'
 b=ctypes.CDLL(str(bridge));b.omap_allocate.restype=ctypes.c_void_p;b.omap_delete.argtypes=[ctypes.c_void_p];b.omap_delete.restype=ctypes.c_uint;b.omap_count.argtypes=[ctypes.c_uint];b.omap_count.restype=ctypes.c_uint;b.omap_delete_provider.restype=ctypes.c_char_p;b.omap_port_size.restype=ctypes.c_uint
 actual_runtime=pathlib.Path(b.omap_delete_provider().decode()).resolve();assert actual_runtime==runtime.resolve()
 cases=[];mappings=[]
 for index in range(32):
  native_this=0x2000000+index*0x1000;sp=0x1108000+index*16;fp=0x11223300+index;lr=0x1200000;host=b.omap_allocate();assert host
  # native_this is deliberately unmapped: any object dereference would fail.
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x100000);u.mem_write(0x86af0,body);u.mem_map(0x1100000,0x10000);u.mem_map(0x1200000,0x1000)
  visits=[];writes=[];deletes=[]
  def hook(u,a,size,data):
   if 0x86af0<=a<0x86af0+20:visits.append(a);return
   if a==0xac10:
    pointer=u.reg_read(UC_ARM_REG_R0);assert pointer==native_this;assert not deletes
    assert b.omap_delete(host)==1
    counts=[b.omap_count(i) for i in range(4)];assert counts==[1,1,1,1]
    deletes.append({'native_pointer':pointer,'allocations':counts[0],'unsized_delete_calls':counts[1],'actual_free_calls':counts[2],'unchanged_host_pointer_matches':counts[3]})
    u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
   raise RuntimeError('Unexpected execution '+hex(a))
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,a,n,v,d:writes.append([a,n,v]))
  for reg,val in [(UC_ARM_REG_R0,native_this),(UC_ARM_REG_SP,sp),(UC_ARM_REG_R11,fp),(UC_ARM_REG_LR,lr)]:u.reg_write(reg,val)
  u.emu_start(0x86af0,lr,count=20)
  assert visits==list(range(0x86af0,0x86af0+20,4));assert u.reg_read(UC_ARM_REG_SP)==sp and u.reg_read(UC_ARM_REG_R11)==fp and u.reg_read(UC_ARM_REG_PC)==lr;assert len(deletes)==1;assert all(sp-16<=a and a+n<=sp for a,n,v in writes)
  mappings.append({'case':index,'native_pointer':native_this,'actual_host_allocation':hex(host),'actual_host_delete_argument':hex(host),'observed_actual_free_calls':b.omap_count(2),'port_size':b.omap_port_size()});b.omap_finish()
  cases.append({'input':{'native_pointer':native_this,'sp':sp,'fp':fp},'instructions':visits,'stack_writes':writes,'stack_balanced':True,'frame_preserved':True,'delete':deletes[0]})
 pathlib.Path(os.environ['OMAP_MAPPING_OUT']).write_text(json.dumps({'mappings':mappings,'runtime':str(actual_runtime),'runtime_sha256':provider['sha256'],'bridge_sha256':hashlib.sha256(bridge.read_bytes()).hexdigest()},indent=2)+'\n')
 return {'task_id':NAME,'elf_sha256':SHA,'range':{'mangled':MANGLED,'address':0x86af0,'size':20,'section':sec.name,'section_index':s['st_shndx'],'file_offset':offset,'bytes_sha256':hashlib.sha256(body).hexdigest(),'binding':'STB_WEAK'},'provider':provider,'port_size':b.omap_port_size(),'emulator_version':__version__,'cases':cases,'domain':'32 independent live exclusive global-new allocations of the explicit trivial source-port type, each released exactly once; native pointer translated to separate actual host allocation, actual unsized host operator delete and real glibc free instrumented. All five original instructions/20 bytes execute with varied native this/SP/FP, preserved frame/stack/this and no object access. Source replay independently exercises repeated fresh allocation/release cycles. No null/stack/placement/custom allocator/double release, original constructor/destructor/class size/layout/hardware/ARM ABI credit.'}
if __name__=='__main__':
 out=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/TEST/'fixtures.json';out.write_text(json.dumps(generate(),indent=2)+'\n')
