"""Exact fadersLocked native instructions with named CCL and mixer boundaries."""
from pathlib import Path
import json,hashlib,struct,math
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4];C=Path('/home/rs/projects/opencs/ai-line-analysis');P=C/'temp/recovery-work/reconstruction10x10-20261116/prepared-main/packets/real10_g08_s04';F=C/'temp/recovery-work/reconstruction10x10-20261116/prepared-main/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer'
def digest(b):return hashlib.sha256(b).hexdigest()
def generate(task='real10_g08_s04'):
 raw=F.read_bytes();t=json.loads((P/'request.json').read_text())['targets'][0];assert digest(raw)==t['original_elf_sha256']
 with F.open('rb') as f:
  ef=ELFFile(f);sym=next(s for s in ef.get_section_by_name('.symtab').iter_symbols() if s.name==t['mangled']);sec=ef.get_section(sym['st_shndx']);off=sec['sh_offset']+sym['st_value']-sec['sh_addr'];b=next(b for b in json.loads((P/'native-context.json').read_text())['bodies'].values() if b['address']==t['address']);assert off==b['file_offset'] and digest(raw[off:off+t['size']])==b['bytes_sha256'];loads=[(s['p_vaddr'],s.data()) for s in ef.iter_segments() if s['p_type']=='PT_LOAD']
 cases=[]
 def positive(bits):return struct.unpack('<f',struct.pack('<I',bits))[0]>0
 for has36 in [0,1]:
  for has38 in [0,1]:
   for bits36,bits38,next36,next38 in [(0,0,0x3f800000,0x3f800000),(0x3f800000,0x3f800000,0,0),(0x3f800000,0,0x3f800000,0x3f800000),(0,0x3f800000,0x3f800000,0x3f800000),(0x3f800000,0x7fc00000,0x3f800000,0x7f800000),(0x7f800000,0xff800000,0x7fc00000,0x3f800000),(0x80000000,0x3f800000,0x3f800000,0x80000000)]:
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x800000)
    for a,data in loads:u.mem_write(a,data)
    obj=0x1000000;mixer=0x1010000;component=0x1020000;param=0x1030000;vtable=0x1040000;slot=0x1050000;stack=0x1100000;stop=0x1200000
    for a,n in [(obj,0x1000),(mixer,0x1000),(component,0x1000),(param,0x1000),(vtable,0x1000),(slot,0x1000),(stack,0x10000),(stop,0x1000)]:u.mem_map(a,n)
    def w(a,v):u.mem_write(a,struct.pack('<I',v))
    w(obj+0x8c,mixer);w(mixer+0x2dc,component);w(param,vtable);w(vtable+0x44,slot);w(4802492,0);w(4802496,0)
    calls=[];writes=[];pcs=[];current36=bits36;current38=bits38
    def ret(x=0):u.reg_write(UC_ARM_REG_R0,x);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def code(uc,a,n,data):
     if a==stop:uc.emu_stop();return
     x=uc.reg_read(UC_ARM_REG_R0);y=uc.reg_read(UC_ARM_REG_R1)
     if a==0xb030:assert x==4802492;calls.append(['guard_acquire']);ret(1);return
     if a==0xaa3c:assert x==4802492;w(x,1);calls.append(['guard_release']);ret();return
     if a==0x119c4c:assert x==component and y==38;calls.append(['getParameterByTag',38]);ret(param if has38 else 0);return
     if a==slot:assert x==param;calls.append(['getValue',current38]);ret(current38);return
     if a==0x157940:assert y==0;calls.append(['fcmpgt',x]);ret(int(positive(x)));return
     if a==0x66030:assert x==obj;calls.append(['canonical_mixerLocked',current36]);ret(int(has36 and positive(current36)));return
     assert t['address']<=a<a+n<=t['address']+t['size'];pcs.append(a)
    def write(uc,access,a,n,v,data):
     assert a in [4802492,4802496] or stack<=a<a+n<=stack+0x10000
     if a in [4802492,4802496]:writes.append([a,n,v])
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
    result=[]
    for i in range(2):
     if i:current36=next36;current38=next38
     u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,stack+0xff00);u.reg_write(UC_ARM_REG_LR,stop);u.emu_start(t['address'],stop,count=2000);assert u.reg_read(UC_ARM_REG_PC)==stop;result.append(bool(u.reg_read(UC_ARM_REG_R0)))
    assert len([c for c in calls if c[0]=='getParameterByTag'])==1
    cases.append({'has36':has36,'has38':has38,'bits':[bits36,bits38,next36,next38],'calls':calls,'writes':writes,'expected':result,'instructions':len(pcs),'pc_sha256':digest(b''.join(struct.pack('<I',a) for a in pcs))})
 return {'version':1,'task':task,'range':dict(t,file_offset=off,bytes_sha256=b['bytes_sha256']),'cases':cases,'domain':'28 cases, two sequential calls each with static tag38 lookup cached including null; real host CCL parameters and canonical mixerLocked. Positive/zero/negative-zero/NaN/infinities and independent lock setting. Native CCL lookup/getValue, EABI compare, guard and existing mixerLocked are explicit boundaries. No exceptions/concurrent first initialization/native provider bodies/ABI/hardware claim.'}
