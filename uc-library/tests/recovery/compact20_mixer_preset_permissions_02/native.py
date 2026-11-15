"""Execute exact original getDelay instructions; never derive expected values from C++."""
import argparse, hashlib, json, struct
from pathlib import Path
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
RANGE_SHA = "3b94db98474a1fc3b065a2ff2b24501b10b282d654099d1446a1c68d31e5906f"
MANGLED = "_ZN8Presonus5Mixer15OutputComponent8getDelayEv"
def observe(elf):
    raw=Path(elf).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==ELF_SHA
    body=raw[0x40270:0x40284]
    assert hashlib.sha256(body).hexdigest()==RANGE_SHA
    cases=[]
    for objindex, obj in enumerate([0x100000,0x110000]):
        for token, word in enumerate([0,0x300000,0x310004,0x7ffffffc,0xfffffffc]):
            u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
            for addr in [0x48000,obj,0x800000,0x900000]:u.mem_map(addr,0x1000)
            u.mem_write(0x48270,body)
            u.mem_write(obj,bytes([0xa5])*0x800)
            u.mem_write(obj+0x1d0,struct.pack('<I',word))
            before=bytes(u.mem_read(obj,0x800));writes=[];trace=[]
            def code(uc,address,size,data):
                if address==0x900000:uc.emu_stop();return
                assert 0x48270<=address<0x48284
                trace.append(address)
            def write(uc,access,address,size,value,data):
                assert 0x800000<=address and address+size<=0x801000
                writes.append(dict(address=address,size=size,value=value))
            u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
            u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,0x800800);u.reg_write(UC_ARM_REG_LR,0x900000)
            u.emu_start(0x48270,0x900004,count=10)
            assert u.reg_read(UC_ARM_REG_PC)==0x900000
            assert bytes(u.mem_read(obj,0x800))==before
            result=u.reg_read(UC_ARM_REG_R0)
            assert result==word
            cases.append(dict(object_index=objindex,object_address=obj,token=token,input_word=word,return_word=result,object_writes=0,stack_writes=writes,instruction_trace=trace))
    return dict(version=1,original_elf_sha256=ELF_SHA,mangled=MANGLED,address=0x48270,size=20,section='.text',section_index=12,file_offset=0x40270,range_sha256=RANGE_SHA,oracle='original ELF ARM instructions executed by Unicorn',unicorn_version=unicorn.__version__,cases=cases,exclusions=['No parameter dereference, provider call, Core decompilation, syscall or hardware execution','Original static return declaration and ARM object layout not established'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--out');p.add_argument('--verify');a=p.parse_args();data=observe(a.elf)
    if a.verify:assert data==json.loads(Path(a.verify).read_text()), 'Fresh original observations differ'
    if a.out:Path(a.out).write_text(json.dumps(data,indent=2)+'\n')
    print('Original ARM executions:',len(data['cases']))
