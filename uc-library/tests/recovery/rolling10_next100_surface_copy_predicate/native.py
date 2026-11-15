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
provider=json.loads(subprocess.check_output([str(pathlib.Path(o.provider_exe).resolve()),'--observe-provider'],text=True))
code,rng=extract('_ZNK8Presonus7Surface19FatChannelClipboard15CopyPasteFilter10shouldSaveEiPKcPv',649804,124);assert rng['sha256']=='2eac0bd6beeaed3b330ab0edffc44d79b6cfdbb727b8f12e0280cba211200320'
rows=[]
for case in provider:
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x90000,0x10000);u.mem_write(649804,code);u.mem_map(0x100000,0x20000);u.mem_map(0xa000,0x1000)
 put=lambda p,x:u.mem_write(p,struct.pack('<I',x&0xffffffff))
 param=0x100100;info=0x100200;controller=0x100300;channel=0x100400;put(param+12,info);put(info+4,case['tag']);calls=[]
 def hook(uc,pc,n,d):
  if pc==1171920:
   assert uc.reg_read(UC_ARM_REG_R0)==param;calls.append('getController');uc.reg_write(UC_ARM_REG_R0,controller if case['controller'] else 0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  elif pc==44632:
   assert uc.reg_read(UC_ARM_REG_R0)==controller;calls.append('actual-source-port-typed-cast-boundary');uc.reg_write(UC_ARM_REG_R0,channel if case['channel'] else 0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook)
 for reg,value in [(UC_ARM_REG_R0,0x100000),(UC_ARM_REG_R1,case['type']),(UC_ARM_REG_R2,0),(UC_ARM_REG_R3,param if case['object'] else 0),(UC_ARM_REG_SP,0x11f000),(UC_ARM_REG_LR,0x90000)]:u.reg_write(reg,value&0xffffffff)
 before=bytes(u.mem_read(param,0x400))
 u.emu_start(649804,0x90000,count=100);assert u.reg_read(UC_ARM_REG_PC)==0x90000 and u.reg_read(UC_ARM_REG_SP)==0x11f000
 assert bytes(u.mem_read(param,0x400))==before
 rows.append(dict(object_unchanged=True,input=case,result=u.reg_read(UC_ARM_REG_R0),calls=calls,returned=True,stack_restored=True))
emit(dict(range=rng,provider_observations=provider,cases=rows,limitations='Core getController and native dynamic_cast boundaries fed by independent actual CCL/SLChannel typed-source-port observations; original ARM RTTI/runtime not executed.'))
