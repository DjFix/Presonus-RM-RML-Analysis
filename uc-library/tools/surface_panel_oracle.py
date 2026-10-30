#!/usr/bin/env python3
"""Run original pure panel/surface helpers under ARM emulation."""
import argparse
import hashlib
import json
import random
import struct
from pathlib import Path
import unicorn
from unicorn import arm_const as arm
from elftools.elf.elffile import ELFFile


SEVEN='_ZNK8Presonus5Panel15SevenSegControl16convertCharToBmpEcb'
GROUP='_ZNK8Presonus7Surface14PanelRegistrar23mapGroupIdToControlTypeENS_5Panel16ControlRegistrar11ControlTypeE'
TRANSPORT='_ZN8Presonus7Surface20SurfaceRootComponent18isTransportControlEPKc'


class Original:
    heap=0x10000000
    stack=0x20000000
    stop=0x30000000
    def __init__(self,repository,role):
        directory=repository/'uc-library/recovered-all'/role
        self.manifest=json.loads((directory/'manifest.json').read_text())
        path=repository/self.manifest['path']
        raw=path.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==self.manifest['sha256']
        self.symbols={s['mangled']:s for s in json.loads((directory/'symbols.json').read_text()) if s['mangled'] in (SEVEN,GROUP,TRANSPORT)}
        self.u=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM)
        with path.open('rb') as stream:
            elf=ELFFile(stream)
            segments=[s for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
            ranges=[]
            for segment in segments:
                start=int(segment['p_vaddr'])&~4095
                end=(int(segment['p_vaddr'])+int(segment['p_memsz'])+4095)&~4095
                if ranges and start<=ranges[-1][1]:ranges[-1]=(ranges[-1][0],max(end,ranges[-1][1]))
                else:ranges.append((start,end))
            for start,end in ranges:self.u.mem_map(start,end-start)
            for segment in segments:self.u.mem_write(int(segment['p_vaddr']),segment.data())
        self.u.mem_map(self.heap,0x10000)
        self.u.mem_map(self.stack,0x10000)
        self.u.mem_map(self.stop,4096)
        self.blocks=set()
        self.u.hook_add(unicorn.UC_HOOK_BLOCK,lambda uc,address,size,data:self.blocks.add(address))
        self.libc_calls=0
        if role=='client':
            def strstr(uc,address,size,data):
                haystack=uc.reg_read(arm.UC_ARM_REG_R0)
                needle=uc.reg_read(arm.UC_ARM_REG_R1)
                h=self.string(haystack)
                n=self.string(needle)
                position=h.find(n)
                uc.reg_write(arm.UC_ARM_REG_R0,haystack+position if position>=0 else 0)
                uc.reg_write(arm.UC_ARM_REG_PC,uc.reg_read(arm.UC_ARM_REG_LR))
                self.libc_calls+=1
            self.u.hook_add(unicorn.UC_HOOK_CODE,strstr,begin=0xae7c,end=0xae7c)
        for symbol in self.symbols.values():
            exported=(directory/symbol['export_path']).read_bytes()
            assert raw[symbol['file_offset']:symbol['file_offset']+symbol['size']]==exported
    def string(self,address):
        result=bytearray()
        for i in range(8192):
            b=self.u.mem_read(address+i,1)[0]
            if b==0:return bytes(result)
            result.append(b)
        raise AssertionError('unterminated modeled string')
    def call(self,mangled,argument=0,second=0,string=None):
        u=self.u
        for i in range(13):u.reg_write(getattr(arm,f'UC_ARM_REG_R{i}'),0)
        u.reg_write(arm.UC_ARM_REG_CPSR,0x10)
        u.reg_write(arm.UC_ARM_REG_SP,self.stack+0xff00)
        u.reg_write(arm.UC_ARM_REG_LR,self.stop)
        u.mem_write(self.heap,b'\x5a'*64)
        u.reg_write(arm.UC_ARM_REG_R0,self.heap)
        if mangled==TRANSPORT:
            if string is None:argument=0
            else:
                assert len(string)<8000
                argument=self.heap+0x1000
                u.mem_write(argument,string+b'\0')
        u.reg_write(arm.UC_ARM_REG_R1,argument&0xffffffff)
        u.reg_write(arm.UC_ARM_REG_R2,second&0xffffffff)
        u.emu_start(self.symbols[mangled]['address'],self.stop,count=2000)
        assert u.reg_read(arm.UC_ARM_REG_PC)==self.stop,'instruction deadline'
        assert u.reg_read(arm.UC_ARM_REG_SP)==self.stack+0xff00,'stack not restored'
        assert bytes(u.mem_read(self.heap,64))==b'\x5a'*64,'pure helper changed its object'
        return u.reg_read(arm.UC_ARM_REG_R0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository',type=Path)
    args=parser.parse_args()
    destination=args.repository/'uc-library/validation/surface-panel'
    destination.mkdir(parents=True,exist_ok=True)
    rng=random.Random(0x53555246)
    originals={role:Original(args.repository,role) for role in ('client','server')}
    lines=[]
    counts={'seven_segment':0,'control_group':0,'transport_name':0}
    for role,original in originals.items():
        for character in range(256):
            for dot in range(2):
                value=original.call(SEVEN,character,dot)
                lines.append(f'S {role} {character} {dot} {value}\n')
                counts['seven_segment']+=1
    groups=list(range(-32768,32768))+[-2147483648,-2147483647,-65536,65536,2147483646,2147483647]
    groups.extend(rng.randrange(-2147483648,2147483648) for _ in range(4096))
    for group in groups:
        value=originals['client'].call(GROUP,group)
        signed=struct.unpack('<i',struct.pack('<I',value))[0]
        lines.append(f'G {group} {signed}\n')
        counts['control_group']+=1
    names=[None,b'',b'transport_',b'transport_play',b'transport_stop',b'transport',b'Transport_play',b'xtransport_play',b'prefix_transport_play',b'transport_\0after',b'\0transport_play',b'transport__',b'transport_\xff']
    for length in range(20):
        names.extend([b'transport_'[:length],b'x'*length,b'x'*length+b'transport_'])
    for _ in range(1024):
        value=bytes(rng.randrange(1,256) for _ in range(rng.randrange(1,80)))
        names.extend([value,b'transport_'+value,value+b'transport_'])
    for name in names:
        value=originals['client'].call(TRANSPORT,string=name)
        assert value in (0,1)
        lines.append(f'T {int(name is None)} {name.hex() if name else "-"} {value}\n')
        counts['transport_name']+=1
    vectors=destination/'arm-vectors.txt'
    vectors.write_text(''.join(lines))
    report=dict(oracle='Original ARM instructions executed under Unicorn',unicorn_version=unicorn.__version__,
        counts=counts,vectors_sha256=hashlib.sha256(vectors.read_bytes()).hexdigest(),
        originals={role:dict(sha256=value.manifest['sha256'],source=value.manifest['path'],functions=list(value.symbols.values()),basic_blocks=[hex(x) for x in sorted(value.blocks)],modeled_libc_strstr_calls=value.libc_calls) for role,value in originals.items()},
        domain='Exhaustive 8-bit character/bool combinations in both ELFs; exhaustive signed16 control-group values plus int32 boundaries/random samples; valid NUL-terminated byte strings or nullptr.',
        dependency_model='Transport helper only: PLT strstr uses its standard substring-search contract; libc implementation is not recovered or claimed verified.',
        declaration_uncertainties=['Original SevenSegControl C++ return spelling is not encoded; portable uint16_t preserves observed zero-extended bitmap return.','Original enum enumerator names, object layouts, inheritance and vtables are not recovered.'],
        hardware_verified=False,original_arm_abi_compatible=False,cpp_differential_passed=False)
    (destination/'arm-oracle.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items() if key!='originals'},indent=2),flush=True)


if __name__=='__main__':main()
