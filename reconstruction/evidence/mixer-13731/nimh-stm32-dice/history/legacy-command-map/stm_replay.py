"""Bounded original STM32 command-loop replay with explicit transport/SDK models."""
from pathlib import Path
import hashlib
import json
import struct
import sys
import unicorn as uc
from unicorn import arm_const as a

root=Path(sys.argv[1]).resolve()
out=root/'evidence/recovery/2026-10-27/nimh-command-map'
b=(root/'evidence/recovery/2026-10-27/xmen-stm32/images/mixer-analysis/_ZL13nimh_arm_code.bin').read_bytes()
assert hashlib.sha256(b).hexdigest()=='b0979352e18a1093051fc6118a47694773cb9240e88087eca03aaa2ffe0f5e17'
BASE=0x08000000
REGS=(a.UC_ARM_REG_R0,a.UC_ARM_REG_R1,a.UC_ARM_REG_R2,a.UC_ARM_REG_R3)


def replay(packet,ready=1,sdk_result=0):
    m=uc.Uc(uc.UC_ARCH_ARM,uc.UC_MODE_THUMB|uc.UC_MODE_MCLASS)
    m.mem_map(BASE,0x80000);m.mem_write(BASE,b)
    m.mem_map(0x20000000,0x10000)
    m.mem_write(0x20000400,b[0x340e8:0x34f4c])
    m.reg_write(a.UC_ARM_REG_SP,0x2000fc00)
    buf=0x2000e500
    m.mem_write(buf,packet+bytes(256-len(packet)))
    emitted,calls,trace,models=[],[],[],[]
    requested=0
    # Register writes beyond normal RAM are forbidden. No hardware is mapped.
    def ret(v=0):
        m.reg_write(a.UC_ARM_REG_R0,v)
        m.reg_write(a.UC_ARM_REG_PC,m.reg_read(a.UC_ARM_REG_LR))
    def hook(m,pc,size,_):
        nonlocal requested
        trace.append(pc)
        regs=[m.reg_read(r) for r in REGS]
        if pc==0x08000ce8:
            if requested:
                m.emu_stop();return
            requested+=1
            m.mem_write(regs[0],bytes([len(packet)]))
            models.append('RX queue returns supplied complete packet and length')
            ret(buf)
        elif pc==0x08014dac:
            models.append('SDK readiness query returns supplied ready flag')
            ret(ready)
        elif pc==0x08014d68:
            models.append('diagnostic sink')
            ret()
        elif pc==0x08000d28:
            models.append('RX queue packet release')
            ret()
        elif pc==0x08000e00:
            data=bytes(m.mem_read(regs[0],256))
            n=data.index(0xf7)+1
            emitted.append(data[:n].hex())
            models.append('TX enqueue captured; queue/DMA/physical SPI not executed')
            ret(1)
        elif pc in (0x0800612c,0x08002840,0x0800f544,0x0800f56c,
                    0x0800f5b0,0x0800f5d4,0x0800f60c,0x0800fd60,
                    0x0800fda4,0x0801181c,0x08011880,0x0800123c):
            calls.append(dict(address=hex(pc),args=regs,
                              stack_args=list(struct.unpack('<II',m.mem_read(m.reg_read(a.UC_ARM_REG_SP),8)))))
            result=sdk_result if pc in (0x0800fda4,0x0800fd60) else 0
            models.append('recorded dependency '+hex(pc)+' returns '+hex(result)+'; no peripheral or scheduler execution')
            ret(result)
    m.hook_add(uc.UC_HOOK_CODE,hook)
    def invalid(m,access,address,size,value,_):
        raise AssertionError(dict(packet=packet.hex(),pc=hex(m.reg_read(a.UC_ARM_REG_PC)),
                                  access=access,address=hex(address),size=size,
                                  recent_trace=[hex(x) for x in trace[-12:]]))
    m.hook_add(uc.UC_HOOK_MEM_INVALID,invalid)
    try:
        m.emu_start(0x080014a3,0,count=50000)
    except uc.UcError as error:
        raise AssertionError(dict(packet=packet.hex(),error=str(error),
                                  pc=hex(m.reg_read(a.UC_ARM_REG_PC)),
                                  recent_trace=[hex(x) for x in trace[-20:]],
                                  calls=calls,emitted=emitted)) from error
    assert requested==1 and trace[-1]==0x08000ce8,hex(trace[-1])
    return dict(packet=packet.hex(),ready=ready,response_packets=emitted,calls=calls,
                state_window_20002b90=bytes(m.mem_read(0x20002b90,8)).hex(),
                avb_rate_state=bytes(m.mem_read(struct.unpack_from('<I',b,0xf58c)[0]+0x10,1)).hex(),
                instructions=len(trace),executed_addresses=[hex(x) for x in sorted(set(trace))],
                boundary_models=sorted(set(models)))


