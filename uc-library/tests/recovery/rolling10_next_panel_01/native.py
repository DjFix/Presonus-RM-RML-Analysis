import hashlib,io,json,pathlib,sys,struct
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
code,rng=extract('_ZNK8Presonus5Panel24BeastFrontPanelComponent17getTablesForGroupEiRPKiS4_Ri',498888,160)
assert rng['sha256']=='cfa8ea93c00c08d08d7cb2989119064ecaa4d21653e46f11f3f47940484b6ca9'
payloads={}
for name,address,size in [('gChSelectTable',3425780,136),('gChSelectOutTable',3425916,80),('gSoloTable',3425996,136),('gSoloOutTable',3426132,80),('gChMuteTable',3426212,136),('gChMuteOutTable',3426348,80)]:
 mangled='_ZN8Presonus5BeastL'+str(len(name))+name+'E';data,meta=extract(mangled,address,size);payloads[str(address)]=dict(meta,words=list(struct.unpack('<'+str(size//4)+'i',data)))
rows=[]
for group in [0,1,2,-1,3,2147483647,-2147483648]:
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x70000,0x10000);u.mem_write(498888,code);u.mem_map(0x100000,0x10000)
 put=lambda p,x:u.mem_write(p,struct.pack('<I',x&0xffffffff))
 put(0x100100,0xdead0001);put(0x100104,0xdead0002);put(0x100108,77);put(0x10f000,0x100108)
 for reg,v in [(UC_ARM_REG_R0,0x100000),(UC_ARM_REG_R1,group),(UC_ARM_REG_R2,0x100100),(UC_ARM_REG_R3,0x100104),(UC_ARM_REG_SP,0x10f000),(UC_ARM_REG_LR,0x70000)]:u.reg_write(reg,v&0xffffffff)
 u.emu_start(498888,0x70000,count=100);assert u.reg_read(UC_ARM_REG_PC)==0x70000 and u.reg_read(UC_ARM_REG_SP)==0x10f000
 a,c,n=struct.unpack('<III',u.mem_read(0x100100,12));rows.append(dict(group=group,first=a,second=c,count=n,returned=True,stack_restored=True))
emit(dict(range=rng,payloads=payloads,cases=rows))
