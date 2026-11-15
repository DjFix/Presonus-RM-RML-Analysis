import hashlib,io,json,pathlib,sys,struct,subprocess,argparse
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
base=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/snapshot')
b=(base/'rootfs/CS18_v13840/home/root/surface').read_bytes();assert hashlib.sha256(b).hexdigest()=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
e=ELFFile(io.BytesIO(b));symbols={s.name:s for s in e.get_section_by_name('.symtab').iter_symbols()}
def extract(name,address,size):
 s=symbols[name];assert s['st_value']==address and s['st_size']==size
 sec=e.get_section(s['st_shndx']);assert sec['sh_addr']<=address and address+size<=sec['sh_addr']+sec['sh_size'];off=sec['sh_offset']+address-sec['sh_addr'];data=b[off:off+size]
 return data,dict(mangled=name,address=address,size=size,section=s['st_shndx'],file_offset=off,sha256=hashlib.sha256(data).hexdigest())
def emit(result):
 text=json.dumps(result,indent=2)+'\n';out=pathlib.Path(__file__).with_name('fixtures.json')
 if '--verify' in sys.argv:assert out.read_text()==text
 else:out.write_text(text)
args=argparse.ArgumentParser();args.add_argument('--verify',action='store_true');args.add_argument('--provider-exe',required=True);o=args.parse_args()
provider=json.loads(subprocess.check_output([str(pathlib.Path(o.provider_exe).resolve()),'--observe-provider'],text=True));assert provider['component_name']=='firmwareupdate' and provider['worker_idle']
rows=[];ranges=[]
for variant,address,sha in [('C1',649240,'cbd215802e6bbc9d43ee0efb6bde8225245b8b3586f58984b6c079b35b02d76a'),('C2',649372,'29a046cb0d0c4f05b47f511e78913306123311e2b12f476fb9c067f6752d1fed')]:
 code,rng=extract('_ZN8Presonus7Surface23FirmwareUpdateComponent'+variant+'Ev',address,132)
 assert rng['sha256']==sha and rng['section']==12
 ranges.append(rng)
 for fill in [0,85,170,255]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x90000,0x10000);u.mem_write(address,code);u.mem_map(0xa000,0x1000);u.mem_map(0xe0000,0x10000);u.mem_map(0x110000,0x10000);u.mem_map(0x190000,0x10000);u.mem_map(0x100000,0x10000)
  # Read actual verified string via its own source ELF section mapping.
  name_address=1701624;sec=next(sec for sec in e.iter_sections() if sec['sh_addr']<=name_address<sec['sh_addr']+sec['sh_size']);name_offset=sec['sh_offset']+name_address-sec['sh_addr'];name=b[name_offset:name_offset+15];assert name==b'firmwareupdate\0';u.mem_write(name_address,name)
  obj=0x100000;worker=0x100400;u.mem_write(obj,bytes([fill])*160);calls=[]
  def hook(uc,pc,n,d):
   if pc==0x11af30:
    assert uc.reg_read(UC_ARM_REG_R0)==obj and uc.reg_read(UC_ARM_REG_R1)==name_address;calls.append('Component(firmwareupdate)');uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   elif pc==0xa90c:
    assert uc.reg_read(UC_ARM_REG_R0)==56;calls.append('native-new-56');uc.reg_write(UC_ARM_REG_R0,worker);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   elif pc==0xeaa78:
    assert uc.reg_read(UC_ARM_REG_R0)==worker;calls.append('BackgroundWorker()');uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook)
  for reg,value in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_SP,0x10f000),(UC_ARM_REG_LR,0x90000)]:u.reg_write(reg,value)
  u.emu_start(address,0x90000,count=100);assert u.reg_read(UC_ARM_REG_PC)==0x90000 and u.reg_read(UC_ARM_REG_SP)==0x10f000
  words={str(offset):struct.unpack('<I',u.mem_read(obj+offset,4))[0] for offset in [0,4,132,144,148]};assert words['144']==worker and words['148']==0
  rows.append(dict(variant=variant,prefill=fill,calls=calls,writes=words,returned=True,stack_restored=True))
emit(dict(ranges=ranges,provider_observations=provider,cases=rows,name_literal=dict(address=name_address,file_offset=name_offset,sha256=hashlib.sha256(name).hexdigest()),limitations='Normal successful allocation only. Core/native allocator calls modeled using independent actual host-provider observations; original exception landing pads not executed. Vptr writes preserved as native observations, not host interfaces/layout.'))
