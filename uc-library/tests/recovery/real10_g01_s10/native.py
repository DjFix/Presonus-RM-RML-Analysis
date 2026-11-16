import ctypes,hashlib,json,struct,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4];EXE=R/'temp/recovery-work/real10_g01_s10/replay'
ELF=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/prepared-main/snapshot/rootfs/CS18_v13840/home/root/surface')
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
NAME='_ZN8Presonus7Surface20MonitorPageComponent12paramChangedEPN4Core8Portable9ParameterEi'
NAMES=['monitor','monitorx','xmonitor','route','routex','xroute','monitorroute','route_monitor','','unrelated']
def generate():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 with ELF.open('rb') as f:
  e=ELFFile(f);s=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name==NAME);sec=e.get_section(s['st_shndx']);a=s['st_value'];size=s['st_size'];off=sec['sh_offset']+a-sec['sh_addr'];body=data[off:off+size]
  assert (a,size,hashlib.sha256(body).hexdigest())==(582612,184,'38b78899fa0661f5006f23f57a2374fd376cb157e26c24dee8c87f196efd4b23')
  def raw(addr,n):
   sec=next(z for z in e.iter_sections() if z['sh_addr']<=addr and addr+n<=z['sh_addr']+z['sh_size'] and z['sh_type']!='SHT_NOBITS');o=sec['sh_offset']+addr-sec['sh_addr'];return data[o:o+n]
  literals={struct.unpack_from('<I',body,k)[0]:None for k in [176,180]}
  for addr in literals:literals[addr]=raw(addr,16).split(b'\0')[0]+b'\0'
  assert set(literals.values())=={b'monitor\0',b'route\0'}
 ranges=[dict(mangled=NAME,address=a,size=size,section=sec.name,section_index=s['st_shndx'],file_offset=off,sha256=hashlib.sha256(body).hexdigest())]
 libc=ctypes.CDLL(None);libc.strstr.restype=ctypes.c_void_p;libc.strstr.argtypes=[ctypes.c_char_p,ctypes.c_char_p]
 cases=[]
 for message in [0,1,2,3]:
  for ni,name in enumerate(NAMES):
   for tag in [100,101,102,103,110,121,122]:
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000);u.mem_write(a,body)
    for addr,value in literals.items():u.mem_write(addr,value)
    u.mem_write(0x42000c,struct.pack('<I',0x430000));u.mem_write(0x430008,name.encode()+b'\0')
    calls=[];writes=[];sites=[];operations=0
    def code(u,addr,n,_):
     nonlocal operations
     if a<=addr<a+size:sites.append(addr);return
     if addr==0xae7c:
      p=u.reg_read(UC_ARM_REG_R0);q=u.reg_read(UC_ARM_REG_R1)
      needle=bytes(u.mem_read(q,32)).split(b'\0')[0];hay=bytes(u.mem_read(p,64)).split(b'\0')[0]
      h=ctypes.create_string_buffer(hay);found=libc.strstr(ctypes.cast(h,ctypes.c_char_p),needle)
      result=p+(found-ctypes.addressof(h)) if found else 0
      calls.append(['strstr',hay.decode(),needle.decode(),None if not found else found-ctypes.addressof(h)])
      u.reg_write(UC_ARM_REG_R0,result)
     elif addr==0x8db3c:
      assert (u.reg_read(UC_ARM_REG_R0),u.reg_read(UC_ARM_REG_R1))==(0x400000,0x420000)
      first=u.reg_read(UC_ARM_REG_R2);last=u.reg_read(UC_ARM_REG_R3);calls.append(['radioSelection',first,last]);operations|=1 if first==100 else 2
     elif addr==0x8e328:
      assert u.reg_read(UC_ARM_REG_R0)==0x400000;calls.append(['applyMonitorSelection']);operations|=4
     else:raise RuntimeError(hex(addr))
     u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,addr,n,v,_:writes.append([addr,n,v]) if not 0x800000<=addr<0x801000 else None)
    for r,v in [(UC_ARM_REG_R0,0x400000),(UC_ARM_REG_R1,0x420000),(UC_ARM_REG_R2,message),(UC_ARM_REG_SP,0x801000),(UC_ARM_REG_LR,0xf00000)]:u.reg_write(r,v)
    u.emu_start(a,0xf00000,count=200);assert u.reg_read(UC_ARM_REG_PC)==0xf00000 and u.reg_read(UC_ARM_REG_SP)==0x801000;assert not writes
    cases.append(dict(stdin=f'{message} {ni} {tag} {operations}',native_calls=calls))
 observed=subprocess.check_output([str(EXE),'--provider'],input=''.join(c['stdin']+'\n' for c in cases),text=True).splitlines();assert len(observed)==len(cases)
 for case,line in zip(cases,observed):case['stdout']=line
 return dict(elf_sha256=SHA,ranges=ranges,nonstack_writes=[],cases=cases,case_count=len(cases),domain='280 native dispatch cases: messages 0/1/2/3, ten exact/prefix/interior/empty names, tags 100/101/102/103/110/121/122. Stable actual CCL registry tags 100..122, initial tag110 positive ensures terminating existing applyMonitorSelection. Compare all values, changed notifications, destination title and busy state.',native_boundary='Original dispatcher runs in Unicorn; libc strstr executes host libc independently. Existing canonical radioSelection/applyMonitorSelection bodies execute separately in --provider mode from native-observed operation flags; their ARM bodies and firmware Core are excluded.',producer_version=__import__('unicorn').__version__,literals={hex(k):hashlib.sha256(v).hexdigest() for k,v in literals.items()})
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
