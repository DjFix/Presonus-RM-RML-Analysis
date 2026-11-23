"""Execute the two sealed original ARM print bodies with named finite runtime models."""
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ_UNMAPPED
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_PC

CLASS_NAME = 'SubDelayFormatter'
TARGETS = [{'original_address': 61260, 'original_size': 200, 'elf_sha256': '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0', 'firmware': 'CS18AI surface 13840', 'role': 'client', 'mangled': '_ZNK8Presonus5Mixer17SubDelayFormatter5printERN4Core9Formatter4DataE', 'section': 12, 'file_offset': 28492, 'content_sha256': '56d6de32cd001d7fab9dd85c59995f25ad652b91d968db7f02eb7679979708bb', 'elf_path': '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11/packeting/actual06-first-capture01/snapshot/rootfs/CS18_v13840/home/root/surface', 'call_targets': {45100: ['strlen@@GLIBC_2.4'], 45424: ['strncpy@@GLIBC_2.4'], 73196: ['_ZN4Core20MutableCStringTraitsINS_13CStringBufferILi128EEEE12appendFormatEPKcz'], 73336: ['_ZN4Core13CStringBufferILi128EEC1EPKc'], 1599844: ['__aeabi_f2d', '__extendsfdf2'], 1603480: ['__aeabi_fcmplt'], 1603576: ['__aeabi_f2iz', '__fixsfsi']}}, {'original_address': 138000, 'original_size': 200, 'elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07', 'firmware': 'RM/RML mixer 13731', 'role': 'server', 'mangled': '_ZNK8Presonus5Mixer17SubDelayFormatter5printERN4Core9Formatter4DataE', 'section': 12, 'file_offset': 105232, 'content_sha256': '25cf5b4d3bc90fe733af6ebef1be391c500336f5c978424af5e52740fde7c109', 'elf_path': '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11/packeting/actual06-first-capture01/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer', 'call_targets': {44696: ['strlen@@GLIBC_2.4'], 45032: ['strncpy@@GLIBC_2.4'], 76532: ['_ZN4Core20MutableCStringTraitsINS_13CStringBufferILi128EEEE12appendFormatEPKcz'], 106804: ['_ZN4Core13CStringBufferILi128EEC1EPKc'], 1403588: ['__aeabi_f2d', '__extendsfdf2'], 1407224: ['__aeabi_fcmplt'], 1407320: ['__aeabi_f2iz', '__fixsfsi']}}]
REFERENCE_PATH = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11/packeting/actual06-first-capture01/snapshot/temp/recovery-work/control10x20-after-4fed70d11/selection/mixer-formatters/SubDelayFormatter.native01.json')
REFERENCE_SHA256 = '93fbff7e8aaa2741b95de1601d883aa15fb2a3f4e6815bfe8dc432853d92a72d'
cases = [(0, 0, 32), (0, 9, 2), (0.001, 7, 32), (0.1, 15, 32), (0.5, 42, 6), (1, 7, 32), (10.125, 1, 32), (999.9, 10, 32), (1000, 12, 32), (3000.25, 99, 32), (-1.25, 7, 32), (-20, 7, 32), (0.25, 7, 1), (0.25, 7, 0), (49.999, 65, 32), (50, 65, 32), (50.001, 65, 32)]

def sha(data):
    return hashlib.sha256(data).hexdigest()

r0,r1,r2,r3=UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3
floatbin={
 '__aeabi_fadd':lambda a,b:a+b,'__aeabi_fsub':lambda a,b:a-b,'__aeabi_fmul':lambda a,b:a*b,
 '__aeabi_fdiv':lambda a,b:a/b,'__aeabi_fcmplt':lambda a,b:int(a<b),
 '__aeabi_fcmple':lambda a,b:int(a<=b),'__aeabi_fcmpgt':lambda a,b:int(a>b),
 '__aeabi_fcmpge':lambda a,b:int(a>=b),'__aeabi_fcmpeq':lambda a,b:int(a==b),
}
def helper_name(names):
    hits=[s for s in names if s.startswith('__aeabi_')]
    if hits:
        [value]=hits
        assert value in floatbin or value in ('__aeabi_f2iz','__aeabi_f2d')
        return value
    [s]=names
    if 'CStringBufferILi128EEC1EPKc' in s:return 'buffer_init'
    if '12appendFormatEPKcz' in s:return 'append_format'
    if s.startswith('strlen@'):return 'strlen'
    if s.startswith('strncpy@'):return 'strncpy'
    raise ValueError(f'Unrecognized selection boundary: {s}')
