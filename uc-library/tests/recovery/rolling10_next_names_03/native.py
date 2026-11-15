import hashlib,json,struct,ctypes
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ELF=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared06/snapshot/rootfs/CS18_v13840/home/root/surface')
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
NAME='_ZN8Presonus7Surface9PageParamC1EPKcS3_'
LIBC=Path('/usr/lib/x86_64-linux-gnu/libc.so.6')
LIBC_SHA='755a371e86cc9f564ab54f66140747700fb0a103f698f659f2060f707897e09a'
def generate():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA;assert hashlib.sha256(LIBC.read_bytes()).hexdigest()==LIBC_SHA
 libc=ctypes.CDLL(str(LIBC));libc.strlen.argtypes=[ctypes.c_void_p];libc.strlen.restype=ctypes.c_size_t;libc.strncat.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t];libc.strncat.restype=ctypes.c_void_p
 with ELF.open('rb') as f:
  e=ELFFile(f);s=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name==NAME);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];body=data[off:off+s['st_size']];assert (s['st_value'],s['st_size'],hashlib.sha256(body).hexdigest())==(519112,324,'e2aea59315e392368f500056e3900c4e9dbe74077c08e18b9e625d69bd2a83e0')
  prefix=struct.unpack_from('<I',body,320)[0];section=next(z for z in e.iter_sections() if z['sh_addr']<=prefix<prefix+6<=z['sh_addr']+z['sh_size']);prefix_off=section['sh_offset']+prefix-section['sh_addr'];prefix_bytes=data[prefix_off:prefix_off+6];assert prefix_bytes==b'page:\0'
 cases=[]
 strings=[None,b'',b'A',b'GEQ',b'x'*57,b'x'*58,b'x'*59,b'y'*63,b'z'*64,b'Q'*127,b'ab\0ignored']
 def token(x):return '-' if x is None else ('e' if x==b'' else x.hex())
 for page in strings:
  for parameter in strings:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000);u.mem_write(s['st_value'],body);u.mem_write(prefix,prefix_bytes);u.mem_write(0x400000,b'\xa5'*128)
   if page is not None:u.mem_write(0x410000,page+b'\0')
   if parameter is not None:u.mem_write(0x420000,parameter+b'\0')
   def cstring(addr):
    out=bytearray()
    for i in range(2048):
     b=bytes(u.mem_read(addr+i,1))
     if b==b'\0':return bytes(out)
     out+=b
    raise AssertionError('unterminated domain')
   trace=[];sites=[];writes=[];provider_writes=[]
   def code(u,a,n,_):
    if s['st_value']<=a<s['st_value']+s['st_size']:sites.append(a);return
    if a==0xb02c:
     ptr=u.reg_read(UC_ARM_REG_R0);buf=ctypes.create_string_buffer(cstring(ptr));result=libc.strlen(ctypes.addressof(buf));trace.append(['strlen',ptr,result]);u.reg_write(UC_ARM_REG_R0,result)
    elif a==0xaf84:
     dst=u.reg_read(UC_ARM_REG_R0);src=u.reg_read(UC_ARM_REG_R1);count=u.reg_read(UC_ARM_REG_R2);assert 0<=count<=63
     before=cstring(dst);source=cstring(src);d=ctypes.create_string_buffer(256);ctypes.memmove(ctypes.addressof(d),before+b'\0',len(before)+1);b=ctypes.create_string_buffer(source);libc.strncat(ctypes.addressof(d),ctypes.addressof(b),count);after=ctypes.string_at(d);assert len(after)<=63
     u.mem_write(dst,after+b'\0');provider_writes.append([dst,(after+b'\0').hex()]);trace.append(['strncat',dst,source.hex(),count,after.hex()]);u.reg_write(UC_ARM_REG_R0,dst)
    else:raise RuntimeError(hex(a))
    u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,a,n,v,_:writes.append([a,n,v]))
   for reg,val in [(UC_ARM_REG_R0,0x400000),(UC_ARM_REG_R1,0x410000 if page is not None else 0),(UC_ARM_REG_R2,0x420000 if parameter is not None else 0),(UC_ARM_REG_SP,0x801000),(UC_ARM_REG_LR,0xf00000),(UC_ARM_REG_R4,0x12345678),(UC_ARM_REG_R8,0x87654321)]:u.reg_write(reg,val)
   u.emu_start(s['st_value'],0xf00000,count=400);assert u.reg_read(UC_ARM_REG_PC)==0xf00000 and u.reg_read(UC_ARM_REG_SP)==0x801000 and u.reg_read(UC_ARM_REG_R4)==0x12345678 and u.reg_read(UC_ARM_REG_R8)==0x87654321
   assert bytes(u.mem_read(0x400040,64))==b'\xa5'*64;output=cstring(0x400000);assert len(output)<=63
   nonstack=[w for w in writes if not 0x800000<=w[0]<0x801000];assert all(0x400000<=w[0]<0x400040 for w in nonstack)
   cases.append(dict(stdin=token(page)+' '+token(parameter),stdout=output.hex(),sites=sites,trace=trace,nonstack_writes=nonstack,provider_writes=provider_writes,raw_buffer=bytes(u.mem_read(0x400000,64)).hex()))
 return dict(elf_sha256=SHA,ranges=[dict(mangled=NAME,address=s['st_value'],size=s['st_size'],section=sec.name,file_offset=off,sha256=hashlib.sha256(body).hexdigest())],cases=cases,provider=dict(path=str(LIBC),sha256=LIBC_SHA,adaptation='Actual host libc strlen/strncat independently called on bounded translated native buffers; source-port runtime boundary, no original firmware libc or ARM ABI equivalence'),prefix=dict(address=prefix,file_offset=prefix_off,hex=prefix_bytes.hex(),sha256=hashlib.sha256(prefix_bytes).hexdigest()))
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
