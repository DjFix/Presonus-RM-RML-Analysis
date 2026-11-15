import hashlib,io,json,pathlib,sys,struct,subprocess,argparse
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
base=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared-remaining14-phasea-proposed01/snapshot')
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
provider=json.loads(subprocess.check_output([str(pathlib.Path(o.provider_exe).resolve()),'--observe-provider'],text=True));assert provider['empty_name'] and provider['views_count']==provider['pages_count']==provider['stack_count']==0 and provider['views_delta']==provider['pages_delta']==5
rows=[];ranges=[]
for variant,address,sha in [('C1',474984,'f9c624ec7818627d30a90eab644fdacdea62a21319f8e9afdf5dd579ec426742'),('C2',475240,'2f200dab019bf995b27e4e851d3215a509aae1c2a1c982d98dd333ec836583b7')]:
 code,rng=extract('_ZN8Presonus16MainLCDComponent'+variant+'Ev',address,256);assert rng['section']==12 and rng['sha256']==sha;ranges.append(rng)
 name_address=2041456;sec=next(s for s in e.iter_sections() if s['sh_addr']<=name_address<s['sh_addr']+s['sh_size']);name_offset=sec['sh_offset']+name_address-sec['sh_addr'];assert b[name_offset:name_offset+1]==b'\0'
 for fill in [0,85,170,255]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x70000,0x10000);u.mem_write(address,code);u.mem_map(0x110000,0x10000);u.mem_map(0x1f2000,0x1000);u.mem_write(name_address,b'\0');u.mem_map(0x100000,0x10000)
  obj=0x100000;u.mem_write(obj,bytes([fill])*256);calls=[]
  def hook(uc,pc,n,d):
   if pc==0x11af30:
    assert uc.reg_read(UC_ARM_REG_R0)==obj and uc.reg_read(UC_ARM_REG_R1)==name_address;calls.append('Component(empty-name)');uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   elif pc in [0x74748,0x748b0]:
    kind='views' if pc==0x74748 else 'pages';offset=0x94 if kind=='views' else 0xa8;assert uc.reg_read(UC_ARM_REG_R0)==obj+offset and uc.reg_read(UC_ARM_REG_R1)==0;calls.append(kind+'.resize(0)');uc.reg_write(UC_ARM_REG_R0,int(provider[kind+'_resize']));uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook)
  for reg,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_SP,0x10f000),(UC_ARM_REG_LR,0x70000)]:u.reg_write(reg,v)
  u.emu_start(address,0x70000,count=150);assert u.reg_read(UC_ARM_REG_PC)==0x70000 and u.reg_read(UC_ARM_REG_SP)==0x10f000
  offsets=[0,4,0x84,0x88,0x8c,0x90,0x94,0x98,0x9c,0xa0,0xa4,0xa8,0xac,0xb0,0xb4,0xb8,0xbc,0xc0,0xc4,0xc8,0xf4]
  words={hex(off):struct.unpack('<I',u.mem_read(obj+off,4))[0] for off in offsets};assert words['0x8c']==40 and words['0xf4']==0 and words['0xc4']==obj+0xcc
  rows.append(dict(variant=variant,prefill=fill,calls=calls,writes=words,returned=True,stack_restored=True))
emit(dict(ranges=ranges,provider_observations=provider,cases=rows,name_literal=dict(address=name_address,file_offset=name_offset,sha256=hashlib.sha256(b'\0').hexdigest()),limitations='Normal constructor-only. Original Core bodies excluded; actual source provider observations feed modeled boundaries. Native secondary vptr words recorded but no phantom host interfaces. EH/destructor/application behavior unproven.'))
