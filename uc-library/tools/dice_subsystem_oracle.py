#!/usr/bin/env python3
"""Execute original ARM DICE filter/string methods, with explicit libc hooks."""
import argparse
import hashlib
import json
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
from elftools.elf.elffile import ELFFile


class Oracle:
    packet=0x10001000
    stack=0x20000000
    stop=0x30000000
    def __init__(self,repository):
        directory=repository/'uc-library/recovered-dice/client'
        self.manifest=json.loads((directory/'manifest.json').read_text())
        binary=repository/self.manifest['path']
        raw=binary.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==self.manifest['sha256']
        self.u=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM)
        with binary.open('rb') as stream:
            elf=ELFFile(stream)
            segments=[s for s in elf.iter_segments() if s['p_type']=='PT_LOAD' and s['p_memsz']]
            pages=set()
            for segment in segments:
                begin=int(segment['p_vaddr'])&~0xfff
                end=(int(segment['p_vaddr'])+int(segment['p_memsz'])+0xfff)&~0xfff
                pages.update(range(begin,end,0x1000))
            for page in sorted(pages): self.u.mem_map(page,0x1000)
            for segment in segments: self.u.mem_write(int(segment['p_vaddr']),segment.data())
        self.u.mem_map(0x10000000,0x10000)
        self.u.mem_map(self.stack,0x10000)
        self.u.mem_map(self.stop,0x1000)
        symbols=json.loads((directory/'symbols.json').read_text())
        self.symbols={operation:next(s for s in symbols if s['kind']=='STT_FUNC' and s['demangled'].startswith(prefix)) for operation,prefix in (
            ('accepts','Presonus::DICE::Dice3Subsystem::accepts('),
            ('string','Presonus::DICE::SysexPacket::getSysexCommandStr('))}
        for sym in self.symbols.values():
            code=(directory/sym['export_path']).read_bytes()
            assert code==raw[sym['file_offset']:sym['file_offset']+sym['size']]
            assert self.u.mem_read(sym['address'],sym['size'])==code
        self.hooks={0xaffc:'memcpy',0xb02c:'strlen',0xaf84:'strncat',0xb1c4:'guard_acquire',0xab7c:'guard_release'}
        self.hook_counts={name:0 for name in self.hooks.values()}
        def hook(uc,address,size,user):
            operation=self.hooks.get(address)
            if operation is None:return
            self.hook_counts[operation]+=1
            r0=uc.reg_read(arm.UC_ARM_REG_R0);r1=uc.reg_read(arm.UC_ARM_REG_R1);r2=uc.reg_read(arm.UC_ARM_REG_R2)
            if operation=='memcpy':
                assert r2<=32
                uc.mem_write(r0,bytes(uc.mem_read(r1,r2)))
                result=r0
            elif operation=='strlen':result=len(self.cstring(r0))
            elif operation=='strncat':
                assert r2<=31
                prefix=self.cstring(r0);suffix=self.cstring(r1)[:r2]
                uc.mem_write(r0+len(prefix),suffix+b'\0');result=r0
            elif operation=='guard_acquire':result=int(not (uc.mem_read(r0,1)[0]&1))
            else:uc.mem_write(r0,b'\1');result=0
            uc.reg_write(arm.UC_ARM_REG_R0,result)
            uc.reg_write(arm.UC_ARM_REG_PC,uc.reg_read(arm.UC_ARM_REG_LR))
        self.u.hook_add(unicorn.UC_HOOK_CODE,hook)

    def cstring(self,address):
        result=bytearray()
        for offset in range(128):
            value=self.u.mem_read(address+offset,1)[0]
            if not value:return bytes(result)
            result.append(value)
        raise AssertionError('unterminated original string')

    def call(self,operation,argument):
        u=self.u
        for i in range(13):u.reg_write(getattr(arm,f'UC_ARM_REG_R{i}'),0)
        u.reg_write(arm.UC_ARM_REG_CPSR,0x10)
        u.reg_write(arm.UC_ARM_REG_SP,self.stack+0xff00)
        u.reg_write(arm.UC_ARM_REG_LR,self.stop)
        u.reg_write(arm.UC_ARM_REG_R0,self.packet+0x1000)
        u.reg_write(arm.UC_ARM_REG_R1,argument)
        u.emu_start(self.symbols[operation]['address'],self.stop,count=10000)
        assert u.reg_read(arm.UC_ARM_REG_PC)==self.stop
        assert u.reg_read(arm.UC_ARM_REG_SP)==self.stack+0xff00
        return u.reg_read(arm.UC_ARM_REG_R0)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('repository',type=Path)
    args=p.parse_args()
    directory=args.repository/'uc-library/validation/dice-subsystem'
    directory.mkdir(parents=True,exist_ok=True)
    oracle=Oracle(args.repository)
    lines=[]
    filter_count=0
    for length in range(256):
        oracle.u.mem_write(oracle.packet+0x108,bytes([length]))
        for command in range(256):
            oracle.u.mem_write(oracle.packet+9,bytes([command]))
            result=oracle.call('accepts',oracle.packet)
            assert result in (0,1)
            lines.append(f'A {length} {command} {result}\n')
            filter_count+=1
    pointer_groups={}
    sequence=list(range(256))+list(reversed(range(256)))+[2,3,1,0,255,30,9,2,3,22,1,22]
    shared_pointer=None
    for command in sequence:
        pointer=oracle.call('string',command)
        group=f'K{command}' if command in (1,9,30) else 'U'
        if group in pointer_groups:assert pointer_groups[group]==pointer
        else:pointer_groups[group]=pointer
        if group=='U':shared_pointer=pointer
        assert shared_pointer is not None
        lines.append(f'G {command} {oracle.cstring(pointer).hex()} {group} {oracle.cstring(shared_pointer).hex()}\n')
    vectors=directory/'arm-vectors.txt'
    vectors.write_text(''.join(lines))
    proof=dict(original_elf_sha256=oracle.manifest['sha256'],oracle='Unicorn original ARM instructions plus explicit libc/C++ guard hooks',
               unicorn_version=unicorn.__version__,symbols=oracle.symbols,
               filter_cases=filter_count,command_string_cases=len(sequence),
               vectors_sha256=hashlib.sha256(vectors.read_bytes()).hexdigest(),
               libc_hooks=oracle.hook_counts,pointer_groups={name:hex(pointer) for name,pointer in pointer_groups.items()},
               namespace='Presonus::DICE',cpp_differential_passed=False,
               domain='All uint8 packet lengths and command bytes; sequential read-only string calls and retained return pointers across two instances. No concurrent access or ARM object-layout claim.',
               limitations=['Original command-string return pointer is proven; character const qualification is not encoded and portable API exposes const char*.',
                            'Unknown commands share mutable non-thread-local storage; sequential aliasing is tested. Original guard implementation and concurrent mutation behavior are not claimed equivalent.',
                            'SysexReceiver::receive remains pending because its original return type is unproven.'])
    (directory/'arm-oracle.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({key:value for key,value in proof.items() if key!='symbols'},indent=2))


if __name__=='__main__':main()
