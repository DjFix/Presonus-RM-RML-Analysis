"""Exact ELF instruction oracle for the three assigned PreDelay child classes."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct
import unicorn
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
from elftools.elf.elffile import ELFFile
PACKET=Path('temp/recovery-work/predelay-children-sol61/CONTEXT.json')
CONTEXT=json.loads(PACKET.read_text())
def sha(data):return hashlib.sha256(data).hexdigest()
def verify_inputs():
    assert sha(PACKET.read_bytes())=='d1d3fbc6b84fe9116a8de2193453e38c368ce967438d11416239e27c751c2a27'
    for path,digest in CONTEXT['canonical_current_reads'].items():assert sha(Path(path).read_bytes())==digest,path
    for name in ('native_context','protected_old_inputs'):
        row=CONTEXT[name];assert sha(Path(row['path']).read_bytes())==row['sha256']
    for path,digest in json.loads(Path(CONTEXT['protected_old_inputs']['path']).read_text()).items():assert sha(Path(path).read_bytes())==digest,path

def observe(task_id=None):
    verify_inputs();targets=[];images={}
    for task in CONTEXT['tasks']:
      if task_id is not None and task['id'] != task_id: continue
      for item in task['originals']:
        original=dict(item['original']);path=Path('/home/rs/projects/opencs/ai-line-analysis')/original['elf_path']
        if path not in images:images[path]=path.read_bytes()
        image=images[path];assert sha(image)==original['elf']
        elf=ELFFile(BytesIO(image));syms=elf.get_section_by_name('.symtab')
        def capture(name):
            symbol,=syms.get_symbol_by_name(name);sec=elf.get_section(symbol['st_shndx']);off=sec['sh_offset']+symbol['st_value']-sec['sh_addr'];return symbol,image[off:off+symbol['st_size']],off
        symbol,body,offset=capture(original['mangled'])
        assert offset==original['file_offset'] and sha(body)==original['range_sha256'] and body.hex()==original['range_hex']
        assert symbol['st_value']==original['address'] and symbol['st_size']==original['size'] and symbol['st_shndx']==original['section']
        cls=next(c for c in CONTEXT['classes'] if c in original['mangled']);n=int(cls[-1])
        rtti,rtti_bytes,_=capture('_ZTIN8Presonus5Mixer19'+cls+'E');parent,_,_=capture('_ZTIN8Presonus5Mixer17PreDelayFormatterE')
        assert struct.unpack_from('<I',rtti_bytes,8)[0]==parent['st_value']
        recorded=next(x for x in json.loads(Path(CONTEXT['native_context']['path']).read_text())['actual_parents'] if x['elf']==original['elf'] and x['class']==cls)
        assert sha(rtti_bytes)==recorded['range_sha256']
        vtable,_,_=capture('_ZTVN8Presonus5Mixer19'+cls+'E');core,_,_=capture('_ZTVN4Core9FormatterE')
        plt=elf.get_section_by_name('.plt');rel=elf.get_section_by_name('.rel.plt');dyn=elf.get_section(rel['sh_link'])
        plt_names={plt['sh_addr']+20+i*12:dyn.get_symbol(r['r_info_sym']).name for i,r in enumerate(rel.iter_relocations())}
        def branch(offset):
            instruction=struct.unpack_from('<I',body,offset)[0];assert instruction>>24 in (0xea,0xeb)
            immediate=instruction&0xffffff
            if immediate&0x800000:immediate-=1<<24
            return original['address']+offset+8+immediate*4
        def machine(receiver=0x20000000):
            m=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM);pages=set()
            for segment in elf.iter_segments():
                if segment['p_type']!='PT_LOAD':continue
                for page in range(segment['p_vaddr']&~4095,(segment['p_vaddr']+segment['p_memsz']+4095)&~4095,4096):
                    if page not in pages:m.mem_map(page,4096);pages.add(page)
                m.mem_write(segment['p_vaddr'],segment.data())
            for page in (receiver&~4095,0x60000000,0x60002000):
                if page not in pages:m.mem_map(page,4096);pages.add(page)
            return m
        cases=[];initializer='addClass' in original['mangled']
        if initializer:
            guard,receiver,nameptr,vptr,dtor,dso=struct.unpack('<IIIIII',body[-24:]);assert vptr==vtable['st_value']+8
            destructor,_,_=capture('_ZN8Presonus5Mixer19'+cls+'D1Ev');assert dtor==destructor['st_value']
            instruction=struct.unpack_from('<I',body,76)[0];assert instruction&0xffffff00==0xe3a02000;state=instruction&255;assert state==n-1
            registry,_,_=capture('_ZN4Core17FormatterRegistry3addEPNS_9FormatterE');assert branch(36)==registry['st_value']
            boundaries={branch(36):'add',branch(44):'acquire',branch(88):'release',branch(104):'atexit'}
            for address,name in ((branch(44),'__cxa_guard_acquire'),(branch(88),'__cxa_guard_release'),(branch(104),'__aeabi_atexit')):assert plt_names[address]==name
            m=machine();name=f'predelayT{n}';assert bytes(m.mem_read(nameptr,len(name)+1))==name.encode()+b'\0'
            def run(label,acquire):
                calls=[];writes=[]
                def code(_,pc,width,_arg):
                    if pc not in boundaries:assert original['address']<=pc<original['address']+112;return
                    kind=boundaries[pc];a,b,c=[m.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
                    if kind=='acquire':assert a==guard;calls.append(dict(kind=kind,guard=a,result=acquire));m.reg_write(UC_ARM_REG_R0,acquire)
                    elif kind=='release':assert a==guard;calls.append(dict(kind=kind,guard=a));m.mem_write(guard,struct.pack('<I',1))
                    elif kind=='atexit':assert (a,b,c)==(receiver,dtor,dso);calls.append(dict(kind=kind,receiver=a,destructor=b,dso=c))
                    else:
                        assert a==receiver and struct.unpack('<II',m.mem_read(receiver,8))==(vptr,nameptr) and m.mem_read(receiver+8,1)[0]==state
                        calls.append(dict(kind=kind,receiver=a))
                    m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
                def write(_,access,address,width,value,_arg):
                    if receiver<=address<receiver+12:writes.append([address,width,value])
                    else:assert 0x60000000<=address<0x60001000
                hooks=[m.hook_add(unicorn.UC_HOOK_CODE,code),m.hook_add(unicorn.UC_HOOK_MEM_WRITE,write)]
                m.reg_write(UC_ARM_REG_SP,0x60001000);m.reg_write(UC_ARM_REG_LR,0x60002000);m.emu_start(original['address'],0x60002000,count=100)
                assert m.reg_read(UC_ARM_REG_PC)==0x60002000 and m.reg_read(UC_ARM_REG_SP)==0x60001000
                for h in hooks:m.hook_del(h)
                expected=['acquire','release','atexit','add'] if label=='cold' else ['acquire','add'] if label=='acquire0' else ['add']
                assert [c['kind'] for c in calls]==expected
                assert writes==([[receiver+4,4,nameptr],[receiver+8,1,state],[receiver,4,vptr]] if label=='cold' else [])
                cases.append(dict(label=label,calls=calls,writes=writes,output=label+' '+','.join(expected)))
            m.mem_write(guard,b'\0'*8);m.mem_write(receiver,b'\0'*12)
            for label in ('cold','warm1','warm2'):run(label,1)
            m.mem_write(guard,b'\0'*8);run('acquire0',0)
        else:
            deleting=original['mangled'].endswith('D0Ev');point=core['st_value']+8;assert struct.unpack('<I',body[-4:])[0]==point
            endpoint=branch(28) if deleting else None
            if deleting:assert plt_names[endpoint]=='_ZdlPv'
            for index in range(3):
                receiver=0x20000000+index*8192;m=machine(receiver);name_word=0x12340000+index*16
                m.mem_write(receiver,struct.pack('<III',vtable['st_value']+8,name_word,0xa5a50000+n-1));writes=[];calls=[]
                def code(_,pc,width,_arg):
                    if pc==endpoint:
                        pointer=m.reg_read(UC_ARM_REG_R0);assert pointer==receiver and struct.unpack('<III',m.mem_read(pointer,12))==(point,name_word,0xa5a50000+n-1)
                        calls.append(dict(kind='unsized_delete',receiver=pointer));m.mem_unmap(pointer,4096);m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
                    else:assert original['address']<=pc<original['address']+original['size']-4
                def write(_,access,address,width,value,_arg):
                    if receiver<=address<receiver+12:writes.append([address,width,value])
                    else:assert 0x60000000<=address<0x60001000
                m.hook_add(unicorn.UC_HOOK_CODE,code);m.hook_add(unicorn.UC_HOOK_MEM_WRITE,write)
                m.reg_write(UC_ARM_REG_R0,receiver);m.reg_write(UC_ARM_REG_SP,0x60001000);m.reg_write(UC_ARM_REG_LR,0x60002000);m.emu_start(original['address'],0x60002000,count=100)
                assert m.reg_read(UC_ARM_REG_PC)==0x60002000 and m.reg_read(UC_ARM_REG_SP)==0x60001000 and m.reg_read(UC_ARM_REG_R0)==receiver
                assert writes==[[receiver,4,point]] and len(calls)==int(deleting)
                if not deleting:assert struct.unpack('<III',m.mem_read(receiver,12))==(point,name_word,0xa5a50000+n-1)
                cases.append(dict(receiver=receiver,initial_name_word=name_word,writes=writes,calls=calls,allocation_released=bool(deleting),output=f'{int(deleting)} 1 1'))
        original['elf_sha256']=original['elf']
        targets.append(dict(task_id=task['id'],original=original,cls=cls,initializer=initializer,cases=cases,rtti_range_sha256=sha(rtti_bytes),rtti_parent=recorded['parent']))
    return dict(unicorn_version=unicorn.__version__,targets=targets)
