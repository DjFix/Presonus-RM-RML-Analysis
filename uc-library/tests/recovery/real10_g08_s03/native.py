"""Original AlertBook ARM execution, explicit CCL/string/clock/EABI boundaries."""
from pathlib import Path
import hashlib,json,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4];C=Path('/home/rs/projects/opencs/ai-line-analysis');F=C/'temp/recovery-work/reconstruction10x10-20261116/prepared-main/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer';P=C/'temp/recovery-work/reconstruction10x10-20261116/prepared-main/packets'
def digest(b):return hashlib.sha256(b).hexdigest()
def generate(task):
 t=json.loads((P/task/'request.json').read_text())['targets'][0];raw=F.read_bytes();assert digest(raw)==t['original_elf_sha256']
 with F.open('rb') as f:
  ef=ELFFile(f);s=next(s for s in ef.get_section_by_name('.symtab').iter_symbols() if s.name==t['mangled']);sec=ef.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];bound=next(b for b in json.loads((P/task/'native-context.json').read_text())['bodies'].values() if b['address']==t['address']);assert off==bound['file_offset'] and digest(raw[off:off+t['size']])==bound['bytes_sha256'];loads=[(s['p_vaddr'],s.data()) for s in ef.iter_segments() if s['p_type']=='PT_LOAD']
 cases=[];deactivate=task.endswith('s02')
 for selection in [0,1]:
  for duplicate in [0,1]:
   for shape in [0,1,2]:
    for ns,mode in [(0,0),(999999,-1),(1000000,1),(4294967297000000,2147483647),(9223372036854000000,-2147483648)]:
     u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x800000)
     for a,data in loads:u.mem_write(a,data)
     obj=0x1000000;param=0x1010000;vt=0x1020000;slot=0x1030000;page=0x1040000;strings=0x1050000;stack=0x1100000;stop=0x1200000
     for a,n in [(obj,0x1000),(param,0x1000),(vt,0x1000),(slot,0x1000),(page,0x1000),(strings,0x1000),(stack,0x10000),(stop,0x1000)]:u.mem_map(a,n)
     def w(a,x):u.mem_write(a,struct.pack('<I',x&0xffffffff))
     def rd(a):return struct.unpack('<I',u.mem_read(a,4))[0]
     def text(a):
      out=bytearray()
      while a:
       b=u.mem_read(a,1)[0]
       if b==0:break
       out.append(b);a+=1
      return out.decode()
     w(param,vt);w(vt+0x58,slot);w(obj+0x11c,mode);w(obj+0x120,page);w(obj+0x124,param if selection else 0);w(obj+0x128,(ns//1000000)&0xffffffff);w(obj+0x12c,(ns//1000000)>>32)
     for i,value in enumerate(['alpha','','omega']):u.mem_write(strings+i*0x100,value.encode()+b'\0')
     sp=stack+0xff00;w(sp,strings+0x100);w(sp+4,strings+0x200);w(sp+8,mode)
     calls=[];writes=[];pcs=[];set_counts=([duplicate] if selection and deactivate else []);observers=duplicate+(selection if deactivate else 0);value=1 if selection and deactivate else 0;texts={100:'alpha' if deactivate else '',101:'',102:'omega' if deactivate else ''}
     def ret(x=0):u.reg_write(UC_ARM_REG_R0,x);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
     def code(uc,a,n,data):
      nonlocal observers,value
      x=uc.reg_read(UC_ARM_REG_R0);y=uc.reg_read(UC_ARM_REG_R1);z=uc.reg_read(UC_ARM_REG_R2)
      if a==stop:uc.emu_stop();return
      if a==0x11697c:calls.append(['DebugPrint',text(x)]);ret();return
      if a in [0x11c2e4,0x11d4f4]:
       assert x==param and y==obj+0x9c;calls.append(['removeObserver' if a==0x11c2e4 else 'addObserver']);observers+=(-1 if a==0x11c2e4 else 1);ret();return
      if a==slot:
       assert x==param and z==0 and y in [0,0x3f800000];set_counts.append(observers);value=int(y!=0);calls.append(['setValue',value,False]);ret();return
      if a==0x6d5a8:
       assert x==obj and z in [100,101,102];v=text(y);calls.append(['setParamString',z,v]);texts[z]=v;ret();return
      if a==0x116908:
       calls.append(['GetAbsoluteTime',ns]);u.reg_write(UC_ARM_REG_R0,ns&0xffffffff);u.reg_write(UC_ARM_REG_R1,ns>>32);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
      if a==0x157a08:
       dividend=x+(y<<32);divisor=z+(uc.reg_read(UC_ARM_REG_R3)<<32);assert divisor==1000000
       q,r=divmod(dividend,divisor);calls.append(['aeabi_ldivmod',dividend,divisor]);u.reg_write(UC_ARM_REG_R0,q&0xffffffff);u.reg_write(UC_ARM_REG_R1,q>>32);u.reg_write(UC_ARM_REG_R2,r&0xffffffff);u.reg_write(UC_ARM_REG_R3,r>>32);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
      assert t['address']<=a<a+n<=t['address']+t['size'],hex(a);pcs.append(a)
     def write(uc,access,a,n,v,data):
      assert obj<=a<a+n<=obj+0x1000 or stack<=a<a+n<=stack+0x10000
      if obj<=a<obj+0x1000:writes.append([a-obj,n,v])
     u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write);u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,page);u.reg_write(UC_ARM_REG_R2,param if selection else 0);u.reg_write(UC_ARM_REG_R3,strings);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop);u.emu_start(t['address'],stop,count=2000);assert u.reg_read(UC_ARM_REG_PC)==stop
     mode_after=struct.unpack('<i',u.mem_read(obj+0x11c,4))[0]
     expected={'mode':mode_after,'page_preserved':rd(obj+0x120)==page,'selection_present':bool(rd(obj+0x124)),'milliseconds':rd(obj+0x128)+(rd(obj+0x12c)<<32),'parameter_value':value,'observers':observers,'set_observer_counts':set_counts,'text':[None if shape==1 and tag!=102 or shape==2 and tag==101 else texts[tag].encode().hex() for tag in [100,101,102]]}
     cases.append({'selection':selection,'duplicate':duplicate,'shape':shape,'nanoseconds':ns,'mode':mode,'calls':calls,'writes':writes,'instructions':len(pcs),'pc_sha256':digest(b''.join(struct.pack('<I',a) for a in pcs)),'expected':expected})
 return {'version':1,'task':task,'range':dict(t,file_offset=off,bytes_sha256=bound['bytes_sha256']),'cases':cases,'domain':'Valid borrowed CCL provider/parameter/page lifetimes; null or live selection; zero/one prior observer; full/missing/wrong-type string tags; modes0/-1/1/INT_MAX/INT_MIN and nanosecond clock boundaries. Native app instructions execute; real CCL parameter, observer, string and SystemClock providers execute in host differential driver. Native provider, debug, clock and EABI boundaries are explicit stubs; no original layout/inheritance/observer-callback/ARM ABI or hardware claim.'}
