#!/usr/bin/env python3
"""Original ARM-only bounded oracle; Core/app/PLT boundaries explicitly stubbed."""
import hashlib, io, json, pathlib, random, struct, time
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP
BASE=pathlib.Path(__file__).resolve().parent
ROOT=BASE.parents[2]
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
RANGES=[(0x8b5b8,20),(0x8b580,56),(0x8b4e0,160),(0x8b32c,436),(0x8b198,168)]
O=0x700000; S=0x710000; V=0x720000; E=0x730000; N=0x740000; VT=0x750000; STOP=0x600000

def oracle(data, elf, line):
    tokens=line.split(); method,a,b,c,d,n=map(int,tokens[:6]); rest=tokens[6:]
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    u.mem_map(0x8000,0x600000)
    for segment in elf.iter_segments():
        if segment['p_type']=='PT_LOAD': u.mem_write(segment['p_vaddr'],segment.data())
    u.mem_map(O,0x100000)
    def w(addr,value): u.mem_write(addr,struct.pack('<I',value&0xffffffff))
    def r(addr): return struct.unpack('<I',u.mem_read(addr,4))[0]
    def string(addr):
        raw=bytearray()
        while True:
            x=bytes(u.mem_read(addr+len(raw),1))
            if x==b'\0': return bytes(raw)
            raw.extend(x)
    w(O,VT); w(VT+12,STOP+0x100); w(VT+16,STOP+0x104)
    w(O+0x54,S if a else 0); u.mem_write(O+0x50,bytes([d&255,n&1 if method==3 else 0]))
    for i in range(6):
        w(O+0x74+408*i,V+4096*i); w(O+0x78+408*i,1); w(V+4096*i,-777)
    trace=[]; rawtrace=[]; writes=[]; ticks=0
    w(E+8,b); w(E+12,c); w(S+0x8c,a)
    w(N,VT+0x100); w(VT+0x100+0x3c,STOP+0x108)
    if method==4:
        w(S+0xa8,0x760000); w(S+0xac,n)
        for i in range(n):
            addr=0x770000+1024*i; id_,ext,text=rest[3*i:3*i+3]
            w(0x760000+4*i,addr); w(addr,int(id_)); u.mem_write(addr+16,bytes([int(ext)]))
            u.mem_write(addr+0x158,(text if text!='_' else '').encode()+b'\0')
    if method==5:
        w(O+0x54,S); w(0x760000,V); w(0x760004,n)
        for i in range(n): w(V+4*i,int(rest[i]))
    def ret(value=None):
        if value is not None: u.reg_write(UC_ARM_REG_R0,value)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(_,pc,size,user):
        nonlocal ticks
        if pc==STOP: u.emu_stop(); return
        arg=u.reg_read(UC_ARM_REG_R0)
        if pc==0x10ea88: trace.append(1); rawtrace.append(['start',arg]); ret(23)
        elif pc==0x10e7d0: trace.extend([2,u.reg_read(UC_ARM_REG_R1)]); rawtrace.append(['join',arg,u.reg_read(UC_ARM_REG_R1)]); ret(b)
        elif pc==0x10e800: trace.append(3); rawtrace.append(['terminate',arg]); ret()
        elif pc==0x10e948: trace.extend([4,arg]); ret()
        elif pc==STOP+0x100:
            phase=u.reg_read(UC_ARM_REG_R1); trace.extend([5,phase]); ticks+=1
            if ticks>=c: u.mem_write(O+0x51,b'\x01')
            ret()
        elif pc==STOP+0x104: trace.extend([7,u.reg_read(UC_ARM_REG_R1)]); ret()
        elif pc==0xfdafc: trace.append(6); ret(b)
        elif pc==0x10e384: rawtrace.append(['lock',arg]); ret()
        elif pc==0x10e460: rawtrace.append(['unlock',arg]); ret()
        elif pc==0xda22c: rawtrace.append(['networkLookup']); ret(N)
        elif pc==STOP+0x108:
            event=u.reg_read(UC_ARM_REG_R1)
            trace.extend([8,r(event+8),r(event+12),u.reg_read(UC_ARM_REG_R2)]); ret(1)
        elif pc==0xad18:
            target=string(u.reg_read(UC_ARM_REG_R1)); index=string(arg).find(target)
            rawtrace.append(['strstr',arg,target.decode(),index]); ret(arg+index if index>=0 else 0)
        elif pc==0xacd0: raise AssertionError('unexpected exception path')
        elif not (RANGES[method-1][0]<=pc<RANGES[method-1][0]+RANGES[method-1][1]):
            raise AssertionError(f'unbound execution {pc:x}')
    u.hook_add(UC_HOOK_CODE,hook)
    u.hook_add(UC_HOOK_MEM_WRITE,lambda _,access,addr,size,value,user:writes.append([addr,size,value]))
    u.reg_write(UC_ARM_REG_R0,O); u.reg_write(UC_ARM_REG_R1,0x760000); u.reg_write(UC_ARM_REG_R2,E)
    u.reg_write(UC_ARM_REG_SP,0x7ff000); u.reg_write(UC_ARM_REG_LR,STOP)
    u.emu_start(RANGES[method-1][0],STOP+0x200,count=100000)
    assert u.reg_read(UC_ARM_REG_PC)==STOP
    if method==1: result=[]
    elif method==2: result=[u.mem_read(O+0x51,1)[0]]
    elif method==3: result=[u.reg_read(UC_ARM_REG_R0),u.mem_read(O+0x50,1)[0],u.mem_read(O+0x51,1)[0]]
    elif method==4:
        result=[]
        for i in range(6):
            count=r(O+0x78+408*i); result.append(count)
            result.extend(struct.unpack('<i',u.mem_read(V+4096*i+4*j,4))[0] for j in range(count))
    else: result=[r(E+8),r(E+12)]
    return {'input':line,'method':method,'observed':result+trace,'external_trace':rawtrace,'native_memory_writes':writes}

