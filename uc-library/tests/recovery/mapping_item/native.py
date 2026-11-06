"""Original ARM Item oracle. CCL is an explicit call capture, never emulated.
Panel cast and LED entries are captures; portable replay delegates to real providers.
"""
import hashlib, json, pathlib, struct, sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
ROOT = pathlib.Path(__file__).resolve().parents[4]
ELF = ROOT / 'rootfs/CS18_v13840/home/root/surface'
SHA = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
TARGETS = [('B', 0x760a8,160), ('I',0x7605c,76), ('C1',0x76148,60), ('C2',0x76528,60)]
def observe(op, text, control, argument):
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM); u.mem_map(0x8000,0x400000)
    with ELF.open('rb') as f:
        for seg in ELFFile(f).iter_segments():
            if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
    u.mem_map(0x1000000,0x400000)
    item, panel, vt, arg, alias, stop = 0x1000000,0x1010000,0x1020000,0x1030000,0x1040000,0x13ff000
    def w(a,v):u.mem_write(a,struct.pack('<I',v))
    def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
    def string(a):
        if not a:return None
        b=bytearray()
        while True:
            c=bytes(u.mem_read(a+len(b),1))
            if c==b'\0':return b.decode()
            b.extend(c)
    def reg(i):return u.reg_read([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2][i])
    def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    u.mem_write(item,b'\xa5'*80); w(item,panel if control else 0);w(panel,vt);w(vt,0x13fe000)
    if text is not None:u.mem_write(arg,text.encode()+b'\0')
    trace=[]; dispatch=[]; providers=[]
    def hook(uc,pc,size,user):
        if pc==stop:uc.emu_stop()
        elif pc==0x13fe000:
            assert reg(0)==panel and reg(1)==1281713219
            trace.append('cast');ret(panel if control==2 else 0)
        elif pc in (0x16308,0x18128):
            assert reg(0)==panel
            dispatch.append(reg(1)); trace.append(('blink' if pc==0x16308 else 'inverse')+':'+str(reg(1)));ret()
        elif pc==0xb0f8:ret(0 if string(reg(0))==string(reg(1)) else 1)
        elif pc==0x24268:
            # A source-provider call capture. Deliberately no Core machine code.
            providers.append({'offset':reg(0)-item,'input':string(reg(1))});ret(reg(0))
    u.hook_add(UC_HOOK_CODE,hook)
    u.reg_write(UC_ARM_REG_SP,0x1300000);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R0,item)
    u.reg_write(UC_ARM_REG_R1, argument if op=='I' else arg if text is not None else 0)
    u.reg_write(UC_ARM_REG_R2,alias if argument else 0)
    address=next(a for name,a,size in TARGETS if name==op)
    u.emu_start(address,stop,count=2000);assert u.reg_read(UC_ARM_REG_PC)==stop
    if op.startswith('C'):
        assert r(item)==0 and r(item+36)==(alias if argument else 0)
        assert providers==[{'offset':4,'input':text},{'offset':40,'input':None}]
    return {'trace':trace,'dispatch':dispatch,'providers':providers}
def generate():
    assert hashlib.sha256(ELF.read_bytes()).hexdigest()==SHA
    ranges=[]
    with ELF.open('rb') as f:
        e=ELFFile(f)
        for op,address,size in TARGETS:
            sec=next(s for s in e.iter_sections() if s['sh_addr']<=address and address+size<=s['sh_addr']+s['sh_size'])
            offset=sec['sh_offset']+address-sec['sh_addr'];f.seek(offset);raw=f.read(size)
            ranges.append(dict(op=op,address=address,size=size,section=sec.name,file_offset=offset,sha256=hashlib.sha256(raw).hexdigest()))
    cases=[]
    for op,texts in [('B',[None,'','off','blink','blink-off','blink-on','BLINK','blink-On','on',' blink','blink ','unknown']),('I',[None]),('C1',[None,'','a'*31,'b'*32,'c'*90]),('C2',[None,'','a'*31,'b'*32,'c'*90])]:
        for text in texts:
            for control in ([0,1,2] if op in ('B','I') else [0]):
                for argument in ([0,1] if op!='B' else [0]):
                    c=dict(op=op,text=text,control=control,argument=argument)
                    c.update(observe(**c));cases.append(c)
    return {'elf_sha256':SHA,'ranges':ranges,'boundary_scope':'CCL CStringBuffer call capture only; cast/LED provider call captures; ARM Item bodies and original blink table/strcmp dispatch execute. C++ replay invokes real pinned CCL and accepted Control/LED providers. No ARM Core execution.', 'cases':cases}
if __name__=='__main__':
    out=pathlib.Path(sys.argv[1]);out.write_text(json.dumps(generate(),indent=2)+'\n');print('Original ARM cases:',len(generate()['cases']))
