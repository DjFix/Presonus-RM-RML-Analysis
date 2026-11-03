"""Execute each exact original ARM range; BL callees are recorded boundaries.
No Core body is decoded/executed. Lifecycle observations are research only.
"""
import hashlib, json, pathlib, struct, sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
ROOT = pathlib.Path(__file__).resolve().parents[5]
PACKETS = ROOT/'temp/recovery-work/ranked20-cycle01/batch02/packets'
ELF = ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
ELF_SHA = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
OBJ, PARAM, INFO, STACK, STOP = 0x400000, 0x410000, 0x420000, 0x500000, 0x600000
REGS = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]

def execute(raw, body, number, inputs):
    u=Uc(UC_ARCH_ARM, UC_MODE_ARM)
    u.mem_map(0x10000,0x280000)
    u.mem_write(body['address'],raw[body['file_offset']:body['file_offset']+body['size']])
    u.mem_map(OBJ,0x30000); u.mem_map(STACK,0x10000); u.mem_map(STOP,0x1000)
    u.mem_write(OBJ,bytes([0xa5])*0x800)
    def put(a,v): u.mem_write(a,struct.pack('<I',v&0xffffffff))
    def word(a): return struct.unpack('<I',u.mem_read(a,4))[0]
    tag, message, section, initial, initial_dirty, mutate = inputs
    put(PARAM+12,INFO); put(INFO+4,tag)
    put(OBJ+0x17c,initial);put(OBJ+0x190,initial)
    u.mem_write(OBJ+0x85,bytes([initial_dirty]))
    args=[OBJ,PARAM,message,INFO] if number==5 else [OBJ,section,PARAM,INFO]
    for reg,val in zip(REGS,args):u.reg_write(reg,val&0xffffffff)
    u.reg_write(UC_ARM_REG_SP,STACK+0x8000);u.reg_write(UC_ARM_REG_LR,STOP)
    put(STACK+0x8000,INFO)
    calls=[];writes=[]
    targets={int(i['operands'].lstrip('#'),16) for i in body['instructions'] if i['mnemonic']=='bl'}
    def hook(uc,address,size,userdata):
        if address not in targets:return
        calls.append({'target':address,'args':[uc.reg_read(r) for r in REGS],
                      'object_at_call':bytes(uc.mem_read(OBJ,0x800)).hex()})
        # Explicit app boundary effect. Mutation cases ensure the derived method
        # observes callback-modified tag/state after the original BL returns.
        if mutate and number in (5,23):
            put(INFO+4,14 if tag!=14 else 400)
            put(OBJ+0x17c,9);put(OBJ+0x190,9)
            uc.mem_write(OBJ+0x85,b'\x00')
        uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    def write(uc,access,address,size,value,userdata):
        if OBJ<=address<OBJ+0x800:writes.append([address-OBJ,size,value])
    u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
    u.emu_start(body['address'],STOP,count=2000)
    assert u.reg_read(UC_ARM_REG_PC)==STOP
    return {'packet':number,'inputs':inputs,'calls':calls,'writes':writes,
            'output':[u.mem_read(OBJ+0x85,1)[0],word(OBJ+0x17c),word(OBJ+0x190)],
            'object_final':bytes(u.mem_read(OBJ,0x800)).hex(),
            'r0_observation':u.reg_read(UC_ARM_REG_R0)}

def produce():
    raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==ELF_SHA
    ranges=[];cases=[]
    with ELF.open('rb') as f:
      elf=ELFFile(f)
      for number in range(1,26):
        packet=PACKETS/f'rank20c01_w01_{number:02}'
        j=json.loads((packet/'native-context.json').read_text()); b=j['bodies'][j['roots'][0]]
        sec=elf.get_section(b['section_index']);offset=sec['sh_offset']+b['address']-sec['sh_addr']
        assert offset==b['file_offset'] and sec.name==b['section']
        code=raw[offset:offset+b['size']]; assert hashlib.sha256(code).hexdigest()==b['bytes_sha256']
        ranges.append({'packet':number,**{k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}})
        if number==5:
          for tag in [-1,0,13,14,15,399,400,401,2147483647]:
           for message in [-1,0,1,2,3,4,5,2147483647]:
            for initial in [0,7]:
             for dirty in [0,1]:
              for mutate in [0,1]:cases.append(execute(raw,b,number,[tag,message,0,initial,dirty,mutate]))
        elif number==23:
          for section in [-2147483648,-1,0,1,2,2147483647]:
           for initial in [0,7]:
            for dirty in [0,1]:
             for mutate in [0,1]:cases.append(execute(raw,b,number,[0,0,section,initial,dirty,mutate]))
        else:cases.append(execute(raw,b,number,[0,0,0,7,1,0]))
    return {'version':1,'elf_sha256':ELF_SHA,'ranges':ranges,'cases':cases,
            'boundary':'BL callees skipped and logged, app mutation explicitly modeled. No callee lifecycle, end-to-end or original return declaration claims.'}

if __name__=='__main__':
    result=produce();path=pathlib.Path(__file__).with_name('fixtures.json')
    if '--write' in sys.argv:path.write_text(json.dumps(result,indent=2)+'\n')
    else:assert result==json.loads(path.read_text())
    print(len(result['cases']),'original ARM range executions; all 25 ranges individually verified')