def main():
    data=ELF.read_bytes(); assert hashlib.sha256(data).hexdigest()==SHA
    elf=ELFFile(io.BytesIO(data)); ranges=[]
    for addr,size in RANGES:
        sec=next(s for s in elf.iter_sections() if s['sh_addr']<=addr< s['sh_addr']+s['sh_size'])
        offset=sec['sh_offset']+addr-sec['sh_addr']; raw=data[offset:offset+size]
        ranges.append({'address':addr,'size':size,'section':sec.name,'file_offset':offset,'sha256':hashlib.sha256(raw).hexdigest()})
    lines=['1 1 0 0 0 0','2 1 0 0 0 0','2 1 1 0 0 0']
    for server in [0,1]:
        for has in [0,1]:
            for loops in [1,2,3,7]:
                for running in [0,1,27]:
                    for stop in [0,1]: lines.append(f'3 {server} {has} {loops} {running} {stop}')
    lines.extend(['4 0 0 0 0 0','4 1 0 0 0 0'])
    clients=[(1,0,'levl'),(-7,1,'redu'),(999,0,'rtan'),(0,1,'prefixlevlredurtansuffix'),(1,0,'levl'),(5,0,'none'),(6,1,'LEVL')]
    lines.append('4 1 0 0 0 '+str(len(clients))+' '+' '.join(f'{x} {y} {z}' for x,y,z in clients))
    for ext in [0,1]:
        for count in [99,100,101,110]:
            lines.append(f'4 1 0 0 0 {count} '+' '.join(f'{i} {ext} levlredurtan' for i in range(count)))
    for count in [0,1,2,99,100]:
        lines.append(f'5 12345 999 54321 0 {count} '+' '.join(str(i-50) for i in range(count)))
    cases=[oracle(data,elf,line) for line in lines]
    output={'elf':str(ELF.relative_to(ROOT)),'elf_sha256':SHA,'ranges':ranges,'producer':{'path':str(pathlib.Path(__file__).relative_to(ROOT)),'sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()},'cases':cases,'limitations':['Core/application/PLT targets are boundary stubs, never reconstructed Core bodies','Normal returns only; native unwind handlers not executed','Mapped valid client/string/event memory; list sizes bounded; no hardware or ARM object ABI claim']}
    (BASE/'native-fixtures.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'original_executions':len(cases),'ranges':ranges}))
if __name__=='__main__':main()
