import hashlib,io,json,pathlib,sys,struct,subprocess,argparse
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
base=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared06/snapshot')
b=(base/'rootfs/RML16AI_Rack_13731/home/root/mixer').read_bytes();assert hashlib.sha256(b).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
e=ELFFile(io.BytesIO(b));symbols={s.name:s for s in e.get_section_by_name('.symtab').iter_symbols()}
def extract(name,address,size):
 s=symbols[name];assert s['st_value']==address and s['st_size']==size
 sec=e.get_section(s['st_shndx']);assert sec['sh_addr']<=address and address+size<=sec['sh_addr']+sec['sh_size'];off=sec['sh_offset']+address-sec['sh_addr'];data=b[off:off+size]
 return data,dict(mangled=name,address=address,size=size,section=s['st_shndx'],file_offset=off,sha256=hashlib.sha256(data).hexdigest())
def emit(result):
 text=json.dumps(result,indent=2)+'\n';out=pathlib.Path(__file__).with_name('fixtures.json')
 if '--verify' in sys.argv:assert out.read_text()==text
 else:out.write_text(text)
code,rng=extract('_ZN8Presonus5Panel24BeastFrontPanelComponent17checkGeqViewRangeEv',499048,140)
assert rng['sha256']=='eb2bcd685fccdb94f65ceb05c5154703957f8eb407474d749db647f532ce24f8'
helper,hrng=extract('__fixsfsi',1407320,92);assert hrng['sha256']=='73908d204e4625c30fc21dff9a2f817e26c53d161164a032bd229a9dcdd6edee'
args=argparse.ArgumentParser();args.add_argument('--verify',action='store_true');args.add_argument('--provider-exe',required=True);options=args.parse_args()
provider_bits=list(map(int,subprocess.check_output([str(pathlib.Path(options.provider_exe).resolve()),'--observe-provider'],text=True).split()));assert len(provider_bits)==9
rows=[]
for value_index,value in enumerate( [None,-2.5,0,3.75,4.5,25.9,26,27,31.75]):
 for offset in [0,4,7,40]:
  for count in [0,4,32]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x70000,0x10000);u.mem_write(499048,code);u.mem_map(0x150000,0x10000);u.mem_write(1407320,helper);u.mem_map(0x100000,0x10000)
   put=lambda p,x:u.mem_write(p,struct.pack('<I',x&0xffffffff))
   obj=0x100000;param=0x100300;vt=0x100400;mixer=0x100500;provider=0x100800
   put(obj+0x17c,0 if value is None else param);put(obj+0x16c,offset);put(obj+0x8c,mixer);put(mixer+0x138,count);put(param,vt);put(vt+68,provider);calls=[]
   def hook(uc,pc,n,d):
    if pc==provider:
     calls.append('NumericParam::getValue');uc.reg_write(UC_ARM_REG_R0,provider_bits[value_index]);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,hook)
   for reg,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_SP,0x10f000),(UC_ARM_REG_LR,0x70000)]:u.reg_write(reg,v)
   u.emu_start(499048,0x70000,count=200);assert u.reg_read(UC_ARM_REG_PC)==0x70000 and u.reg_read(UC_ARM_REG_SP)==0x10f000
   rows.append(dict(value=value,offset=offset,count=count,result=u.reg_read(UC_ARM_REG_R0),new_offset=struct.unpack('<i',u.mem_read(obj+0x16c,4))[0],calls=calls,returned=True,stack_restored=True))
emit(dict(range=rng,helper=hrng,actual_provider_getter_bits=provider_bits,cases=rows,limitations='Original NumericParam getValue boundary fed by separate actual CCL getter observations; original non-Core f2iz executes. Finite float values and safe signed subtraction.'))
