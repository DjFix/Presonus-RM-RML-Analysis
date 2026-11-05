"""Execute each exact app destructor range. Pinned Core and base application
providers are explicit call boundaries, never native Core reconstruction.
No syscalls, mapped host pointers, hardware, or original allocator execution.
"""
import hashlib,json,pathlib,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ROOT=pathlib.Path(__file__).resolve().parents[4]
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def digest(b):return hashlib.sha256(b).hexdigest()
def generate():
 blob=ELF.read_bytes();assert digest(blob)==SHA
 cases=[];ranges=[]
 with ELF.open('rb') as f:
  elf=ELFFile(f);symtab=elf.get_section_by_name('.symtab')
  for variant in range(3):
   name=f'_ZN8Presonus5Panel17FxPresetComponentD{variant}Ev';s=symtab.get_symbol_by_name(name)[0];sec=elf.get_section(s['st_shndx']);start=s['st_value'];size=s['st_size'];off=sec['sh_offset']+start-sec['sh_addr']
   ranges.append(dict(mangled=name,address=start,size=size,section=sec.name,section_index=s['st_shndx'],file_offset=off,sha256=digest(blob[off:off+size])))
   for observe in (0,1):
    for count in (0,3):
     for cache in (0,1):
      u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
      for seg in elf.iter_segments():
       if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
      obj=0x1000000;param=obj+0x1000;array=obj+0x2000;stack=0x9000000;stop=0x100f000
      u.mem_map(obj,0x10000);u.mem_map(stack,0x10000)
      def word(p,v):u.mem_write(p,struct.pack('<I',v))
      word(obj+0xe4,param if observe else 0)
      # Native vector representation is only boundary input memory. Its Core
      # body is not executed; storage release is tested using pinned CCL on host.
      word(obj+0xd0,array if count else 0);word(obj+0xd4,count)
      trace=[];writes=[];pcs=[];deleted=[]
      def code(uc,pc,n,_):
       if pc==stop:uc.emu_stop();return
       r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1)
       if pc==0x11c2e4:
        assert observe and r0==param and r1==obj+4;trace.append('O')
       elif pc==0x57034:
        assert r0==obj+0xcc;trace.append('V')
       elif pc==0x84348:
        assert r0==obj;trace.append('B')
       elif pc==0xac10:
        assert variant==0 and r0==obj;deleted.append(r0);trace.append('D')
       else:
        assert start<=pc<start+size,hex(pc)
        # Fail closed on untested unwind landing pads or literal execution.
        limit=start+(0x64 if variant==0 else 0x5c)
        assert pc<=limit,hex(pc)
        pcs.append(pc);return
       uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
      def write(uc,access,p,n,value,_):
       if obj<=p<obj+0x100:
        assert n==4 and p-obj in (0,4,0x84,0xc8)
        writes.append([p-obj,n,value])
       else:assert stack<=p and p+n<=stack+0x10000
      u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
      u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,stack+0x8000);u.reg_write(UC_ARM_REG_LR,stop)
      u.emu_start(start,stop+4,count=200)
      expected=(['O'] if observe else [])+['V','B']+(['D'] if variant==0 else [])
      assert trace==expected,(trace,expected)
      assert len(writes)==4
      assert writes==[[4,4,0x31a120],[0x84,4,0x31a130],[0xc8,4,0x31a140],[0,4,0x31a0c0]]
      assert u.reg_read(UC_ARM_REG_PC)==stop
      assert len(deleted)==(variant==0)
      cases.append(dict(argv=[str(variant),str(observe),str(count),str(cache)],trace=trace,writes=writes,executed_pcs=pcs,delete_boundary=deleted,expected=''.join(x for x in trace if x!='O')+' '+str(int(count>0))+'\n'))
 return dict(elf_path=str(ELF.relative_to(ROOT)),elf_sha256=SHA,ranges=ranges,cases=cases,scope='Actual original target instructions. Core removeObserver/vector and app PresetComponent are bounded provider calls; native delete is actual app call observed at allocator boundary, not native allocator execution. No exception unwinding, ARM ABI, original object layout or hardware claim.')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
 pathlib.Path(a.out).write_text(json.dumps(generate(),indent=2)+'\n')
