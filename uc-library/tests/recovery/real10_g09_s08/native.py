"""Execute only the original getTDMRoutes body; dynamic_cast is an explicit stub.
The provider's actual RTTI behavior is independently checked in Replay.cpp.
"""
import importlib.metadata
import argparse, hashlib, io, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
START=0x80158; SIZE=376

def generate(elf_path):
    raw=Path(elf_path).read_bytes(); assert hashlib.sha256(raw).hexdigest()==SHA
    elf=ELFFile(io.BytesIO(raw)); sec=elf.get_section(12)
    offset=sec['sh_offset']+START-sec['sh_addr']
    assert offset==0x78158
    assert hashlib.sha256(raw[offset:offset+SIZE]).hexdigest()=='29604a0168274b65cb9fbf56ae4e6c830e49c1d2e30ecfef6735eb764434b673'
    table=struct.unpack('<15I',raw[offset+0x34:offset+0x70])
    rows=[]
    for route in [-2147483648,-1,*range(17),2147483647]:
      for initial in [0,19,255]:
       for count,kind,source,mode in [(0,0,0,0),(1,0,0,0),(1,1,0,0),(1,2,255,9),(1,2,320,0xffffffff),(-1,0,0,0)]:
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
        for segment in elf.iter_segments():
          if segment['p_type']=='PT_LOAD':u.mem_write(segment['p_vaddr'],segment.data())
        u.mem_map(0x1000000,0x20000)
        obj=0x1000000; vec=obj+0x1000; child=obj+0x2000; cast=obj+0x3000; out=obj+0x4000; sp=obj+0x18000; stop=obj+0x1f000
        def word(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
        word(obj+0x200,count);word(obj+0x1fc,vec);word(vec,child if kind else 0)
        word(0x493788,child if kind else 0)
        word(cast+0x234,source);word(cast+0x22c,mode)
        u.mem_write(out,bytes([initial,77]));word(out+4,123);word(sp,out+4)
        calls=[];writes=[]
        def code(u,address,size,data):
          if address==0xacf4:
            calls.append([u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]])
            u.reg_write(UC_ARM_REG_R0,cast if kind==2 else 0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        def write(u,access,address,size,value,data):
          if out<=address<out+8:writes.append([address-out,size,value])
        u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
        for reg,value in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,route&0xffffffff),(UC_ARM_REG_R2,out),(UC_ARM_REG_R3,out+1),(UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,value)
        u.emu_start(START,stop,count=1000);assert u.reg_read(UC_ARM_REG_PC)==stop
        rows.append({'input':[route,initial,count,kind,source,mode], 'output':[u.mem_read(out,1)[0],u.mem_read(out+1,1)[0],struct.unpack('<I',u.mem_read(out+4,4))[0]],'calls':calls,'writes':writes})
    return {'producer':{'path':__file__,'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'unicorn_version':importlib.metadata.version('unicorn'),'pyelftools_version':importlib.metadata.version('pyelftools'),'oracle':'original ARM instructions via Unicorn; __dynamic_cast boundary stub, no original provider execution claimed'},'elf_sha256':SHA,'range':{'address':START,'size':SIZE,'section':12,'file_offset':offset},'jump_table':list(table),'domain':'all switch cases; signed invalid bounds; initial byte 0/19/255; empty/null/non-talkback/talkback; negative count sentinel; source truncation and uint32 mode','cases':rows}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_text(json.dumps(generate(a.elf),indent=2)+'\n')
