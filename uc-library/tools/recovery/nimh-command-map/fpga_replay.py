"""NIMH-only bounded register-write replay; no other device firmware is mapped."""
from pathlib import Path
import hashlib,json,sys
import unicorn as uc
from unicorn import arm_const as a
root=Path(sys.argv[1]).resolve()
out=root/'evidence/recovery/2026-10-27/nimh-command-map'
b=(root/'evidence/recovery/2026-10-27/xmen-stm32/images/mixer-analysis/_ZL13nimh_arm_code.bin').read_bytes()
assert hashlib.sha256(b).hexdigest()=='b0979352e18a1093051fc6118a47694773cb9240e88087eca03aaa2ffe0f5e17'
m=uc.Uc(uc.UC_ARCH_ARM,uc.UC_MODE_THUMB|uc.UC_MODE_MCLASS)
m.mem_map(0x08000000,0x80000);m.mem_write(0x08000000,b)
m.mem_map(0x20000000,0x10000)
m.mem_map(0x60005000,4096) # Emulated RAM only, never a physical mapping.
stop=0x2000ff00
writes=[]
diagnostics=[]
def mem(m,access,addr,size,value,_):
    assert size==4 and addr==0x60005204,(hex(addr),size)
    writes.append(dict(address=hex(addr),value=value&0xffffffff))
def code(m,pc,size,_):
    if pc==stop:
        m.emu_stop()
    elif pc==0x08014c70:
        diagnostics.append('assertion diagnostic model; normal return only')
        m.reg_write(a.UC_ARM_REG_R0,0)
        m.reg_write(a.UC_ARM_REG_PC,m.reg_read(a.UC_ARM_REG_LR))
m.hook_add(uc.UC_HOOK_MEM_WRITE,mem,begin=0x60005000,end=0x60005fff)
m.hook_add(uc.UC_HOOK_CODE,code)
cases=[]
for row in (0,1,15,31,32,0xffffffff):
    for col in (0,1,15,31,32,0xffffffff):
        for gain in (0,1,0x7fff,0xffff,0x10000,0xffffffff):
            writes.clear();diagnostics.clear()
            for reg,value in ((a.UC_ARM_REG_R0,row),(a.UC_ARM_REG_R1,col),(a.UC_ARM_REG_R2,gain),
                              (a.UC_ARM_REG_SP,0x2000fc00),(a.UC_ARM_REG_LR,stop|1)):
                m.reg_write(reg,value)
            m.emu_start(0x0801d235,0,count=1000)
            assert m.reg_read(a.UC_ARM_REG_PC)==stop
            result=m.reg_read(a.UC_ARM_REG_R0)
            if row<32 and col<32:
                assert writes==[dict(address='0x60005204',value=(row<<27)|(col<<22)|(gain&0xffff))]
                assert result==0 and not diagnostics
            else:
                assert not writes and diagnostics and result!=0,dict(row=row,col=col,gain=gain,result=hex(result),writes=writes,diagnostics=diagnostics)
            cases.append(dict(row=row,column=col,gain=gain,result=hex(result),writes=list(writes),
                              diagnostics=list(diagnostics)))
(out/'fpga-register-replay.json').write_text(json.dumps(dict(
    image_sha256=hashlib.sha256(b).hexdigest(),tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    entry='0x0801d234',identity='TCAT CLI mix.gain callback; recovered label, original symbol unknown',
    physical_address='0x60005204',register_word='(arg0 << 27) | (arg1 << 22) | (gain & 0xffff)',
    cases=cases,hardware_actions=0,other_firmware_compared=False,
    scope='original NIMH instructions with MMIO replaced by RAM and assertion diagnostic normal-return model; proves bounded register writes, not FPGA interpretation/audio/timing'),indent=2)+'\n')
print('NIMH-only mixer register cases passed:',len(cases))
