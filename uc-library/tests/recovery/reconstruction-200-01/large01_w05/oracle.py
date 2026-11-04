"""Offline exact ARM app instruction oracle. Never runs Core or device code."""
import bisect, hashlib, io, json, struct, sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
ROOT=Path(__file__).resolve().parents[5]
PACKETS=ROOT/'temp/recovery-work/reconstruction-200-01/large-batch01/packets'
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
OBJ=0x4000000; EVENT=OBJ+0x1000; TIME=OBJ+0x2000; MAP=OBJ+0x3000; RECORDS=OBJ+0x4000; STACK=0x5000000; STOP=0x6000000

def sha(b):return hashlib.sha256(b).hexdigest()
def w(*v):return struct.pack('<'+'I'*len(v),*(x&0xffffffff for x in v))
def d(v):return struct.pack('<d',v)
def inputs():
    for target in [1,2]:
        for seed in [0,1,255]:yield dict(kind='getter',target=target,seed=seed)
    for seed in [0,1,255]:yield dict(kind='name',target=6,seed=seed)
    for seed in [0,1,255]:yield dict(kind='destructor',target=5,seed=seed)
    for bars in [[],[0],[0,4],[0,2,6,9,14]]:
        for value in [-3,-1,0,1,2,3,4,5,6,8,9,13,14,15,100,2147483647]:
            yield dict(kind='bar',target=3,bars=bars,value=value)
    for records in [[],[[0,.5,0]],[[0,.5,0],[20,1,10],[30,.25,20]]]:
        for value in [-20.,-1.,-0.,0.,.5,9.5,10.,12.,20.,20.5,30.]:yield dict(kind='tempo',target=4,records=records,value=value)
    for musical in [False,True]:
        for blocked in [False,True]:
            for count in [0,3,4,255]:
                for delta in [-121,-61,-1,0,1,61,121]:
                    for values in [[0,0,0,19],[1,0,0,37],[3,59,59,65539],[5,2,3,-1]]:
                        yield dict(kind='delta',target=7,musical=musical,blocked=blocked,count=count,delta=delta,values=values,bars=[0,2,4],numerators=[4,3,7])

