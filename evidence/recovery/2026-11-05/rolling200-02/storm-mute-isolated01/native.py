from pathlib import Path
import hashlib,json,struct,subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
R=Path.cwd();O=R/'evidence/recovery/2026-11-05/rolling200-02/storm-mute-isolated01';elf=R/'rootfs/RML16AI_Rack_13731/home/root/mixer';blob=elf.read_bytes();digest=hashlib.sha256(blob).hexdigest();assert digest=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
with elf.open('rb') as f:
 e=ELFFile(f);segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']; sections=[(x.name,x['sh_addr'],x['sh_offset'],x['sh_size']) for x in e.iter_sections() if x['sh_type']!='SHT_NOBITS']
lo=min(a for a,_,_ in segments)&~4095;hi=(max(a+n for a,n,_ in segments)+4095)&~4095
roots={'mute':(0x753fc,128,0x458b30,'Mute Group',{0xae98:0x75434,0xafe8:0x75458,0x3987c:0x7546c})}
OUT=0x60001000;TEXT=0x60002000;OBJ=0x60003000;STOP=0x71000000
cases=[];ranges=[]
def raw_at(a,n):
 sec=next(x for x in sections if x[1]<=a and a+n<=x[1]+x[3]);offset=sec[2]+a-sec[1];return blob[offset:offset+n],sec[0],offset
def z_at(a):
 out=bytearray()
 while True:
  v=raw_at(a+len(out),1)[0][0]
  if not v:return bytes(out)
  out.append(v)
pointer,_,_=raw_at(0x458b30,4);default_addr=struct.unpack('<I',pointer)[0];assert z_at(default_addr)==b'Mute Group'
assert z_at(0x339348)==b' %i'
for role,(start,size,cell,initial,sites) in roots.items():
 assert hashlib.sha256(raw_at(start,size)[0]).hexdigest()=='5fc28d4b83cf5698aa8593e56a427a3a9d6ff977c316f7401bea0c44bfaa09cc'
 original=next(data[start-a:start-a+size] for a,n,data in segments if a<=start and start+size<=a+len(data));ranges.append({'role':role,'address':start,'size':size,'sha256':hashlib.sha256(original).hexdigest(),'section':raw_at(start,size)[1],'file_offset':raw_at(start,size)[2]})
 for prefix in [initial,None,'','X','A'*15,'B'*30,'C'*31,'D'*40]:
  for index in [-2147483648,-2,-1,0,1,9,99,2147483646,2147483647]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(lo,hi-lo)
   for a,n,data in segments:u.mem_write(a,data)
   u.mem_map(0x60000000,0x10000);u.mem_map(0x70000000,0x10000);u.mem_map(STOP,4096)
   u.mem_write(OUT-8,b'\x5a'*8+b'\xa5'*32+b'\x5a'*8)
   if prefix is not None:u.mem_write(TEXT,prefix.encode()+b'\0')
   u.mem_write(cell,struct.pack('<I',0 if prefix is None else TEXT));u.reg_write(UC_ARM_REG_R0,OUT);u.reg_write(UC_ARM_REG_R1,OBJ);u.reg_write(UC_ARM_REG_R2,index&0xffffffff);u.reg_write(UC_ARM_REG_SP,0x7000f000);u.reg_write(UC_ARM_REG_LR,STOP)
   trace=[];done=[];writes=[]
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
    if start<=pc<start+size:return
    assert pc in sites,('unbound PC',hex(pc));assert uc.reg_read(UC_ARM_REG_LR)==sites[pc]
    before=bytes(uc.mem_read(OUT,32)).hex();a,b,c=[uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]];trace.append({'entry':pc,'lr':sites[pc],'r0':a,'r1':b,'r2':c})
    if pc==0x1debc:write_string(a,(string(b) if b else b'')[:31]);ret=a
    elif pc==0xae98:ret=len(string(a))
    elif pc==0xafe8:
     raw=string(b);uc.mem_write(a,(raw+b'\0'*c)[:c]);ret=a
    elif pc==0x3987c:
     assert string(b)==b' %i';signed=struct.unpack('<i',struct.pack('<I',c))[0];write_string(a,(string(a)+(' '+str(signed)).encode())[:31]);ret=a
    trace[-1].update({'return_r0':ret,'buffer_before':before,'buffer_after':bytes(uc.mem_read(OUT,32)).hex()});uc.reg_write(UC_ARM_REG_R0,ret);uc.reg_write(UC_ARM_REG_PC,sites[pc])
   u.hook_add(UC_HOOK_MEM_WRITE,lambda uc,access,address,size,value,data: writes.append({'address':address,'size':size,'value':value}) if OUT<=address<OUT+32 else None);u.hook_add(UC_HOOK_CODE,hook);u.emu_start(start,STOP+4,count=1000);assert done
   assert bytes(u.mem_read(OUT-8,8))==b'\x5a'*8 and bytes(u.mem_read(OUT+32,8))==b'\x5a'*8
   expected=string(OUT).decode();actual=subprocess.run([str(O/'replay'),role,str(index),'<null>' if prefix is None else prefix],capture_output=True,text=True,check=True).stdout
   assert actual==expected,(role,prefix,index,expected,actual)
   cases.append({'role':role,'index':index,'prefix':prefix,'native_output':expected,'native_output_writes':writes,'native_trace':trace,'output_guard_bytes_preserved':True,'cpp_output':actual})
proof={'passed':True,'original_elf_sha256':digest,'ranges':ranges,'cases':cases,'case_count':len(cases),'static_data':{'pointer_address':0x458b30,'pointer_hex':pointer.hex(),'pointee_address':default_addr,'default':'Mute Group','format_address':0x339348},'producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':'Exact original application instructions with explicit intercepted libc and CCL string provider semantics; no original Core/libc instruction execution. Real pinned CCL used in compiled C++ replay. Outputs and guard bytes checked; uninitialized unused string-tail bytes excluded. All integer boundaries including ARM32 addition wrap, null/empty/long default string. Private emulator memory only, no syscalls/network/devices. Isolated candidate sources; not integration/readiness/ARM ABI proof.'}
(O/'NATIVE_REPLAY.json').write_text(json.dumps(proof,indent=2)+'\n');print('Independent original-instruction replay passed:',len(cases),'cases, 1 function')
