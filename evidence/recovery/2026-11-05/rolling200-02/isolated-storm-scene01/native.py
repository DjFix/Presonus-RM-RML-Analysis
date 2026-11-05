from pathlib import Path
import hashlib,json,struct,platform
import unicorn, elftools
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
R=Path.cwd();O=R/'evidence/recovery/2026-11-05/rolling200-02/isolated-storm-scene01';elf=R/'rootfs/RML16AI_Rack_13731/home/root/mixer';blob=elf.read_bytes();digest=hashlib.sha256(blob).hexdigest();assert digest=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
with elf.open('rb') as f:
 e=ELFFile(f)
 symbols=[s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name=='_ZNK8Presonus22StormMixSceneComponent17createDefaultNameEi']
 assert len(symbols)==1 and symbols[0]['st_value']==0x73210 and symbols[0]['st_size']==64
 segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
lo=min(a for a,_,_ in segments)&~4095;hi=(max(a+n for a,n,_ in segments)+4095)&~4095
def mapped(address,size):
 with elf.open('rb') as f:
  e=ELFFile(f)
  for section in e.iter_sections():
   a=section['sh_addr']; n=section['sh_size']
   if section['sh_type']!='SHT_NOBITS' and a<=address and address+size<=a+n:
    off=section['sh_offset']+address-a; raw=blob[off:off+size]
    return {'section':section.name,'address':address,'size':size,'file_offset':off,'sha256':hashlib.sha256(raw).hexdigest(),'hex':raw.hex()}
 raise AssertionError('unmapped range')
cell_proof=mapped(0x458b24,4); assert cell_proof['hex']=='90901500'
string_proof=mapped(0x159090,10);assert bytes.fromhex(string_proof['hex'])==b'Mix Scene\0'
format_proof=mapped(0x339348,4);assert bytes.fromhex(format_proof['hex'])==b' %i\0'
body_proof=mapped(0x73210,64);assert body_proof['sha256']=='a4685df65b258a26b06989344195de989e9f6cbc71c7efa511a377121101c317'
roots={'scene':(0x73210,64,0x458b24,'Mix Scene',{0x1debc:0x73230,0x3987c:0x73240})}
OUT=0x60001000;TEXT=0x60002000;OBJ=0x60003000;STOP=0x71000000
cases=[];ranges=[]
for role,(start,size,cell,initial,sites) in roots.items():
 original=next(data[start-a:start-a+size] for a,n,data in segments if a<=start and start+size<=a+len(data));ranges.append({'role':role,'address':start,'size':size,'sha256':hashlib.sha256(original).hexdigest()})
 for prefix in ['<original>',initial,None,'','X','A'*15,'B'*30,'C'*31,'D'*40]:
  for index in [-2147483648,-2,-1,0,1,9,99,2147483646,2147483647]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(lo,hi-lo)
   for a,n,data in segments:u.mem_write(a,data)
   u.mem_map(0x60000000,0x10000);u.mem_map(0x70000000,0x10000);u.mem_map(STOP,4096)
   u.mem_write(OUT-8,b'\x5a'*8+b'\xa5'*32+b'\x5a'*8)
   if prefix not in [None,'<original>']:u.mem_write(TEXT,prefix.encode()+b'\0')
   if prefix != '<original>':u.mem_write(cell,struct.pack('<I',0 if prefix is None else TEXT))
   u.reg_write(UC_ARM_REG_R0,OUT);u.reg_write(UC_ARM_REG_R1,OBJ);u.reg_write(UC_ARM_REG_R2,index&0xffffffff);u.reg_write(UC_ARM_REG_SP,0x7000f000);u.reg_write(UC_ARM_REG_LR,STOP)
   trace=[];done=[]
   def string(a):
    result=bytearray()
    for i in range(256):
     x=u.mem_read(a+i,1)[0]
     if not x:return bytes(result)
     result.append(x)
    raise RuntimeError('unterminated out-of-domain string')
   def write_string(a,s):u.mem_write(a,s+b'\0')
   def hook(uc,pc,sz,data):
    if pc==STOP:done.append(True);uc.emu_stop();return
    if pc in range(start,start+56,4):return
    assert pc in sites,('unbound PC',hex(pc));assert uc.reg_read(UC_ARM_REG_LR)==sites[pc]
    a,b,c=[uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]];trace.append({'entry':pc,'lr':sites[pc],'r0':a,'r1':b,'r2':c})
    if pc==0x1debc:
     trace[-1]['constructor_input']=None if not b else string(b).decode();write_string(a,(string(b) if b else b'')[:31]);ret=a
    elif pc==0x3987c:
     trace[-1]['format']=string(b).decode();trace[-1]['before']=string(a).decode();assert string(b)==b' %i';signed=struct.unpack('<i',struct.pack('<I',c))[0];write_string(a,(string(a)+(' '+str(signed)).encode())[:31]);ret=a
    trace[-1]['output']=string(a).decode();trace[-1]['return_r0']=ret
    uc.reg_write(UC_ARM_REG_R0,ret);uc.reg_write(UC_ARM_REG_PC,sites[pc])
   u.hook_add(UC_HOOK_CODE,hook);u.emu_start(start,STOP+4,count=1000);assert done
   assert bytes(u.mem_read(OUT-8,8))==b'\x5a'*8 and bytes(u.mem_read(OUT+32,8))==b'\x5a'*8
   expected=string(OUT).decode()
   assert u.reg_read(UC_ARM_REG_R0)==OUT
   cases.append({'role':role,'index':index,'prefix':prefix,'native_output':expected,'native_trace':trace,'output_guard_bytes_preserved':True,'native_return_r0':OUT})
proof={'passed':True,'versions':{'python':platform.python_version(),'unicorn':unicorn.__version__,'pyelftools':elftools.__version__},'original_mangled':'_ZNK8Presonus22StormMixSceneComponent17createDefaultNameEi','original_elf_sha256':digest,'ranges':[body_proof], 'default_pointer':cell_proof,'default_string':string_proof,'format_string':format_proof,'cases':cases,'case_count':len(cases),'producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':'Exact original application instructions with explicit intercepted CCL string provider semantics; no original Core/libc instruction execution. Compiled pinned CCL comparison is performed by separate replay.py, never used to generate expected observations. Outputs and guard bytes checked; uninitialized unused string-tail bytes excluded. All integer boundaries including ARM32 addition wrap, null/empty/long default string. Private emulator memory only, no syscalls/network/devices. Isolated canonical source changes; not integration/readiness/ARM ABI proof.'}
(O/'FIXTURES.json').write_text(json.dumps(proof,indent=2)+'\n');print('Independent original-instruction replay passed:',len(cases),'cases, 1 function')