def word_float(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def float_word(x):return struct.unpack('<f',struct.pack('<I',x))[0]

def data_provider(e):
    return [(s['sh_addr'],s['sh_addr']+s['sh_size'],s.name,s.data())
            for s in e.iter_sections() if s.name in ('.rodata','.data.rel.ro','.data','.data.rel.ro.local') and s['sh_flags']&2]
def app_bytes(data,address,count):
    for a,b,_,blob in data:
        if a<=address<address+count<=b:return blob[address-a:address-a+count]
    raise ValueError(f'outside validated data sections {hex(address)} {count}')

def replay(e,original,symbol,data,imports):
    a,n=original['original_address'],original['original_size']
    ss=e.get_section_by_name('.symtab')
    [sym]=ss.get_symbol_by_name(symbol)
    sec=e.get_section(sym['st_shndx']); off=sym['st_value']-sec['sh_addr']
    code=sec.data()[off:off+n]
    assert (sym['st_value'], sym['st_size'], sym['st_shndx'], sec['sh_offset'] + off) == (
        a, n, original['section'], original['file_offset'])
    assert sha(code)==original['content_sha256']
    rows=[]
    for value,style,capacity in cases:
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        receiver,d,output,stack,end=0x24000000,0x25000000,0x26000000,0x27000000,0x28000000
        mapped={x&~4095 for x in (receiver,d,output,stack,end,a,a+n-1,*imports)}
        for page in mapped:u.mem_map(page,4096)
        u.mem_write(a,code)
        u.mem_write(receiver,b'\0'*8+bytes([style])+b'\0'*23)
        u.mem_write(d,struct.pack('<III',0,output,capacity)+struct.pack('<fI',value,0))
        u.mem_write(output,b'\xD9'*64)
        sp=stack+0xe00
        for reg,v in ((r0,receiver),(r1,d),(UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,end)):u.reg_write(reg,v)
        events=[]
        def read_string(addr):
            if not addr:return b''
            if addr&~4095 in mapped:return bytes(u.mem_read(addr,128)).split(b'\0')[0]
            return app_bytes(data,addr,128).split(b'\0')[0]
        def demand_data(cpu,access,address,size,value,ctx):
            page=address&~4095
            if page in mapped:return False
            valid=[(l,h,blob) for l,h,_,blob in data if l<=address<address+size<=h]
            if not valid:return False
            [(l,h,blob)]=valid
            cpu.mem_map(page,4096)
            first,last=max(page,l),min(page+4096,h)
            cpu.mem_write(first,blob[first-l:last-l])
            mapped.add(page)
            return True
        def code_provider(cpu,addr,size,ctx):
            if a<=addr<a+n:return
            assert addr in imports,f'Unreviewed code target {hex(addr)}'
            kind=imports[addr]
            aa,bb,cc,dd=[cpu.reg_read(i) for i in (r0,r1,r2,r3)]
            if kind in floatbin:
                result=floatbin[kind](float_word(aa),float_word(bb))
                cpu.reg_write(r0,result if kind.startswith('__aeabi_fcmp') else word_float(result))
            elif kind=='__aeabi_f2iz':
                cpu.reg_write(r0,int(float_word(aa))&0xffffffff)
            elif kind=='__aeabi_f2d':
                lo,hi=struct.unpack('<II',struct.pack('<d',float_word(aa)))
                cpu.reg_write(r0,lo);cpu.reg_write(r1,hi)
            elif kind=='buffer_init':
                assert stack<=aa<stack+4096-128
                cpu.mem_write(aa,(read_string(bb)[:127]+b'\0').ljust(128,b'\0'))
            elif kind=='append_format':
                assert stack<=aa<stack+4096-128
                fmt=read_string(bb).decode('ascii')
                specs=re.findall(r'%(?:[-+ #0]*)(?:\d+)?(?:\.\d+)?[cdiufgsxX%]',fmt)
                assert ''.join(specs).count('%')==fmt.count('%'),fmt
                args=[]; words=[cc,dd,*struct.unpack('<8I',cpu.mem_read(cpu.reg_read(UC_ARM_REG_SP),32))]
                z=0
                for spec in specs:
                    k=spec[-1]
                    if k=='%':continue
                    if k in ('f','g'):
                        z=(z+1)&~1
                        args.append(struct.unpack('<d',struct.pack('<II',*words[z:z+2]))[0]);z+=2
                    elif k=='s':
                        args.append(read_string(words[z]).decode('ascii'));z+=1
                    else:
                        raw=words[z];z+=1
                        args.append(raw-0x100000000 if k in 'di' and raw>=0x80000000 else raw)
                formatted=(fmt%tuple(args)).encode('ascii')
                cpu.mem_write(aa,(read_string(aa)+formatted)[:127]+b'\0')
                events.append(dict(format=fmt,args=args,result=formatted.decode('ascii')))
            elif kind=='strlen':
                cpu.reg_write(r0,len(read_string(aa)))
            elif kind=='strncpy':
                assert (aa==output and 0<=cc<=capacity and cc<=32) or (stack<=aa<stack+4096-128 and 0<=cc<=127), (aa,cc,capacity)
                cpu.mem_write(aa,read_string(bb)[:cc].ljust(cc,b'\0'))
                cpu.reg_write(r0,aa)
            else:raise ValueError(kind)
            cpu.reg_write(UC_ARM_REG_PC,cpu.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_MEM_READ_UNMAPPED,demand_data)
        u.hook_add(UC_HOOK_CODE,code_provider)
        u.emu_start(a,end,count=240)
        assert (u.reg_read(UC_ARM_REG_PC),u.reg_read(UC_ARM_REG_SP))==(end,sp)
        payload=bytes(u.mem_read(output,64))
        assert payload[capacity:]==b'\xD9'*(64-capacity)
        assert not capacity or b'\0' in payload[:capacity]
        assert u.mem_read(receiver,32)==b'\0'*8+bytes([style])+b'\0'*23
        assert bytes(u.mem_read(d, 12)) == struct.pack('<III', 0, output, capacity)
        assert bytes(u.mem_read(d + 16, 4)) == bytes(4)
        rows.append(dict(input_value=word_float(value),style=style,capacity=capacity,
            output_hex=payload[:capacity].hex(),value_after=struct.unpack('<I',u.mem_read(d+12,4))[0],
            format_calls=events))
    return dict(elf_sha256=original['elf_sha256'],original_mangled=symbol,address=a,size=n,
                file_offset=sec['sh_offset']+off,range_sha256=sha(code),iterations=len(rows),cases=rows)

def companion_ranges(elf, target):
    symbols = elf.get_section_by_name('.symtab')
    prefix = f'_ZN8Presonus5Mixer{len(CLASS_NAME)}{CLASS_NAME}'
    result = []
    for variant in ('D0', 'D1'):
        name = prefix + variant + 'Ev'
        [sym] = symbols.get_symbol_by_name(name)
        section = elf.get_section(sym['st_shndx'])
        offset = sym['st_value'] - section['sh_addr']
        assert 0 <= offset and 0 < sym['st_size'] <= section['sh_size'] - offset
        data = section.data()[offset:offset + sym['st_size']]
        result.append(dict(mangled=name, variant=variant, address=sym['st_value'],
                           size=sym['st_size'], section=sym['st_shndx'],
                           file_offset=section['sh_offset'] + offset, sha256=sha(data)))
    return result


def generate():
    raw_reference = REFERENCE_PATH.read_bytes()
    assert sha(raw_reference) == REFERENCE_SHA256
    historical = json.loads(raw_reference)['exact_role_results']
    by_elf = {row['elf_sha256']: row for row in historical.values()}
    results = []
    for target in TARGETS:
        path = Path(target['elf_path'])
        assert sha(path.read_bytes()) == target['elf_sha256']
        with path.open('rb') as stream:
            elf = ELFFile(stream)
            imports = {addr: helper_name(names) for addr, names in target['call_targets'].items()}
            record = replay(elf, target, target['mangled'], data_provider(elf), imports)
            record['native_companion_ranges'] = companion_ranges(elf, target)
        baseline = by_elf[target['elf_sha256']]
        assert record['cases'][:len(baseline['cases'])] == baseline['cases'], target['role']
        record['section'] = target['section']
        record['role'] = target['role']
        record['firmware'] = target['firmware']
        record['modeled_call_boundaries'] = [
            dict(address=address, provider=kind) for address, kind in imports.items()]
        results.append(record)
    return {'originals': results, 'sealed_reference_sha256': REFERENCE_SHA256}


if __name__ == '__main__':
    Path(sys.argv[1]).write_text(json.dumps(generate(), indent=2) + '\n')