def generate():
    blob=ELF.read_bytes();assert sha(blob)=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
    elf=ELFFile(io.BytesIO(blob)); ranges=[]
    for i in range(1,8):
        c=json.loads((PACKETS/f'large01_w05_{i:02d}/context.json').read_text())
        for b in c['native_context']['bodies'].values():
            sec=elf.get_section(b['section_index']);off=int(sec['sh_offset'])+b['address']-int(sec['sh_addr']);assert off==b['file_offset'];assert sha(blob[off:off+b['size']])==b['bytes_sha256'];ranges.append(dict(target=i,address=b['address'],size=b['size'],section=sec.name,file_offset=off,sha256=b['bytes_sha256']))
    out=[];executed=set();writes=set()
    segments=[(int(s['p_vaddr']),s.data(),int(s['p_memsz'])) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
    # Only app methods and compiler soft-float support may execute. No Core code.
    allowed=[(r['address'],r['address']+r['size']) for r in ranges]+[(0x7724c,0x7734c),(0x186000,0x187200)]
    for case in inputs():
        u=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM)
        pages=set()
        for a,b,n in segments:
            for page in range(a&~4095,(a+n+4095)&~4095,4096):
                if page not in pages:u.mem_map(page,4096);pages.add(page)
            u.mem_write(a,b)
        u.mem_map(OBJ,0x10000);u.mem_map(STACK,0x10000);u.mem_map(STOP,4096)
        state=bytearray([case.get('seed',0x5a)]*0x200);event=bytearray([0xa5]*0x70);time=bytearray([0x77]*0x60)
        args=[OBJ,0,0,0];kind=case['kind'];record_blob=b''
        if kind=='bar':
            record_blob=b''.join(d(float(i))+w(4,4,b,0) for i,b in enumerate(case['bars']));u.mem_write(OBJ,w(0,RECORDS,len(case['bars'])));args[1]=case['value']
        elif kind=='tempo':
            record_blob=b''.join(struct.pack('<ddd',*r) for r in case['records']);u.mem_write(OBJ,w(0,RECORDS,len(case['records'])));args[2:]=struct.unpack('<II',d(case['value']))
        elif kind=='delta':
            state[0x134]=int(case['musical']);state[0x135]=int(case['blocked']);state[0x13c:0x140]=w(MAP)
            event[0x14]=case['count'];offset=0x50 if case['musical'] else 0x20;time[offset:offset+16]=w(*case['values'])
            record_blob=b''.join(d(float(i))+w(n,4,b,0) for i,(b,n) in enumerate(zip(case['bars'],case['numerators'])))
            u.mem_write(MAP,w(0,RECORDS,len(case['bars'])));args=[OBJ,EVENT,case['delta'],TIME]
        if kind not in ['bar','tempo']:u.mem_write(OBJ,bytes(state))
        if record_blob:u.mem_write(RECORDS,record_blob)
        u.mem_write(EVENT,bytes(event));u.mem_write(TIME,bytes(time));u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP)
        for r,a in zip(REGS,args):u.reg_write(r,a&0xffffffff)
        pcs=set();call_trace=[];memory_writes=[]
        def code(uc,a,size,data):
            assert any(lo<=a<hi for lo,hi in allowed),f'unbound PC {a:x}'
            pcs.add(a)
            if a in [0x774e8,0x7724c,0x186608,0x186604,0x186ca8,0x186f94]:call_trace.append(hex(a))
        def mem(uc,access,a,size,value,data):
            if OBJ<=a<OBJ+0x10000:memory_writes.append([a-OBJ,size,value])
        u.hook_add(unicorn.UC_HOOK_CODE,code);u.hook_add(unicorn.UC_HOOK_MEM_WRITE,mem)
        address=ranges[case['target']-1]['address'];u.emu_start(address,STOP,count=100000);assert u.reg_read(UC_ARM_REG_PC)==STOP
        result={}
        if kind=='getter':result['offset']=u.reg_read(UC_ARM_REG_R0)-OBJ
        elif kind=='name':
            ptr=u.reg_read(UC_ARM_REG_R0);result.update(pointer=ptr,text=bytes(u.mem_read(ptr,32)).split(b'\0')[0].decode())
        elif kind=='destructor':result.update(pointer=u.reg_read(UC_ARM_REG_R0),object=bytes(u.mem_read(OBJ,0x200)).hex(),vptr=struct.unpack('<I',u.mem_read(OBJ,4))[0])
        elif kind=='bar':
            ptr=u.reg_read(UC_ARM_REG_R0);result.update(index=(ptr-RECORDS)//24 if case['bars'] else -1,record=bytes(u.mem_read(ptr,24)).hex())
        elif kind=='tempo':result['value']=struct.unpack('<d',w(u.reg_read(REGS[0]),u.reg_read(REGS[1])))[0]
        elif kind=='delta':result['event']=bytes(u.mem_read(EVENT,0x70)).hex()
        result['writes']=memory_writes;result['calls']=call_trace
        # Preserve all app-visible memory bounds, including unchanged sentinel bytes.
        if kind not in ['bar','tempo']:assert bytes(u.mem_read(TIME,0x60))==bytes(time)
        if kind in ['getter','name','delta']:assert bytes(u.mem_read(OBJ,0x200))==bytes(state)
        if record_blob:assert bytes(u.mem_read(RECORDS,len(record_blob)))==record_blob
        executed|=pcs;out.append(dict(input=case,expected=result))
    deps=[]; sorted_executed=sorted(executed)
    for sec in elf.iter_sections():
        if sec['sh_type']=='SHT_SYMTAB':
            for sym in sec.iter_symbols():
                a=int(sym['st_value']);n=int(sym['st_size'])
                if n and bisect.bisect_left(sorted_executed,a)<len(sorted_executed) and sorted_executed[bisect.bisect_left(sorted_executed,a)]<a+n and sym['st_info']['type']=='STT_FUNC':
                    s=elf.get_section(sym['st_shndx']);off=int(s['sh_offset'])+a-int(s['sh_addr']);deps.append(dict(mangled=sym.name,address=a,size=n,section=s.name,file_offset=off,sha256=sha(blob[off:off+n])))
    return dict(version=1,oracle='Unicorn exact original ARM instructions; no hooks replacing calls',unicorn=unicorn.__version__,elf_sha256=sha(blob),ranges=ranges,executed_dependencies=deps,cases=out,executed_addresses=sorted(executed))
if __name__=='__main__':Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
