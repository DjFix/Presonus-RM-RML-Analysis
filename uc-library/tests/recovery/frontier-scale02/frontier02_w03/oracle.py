"""Execute exact original constructor; fixture interception is explicit."""
import argparse, hashlib, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC

ELF_PATH = Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
ELF_HASH = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
TARGET = '_ZN8Presonus3Dsp18SLReverbControllerC1Ei'

def observe(identity, fill):
    assert hashlib.sha256(ELF_PATH.read_bytes()).hexdigest() == ELF_HASH
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    with ELF_PATH.open('rb') as stream:
        elf = ELFFile(stream)
        sections = elf.get_section_by_name('.symtab')
        symbol = next(s for s in sections.iter_symbols() if s.name == TARGET)
        assert symbol['st_value'] == 0xbf358 and symbol['st_size'] == 260
        section = elf.get_section(symbol['st_shndx'])
        offset = section['sh_offset'] + symbol['st_value'] - section['sh_addr']
        stream.seek(offset)
        native = stream.read(symbol['st_size'])
        assert hashlib.sha256(native).hexdigest() == '5aa56f885f0ef761f1b6ce5964981569c21b644e5bd70b9a5429e202180e76f4'
        provider_ranges = []
        for name, address, size, expected_hash in [('_ZN8Presonus3Dsp10ControllerC2EiPKNS0_19ParamDescriptorListE', 0xb251c, 80, 'd5f9264563594fe57ab0e1a269ac19b0481500550891848b8584f82d4deeb30a'), ('_ZN3DSP10BiquadCalcIdLb0EEC1Ev', 0xb9518, 416, '93937b23ab4bf9f202dca909f51ac346713116b0b048d7c357f57a331bbe822f')]:
            provider = next(s for s in sections.iter_symbols() if s.name == name)
            assert provider['st_value']==address and provider['st_size']==size
            sec=elf.get_section(provider['st_shndx'])
            off=sec['sh_offset']+address-sec['sh_addr']
            stream.seek(off); body=stream.read(size)
            assert hashlib.sha256(body).hexdigest()==expected_hash
            provider_ranges.append({'mangled':name,'address':address,'size':size,'section':int(provider['st_shndx']),'file_offset':off,'sha256':expected_hash})
        pages = set()
        for segment in elf.iter_segments():
            if segment['p_type'] != 'PT_LOAD':
                continue
            start, size = segment['p_vaddr'], segment['p_memsz']
            for page in range(start & ~4095, (start + size + 4095) & ~4095, 4096):
                if page not in pages:
                    uc.mem_map(page, 4096)
                    pages.add(page)
            uc.mem_write(start, segment.data())
    obj, stack, stop = 0x10000000, 0x20000000, 0x30000000
    for address in (obj, stack, stop):
        uc.mem_map(address, 0x10000)
    uc.mem_write(obj, bytes([fill]) * 1024)
    uc.reg_write(UC_ARM_REG_R0, obj)
    uc.reg_write(UC_ARM_REG_R1, identity & 0xffffffff)
    uc.reg_write(UC_ARM_REG_SP, stack + 0x8000)
    uc.reg_write(UC_ARM_REG_LR, stop)
    calls, writes = [], []
    allowed = [(0xbf358,0xbf44c),(0xb9518,0xb969c),(0xb251c,0xb2568)]
    # Execute all three bound application bodies. No boundary interception,
    # no Core binary execution, and no external providers are permitted.
    def code(machine, pc, size, _):
        if pc == stop:
            machine.emu_stop()
            return
        if pc in (0xb251c, 0xb9518):
            args=[machine.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
            args[0] -= obj
            calls.append({'address':pc,'args':args})
        if not any(lo <= pc < hi for lo,hi in allowed):
            raise RuntimeError('Unbound native execution: '+hex(pc))
    def write(machine, access, address, size, value, _):
        if obj <= address < obj + 1024:
            writes.append([address-obj,size,value,machine.reg_read(UC_ARM_REG_PC)])
    uc.hook_add(UC_HOOK_CODE,code)
    uc.hook_add(UC_HOOK_MEM_WRITE,write)
    uc.emu_start(0xbf358,stop,count=10000)
    assert len(calls)==2
    return {'id':identity,'fill':fill,'calls':calls,'writes':writes,'memory':bytes(uc.mem_read(obj,1024)).hex(),'provider_ranges':provider_ranges,'range':{'address':0xbf358,'size':260,'section':int(symbol['st_shndx']),'file_offset':offset,'sha256':hashlib.sha256(native).hexdigest()}}

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    result={'elf_sha256':ELF_HASH,'oracle':'Unicorn original target, actual Controller C2 and actual Biquad C1 instructions; no provider interception','cases':[observe(i,f) for i,f in [(0,0xa5),(1,0x5a),(-1,0xc3),(2147483647,0xff),(-2147483648,0x39)]]}
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
