"""Execute hash/range-verified original ARM app instructions only.
BL bodies are explicit intercepted boundaries, not claimed native callee proof.
No Core binary body is executed. Provider cleanup is observed in driver.cpp.
"""
import hashlib, itertools, json, pathlib, struct, sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
ROOT = pathlib.Path(__file__).resolve().parents[5]
PACKETS = ROOT/'temp/recovery-work/frontier-small01/batch01/packets'
ELF = ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
OBJ, PARAM, INFO, PARENT, ARRAY, CHILD, STACK, STOP = 0x400000,0x410000,0x420000,0x430000,0x440000,0x450000,0x500000,0x600000
REGS=[UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]

def run(raw, b, n, inp):
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    u.mem_map(0x10000,0x380000);u.mem_map(OBJ,0x80000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
    u.mem_write(b['address'],raw[b['file_offset']:b['file_offset']+b['size']])
    def put(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
    def word(a):return struct.unpack('<I',u.mem_read(a,4))[0]
    tag,msg,count,initial,dirty,mutate=inp
    put(PARAM+12,INFO);put(INFO+4,tag);put(OBJ+0x174,PARENT)
    put(PARENT+0x1d4,ARRAY);put(PARENT+0x1d8,count)
    for index in range(count):put(ARRAY+4*index,CHILD+0x1000*index)
    for addr in [OBJ]+[CHILD+0x1000*i for i in range(count)]:
        for off in [0x178,0x17c,0x18c]:put(addr+off,initial)
        u.mem_write(addr+0x85,bytes([dirty]))
    put(OBJ+0x4d0,initial)
    for reg,val in zip(REGS,[OBJ,PARAM,msg,0]):u.reg_write(reg,val&0xffffffff)
    u.reg_write(UC_ARM_REG_SP,STACK+0x8000);u.reg_write(UC_ARM_REG_LR,STOP)
    calls=[];writes=[]
    targets={int(i['operands'].lstrip('#'),16) for i in b['instructions'] if i['mnemonic']=='bl'}
    def hook(uc,a,size,data):
        if a not in targets:return
        calls.append({'target':a,'args':[uc.reg_read(r) for r in REGS],
                      'tag_at_call':word(INFO+4),'state_at_call':[word(OBJ+0x178),word(OBJ+0x17c),word(OBJ+0x18c),uc.mem_read(OBJ+0x85,1)[0]],
                      'children_at_call':[[word(CHILD+0x1000*i+0x178),word(CHILD+0x1000*i+0x17c),word(CHILD+0x1000*i+0x18c),uc.mem_read(CHILD+0x1000*i+0x85,1)[0]] for i in range(count)],'vptr_words_at_call':[word(OBJ),word(OBJ+4)]})
        # Explicit modeled Output boundary; real existing Output implementation
        # is exercised separately by C++ replay. Captured tag remains original.
        if n==2:
            if mutate:
                put(INFO+4,400 if tag==14 else 14)
                put(OBJ+0x178,9);put(OBJ+0x17c,9);put(OBJ+0x18c,9)
                uc.mem_write(OBJ+0x85,b'\x00')
            posttag=word(INFO+4)
            if msg==3:
                if posttag==14:put(OBJ+0x17c,1);uc.mem_write(OBJ+0x85,b'\x01')
                elif posttag==400:uc.mem_write(OBJ+0x85,b'\x01')
        if n==1 and a==0x30fe0:uc.reg_write(UC_ARM_REG_R0,tag)
        uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    def write(uc,access,a,size,val,data):
        if OBJ<=a<OBJ+0x800 or CHILD<=a<CHILD+0x4000:writes.append([a,size,val])
    u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
    u.emu_start(b['address'],STOP,count=4000)
    assert u.reg_read(UC_ARM_REG_PC)==STOP
    def state(a):return [word(a+0x178),word(a+0x17c),word(a+0x18c),u.mem_read(a+0x85,1)[0]]
    return {'packet':n,'inputs':inp,'calls':calls,'writes':writes,'state':state(OBJ),'children':[state(CHILD+0x1000*i) for i in range(count)],'rack_state':word(OBJ+0x4d0),'vptr_words':[word(OBJ),word(OBJ+4)],'r0_observation':u.reg_read(UC_ARM_REG_R0)}

def produce():
    raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
    ranges=[];cases=[]
    with ELF.open('rb') as f:
      elf=ELFFile(f)
      for n in range(1,5):
        j=json.loads((PACKETS/f'frontier01_w02_{n:02}'/'native-context.json').read_text());b=j['bodies'][j['roots'][0]]
        sec=elf.get_section(b['section_index']);off=sec['sh_offset']+b['address']-sec['sh_addr']
        assert off==b['file_offset'] and sec.name==b['section']
        assert hashlib.sha256(raw[off:off+b['size']]).hexdigest()==b['bytes_sha256']
        ranges.append({'packet':n,**{k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}})
        if n==1:inputs=itertools.product([0,1],[0],[0,1,3],[0,7,0xffffffff],[0],[0])
        elif n==2:inputs=itertools.product([-2147483648,-1,0,13,14,15,20,21,22,399,400,411,412,413,414,2147483647],[-1,0,2,3,4],[0,1,3],[0,7],[0,1],[0,1])
        else:inputs=[[0,0,0,0,0,0]]
        cases.extend(run(raw,b,n,list(inp)) for inp in inputs)
    return {'version':1,'elf_sha256':SHA,'ranges':ranges,'cases':cases,
            'boundary':'Only exact selected app ranges execute. BL boundary interception models Output post-callback effects and slave query. CCL cleanup is preferred upstream behavior, observed separately; original return/layout/ABI unproved.'}
if __name__=='__main__':
    result=produce();path=pathlib.Path(__file__).with_name('fixtures.json')
    if '--write' in sys.argv:path.write_text(json.dumps(result,indent=2)+'\n')
    else:assert result==json.loads(path.read_text())
    print(len(result['cases']),'native app range executions; four exact original ranges verified')
