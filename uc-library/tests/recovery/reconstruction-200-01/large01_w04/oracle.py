"""Original app ARM leaf execution only. No Core firmware execution or call stubs."""
import hashlib, json, struct, sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_WRITE, __version__
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
BASE=Path('temp/recovery-work/reconstruction-200-01/large-batch01/packets')
ELF=Path('rootfs/CS18_v13840/home/root/surface')
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
def generate():
 data=ELF.read_bytes(); assert hashlib.sha256(data).hexdigest()==SHA
 with ELF.open('rb') as f:
  elf=ELFFile(f); segments=[(int(s['p_vaddr']),s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
  records=[]; cases=[]
  for op in range(1,11):
   request=json.loads((BASE/f'large01_w04_{op:02d}'/'request.json').read_text()); target=request['targets'][0]
   symbol=next(s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name==target['mangled'])
   section=elf.get_section(symbol['st_shndx']); offset=int(section['sh_offset'])+int(symbol['st_value'])-int(section['sh_addr'])
   address=target['address']; size=target['size']; assert int(symbol['st_value'])==address and int(symbol['st_size'])==size
   records.append(dict(op=op,elf_sha256=SHA,elf_path=str(ELF),mangled=target['mangled'],address=address,size=size,section=section.name,file_offset=offset,range_sha256=hashlib.sha256(data[offset:offset+size]).hexdigest()))
   if op==1: inputs=[(a,b) for a in [0,1] for b in [0,1,2,3,0x7fffffff,0x80000000,0xffffffff]]
   elif op in (2,3,5): inputs=[(0,0),(1,0xffffffff)]
   elif op in (4,7,10): inputs=[(a,b) for a in range(14 if op!=10 else 9) for b in [0,0x300000,0x300080]]
   elif op==6: inputs=[(a,b) for a in [0,1] for b in [0,1,15,0x7fffffff,0x80000000,0xffffffff]]
   elif op==8: inputs=[(0,b) for b in [0,0x300000,0x300080]]
   else: inputs=[(a,0) for a in [0,1]]
   for a,b in inputs:
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    # Read-only original image is loaded to retain literal pools/strings.
    for va,blob in segments:
     lo=va&~4095; hi=(va+len(blob)+4095)&~4095
     u.mem_map(lo,hi-lo); u.mem_write(va,blob)
    u.mem_map(0x300000,0x10000); u.mem_map(0x400000,0x10000); u.mem_map(0x500000,0x10000)
    obj=0x400000; other=0x402000; arr=0x404000
    def word(at,value): u.mem_write(at,struct.pack('<I',value&0xffffffff))
    if op==1: word(obj+0x14,other if a else 0); word(other+0x6b4,b)
    if op==6: word(obj+0x2c,other if a else 0); word(other+0xc8,b)
    if op==9: u.mem_write(obj+0x140,bytes([a]))
    if op in (4,7,10):
     ptr,count={4:(0xd0,0xd4),7:(0xc8,0xcc),10:(0,4)}[op]
     word(obj+ptr,arr); word(obj+count,a)
     for i in range(a): word(arr+4*i,0x300000+4*i)
    before=bytes(u.mem_read(obj,0x6000)); writes=[]
    def trace(uc,access,addr,size,value,user):
     if obj<=addr<obj+0x6000: writes.append([addr-obj,size,value&((1<<(size*8))-1)])
    u.hook_add(UC_HOOK_MEM_WRITE,trace)
    u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,b);u.reg_write(UC_ARM_REG_SP,0x50f000);u.reg_write(UC_ARM_REG_LR,0x300000)
    u.emu_start(address,0x300000,count=100)
    assert u.reg_read(UC_ARM_REG_PC)==0x300000
    r=u.reg_read(UC_ARM_REG_R0)
    if op in (2,3): output=bytes(u.mem_read(r,32)).split(b'\0')[0].decode()
    elif op in (4,7,10):
     n=struct.unpack('<I',u.mem_read(obj+count,4))[0]
     output=' '.join(map(str,[n]+list(struct.unpack('<'+'I'*n,u.mem_read(arr,n*4)))))
    elif op==8: output=str(struct.unpack('<I',u.mem_read(obj+0xe8,4))[0])
    else: output=str(r)
    after=bytes(u.mem_read(obj,0x6000)); changed=[i for i,(x,y) in enumerate(zip(before,after)) if x!=y]
    cases.append(dict(input=[op,a,b],output=output,writes=writes,changed_bytes=changed,return_r0=r,external_calls=[],instructions_bound=100))
 return dict(version=1,producer=str(Path(__file__)),unicorn_version=__version__,originals=records,cases=cases,domain='Valid nonnegative container sizes 0..13 (handler 0..8), repeated/null borrowed identities, full 32-bit selected flags/offset boundaries, canonical bool bytes 0/1. No calls leave exact leaf range; complete object/array writes captured; stack writes excluded.')
if __name__=='__main__': Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
