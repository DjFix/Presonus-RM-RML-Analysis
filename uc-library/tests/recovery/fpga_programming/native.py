"""Execute only hash-bound application ARM ranges in private Unicorn memory.
All guest Core/libc/stream/transport calls are explicit rejecting/captured traps.
No guest instruction can invoke a host syscall, device, or network operation.
"""
import hashlib, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_INTR, UC_HOOK_MEM_INVALID
from unicorn.arm_const import *
ELF = Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
SHA = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
OUT = Path('uc-library/tests/recovery/fpga_programming/fixtures.json')
EVIDENCE = Path('evidence/recovery/2026-11-05/rolling200-02/fpga-resume18')
raw = ELF.read_bytes()
assert hashlib.sha256(raw).hexdigest() == SHA
A=0x1000000; V=A+0x1000; DATA=A+0x2000; STR=A+0x3000; STACK=0x2000000; STOP=0x3000000; POST=STOP+0x100
WAIT=0xa4fbc; UPDATE=0xa51e4; PACK=0xa468c
ranges=[]
with ELF.open('rb') as f:
    elf=ELFFile(f)
    segments=[(int(s['p_vaddr']),s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
    for name,expected in [('_ZN8Presonus4NOAA16TCardFPGAUpdater19waitFirmwareCommandEPhiPKcx','52e61307d823bd76c42f27aa6ad5e5ac84b91683d3b8c30183842842277708c7'),('_ZN8Presonus4NOAA16TCardFPGAUpdater6updateEv','52d293a8b8edc0ab6f498eac5504903cfef855cc3509c1d842f337f76782862a'),('_Z6pack32jPh','d84b5e489320a5a313d93284642889436b2b26497a908712985c9099a77a4345')]:
        sym=elf.get_section_by_name('.symtab').get_symbol_by_name(name)[0];sec=elf.get_section(sym['st_shndx']);a=int(sym['st_value']);n=int(sym['st_size']);off=int(sec['sh_offset'])+a-int(sec['sh_addr']);h=hashlib.sha256(raw[off:off+n]).hexdigest();assert h==expected
        ranges.append(dict(mangled=name,address=a,size=n,section=sec.name,section_index=int(sym['st_shndx']),file_offset=off,range_sha256=h,elf_sha256=SHA,role='server',firmware='RM/RML mixer 13731'))

def execute(c):
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x500000);u.mem_map(A,0x10000);u.mem_map(STACK,0x10000);u.mem_map(STOP,4096)
    for a,b in segments:u.mem_write(a,b)
    def w(a,x):u.mem_write(a,struct.pack('<I',x&0xffffffff))
    def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
    def text(a):return bytes(u.mem_read(a,512)).split(b'\0')[0].decode() if a else None
    def ret(x=0):u.reg_write(UC_ARM_REG_R0,x&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    obs=dict(packets=[],messages=[],debug=[],sleeps=[],closes=0,opens=0,reads=0,pumps=[],notices=0)
    writes_log=[]; instruction_counts={str(x['address']):0 for x in ranges}
    state=dict(stopped=False,tick=0,post=False,packet_clock=0,offset=0,command_index=0,writes=0)
    image=bytes((i*73+19)&255 for i in range(c.get('size',0)))
    def progress(s):
        # Native Core/listener provider boundaries, not recovered Core code.
        clock();obs['messages'].append(s if s is not None else '<null>')
        if s:obs['debug'].extend([s,'\n'])
    def hook(uc,pc,n,_):
        if pc==STOP:state['stopped']=True;uc.emu_stop();return
        r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2);r3=uc.reg_read(UC_ARM_REG_R3)
        if pc==0x116908:
            # First two calls inside packet construction use the real packet
            # gateway in C++; fixture service clock begins after captured post.
            value=clock()&((1<<64)-1);uc.reg_write(UC_ARM_REG_R0,value&0xffffffff);uc.reg_write(UC_ARM_REG_R1,value>>32);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
        if pc==0x157a08:
            signed=lambda x:x-(1<<64) if x&(1<<63) else x
            x=signed(r0+(r1<<32));d=signed(r2+(r3<<32));q=abs(x)//abs(d);q=-q if (x<0)!=(d<0) else q;bits=q&((1<<64)-1);uc.reg_write(UC_ARM_REG_R0,bits&0xffffffff);uc.reg_write(UC_ARM_REG_R1,bits>>32);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
        if pc==0xa4f0c:progress(text(r1));ret();return
        if pc==0xa4fa0:progress(text(r1));obs['sleeps'].append(2000);ret();return
        if pc==0x116a38:
            fmt=text(r0);args=(r1,r2)
            if '%i' in fmt:fmt=fmt.replace('%i','%d')
            obs['debug'].append(fmt % args[:fmt.count('%')] if '%' in fmt else fmt);ret();return
        if pc==0x10e948:obs['sleeps'].append(r0);ret();return
        if pc in [0xaa60,0xae68]:
            assert r2<=256
            b=bytes([r1&255])*r2 if pc==0xaa60 else bytes(uc.mem_read(r1,r2))
            assert STACK<=r0 and r0+r2<=STACK+65536
            uc.mem_write(r0,b);ret(r0);return
        if pc==0x1cf90:
            assert STACK<=r0<STACK+65536
            uc.mem_write(r0,b'\0');ret(r0);return
        if pc==0x4e974:
            fmt=text(r1);value=r2
            if '%d' in fmt and value&(1<<31):value-=1<<32
            b=(fmt % value).encode()+b'\0';assert len(b)<=64 and STACK<=r0 and r0+len(b)<=STACK+65536;uc.mem_write(r0,b);ret(r0);return
        if pc==0x8cf44:
            assert r0==A+0x4000
            obs['opens']+=1;ret(-1 if c.get('fault')=='open' else 0);return
        if pc==0x8cec4:
            assert r0==A+0x4000 and r2==200 and STACK<=r1 and r1+200<=STACK+65536
            chunk=image[state['offset']:state['offset']+200];uc.mem_write(r1,chunk);state['offset']+=len(chunk);obs['reads']+=1;ret(len(chunk));return
        if pc==0x8cf18:
            assert r0==A+0x4000
            obs['closes']+=1;ret();return
        if pc==0xa4b90:
            assert r1==A+8
            # Dedicated boundary-contract cases. Actual portable wait provider
            # separately replays response injection/timeout, not native Core.
            obs['delegated']=[r1-A,(r2+(r3<<32))];w(r1,7 if c.get('delegate_reply') else 0);ret(bool(c.get('delegate_reply')));return
        if pc==POST:
            p=r1;assert STACK<=p and p+0x109<=STACK+65536;length=bytes(uc.mem_read(p+0x108,1))[0];packet=bytes(uc.mem_read(p+8,length));obs['packets'].append(packet.hex())
            # Inherited post resets shared response storage before transport.
            uc.mem_write(A+4,b'\0\0');w(A+8,0)
            stage=packet[1] if len(packet)>1 else -1
            reply=127 if stage==2 else packet[3] if stage==3 else state['command_index']&127
            if stage==3:state['command_index']=(state['command_index']+1)&127
            fault=c.get('fault','none');target=(stage==2 and fault.startswith('erase')) or (stage==3 and len(obs['packets'])==2 and fault.startswith('block')) or (stage==5 and fault.startswith('finish'))
            status=3 if target and fault.endswith('status') else 0
            if target and fault.endswith('seq'):reply=(reply+1)&255
            state.update(post=True,tick=0,reply=reply,status=status)
            state['reply_after']=c.get('reply_after',0)
            if target and fault.endswith('timeout'):state['reply_after']=-1
            # Reply injection is captured state only; no transport body runs.
            if state['reply_after']==0:uc.mem_write(A+4,b'\1');w(A+8,reply);uc.mem_write(A+5,bytes([status]))
            ret();return
        assert any(x['address']<=pc<x['address']+x['size'] for x in ranges),(c['name'],'PC outside allowlist',hex(pc))
        for x in ranges:
            if x['address']<=pc<x['address']+x['size']:instruction_counts[str(x['address'])]+=1
        # ARM SVC/SWI/undefined software interrupt is forbidden even inside ranges.
        opcode=struct.unpack('<I',uc.mem_read(pc,4))[0];assert (opcode&0x0f000000)!=0x0f000000
    # Correct reply schedule uses per-transaction failure plan.
    def clock():
        if state['post']:
            idx=state['tick'];state['tick']+=1
            after=state.get('reply_after',c.get('reply_after',0))
            if after>=0 and idx>=after:
                u.mem_write(A+4,b'\1');w(A+8,state['reply']);u.mem_write(A+5,bytes([state['status']]))
            return (c.get('start_ms',100)+idx*c.get('step_ms',400))*1000000
        return 100000000
    def writes(uc,access,a,n,value,_):
        assert (STACK<=a and a+n<=STACK+65536) or (A<=a and a+n<=A+512) or (0x4953a0<=a and a+n<=0x4953ac),(hex(a),n)
        state['writes']+=1
        if not STACK<=a<STACK+65536:writes_log.append(dict(address=a,size=n,value=value))
    def forbidden(*_):raise AssertionError('Guest syscall/interrupt or invalid memory rejected')
    u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,writes);u.hook_add(UC_HOOK_INTR,forbidden);u.hook_add(UC_HOOK_MEM_INVALID,forbidden)
    w(A,V);w(V+8,POST);u.mem_write(A+20,bytes([c.get('cancel',0)]));w(A+12,A+0x4000);u.mem_write(DATA,bytes((i*17+3)&255 for i in range(260)));u.mem_write(STR,b'wait\0');u.mem_write(STR+32,b'\0');u.mem_write(STACK,b'\0'*65536)
    for i in range(13):u.reg_write(UC_ARM_REG_R0+i,0)
    u.reg_write(UC_ARM_REG_R0,A);u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP)
    if c['mode']=='wait':
        u.reg_write(UC_ARM_REG_R1,0 if c.get('null') else DATA);u.reg_write(UC_ARM_REG_R2,c.get('length',4)&0xffffffff);u.reg_write(UC_ARM_REG_R3,STR+32 if c.get('message')==2 else STR if c.get('message',True) else 0)
        timeout=c.get('timeout',4000)&((1<<64)-1);w(STACK+0xf000,timeout);w(STACK+0xf004,timeout>>32)
        entry=WAIT
    else:entry=UPDATE
    u.emu_start(entry,STOP+4,count=3000000);assert state['stopped'],c['name'];obs['return']=u.reg_read(UC_ARM_REG_R0);obs['memory_write_count']=state['writes'];obs['object_global_writes']=writes_log;obs['instruction_counts']=instruction_counts;obs['state']=[bytes(u.mem_read(A+4,1))[0],r(A+8),bytes(u.mem_read(A+5,1))[0]]
    return obs

