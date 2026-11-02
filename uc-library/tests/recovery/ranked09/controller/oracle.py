"""Execute original target and actual comparison helpers under Unicorn."""
import hashlib,json,random,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
ELF_HASH='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def generate(output):
    assert hashlib.sha256(ELF.read_bytes()).hexdigest()==ELF_HASH
    with ELF.open('rb') as f:
        elf=ELFFile(f); segments=[(s['p_vaddr'],s.data(),s['p_memsz']) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
        sec=elf.get_section(12); offset=sec['sh_offset']+0xb2664-sec['sh_addr'];f.seek(offset);body=f.read(52)
        assert hashlib.sha256(body).hexdigest()=='487e55337ec7fc3e601ad90d13a4c29edb3a8d5e94030e4907fbe66035bbec53'
    edges=[0,0x80000000,0x3f800000,0xbf800000,0x473b8000,0x477a0000,0x7f800000,0xff800000,0x7fc00000,0x7fa12345,1,0x80000001,0x7f7fffff]
    pairs=[(a,b,d) for a in edges for b in edges for d in (0,1,173)]
    rng=random.Random(1709);pairs += [(rng.getrandbits(32),rng.getrandbits(32),rng.randrange(256)) for _ in range(256)]
    cases=[];visited=set()
    for old,new,dirty in pairs:
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        ranges=sorted((addr & ~4095,(addr+size+4095)&~4095) for addr,data,size in segments)
        merged=[]
        for start,end in ranges:
            if merged and start<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],end)
            else:merged.append([start,end])
        for start,end in merged:u.mem_map(start,end-start)
        for addr,data,size in segments:u.mem_write(addr,data)
        u.mem_map(0x1000000,0x10000);u.mem_map(0x2000000,0x10000)
        state=bytearray([0xa5]*64);state[28]=dirty;struct.pack_into('<I',state,36,old)
        prop=bytearray([0x5a]*16);struct.pack_into('<I',prop,8,new)
        u.mem_write(0x1000000,bytes(state));u.mem_write(0x1000100,bytes(prop))
        u.reg_write(UC_ARM_REG_R0,0x1000000);u.reg_write(UC_ARM_REG_R1,0x1000100);u.reg_write(UC_ARM_REG_SP,0x2008000);u.reg_write(UC_ARM_REG_LR,0x1008000)
        calls=[];writes=[]
        def code(uc,addr,size,unused):
            visited.add(addr)
            if addr in (0x1578e0,0x1578c8):calls.append(addr)
        def write(uc,access,addr,size,value,unused):
            if 0x1000000<=addr<0x1000040:writes.append([addr-0x1000000,size,value])
        u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
        u.emu_start(0xb2664,0x1008000,count=1000)
        assert u.reg_read(UC_ARM_REG_PC)==0x1008000, 'native did not return'
        after=bytes(u.mem_read(0x1000000,64));assert bytes(u.mem_read(0x1000100,16))==prop
        assert all(after[i]==state[i] for i in range(64) if i not in (28,36,37,38,39))
        cases.append({'old':old,'incoming':new,'dirty':dirty,'rate':struct.unpack_from('<I',after,36)[0],'dirty_after':after[28],'writes':writes,'calls':calls})
    Path(output).write_text(json.dumps({'elf_sha256':ELF_HASH,'range':{'address':0xb2664,'size':52,'section':12,'offset':offset,'sha256':hashlib.sha256(body).hexdigest()},'cases':cases,'executed_instruction_addresses':sorted(visited)},indent=2)+'\n')
if __name__=='__main__':
    import sys
    generate(sys.argv[1])
