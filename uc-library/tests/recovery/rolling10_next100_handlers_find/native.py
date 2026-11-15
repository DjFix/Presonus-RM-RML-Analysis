"""Verified original app ranges; actual host strcmp boundary; no Core body execution."""
import ctypes,hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[4]
NAME='_ZNK8Presonus22AssignmentHandlerTable11findHandlerEPKc'
GET='_ZNK8Presonus7Surface15DAWMixerHandler7getNameEv'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
def inputs():
 names=[[],['P'],['P','P'],['-','.','P','P'],['617578','P','P'],['4441574d49584552','P','.'],['c3a9','c389','.'],['.','-']]
 queries=['-','.','6461776d69786572','4441574d49584552','617578','646177','c3a9','c389','6d697373696e67']
 return [dict(names=n,query=q) for n in names for q in queries]
def decode(token):return b'' if token in ['-','.'] else bytes.fromhex(token)
def observations():
 binding=json.loads((ROOT/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared-next-flow01-rolling10_names.json').read_text());elf=Path(binding['rootfs/CS18_v13840/home/root/surface']['frozen_read_path']);data=elf.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 with elf.open('rb') as f:
  e=ELFFile(f);symtab=e.get_section_by_name('.symtab')
  def symbol(name,address,size):
   s=next(s for s in symtab.get_symbol_by_name(name) if s['st_value']==address and s['st_size']==size);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+address-sec['sh_addr'];return dict(mangled=name,address=address,size=size,section=sec.name,file_offset=off,sha256=hashlib.sha256(data[off:off+size]).hexdigest()),data[off:off+size]
  target,code=symbol(NAME,0x75dc0,136);assert target['sha256']=='d1b80f21aa01824cc5b5d657bd8f05f22fa7d107a59f7d0d281fb5831904d1d9'
  provider,provider_code=symbol(GET,0x7b80c,24)
  vt=next(s for s in symtab.get_symbol_by_name('_ZTVN8Presonus7Surface15DAWMixerHandlerE') if s['st_value']==1697280);vsec=e.get_section(vt['st_shndx']);voff=vsec['sh_offset']+vt['st_value']-vsec['sh_addr'];vbytes=data[voff:voff+vt['st_size']];assert hashlib.sha256(vbytes).hexdigest()=='3fab541bdc5a11f35d73c075fc24c8e8da6a87528bdeb6ca81dc6118b50470f6';assert struct.unpack_from('<I',vbytes,8+3*4)[0]==provider['address']
  literals=[]
  for address,size in [(0x1f2670,1),(0x19e238,9)]:
   sec=next(s for s in e.iter_sections() if s['sh_type']!='SHT_NOBITS' and s['sh_addr']<=address and address+size<=s['sh_addr']+s['sh_size']);off=sec['sh_offset']+address-sec['sh_addr'];payload=data[off:off+size];literals.append(dict(address=address,size=size,section=sec.name,file_offset=off,hex=payload.hex(),sha256=hashlib.sha256(payload).hexdigest()))
 assert bytes.fromhex(literals[0]['hex'])==bytes([0]);assert bytes.fromhex(literals[1]['hex'])==b'dawmixer'+bytes([0])
 libcpath=Path('/usr/lib/x86_64-linux-gnu/libc.so.6');libc=ctypes.CDLL(str(libcpath));strcmp=libc.strcmp;strcmp.argtypes=[ctypes.c_char_p,ctypes.c_char_p];strcmp.restype=ctypes.c_int
 cases=[]
 for case in inputs():
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages={0x75000,0x7b000,0xb000,0x200000,0x210000,0x220000,0x300000,0x400000,0x410000,0x420000,0x19e000,0x1f2000}
  for page in pages:u.mem_map(page,4096)
  u.mem_write(0x75dc0,code);u.mem_write(provider['address'],provider_code)
  for lit in literals:u.mem_write(lit['address'],bytes.fromhex(lit['hex']))
  # Native receiver vtable slot3 uses exact verified getName identity.
  u.mem_write(0x41000c,struct.pack('<I',0x420000));u.mem_write(0x19e000+(1697280&4095),vbytes)
  names=case['names'];objects=[0x210000+i*64 for i in range(len(names))]
  u.mem_write(0x200000,struct.pack('<II',0x220000,len(names)))
  for i,(token,obj) in enumerate(zip(names,objects)):
   u.mem_write(0x220000+4*i,struct.pack('<I',obj));u.mem_write(obj,struct.pack('<I',1697280+8 if token=='P' else 0x410000));u.mem_write(0x210800+i*128,decode(token) + bytes([0]) if token!='P' else bytes([0]))
  u.mem_write(0x200800,decode(case['query'])+bytes([0]));u.reg_write(UC_ARM_REG_R0,0x200000);u.reg_write(UC_ARM_REG_R1,0 if case['query']=='-' else 0x200800);u.reg_write(UC_ARM_REG_SP,0x300f00);u.reg_write(UC_ARM_REG_LR,0x400000);calls=[];comparisons=[];writes=[]
  def cstr(address):
   result=bytearray()
   for i in range(256):
    v=u.mem_read(address+i,1)[0]
    if v==0:return bytes(result)
    result.append(v)
   raise AssertionError('bounded string exceeded')
  def hook(uc,pc,size,_):
   if pc==0x400000:uc.emu_stop();return
   if pc in [0x420000,provider['address']]:
    index=objects.index(uc.reg_read(UC_ARM_REG_R0));calls.append(index)
    if pc==0x420000:
     token=names[index];uc.reg_write(UC_ARM_REG_R0,0 if token=='-' else 0x210800+index*128);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   if pc==0xb0f8:
    a=cstr(uc.reg_read(UC_ARM_REG_R0));b=cstr(uc.reg_read(UC_ARM_REG_R1));value=strcmp(a,b);comparisons.append(dict(left=a.hex(),right=b.hex(),result=value));uc.reg_write(UC_ARM_REG_R0,value&0xffffffff);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   assert 0x75dc0<=pc<0x75e44 or provider['address']<=pc<provider['address']+20,hex(pc)
  def write(uc,access,address,size,value,_):
   assert 0x300000<=address<0x301000,hex(address)
   writes.append(dict(address=address,size=size,value=value))
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write);u.emu_start(0x75dc0,0,count=10000);assert u.reg_read(UC_ARM_REG_PC)==0x400000;assert u.reg_read(UC_ARM_REG_SP)==0x300f00
  returned=u.reg_read(UC_ARM_REG_R0);result=objects.index(returned) if returned else -1
  cases.append(dict(**case,result=result,calls=calls,comparisons=comparisons,writes=writes,return_pc=u.reg_read(UC_ARM_REG_PC),sp_restored=True))
 return dict(elf_sha256=SHA,target=target,provider=provider,vtable=dict(address=1697280,size=len(vbytes),sha256=hashlib.sha256(vbytes).hexdigest(),slot=3,address_point_bias=8,target=provider['address']),literals=literals,host_strcmp=dict(path=str(libcpath),sha256=hashlib.sha256(libcpath.read_bytes()).hexdigest()),cases=cases,limitations='Actual original app findHandler and real DAWMixer getName ranges execute; only strcmp uses actual host libc. Other named/null getName receivers are explicitly abstract-interface fixtures, not recovered app providers. Stable vectors/non-null handlers; no ownership, concurrency, unknown overrides, original static return declaration, ARM interoperability or hardware claim.')
if __name__=='__main__':print(json.dumps(observations(),indent=2))