cases=[]
for src in (0,1,15,16,127,255):
    r=replay(bytes((0xf0,0x28,src>>4,src&15,0xf7)))
    assert r['response_packets']==['f02801f7'],r
    assert any(c['address']=='0x800fd60' and c['args'][1]==src for c in r['calls']),r
    cases.append(r)
for src in (0,1,15,16,127,255):
    p=bytes((0xf0,0x31,src>>4,src&15,0xf7))
    r=replay(p)
    assert r['response_packets']==['f03101f7'],r
    assert any(c['address']=='0x8002840' and c['args'][0]==src for c in r['calls']),r
    cases.append(r)
for rate in range(4):
    for link in (0,1,127):
        r=replay(bytes((0xf0,0x11,rate,link,0xf7)))
        assert r['response_packets']==['f01101f7'],r
        assert r['avb_rate_state']==bytes([rate+1]).hex(),r
        assert any(c['address']=='0x800612c' for c in r['calls']),r
        cases.append(r)
# Selected AVB commands use nibble pairs; firmware itself assembles their args.
for cmd in (0x23,0x24,0x25):
    p=bytes((0xf0,cmd,1,2,3,4,5,6,0xf7))
    r=replay(p)
    assert r['response_packets']==[bytes((0xf0,cmd,1,0xf7)).hex()],r
    cases.append(r)
r=replay(bytes.fromhex('f02df7'))
assert r['response_packets']==['f02d01f7'];cases.append(r)
r=replay(bytes.fromhex('f0110000f7'),ready=0)
assert r['response_packets']==['f01100f7'];cases.append(r)
source_blocks=(1,1,3,5,5,12,8,9)
destination_blocks=(1,1,0,5,5,12,8,9)
for src_type in range(8):
    for dst_type in range(8):
        for channel in (0,1,63):
            r=replay(bytes((0xf0,0x16,src_type,channel,dst_type,channel,0xf7)))
            assert r['response_packets']==['f01601f7'],r
            call=next(c for c in r['calls'] if c['address']=='0x800fda4')
            assert call['args']==[0,source_blocks[src_type],channel+(64 if src_type in (1,4) else 0),destination_blocks[dst_type]],r
            assert call['stack_args']==[channel+(64 if dst_type in (1,4) else 0),1],r
            cases.append(r)
r=replay(bytes.fromhex('f01600000000f7'),sdk_result=0xc4000005)
assert r['response_packets']==['f01600f7'];cases.append(r)
worker_cases=[]
for producer in cases:
    if not producer['packet'].startswith('f011') or not producer['ready']:
        continue
    state=bytes.fromhex(producer['state_window_20002b90'])
    assert state[0]==1
    m=uc.Uc(uc.UC_ARCH_ARM,uc.UC_MODE_THUMB|uc.UC_MODE_MCLASS)
    m.mem_map(BASE,0x80000);m.mem_write(BASE,b)
    m.mem_map(0x20000000,0x10000)
    m.mem_write(0x20002b90,state)
    m.reg_write(a.UC_ARM_REG_R4,0x20002a54)
    m.reg_write(a.UC_ARM_REG_SP,0x2000fc00)
    observed=[]
    def worker_hook(m,pc,size,_):
        if pc==0x08003026:
            m.emu_stop()
        elif pc==0x08002e20:
            observed.append(m.reg_read(a.UC_ARM_REG_R0))
            m.reg_write(a.UC_ARM_REG_PC,m.reg_read(a.UC_ARM_REG_LR))
    m.hook_add(uc.UC_HOOK_CODE,worker_hook)
    m.emu_start(0x08003001,0,count=1000)
    assert m.reg_read(a.UC_ARM_REG_PC)==0x08003026
    link=struct.unpack('<I',m.mem_read(0x20002a58,4))[0]
    rate=struct.unpack('<I',m.mem_read(0x20002a64,4))[0]
    assert link==state[3] and rate==state[1]
    assert m.mem_read(0x20002b90,1)==b'\0' and observed==[1]
    worker_cases.append(dict(producer_packet=producer['packet'],consumed_link=link,
                             consumed_rate=rate,transition_requests=observed,
                             scope='actual consumer segment; inactive link-state byte at +0x18 equals zero; state-transition helper hooked; no scheduler/topology completion proof'))
(out/'stm-replay.json').write_text(json.dumps(dict(
    image_sha256=hashlib.sha256(b).hexdigest(),
    tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    loop_entry='0x080014a2',dispatcher_function_candidate='0x08001454',
    cases=cases,worker_cases=worker_cases,hardware_actions=0,reconstructed_cpp_functions=0,
    scope='original instruction dispatch/field decoding/ack construction and small state helpers; completed RX frame injected; SDK readiness, event wake, SDK device calls and TX queue are explicit boundary models; no full boot/concurrency/hardware proof'),indent=2)+'\n')
print('STM32 command-loop cases passed:',len(cases),'deferred consumer cases:',len(worker_cases))
