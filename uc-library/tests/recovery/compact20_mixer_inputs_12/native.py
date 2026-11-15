"""Execute original application instructions; Core calls are capture boundaries only."""
import argparse, ctypes, datetime, hashlib, json, pathlib, random, struct, time
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
TASK = 12
IDENTITIES = {10:(0x41aa4,268,0x39aa4,"2e62293f0a4e7d76d209bc020810a5fd32ffde213b64b947a2fc836526e61c28"),12:(0x45b9c,20,0x3db9c,"20e34118329c993041111053eeca75a3d3851c20177a34de06ae4d3b2fc55499"),13:(0x41e34,388,0x39e34,"361050c6508760b5bc286574c6832b0d52d267de98583fd428daaf25092ee3c8")}
ELF_SHA="9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
def bits(f): return struct.unpack('<I',struct.pack('<f',f))[0]
def flt(i): return struct.unpack('<f',struct.pack('<I',i))[0]
def generate(elf):
    began=time.monotonic(); raw=elf.read_bytes(); assert hashlib.sha256(raw).hexdigest()==ELF_SHA
    address,size,offset,sha=IDENTITIES[TASK]; assert hashlib.sha256(raw[offset:offset+size]).hexdigest()==sha
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    if TASK==12:
        u.mem_map(address&~4095,4096);u.mem_write(address,raw[offset:offset+size])
    else:
        with elf.open('rb') as f:
            for s in ELFFile(f).iter_segments():
                if s['p_type']=='PT_LOAD':
                    a=s['p_vaddr'];base=a&~4095;u.mem_map(base,((a+s['p_memsz']+4095)&~4095)-base);u.mem_write(a,s.data())
    for a in [0x10000000,0x20000000,0x30000000,0x40000000]: u.mem_map(a,0x10000)
    def put(a,v):u.mem_write(a,struct.pack('<I',v))
    def get(a):return struct.unpack('<I',u.mem_read(a,4))[0]
    def run(regs):
        for reg,v in regs.items():u.reg_write(reg,v)
        u.reg_write(UC_ARM_REG_SP,0x1000fff0);u.reg_write(UC_ARM_REG_LR,0x30000000);u.emu_start(address,0x30000000,count=200000)
        assert u.reg_read(UC_ARM_REG_PC)==0x30000000
    cases=[];meta={}
    if TASK==10:
        table=bytes(u.mem_read(0x174524,1024));tablef=struct.unpack('<256f',table)
        libm=ctypes.CDLL('libm.so.6');libm.powf.argtypes=[ctypes.c_float,ctypes.c_float];libm.powf.restype=ctypes.c_float
        events=[]
        def hook(uc,a,size,data):
            if a==0xae5c:
                x,y=uc.reg_read(UC_ARM_REG_R0),uc.reg_read(UC_ARM_REG_R1);z=bits(libm.powf(flt(x),flt(y)));events.append([x,y,z]);uc.reg_write(UC_ARM_REG_R0,z);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,hook)
        rng=random.Random(130510);inputs=[bits(x) for x in [-1.,-0.,0.,1.,25.,50.,100.,101.,float('inf'),float('-inf')]]+[0x7fc00000,0xffc00000]+list(struct.unpack('<256I',table))+[bits((a+b)*0.5) for a,b in zip(tablef,tablef[1:])]+[bits(rng.uniform(-2,102)) for _ in range(48)]
        for index,x in enumerate(inputs):
            alias=index%31==0;events.clear();put(0x20000000,0xdeadbeef);put(0x20000004,0xabadcafe)
            run({UC_ARM_REG_R0:0x12345678,UC_ARM_REG_R1:0x20000000,UC_ARM_REG_R2:0x20000000 if alias else 0x20000004,UC_ARM_REG_R3:x})
            cases.append({'input_bits':x,'alias':alias,'status':u.reg_read(UC_ARM_REG_R0),'outputs':[get(0x20000000),get(0x20000004)],'powf':list(events)})
        meta={'table_address':0x174524,'table_size':1024,'table_sha256':hashlib.sha256(table).hexdigest(),'boundary':'Original application and compiler softfloat instructions run. Only imported powf uses real host libm.so.6 powf; firmware powf equivalence excluded. No Core firmware execution. Valid output pointers; all other memory excluded.'}
    elif TASK==12:
        for value in range(256):
            for arg in [0,1,0xffffffff,0x80000000]:
                u.mem_write(0x20000231,bytes([value]));run({UC_ARM_REG_R0:0x20000000,UC_ARM_REG_R1:arg});cases.append({'value':value,'argument':arg,'result':u.reg_read(UC_ARM_REG_R0)})
        meta={'boundary':'Exact complete native method. No substituted providers. All256 byte states and4 integer arguments. Valid object/stack only.'}
    else:
        events=[];counts=[0,0]
        def hook(uc,a,size,data):
            if a not in [0x12640,0x12740,0x119c4c,0x11d4f4,0x11c2e4]:return
            x,y=uc.reg_read(UC_ARM_REG_R0),uc.reg_read(UC_ARM_REG_R1)
            if a==0x12640:put(x+4,0x40000000);put(x+12,5);uc.reg_write(UC_ARM_REG_R0,1)
            elif a==0x12740:pass
            elif a==0x119c4c:
                events.append(['lookup',x,y]);uc.reg_write(UC_ARM_REG_R0,0x20004000 if y==49 else 0x20005000)
            else:
                ix=0 if x==0x20004000 else 1;assert x in [0x20004000,0x20005000] and y==0x20000004
                events.append(['add' if a==0x11d4f4 else 'remove',ix]);counts[ix]=counts[ix]+1 if a==0x11d4f4 else max(0,counts[ix]-1)
            uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,hook)
        for present in [False,True]:
            for actions in [[True],[False],[True,True,False,False],[False,True,False],[True,False,True,False]]:
                counts[:]=[0,0];steps=[]
                for add in actions:
                    events.clear();put(0x20000174,0x20001000);put(0x200012dc,0x20003000 if present else 0)
                    run({UC_ARM_REG_R0:0x20000000,UC_ARM_REG_R1:int(add)});steps.append({'add':add,'events':list(events),'counts':list(counts)})
                cases.append({'settings_present':present,'steps':steps})
        meta={'boundary':'Original application instructions only; Core Vector resize/destructor, Component lookup and Parameter observer calls are explicit capture doubles. Counts model only captured add/remove multiplicity, never Core behavioral proof. Real CCL replay checks actual provider observer state independently. Successful allocation/distinct parameter identities only; no null parameter, allocator failure or exception-unwind claim.'}
    return {'version':1,'task':TASK,'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'producer_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'elf_sha256':ELF_SHA,'range':{'address':address,'size':size,'section':'.text','section_index':12,'file_offset':offset,'sha256':sha},'engine':'Unicorn ARM','seconds':time.monotonic()-began,'metadata':meta,'cases':cases}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--elf',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();d=generate(a.elf);a.out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'task':TASK,'cases':len(d['cases']),'seconds':d['seconds']}))