cases=[]
for n in [0,1,2,3,4,5,199,200,201,399,400,4201,25601]:cases.append(dict(name='image_'+str(n),mode='update',size=n))
for fault in ['erase_timeout','erase_status','erase_seq','open','block_timeout','block_status','block_seq','finish_timeout','finish_status','finish_seq']:
    cases.append(dict(name=fault,mode='update',size=4,fault=fault,step_ms=20000))
cases.append(dict(name='cancel_update',mode='update',size=4,cancel=1))
for name,extra in [('immediate',{}),('null_command_message',dict(message=False)),('empty_command_message',dict(message=2)),('zero_timeout',dict(timeout=0,reply_after=-1)),('negative_timeout',dict(timeout=-1,reply_after=-1)),('timeout_equal',dict(timeout=400,reply_after=-1)),('cadence',dict(timeout=4000,reply_after=-1)),('delayed',dict(reply_after=7,step_ms=300)),('cancel',dict(cancel=1)),('truncated_256',dict(length=256)),('negative_length',dict(length=-1)),('negative_clock',dict(start_ms=-4294967300)),('low_word_wrap',dict(start_ms=4294967290)),('elapsed_low_word_wrap',dict(timeout=8589934592,step_ms=4294967396,reply_after=-1)),('backwards_clock',dict(step_ms=-400,reply_after=4)),('minimum_timeout',dict(timeout=-9223372036854775808,reply_after=-1)),('maximum_timeout',dict(timeout=9223372036854775807,reply_after=4)),('null_delegate',dict(null=True,delegate_reply=True)),('zero_length_delegate',dict(length=0,delegate_reply=False)),('null_message_delegate',dict(null=True,message=False,delegate_reply=True))]:
    cases.append(dict(name='wait_'+name,mode='wait',size=0,**extra))
for c in cases:c['expected']=execute(c)
OUT.write_text(json.dumps(dict(version=1,elf_sha256=SHA,ranges=ranges,unicorn_version=__import__('unicorn').__version__,cases=cases,limitations=['Only exact application updater/wait/pack32 instructions execute. All Core, C library, FirmwareBundle stream and virtual post calls are explicit bounded emulated boundaries.','Stack image tail initialized to zero and retains previous block data; no arbitrary uninitialized native tail equivalence.','Ordinary original returns, layout, ARM ABI, exceptions, hardware and concurrency unverified.','Native waitResponseSet delegated contract only; actual source provider replay is separate.','Native negative read has unsafe/unbounded behavior and is excluded; portable fail-closed adaptation is separately tested.'],isolation=dict(pc_allowlist=True,write_bounds=True,interrupt_rejection=True,invalid_memory_rejection=True,host_syscall_passthrough=False,device_access=False)),indent=2)+'\n')
print('Native private-memory executions:',len(cases),'exact application ranges; no hardware/host syscall passthrough')
