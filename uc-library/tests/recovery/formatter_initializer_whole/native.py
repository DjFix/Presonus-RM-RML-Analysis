"""Exact application initializer instructions; runtime/Core boundaries intercepted."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct
import unicorn
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
from elftools.elf.elffile import ELFFile
PACKET = Path('temp/recovery-work/formatter-initializer-extension-sol61/CONTEXT.json')
OWNED = set(json.loads(PACKET.read_text())['owned_files'])
def sha(data): return hashlib.sha256(data).hexdigest()
def observe():
    context=json.loads(PACKET.read_text())
    for path,digest in context['read_files'].items():
        if path not in OWNED: assert sha(Path(path).read_bytes())==digest,path
    targets=[]
    for task in context['tasks']:
      for original in task['originals']:
        image=(Path('/home/rs/projects/opencs/ai-line-analysis')/original['elf_path']).read_bytes()
        assert sha(image)==original['elf']
        elf=ELFFile(BytesIO(image));syms=elf.get_section_by_name('.symtab')
        symbol,=syms.get_symbol_by_name(original['mangled']);section=elf.get_section(symbol['st_shndx'])
        offset=section['sh_offset']+symbol['st_value']-section['sh_addr'];body=image[offset:offset+symbol['st_size']]
        assert offset==original['file_offset'] and sha(body)==original['range_sha256']
        assert symbol['st_value']==original['address'] and symbol['st_size']==original['size'] and symbol['st_shndx']==int(original['section_json'])
        literals=[r['value'] for r in original['literal_pool']];guard,receiver,nameptr,vptr,dtor,dso=literals
        cls='PreDelayFormatterT9' if 'PreDelayFormatterT9' in original['mangled'] else 'FxReverbNumFormatter'
        cls_code=('19' if cls.startswith('PreDelay') else '20')+cls
        vtable,=syms.get_symbol_by_name('_ZTVN8Presonus5Mixer'+cls_code+'E');assert vptr==vtable['st_value']+8
        destructor,=syms.get_symbol_by_name('_ZN8Presonus5Mixer'+cls_code+'D1Ev');assert dtor==destructor['st_value']
        state=8 if cls.startswith('PreDelay') else ord('R')
        boundaries={r['address']:r['symbol'] for r in original['calls']}
        cases=[]
        def machine():
          m=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM);pages=set()
          for seg in elf.iter_segments():
            if seg['p_type']!='PT_LOAD':continue
            for page in range(seg['p_vaddr']&~4095,(seg['p_vaddr']+seg['p_memsz']+4095)&~4095,4096):
              if page not in pages:m.mem_map(page,4096);pages.add(page)
            m.mem_write(seg['p_vaddr'],seg.data())
          for page in (0x60000000,0x60002000):m.mem_map(page,4096)
          return m
        m=machine()
        expected_name=b'predelayT9' if state==8 else b'reverbnum'
        assert bytes(m.mem_read(nameptr,len(expected_name)+1))==expected_name+b'\0'
        def run(label,acquire):
          calls=[];writes=[]
          def code(_,pc,width,_arg):
            if pc not in boundaries:
              assert original['address']<=pc<original['address']+112
              return
            symbol=boundaries[pc];a,b,c=[m.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
            if 'guard_acquire' in symbol:
              assert a==guard;calls.append(dict(kind='acquire',guard=a,result=acquire));m.reg_write(UC_ARM_REG_R0,acquire)
            elif 'guard_release' in symbol:
              assert a==guard;calls.append(dict(kind='release',guard=a));m.mem_write(guard,struct.pack('<I',1))
            elif '__aeabi_atexit' in symbol:
              assert (a,b,c)==(receiver,dtor,dso);calls.append(dict(kind='atexit',receiver=a,destructor=b,dso=c))
            else:
              assert a==receiver
              assert struct.unpack('<II',m.mem_read(receiver,8))==(vptr,nameptr) and m.mem_read(receiver+8,1)[0]==state
              calls.append(dict(kind='add',receiver=a));
            m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
          def write(_,access,address,width,value,_arg):
            if receiver<=address<receiver+12:writes.append([address,width,value])
            else:assert 0x60000000<=address<0x60001000
          hooks=[m.hook_add(unicorn.UC_HOOK_CODE,code),m.hook_add(unicorn.UC_HOOK_MEM_WRITE,write)]
          m.reg_write(UC_ARM_REG_SP,0x60001000);m.reg_write(UC_ARM_REG_LR,0x60002000)
          m.emu_start(original['address'],0x60002000,count=100)
          assert m.reg_read(UC_ARM_REG_PC)==0x60002000 and m.reg_read(UC_ARM_REG_SP)==0x60001000
          for h in hooks:m.hook_del(h)
          expected=['acquire','release','atexit','add'] if label=='cold' else ['acquire','add'] if label=='acquire0' else ['add']
          assert [c['kind'] for c in calls]==expected
          assert writes==([[receiver+4,4,nameptr],[receiver+8,1,state],[receiver,4,vptr]] if label=='cold' else [])
          cases.append(dict(label=label,calls=calls,writes=writes,output=label+' '+','.join(expected)))
        m.mem_write(guard,b'\0'*8);m.mem_write(receiver,b'\0'*12)
        for label in ('cold','warm1','warm2'):run(label,1)
        m.mem_write(guard,b'\0'*8);run('acquire0',0)
        record=dict(original);record.update(elf_sha256=original['elf'],section=int(original['section_json']))
        targets.append(dict(task_id=task['id'],original=record,receiver=receiver,guard=guard,vptr=vptr,name=expected_name.decode(),state_byte=state,cases=cases))
    return dict(unicorn_version=unicorn.__version__,targets=targets)
