"""Reviewed-only memory oracle; no guest host-call forwarding."""
import hashlib
import json
import re
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_INTR, UC_HOOK_MEM_INVALID, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC

BASE = Path('uc-library/candidates/rolling200_02_programmer_resume_w01')
OUT = Path('evidence/recovery/2026-11-05/rolling200-02/programmer-resume-w01')
PACKETS = Path('temp/recovery-work/rolling200-02/programmer-resume01/packets-batch01/packets')
ELF = Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
SHA = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
OBJ, IMAGE, STACK, STOP = 0x50000000, 0x50010000, 0x50020000, 0x50040000
LIMIT = 20000
APPROVED = {
 'rolling200_02_impl_programmer_01': ('_ZN8Presonus4NOAA15TCardProgrammer10writeImageEv', 0xa60f8, 428),
 'rolling200_02_impl_programmer_02': ('_ZN8Presonus4NOAA15TCardProgrammer6updateEv', 0xa62a4, 232),
 'rolling200_02_impl_programmer_03': ('_ZN8Presonus4NOAA15TCardProgrammer8eraseAllEv', 0xa5fe4, 104),
 'rolling200_02_impl_programmer_04': ('_ZN8Presonus4NOAA15TCardProgrammer9unprotectEv', 0xa5e14, 76),
}

def reject(reason):
    raise RuntimeError(reason)

def guard_pc(pc, pcs):
    if pc not in pcs: reject(('unexpected PC',hex(pc)))

def guard_instruction(word):
    if word & 0x0f000000 == 0x0f000000: reject('guest syscall forbidden')

def guard_write(address,size,ranges):
    if not any(lo <= address and address+size <= lo+n for lo,n in ranges):
        reject(('write outside private data',hex(address),size))

def guard_interrupt():
    reject('guest interrupt forbidden')

def negative_checks():
    tests=[('unknown_pc',lambda:guard_pc(0xdeadbeec,{0xa60f8})),
           ('svc',lambda:guard_instruction(0xef000000)),
           ('out_of_bounds_write',lambda:guard_write(0x50000fff,2,[(OBJ,4096)])),
           ('interrupt',guard_interrupt)]
    results=[]
    for name,test in tests:
        try: test()
        except RuntimeError as error: results.append({'guard':name,'rejected':str(error)})
        else: raise AssertionError(('guard failed',name))
    return results
BOUNDARIES = {0xa5d98:'command', 0xa5d1c:'ack', 0xa5d3c:'char', 0xa60b4:'address', 0xa6064:'packet', 0xa5ab4:'progress', 0xae68:'memcpy', 0x4e974:'format', 0x116a38:'debug', 0x116908:'clock', 0x157a08:'divide'}

