"""Execute original application instructions. Core calls are capture boundaries.
Core binaries are never executed; queue insertion is checked using real CCL in C++.
"""
import argparse, hashlib, json, random, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_R0, UC_ARM_REG_R1
ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
MANGLED = "_ZN8Presonus5Mixer18CascadeLinkHandler13connectDeviceEv"
RANGE_SHA = "861ab04fa3cb870dcaf9ec5264b8003e81247e23c6de3feeca9473db99218f6b"
def observe(elf_path):
    data = elf_path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == ELF_SHA
    assert hashlib.sha256(data[356052:356052+104]).hexdigest() == RANGE_SHA
    rng=random.Random(901)
    cases=[]
    for i in range(60):
        primary=[rng.choice([0,0x120,0x240,0x360,0x480]) for _ in range(i%21)]
        pending=[rng.choice([0,0x120,0x480]) for _ in range(i%6)]
        case=dict(primary=primary,pending=pending,repeats=1+i%3,present=i%2,id=[0,17,-3,2147483647][i%4])
        uc=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        uc.mem_map(0x50000,0x20000)
        uc.mem_write(388820,data[356052:356052+104])
        # The instruction's format literal lives just after its declared range.
        uc.mem_write(388924-4,data[356052+100:356052+108])
        uc.mem_map(0x116000,0x1000)
        uc.mem_map(0x31e000,0x2000)
        with elf_path.open('rb') as f:
            elf=ELFFile(f)
            for seg in elf.iter_segments():
                if seg['p_type']=='PT_LOAD' and seg['p_vaddr']<=0x31ee04<seg['p_vaddr']+seg['p_filesz']:
                    off=seg['p_offset']+0x31ee04-seg['p_vaddr']
                    uc.mem_write(0x31ee04,data[off:off+64])
        uc.mem_map(0x1000000,0x10000);uc.mem_map(0x2000000,0x1000);uc.mem_map(0x3000000,0x10000)
        obj=0x3000000; arr=obj+0x1000; client=obj+0x2000
        def put(addr,value): uc.mem_write(addr,struct.pack('<I',value&0xffffffff))
        put(obj+0x90,arr);put(obj+0x94,len(primary));put(obj+0xb8,client if case['present'] else 0);put(client+0x90,case['id'])
        for j,v in enumerate(primary):put(arr+4*j,v)
        events=[]
        def hook(u,address,size,user):
            if address==0x116a38:
                ptr=u.reg_read(UC_ARM_REG_R0); text=bytes(u.mem_read(ptr,64)).split(b'\0')[0].decode()
                events.append(dict(kind='debug',format=text,id=u.reg_read(UC_ARM_REG_R1)))
                u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            elif address==0x608bc:
                ptr=u.reg_read(UC_ARM_REG_R1)
                events.append(dict(kind='add',receiver=u.reg_read(UC_ARM_REG_R0)-obj,value=struct.unpack('<I',u.mem_read(ptr,4))[0]))
                u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        uc.hook_add(UC_HOOK_CODE,hook)
        before=bytes(uc.mem_read(obj,0x2000))
        for _ in range(case['repeats']):
            uc.reg_write(UC_ARM_REG_R0,obj);uc.reg_write(UC_ARM_REG_LR,0x2000000);uc.reg_write(UC_ARM_REG_SP,0x100f000)
            uc.emu_start(388820,0x2000000,count=20000)
            assert uc.reg_read(UC_ARM_REG_PC)==0x2000000
        assert bytes(uc.mem_read(obj,0x2000))==before
        case['events']=events;case['original_object_and_primary_unchanged']=True;cases.append(case)
    return dict(producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), unicorn_version=__import__('unicorn').__version__, version=1,original_elf_sha256=ELF_SHA,mangled=MANGLED,address=388820,size=104,section=12,file_offset=356052,range_sha256=RANGE_SHA,native_oracle='Unicorn ARM application body; capture-only Core DebugPrintf/MutableVector.add boundaries, no Core binary execution',cases=cases)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--elf',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(observe(a.elf),indent=2)+'\n')
