import json,pathlib,hashlib,struct
from unicorn import *
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
root=pathlib.Path.cwd(); elf=root/'rootfs/RML16AI_Rack_13731/home/root/mixer';raw=elf.read_bytes();assert hashlib.sha256(raw).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
results=[]
with elf.open('rb') as f:
 e=ELFFile(f)
 for i in range(1,6):
  p=root/f'temp/recovery-work/rolling200-implementation01/packets-batch04/packets/rolling200_impl_c22_{i:02}'
  req=json.loads((p/'request.json').read_text());target=req['targets'][0];a=target['address'];size=target['size'];sym=e.get_section_by_name('.symtab').get_symbol_by_name(target['mangled']);s=next(s for s in sym if s['st_value']==a and s['st_size']==size);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+a-sec['sh_addr']
  for match in [False,True]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x700000);u.mem_map(0x800000,0x300000)
   for seg in e.iter_segments():
    if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
   T=0x800000;stop=0xa00000;trace=[]
   u.mem_write(T,b'\xa5'*128);u.mem_write(0x494c3c,struct.pack('<I',T if match else T+256));u.reg_write(UC_ARM_REG_R0,T);u.reg_write(UC_ARM_REG_SP,0x9ff000);u.reg_write(UC_ARM_REG_LR,stop)
   def hook(uc,pc,sz,data):
    if pc==stop:uc.emu_stop();return
    if not a<=pc<a+size:
     trace.append({'pc':pc,'r0':uc.reg_read(UC_ARM_REG_R0),'r1':uc.reg_read(UC_ARM_REG_R1)})
     assert pc in [0x10e5e8,0x116a38,0x10e4cc,0xac10]
     uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,hook);u.emu_start(a,stop,count=200)
   results.append(dict(task=req['task_id'],mangled=target['mangled'],address=a,size=size,offset=off,range_sha256=hashlib.sha256(raw[off:off+size]).hexdigest(),match=match,trace=trace,word8=struct.unpack('<I',u.mem_read(T+8,4))[0],word12=struct.unpack('<I',u.mem_read(T+12,4))[0],release=u.mem_read(T+16,1)[0],singleton=struct.unpack('<I',u.mem_read(0x494c3c,4))[0]))
print(json.dumps({'domain':'exact ARM normal paths; provider calls observed boundary only, not executed; exception paths excluded','cases':results},indent=2))