def inputs():
    raw = ELF.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SHA
    targets = []
    pcs = set()
    with ELF.open('rb') as stream:
        elf = ELFFile(stream)
        segments = [(int(s['p_vaddr']), s.data(), int(s['p_memsz'])) for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD']
        assert {p.name for p in PACKETS.iterdir()} == set(APPROVED), 'extra/missing packets'
        for task_id, approved in APPROVED.items():
            packet = PACKETS/task_id
            request = json.loads((packet/'request.json').read_text())
            assert request['task_id'] == task_id
            assert len(request['originals']) == 1
            target = request['originals'][0]['original']
            assert (target['mangled'], target['address'], target['size']) == approved
            assert target['elf'] == SHA and target['firmware'] == 'RM/RML mixer 13731'
            assert target['role'] == 'server' and target['section_json'] == '12'
            assert request['targets'] == [{'original_elf_sha256':SHA,'mangled':approved[0],'address':approved[1],'size':approved[2]}]
            section = elf.get_section(int(target['section_json']))
            off = int(section['sh_offset']) + target['address'] - int(section['sh_addr'])
            body = raw[off:off+target['size']]
            text = (packet/'ELF_CONTEXT.md').read_text()
            expected = re.search(r'section .text; SHA256 `([a-f0-9]+)`', text)[1]
            assert hashlib.sha256(body).hexdigest() == expected
            instructions = re.search(r'```asm\n(.*?)```', text, re.S)[1]
            localpcs = [int(x,16) for x in re.findall(r'^([0-9a-f]{8}) ', instructions, re.M)]
            assert localpcs and all(pc % 4 == 0 and approved[1] <= pc and pc+4 <= approved[1]+approved[2] for pc in localpcs)
            pcs.update(localpcs)
            targets.append(dict(target, file_offset=off, range_sha256=expected, packet=str(packet), pcs=localpcs))
    return segments, targets, pcs


def run(segments, targets, pcs, case):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    pages = set()
    for addr, data, size in segments:
        for page in range(addr & ~4095, (addr+size+4095)&~4095, 4096):
            if page not in pages:
                uc.mem_map(page,4096); pages.add(page)
        uc.mem_write(addr,data)
    for address,size in [(OBJ,4096),(IMAGE,65536),(STACK,65536),(STOP,4096)]:
        uc.mem_map(address,size)
    length = case['length']
    uc.mem_write(IMAGE,bytes((i*37+11)&255 for i in range(length)))
    uc.mem_write(OBJ+4,IMAGE.to_bytes(4,'little')+length.to_bytes(4,'little'))
    uc.mem_write(OBJ+24,bytes([case['cancel']]))
    trace=[]; failures=0; chunks=0; stopped=False; count=0
    executed_pcs={}; intercepted={}
    # Epoch is the sole authorized guest global store, discovered from update literal.
    epoch = int.from_bytes(uc.mem_read(0xa6368,4),'little')
    def bounded(address,size):
        guard_write(address,size,[(OBJ,4096),(IMAGE,65536),(STACK,65536),(epoch,8)])
        return True
    def write(address,data):
        assert bounded(address,len(data)), ('host model write outside private data',hex(address),len(data))
        uc.mem_write(address,data)
    def string(address):
        data=bytearray()
        for i in range(512):
            b=bytes(uc.mem_read(address+i,1))
            if b==b'\0': return data.decode('ascii')
            data.extend(b)
        raise RuntimeError('unterminated boundary string')
    def code(machine,pc,size,user):
        nonlocal failures,chunks,stopped,count
        count+=1
        if count>LIMIT: raise RuntimeError('instruction limit')
        if pc==STOP:
            stopped=True; machine.emu_stop(); return
        if pc in BOUNDARIES:
            intercepted[hex(pc)]=intercepted.get(hex(pc),0)+1
            name=BOUNDARIES[pc]
            a,b,c,d=[machine.reg_read(reg) for reg in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
            ret=1
            if name in ['command','ack']:
                ret=0 if failures==case['fail'] else 1; failures+=1
                trace.append([name,b,ret])
                if name=='ack' and case.get('overwrite'):
                    write(OBJ+172,b'\x00'); trace.append(['overwrite',0])
            elif name in ['char','address']: trace.append([name,b])
            elif name=='packet': trace.append([name,bytes(machine.mem_read(b,c)).hex()])
            elif name=='progress':
                text=string(b);trace.append([name,text,c])
                if text.startswith('writing address'):
                    chunks+=1
                    if chunks==case.get('cancel_after'):
                        write(OBJ+24,b'\x01'); trace.append(['cancel',1])
            elif name=='memcpy': write(a,bytes(machine.mem_read(b,c))); ret=a
            elif name=='format':
                fmt=string(b); assert fmt=='writing address 0x%X'
                write(a,(fmt.replace('%X',format(c,'X'))+'\0').encode()); trace.append(['format',fmt,c])
            elif name=='debug':
                fmt=string(a)
                text=fmt.replace('%X',format(b,'X')) if '%X' in fmt else fmt
                trace.append(['debug',text])
            elif name=='clock':
                ticks=1234567890123;ret=ticks&0xffffffff; machine.reg_write(UC_ARM_REG_R1,ticks>>32);trace.append(['clock',ticks])
            elif name=='divide':
                dividend=a+(b<<32); divisor=c+(d<<32)
                assert divisor==1000000
                result=dividend//divisor;ret=result&0xffffffff;machine.reg_write(UC_ARM_REG_R1,result>>32);trace.append(['divide',dividend,divisor,result])
            machine.reg_write(UC_ARM_REG_R0,ret)
            machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR));return
        guard_pc(pc,pcs)
        executed_pcs[hex(pc)]=executed_pcs.get(hex(pc),0)+1
        word=int.from_bytes(machine.mem_read(pc,4),'little')
        guard_instruction(word)
    def memwrite(machine,access,address,size,value,user):
        if not bounded(address,size): raise RuntimeError(('guest write outside private data',hex(address),size))
    def invalid(*args): raise RuntimeError('unmapped guest memory access')
    def interrupt(*args): guard_interrupt()
    uc.hook_add(UC_HOOK_CODE,code);uc.hook_add(UC_HOOK_MEM_WRITE,memwrite)
    uc.hook_add(UC_HOOK_MEM_INVALID,invalid);uc.hook_add(UC_HOOK_INTR,interrupt)
    uc.reg_write(UC_ARM_REG_R0,OBJ);uc.reg_write(UC_ARM_REG_SP,STACK+65520);uc.reg_write(UC_ARM_REG_LR,STOP)
    target=next(t for t in targets if case['method']+'()' in t['demangled'])
    uc.emu_start(target['address'],STOP+4,count=LIMIT+1)
    assert stopped,'instruction limit without return'
    return dict(case, result=uc.reg_read(UC_ARM_REG_R0), trace=trace, packet=bytes(uc.mem_read(OBJ+172,257)).hex(), cancel_final=bytes(uc.mem_read(OBJ+24,1))[0], epoch_memory=bytes(uc.mem_read(epoch,8)).hex(), epoch_address=epoch, instructions=count, executed_pcs=executed_pcs, intercepted_entries=intercepted)


def main():
    guards=negative_checks()
    segments,targets,pcs=inputs()
    cases=[dict(method='update',length=length,cancel=cancel,fail=fail) for length,cancel,fail in [(0,0,-1),(257,0,-1),(257,0,0),(257,0,2),(257,1,-1)]]
    cases.append(dict(method='update',length=512,cancel=0,fail=-1,cancel_after=1))
    observations=[run(segments,targets,pcs,c) for c in cases]
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'epoch-audit.json').write_text(json.dumps(dict(negative_guard_checks=guards,elf_sha256=SHA,targets=targets,cases=observations,oracle_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
    print(json.dumps({'cases':len(observations),'output':str(OUT/'epoch-audit.json')}))

if __name__=='__main__': main()
