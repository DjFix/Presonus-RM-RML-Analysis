"""Original ARM HiPass/LoPass controller execution, with no replaced calls."""
import argparse
import hashlib
import json
import random
import struct
from pathlib import Path
import capstone
from unicorn import arm_const as arm
import mixer_dsp_oracle as dsp

METHODS = {
    'H': 'Presonus::Dsp::HiPassController::setValue(',
    'L': 'Presonus::Dsp::LoPassController::setValue(',
    'h': 'Presonus::Dsp::HiPassController::getValue(',
    'l': 'Presonus::Dsp::LoPassController::getValue(',
}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('repository',type=Path)
    p.add_argument('--inspect',action='store_true')
    a=p.parse_args()
    dsp.PREFIXES=METHODS
    oracle=dsp.Oracle(a.repository)
    out=a.repository/'uc-library/validation/filter-control'
    out.mkdir(parents=True,exist_ok=True)
    if a.inspect:
        cs=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_ARM)
        for op,s in oracle.functions.items():
            print(op,s['demangled'],hex(s['address']))
            for ins in cs.disasm(bytes(oracle.u.mem_read(s['address'],s['size'])),s['address']):
                print(hex(ins.address),ins.mnemonic,ins.op_str)
        return
    # Permit the complete disjoint primary and process-state objects, recording
    # writes to their entire initialized extents. No Core methods may execute.
    oracle.ranges.append((oracle.obj,oracle.obj+4096))
    core_symbols=json.loads((a.repository/'uc-library/recovered-all/server/symbols.json').read_text())
    core_ranges=[(s['address'],s['address']+s['size']) for s in core_symbols if s['kind']=='STT_FUNC' and s['mangled'].startswith(('_ZN4Core','_ZNK4Core')) and s['size']]
    import unicorn
    def guard_core(uc,address,size,user):
        assert not any(lo<=address<hi for lo,hi in core_ranges),f'Core body entered: {address:x}'
    oracle.u.hook_add(unicorn.UC_HOOK_BLOCK,guard_core)
    rng=random.Random(0x46494c54)
    edges=[0,0x80000000,1,0x80000001,0x7f800000,0xff800000,0x7fc12345,0x7fa12345,0xffa12345,1103102475,1103102476,1103102477,0x469c3ffe,0x469c3fff,0x469c4000,0x3f800000,0xbf800000]
    rows=[]
    counts={op:0 for op in METHODS}
    for op,s in oracle.functions.items():
        cases=[]
        for index in (0,1,-1,0x7fffffff,-0x80000000):
            for old in (0,1,2,0x80,0xff):
                for pending in (0,1,0x80,0xff):
                    for value in edges:
                        cases.append((index,value,rng.getrandbits(32),rng.randrange(256),old,pending))
        cases.extend((rng.choice((0,0,0,1,-1)),rng.getrandbits(32),rng.getrandbits(32),rng.randrange(256),rng.randrange(256),rng.randrange(256)) for _ in range(1000))
        for index,value,prior,dirty,active,pending in cases:
            primary=bytearray([0xa5]*64)
            process=bytearray([0x5a]*0x140)
            struct.pack_into('<I',primary,0x28,oracle.obj+0x100)
            primary[0x1c]=pending
            struct.pack_into('<I',process,4,prior)
            process[0x139]=dirty
            process[0x13a]=active
            u=oracle.u
            u.mem_write(oracle.obj,bytes(primary))
            u.mem_write(oracle.obj+0x100,bytes(process))
            for i in range(13):u.reg_write(getattr(arm,f'UC_ARM_REG_R{i}'),0xaaaa0000+i)
            u.reg_write(arm.UC_ARM_REG_CPSR,0x10)
            u.reg_write(arm.UC_ARM_REG_R0,oracle.obj)
            u.reg_write(arm.UC_ARM_REG_R1,index&0xffffffff)
            u.reg_write(arm.UC_ARM_REG_R2,value)
            u.reg_write(arm.UC_ARM_REG_SP,oracle.stack+0xff00)
            u.reg_write(arm.UC_ARM_REG_LR,oracle.stop)
            u.emu_start(s['address'],oracle.stop,count=20000)
            assert u.reg_read(arm.UC_ARM_REG_PC)==oracle.stop
            assert u.reg_read(arm.UC_ARM_REG_SP)==oracle.stack+0xff00
            after=bytearray(u.mem_read(oracle.obj,64))
            changed=bytearray(u.mem_read(oracle.obj+0x100,0x140))
            expected_primary=bytearray(primary)
            expected_process=bytearray(process)
            expected_primary[0x1c]=after[0x1c]
            expected_process[4:8]=changed[4:8]
            expected_process[0x139:0x13b]=changed[0x139:0x13b]
            assert expected_primary==after and expected_process==changed,'unexpected write'
            result=u.reg_read(arm.UC_ARM_REG_R0) if op.islower() else 0
            rows.append(f'{op} {index} {value:08x} {prior:08x} {dirty} {active} {pending} {result:08x} {struct.unpack_from("<I",changed,4)[0]:08x} {changed[0x139]} {changed[0x13a]} {after[0x1c]}\n')
            counts[op]+=1
    fixture=out/'arm-vectors.txt'
    fixture.write_text(''.join(rows))
    report=dict(original_elf_sha256=oracle.manifest['sha256'],functions=oracle.functions,cases=counts,
        oracle='Original ELF ARM instructions and original soft-float compare; no intercepted/replaced functions; guarded against Core execution',
        fixtures_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
        domain='Disjoint initialized valid primary/process state. Every method index 0,1,-1,INT_MIN,INT_MAX; all flag branches including noncanonical bytes; threshold adjacent bits, NaNs, infinities, signed zeros, subnormals, deterministic random bit patterns. Full state/sentinels checked. Setter return declaration unresolved and R0 ignored. No ARM layout/ownership/hardware claim.')
    (out/'arm-oracle.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=counts,fixtures_sha256=report['fixtures_sha256'])),flush=True)

if __name__=='__main__':main()
