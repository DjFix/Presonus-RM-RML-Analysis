"""Independent ARM execution; never imports reconstructed C++ behavior."""
import hashlib,json,struct,sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'

def run():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 proof=[]
 with ELF.open('rb') as f:
  elf=ELFFile(f);sec=elf.get_section(12)
  error_data=[]
  symtab=elf.get_section_by_name('.symtab')
  for name,address in [('_ZN4Core11ConstVectorIPN8Presonus5Panel15PresetNameCacheEE5errorE',4803640),('_ZN4Core11ConstVectorIPN8Presonus5Mixer16ChannelComponentEE5errorE',4798344)]:
   sym=symtab.get_symbol_by_name(name)[0];section=elf.get_section(sym['st_shndx'])
   assert sym['st_value']==address and sym['st_size']==4 and section['sh_type']=='SHT_NOBITS'
   error_data.append(dict(mangled=name,address=address,size=4,section=section.name,section_type=section['sh_type'],storage='zero-initialized NOBITS; injected nonzero state separately bounded'))
  for addr,size,sha in [(0x846b0,68,'28624ef700eaa97474808a444c349cd4d337e98eedb4ec3c22e5f0ca988ec3a3'),(0x70c14,144,'6d1b480a96fc055a4423ded5b02cd8aaac1908439ff477554e9926cf946651ec'),(0xad15c,192,'cd5dce178d76e2c96d90fc26ab0c4947e42e26285c72fafbcc285ce13a9dd9a9'),(0xad00c,336,'b302ffc228551baab3bcc4c962c2682f50a705a435c239f167605caf99430079')]:
   off=sec['sh_offset']+addr-sec['sh_addr'];assert hashlib.sha256(data[off:off+size]).hexdigest()==sha
   proof.append(dict(address=addr,size=size,section=sec.name,file_offset=off,sha256=sha))
 cases=[]
 for count in [0,1,3]:
  for idx in [-2147483648,-1,0,1,2,3,2147483647]:
   for error in [0,0x230040]:
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x810000)
    with ELF.open('rb') as f:
     e=ELFFile(f)
     for seg in e.iter_segments():
      if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
    def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
    w(0x200008,0x210000);w(0x20000c,count)
    vals=[0x220010,0,0x220030]
    for n,v in enumerate(vals):w(0x210000+4*n,v)
    w(4803640,error)
    u.reg_write(UC_ARM_REG_R0,0x200000);u.reg_write(UC_ARM_REG_R1,idx&0xffffffff)
    u.reg_write(UC_ARM_REG_SP,0x700000);u.reg_write(UC_ARM_REG_LR,0x600000)
    reads=[];writes=[]
    def read(u,a,ad,sz,val,user):
     if ad==4803640:reads.append(dict(address=ad,size=sz,value=struct.unpack('<I',u.mem_read(ad,4))[0]))
    def write(u,a,ad,sz,val,user):
     if 0x200000<=ad<0x240000 or ad==4803640:writes.append(dict(address=ad,size=sz,value=val))
    u.hook_add(UC_HOOK_MEM_READ,read);u.hook_add(UC_HOOK_MEM_WRITE,write)
    u.emu_start(0x846b0,0x600000,count=1000)
    assert u.reg_read(UC_ARM_REG_SP)==0x700000
    cases.append(dict(kind='cache',count=count,index=idx,error=error,items=vals,result=u.reg_read(UC_ARM_REG_R0),error_reads=reads,writes=writes))
 for geq in [-2147483648,-1,0,1,2,3,4,5,2147483647]:
  for main_count,aux_count,geq_count in [(0,0,0),(1,3,5),(2,1,5),(-1,-1,5),(1,0,5)]:
   for error in [0,0x230040]:
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x810000)
    with ELF.open('rb') as f:
     for seg in ELFFile(f).iter_segments():
      if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
    def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
    w(0x200084,geq);w(0x200090,0x201000)
    w(0x2011ac,0x210000);w(0x2011b0,main_count)
    w(0x201170,0x211000);w(0x201174,aux_count);w(0x2012b4,geq_count)
    vals=[0x220010,0,0x220030]
    for n,v in enumerate(vals):w(0x210000+4*n,v);w(0x211000+4*n,v+0x100 if v else 0)
    w(4798344,error)
    u.reg_write(UC_ARM_REG_R0,0x200000);u.reg_write(UC_ARM_REG_SP,0x700000);u.reg_write(UC_ARM_REG_LR,0x600000)
    reads=[];writes=[]
    def read(u,a,ad,sz,val,user):
     if ad==4798344:reads.append(dict(address=ad,size=sz,value=struct.unpack('<I',u.mem_read(ad,4))[0]))
    def write(u,a,ad,sz,val,user):
     if 0x200000<=ad<0x240000 or ad==4798344:writes.append(dict(address=ad,size=sz,value=val))
    u.hook_add(UC_HOOK_MEM_READ,read);u.hook_add(UC_HOOK_MEM_WRITE,write)
    u.emu_start(0x70c14,0x600000,count=1000)
    assert u.reg_read(UC_ARM_REG_SP)==0x700000
    cases.append(dict(kind='geq',geq=geq,main_count=main_count,aux_count=aux_count,geq_count=geq_count,error=error,main_items=vals,aux_items=[v+0x100 if v else 0 for v in vals],result=u.reg_read(UC_ARM_REG_R0),error_reads=reads,writes=writes))
 for dirty in [0,1]:
  for descriptor in [-1,7]:
   for width in [-1,0,1,2,3,4,5,8]:
    for count in [0,1,3,17,41,65]:
     u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x810000)
     with ELF.open('rb') as f:
      for seg in ELFFile(f).iter_segments():
       if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
     def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
     u.mem_write(0x200000,bytes(0x500))
     w(0x200008,0x210000);w(0x20000c,count);w(0x200414,width);w(0x200418,descriptor)
     u.mem_write(0x200426,bytes([dirty]))
     controls=[(0 if n%3==1 else (0x80000000 if n%3==2 else 1)) for n in range(count)]
     for n in range(count+1):
      w(0x210000+4*n,0x230000+8*n)
      w(0x230004+8*n,controls[n] if n<count else 0)
     calls=[];writes=[];bitbang=[]
     def code(u,ad,sz,user):
      if ad==0xad00c:
       bitbang.append(dict(low=u.reg_read(UC_ARM_REG_R2),high=u.reg_read(UC_ARM_REG_R3)))
      if ad==0xab80:
       fd=u.reg_read(UC_ARM_REG_R0);request=u.reg_read(UC_ARM_REG_R1);ptr=u.reg_read(UC_ARM_REG_R2)
       words=struct.unpack('<8I',u.mem_read(ptr,32));tx=words[0];rx=words[2];length=words[4]
       output=list(range(0xa0,0xa0+length))
       calls.append(dict(descriptor=fd,request=request,tx=list(u.mem_read(tx,length)),rx_before=list(u.mem_read(rx,length)),rx_after=output,length=length,descriptor_words=list(words)))
       u.mem_write(rx,bytes(output));u.reg_write(UC_ARM_REG_R0,0xffffffff)
       u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
     def write(u,a,ad,sz,val,user):
      if 0x200000<=ad<0x200500:writes.append(dict(offset=ad-0x200000,size=sz,value=val))
     u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
     u.reg_write(UC_ARM_REG_R0,0x200000);u.reg_write(UC_ARM_REG_SP,0x700000);u.reg_write(UC_ARM_REG_LR,0x600000)
     u.emu_start(0xad15c,0x600000,count=10000)
     assert u.reg_read(UC_ARM_REG_SP)==0x700000
     cases.append(dict(kind='spi',dirty=dirty,descriptor=descriptor,width=width,controls=controls,calls=calls,bitbang=bitbang,writes=writes,dirty_after=u.mem_read(0x200426,1)[0],tx=list(u.mem_read(0x20041c,5)),rx=list(u.mem_read(0x200421,5)),native_r0=u.reg_read(UC_ARM_REG_R0)))
 return dict(elf_sha256=SHA,ranges=proof,data=error_data,cases=cases,oracle='Unicorn ARM original instructions; mapped ELF PT_LOAD, supplied object/vector state and NOBITS sentinel state; original SPI bitBang executed, ioctl stub captures descriptor/payload then writes deterministic receive bytes and returns -1; no real hardware or Core binary execution')
if __name__=='__main__':
 out=run();Path(sys.argv[1]).write_text(json.dumps(out,indent=2)+'\n');print('ARM panel cases',len(out['cases']))
