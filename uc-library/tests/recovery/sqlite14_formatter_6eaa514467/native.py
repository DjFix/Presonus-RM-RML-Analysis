"""Execute exact ELF destructor ranges; Core implementation is never executed."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
TASK = Path(__file__).parent.name
PACKET = Path('temp/recovery-work/sqlite-issued/packet-sol61') / TASK / 'CONTEXT.json'
ROOT = Path.cwd()
def sha(data): return hashlib.sha256(data).hexdigest()
def observe():
    packet = json.loads(PACKET.read_text())
    extension = json.loads(Path('temp/recovery-work/formatter-initializer-extension-sol61/CONTEXT.json').read_text())
    for path, digest in extension['read_files'].items():
        if path not in extension['owned_files']:
            assert sha(Path(path).read_bytes()) == digest, path
    for path, digest in packet['task']['sources'].items():
        assert sha(Path(path).read_bytes()) == digest, path
    evidence = next(x for x in packet['task']['review']['evidence'] if x['path'].endswith('FORMATTER-NATIVE.json'))
    raw = Path(evidence['path']).read_bytes()
    assert sha(raw) == evidence['sha256']
    rows = json.loads(raw)
    targets = []
    for item in packet['originals']:
        original = dict(item['original'])
        image = (Path('/home/rs/projects/opencs/ai-line-analysis') / original['elf_path']).read_bytes()
        assert sha(image) == original['elf']
        elf = ELFFile(BytesIO(image)); syms = elf.get_section_by_name('.symtab')
        symbol, = syms.get_symbol_by_name(original['mangled'])
        section = elf.get_section(symbol['st_shndx'])
        offset = section['sh_offset'] + symbol['st_value'] - section['sh_addr']
        body = image[offset:offset + symbol['st_size']]
        assert offset == original['file_offset']
        assert symbol['st_value'] == original['address'] and symbol['st_size'] == original['size']
        assert symbol['st_shndx'] == original['section'] and sha(body) == original['range_sha256']
        row, = [r for r in rows if r['elf'] == original['elf'] and r['mangled'] == original['mangled']]
        core, = syms.get_symbol_by_name('_ZTVN4Core9FormatterE')
        point = core['st_value'] + 8
        assert struct.unpack('<I', body[-4:])[0] == point
        deleting = original['mangled'].endswith('D0Ev')
        endpoint = row['calls'][0]['address'] if deleting else None
        if deleting: assert row['calls'][0]['symbol'] == '_ZdlPv@@GLIBCXX_3.4'
        cases=[]
        for index in range(3):
            receiver=0x20000000+index*0x2000; stack=0x21001000; end=0x22000000
            model=unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
            pages=set()
            for address in (original['address'],original['address']+len(body)-1,receiver,stack-0x1000,end,endpoint or end):
                page=address&~4095
                if page not in pages: model.mem_map(page,4096);pages.add(page)
            model.mem_write(original['address'],body)
            name=0x12340000+index*16
            model.mem_write(receiver,struct.pack('<II',0x87654321,name))
            writes=[]; calls=[]; released=[]
            def code(_,pc,width,_arg):
                if pc==endpoint:
                    pointer=model.reg_read(UC_ARM_REG_R0)
                    assert pointer==receiver
                    assert bytes(model.mem_read(pointer,8))==struct.pack('<II',point,name)
                    calls.append({'kind':'unsized_delete','receiver':pointer,'provider_callbacks':1})
                    model.mem_unmap(pointer,4096);released.append(pointer)
                    model.reg_write(UC_ARM_REG_PC,model.reg_read(UC_ARM_REG_LR))
                else: assert original['address']<=pc<original['address']+original['size']-4
            def write(_,access,address,width,value,_arg):
                if receiver<=address<receiver+4096: writes.append([address,width,value])
                else: assert stack-4096<=address<stack
            model.hook_add(unicorn.UC_HOOK_CODE,code)
            model.hook_add(unicorn.UC_HOOK_MEM_WRITE,write)
            model.reg_write(UC_ARM_REG_R0,receiver);model.reg_write(UC_ARM_REG_SP,stack);model.reg_write(UC_ARM_REG_LR,end)
            model.emu_start(original['address'],end,count=100)
            assert model.reg_read(UC_ARM_REG_PC)==end and model.reg_read(UC_ARM_REG_SP)==stack
            assert writes==[[receiver,4,point]] and len(released)==int(deleting)
            if not deleting: assert bytes(model.mem_read(receiver,8))==struct.pack('<II',point,name)
            cases.append(dict(receiver=receiver,initial_name_word=name,writes=writes,calls=calls,released= released,output=f'{int(deleting)} 1 1'))
        original['elf_sha256']=original['elf']
        targets.append(dict(original=original,core_vtable_address=core['st_value'],cases=cases))
    return dict(unicorn_version=unicorn.__version__,targets=targets)
