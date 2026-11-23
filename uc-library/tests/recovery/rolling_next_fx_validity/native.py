"""Original ARM oracle: complete app method and original local jump table.
No provider stubs, reconstructed-code expectations, Core binary execution or I/O.
"""
import hashlib,json,random,sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
NAME='_ZN8Presonus5Mixer11FXComponent19isValidParamForTypeENS_10EffectTypeEi'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
ELF=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11/packeting/seed-wave02-batch/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer')
def generate():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 with ELF.open('rb') as stream:
  e=ELFFile(stream);symbols=e.get_section_by_name('.symtab').get_symbol_by_name(NAME);assert len(symbols)==1;s=symbols[0];section=e.get_section(s['st_shndx']);offset=section['sh_offset']+s['st_value']-section['sh_addr'];body=data[offset:offset+s['st_size']]
  assert (s['st_value'],s['st_size'],s['st_shndx'])==(239692,164,12)
  assert hashlib.sha256(body).hexdigest()=='6aa9218e1c93729d75e31cabf48c498e22fed0c203b456595f4602e56a237848'
  identity=dict(mangled=NAME,address=s['st_value'],size=s['st_size'],section=section.name,section_index=s['st_shndx'],file_offset=offset,sha256=hashlib.sha256(body).hexdigest())
 types=[-2147483648,-65536,-1,*range(16),65536,2147483647]
 parameters=[-2147483648,-65536,*range(-20,32),65536,2147483647]
 inputs=[(t,p) for t in types for p in parameters];rng=random.Random(20261113)
 inputs += [(rng.randint(-2147483648,2147483647),rng.randint(-2147483648,2147483647)) for _ in range(512)]
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x3a000,4096);u.mem_write(239692,body);u.mem_map(0x800000,4096);u.mem_map(0x900000,4096)
 sites=set();writes=[]
 def code_hook(uc,address,size,_):
  assert 239692<=address<239856 and not 0x3a864<=address<0x3a898,hex(address)
  sites.add(address)
 def write_hook(uc,access,address,size,value,_):
  assert 0x800000<=address and address+size<=0x801000
  writes.append((address,size))
 u.hook_add(UC_HOOK_CODE,code_hook);u.hook_add(UC_HOOK_MEM_WRITE,write_hook)
 cases=[]
 for typ,param in inputs:
  for register,value in [(UC_ARM_REG_R0,0x70000000),(UC_ARM_REG_R1,typ&0xffffffff),(UC_ARM_REG_R2,param&0xffffffff),(UC_ARM_REG_SP,0x800f00),(UC_ARM_REG_LR,0x900000)]:u.reg_write(register,value)
  writes.clear();u.emu_start(239692,0x900000,count=100)
  assert u.reg_read(UC_ARM_REG_PC)==0x900000
  value=u.reg_read(UC_ARM_REG_R0);assert value in (0,1)
  cases.append({'input':[typ,param],'expected':value})
 return {'elf_sha256':SHA,'ranges':[identity],'cases':cases,'native_sites':sorted(sites),'scope':'Complete original 164-byte ARM function including 13-entry local jump table; no external calls, no stubs; unmapped this pointer and stack-only writes; all type classes and signed boundaries plus deterministic random cases. Original return/enum declarations and ABI remain unresolved.'}
if __name__=='__main__':
 observation=generate();Path(sys.argv[1]).write_text(json.dumps(observation,indent=2)+'\n');print(json.dumps({'native_cases':len(observation['cases']),'sites':len(observation['native_sites'])}))
