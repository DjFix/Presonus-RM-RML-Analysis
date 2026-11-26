"""Original ARM execution; Core bodies excluded, pinned host provider boundaries explicit."""
import ctypes
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct
import subprocess
import unicorn as u
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
PACKETS=Path('temp/recovery-work/sqlite-issued/packet-sol61-r3')
SUPPLEMENT=Path('temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/uc_descriptor_family_sol61/packet-sol61-r3/SUPPLEMENT-native-child-cleanup01/SUPPLEMENT.json')
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
LIBC=ctypes.CDLL(None)
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
OBJ,ATTR,VT,LOOK,STORE,STOP,STACK,DATA=0x20000000,0x21000000,0x21000100,0x22000000,0x22000004,0x23000000,0x24000000,0x25000000
PARSE=[None,'','bad','#','#xyz','#0','#ff','#7fffffffffffffff','#8000000000000000','#ffffffffffffffff','-2.75',' 3.5tail','1#ff','-0','1e20']
RANGES=[{}, {'min':'-2.5','max':'12.5','mid':'4','def':'7','steps':'5.9','units':'dB','curve':'linear','id':'gain'}, {'min':'#ff','max':'bad','mid':'#xyz','def':'bad','steps':'-3.9','units':'u'*100,'curve':'c'*100}, {'min':'-10','def':'#bad','steps':'bad'}, {'min':'1e20','max':'-1e20','mid':'0.001','steps':'0'}]
STRINGS=[None,'','a','hello world','x'*127,'y'*128,'z'*400]
LISTS=[[],['a'],['a','','long'*80]]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hx(s):return s.encode().hex() or '-'
def bits(x):return struct.unpack('<Q',struct.pack('<d',x))[0]
def task_contexts():return [json.loads(p.read_text()) for p in sorted(PACKETS.glob('*/CONTEXT.json'))]
def cls_of(name):return next(c for c in ('ParamRangeElement','StringListElement','StringElement','Element') if c in name)
def verify():
    assert sha(SUPPLEMENT)=='9836f89ff5565186ad5a906e93f1078bdca340b785d58c0979007a08042061fe'
    owned={x for d in task_contexts() for x in d['write_files']}
    reads={p:h for d in task_contexts() for p,h in d['task']['sources'].items()}
    for p,h in reads.items():
        if p not in owned:assert sha(p)==h,p

def observe(exe,task_id=None):
    verify();result=[];images={}
    def provider(cap,kind,value,initial=None):
        argv=[str(exe),'provider',str(cap),kind,hx(str(value))]
        if initial is not None:argv.append(hx(initial))
        text=subprocess.check_output(argv,text=True).strip()
        return b'' if text=='-' else bytes.fromhex(text)
    for context in task_contexts():
      if task_id and context['task']['id']!=task_id:continue
      for row in context['originals']:
        o=row['original'];path=ROOT/o['elf_path']
        if path not in images:images[path]=path.read_bytes()
        image=images[path];assert hashlib.sha256(image).hexdigest()==o['elf']
        elf=ELFFile(BytesIO(image));symtab=elf.get_section_by_name('.symtab');symbols={s.name:s for s in symtab.iter_symbols() if s['st_value']}
        sym=symbols[o['mangled']];sec=elf.get_section(sym['st_shndx']);offset=sec['sh_offset']+sym['st_value']-sec['sh_addr'];body=image[offset:offset+sym['st_size']]
        assert (offset,sym['st_value'],sym['st_size'],sym['st_shndx'])==(o['file_offset'],o['address'],o['size'],o['section'])
        assert body.hex()==o['range_hex'] and hashlib.sha256(body).hexdigest()==o['range_sha256']
        supp=json.loads(SUPPLEMENT.read_text());verified_dependencies=[]
        for record in supp['provider_items']:
            dep=record['original']
            if dep['elf']!=o['elf']:continue
            ds=symbols[dep['mangled']];section=elf.get_section(ds['st_shndx']);off=section['sh_offset']+ds['st_value']-section['sh_addr'];raw=image[off:off+ds['st_size']]
            assert off==dep['file_offset'] and raw.hex()==dep['range_hex'] and hashlib.sha256(raw).hexdigest()==dep['range_sha256'];verified_dependencies.append(dep)
        for dep_name in ('_ZN8Presonus2UC7ElementC2ERKNS0_11MetaElementE','_ZN8Presonus2UC13StringElementC1ERKNS0_11MetaElementE','_ZN8Presonus2UC13StringElementD0Ev'):
            ds=symbols[dep_name];section=elf.get_section(ds['st_shndx']);off=section['sh_offset']+ds['st_value']-section['sh_addr'];raw=image[off:off+ds['st_size']]
            verified_dependencies.append(dict(elf=o['elf'],mangled=dep_name,address=ds['st_value'],size=ds['st_size'],section=ds['st_shndx'],file_offset=off,range_sha256=hashlib.sha256(raw).hexdigest(),range_hex=raw.hex(),source='Hash-verified original ELF symbol and section mapping; supplemental lifecycle dependency, zero new credit'))
        for record in supp['native_vtable_data']:
            dep=record.get('original',record)
            if dep.get('elf')!=o['elf']:continue
            # Exact table bytes are also checked directly against native symbol.
            ds=symbols[dep['mangled']];section=elf.get_section(ds['st_shndx']);off=section['sh_offset']+ds['st_value']-section['sh_addr'];raw=image[off:off+ds['st_size']]
            assert hashlib.sha256(raw).hexdigest()==dep['range_sha256']
            if 'StringElement' in dep['mangled']:
                assert struct.unpack_from('<I',raw,12)[0]==symbols['_ZN8Presonus2UC13StringElementD0Ev']['st_value']
        plt=elf.get_section_by_name('.plt');rel=elf.get_section_by_name('.rel.plt');dyn=elf.get_section(rel['sh_link'])
        names={s['st_value']:s.name for s in symbols.values() if s.name.startswith('_ZN4Core')}
        for i,r in enumerate(rel.iter_relocations()):names[plt['sh_addr']+20+i*12]=dyn.get_symbol(r['r_info_sym']).name
        # Only the selected app boundary providers are intercepted. Native target,
        # nested parse, ParamRange and compiler numeric helper instructions execute.
        for name in ('_ZN8Presonus2UC7ElementC2ERKNS0_11MetaElementE','_ZN8Presonus2UC7ElementD2Ev','_ZN8Presonus2UC7Element4loadERKNS0_17ElementAttributesE','_ZNK8Presonus2UC7Element4saveERNS0_17ElementAttributesE'):
            names[symbols[name]['st_value']]=name
        cls=cls_of(o['mangled']);name=o['mangled'];cases=[]
        if 'parseValue' in name:inputs=[('parse',s) for s in PARSE]
        elif '4load' in name or '4save' in name:inputs=[('range',s) for s in RANGES] if cls=='ParamRangeElement' else [('string',s) for s in STRINGS]
        elif 'getString' in name or 'countStrings' in name:inputs=[('list',s) for s in LISTS]
        elif 'C1E' in name or 'C2E' in name:inputs=[('ctor',None)]
        else:inputs=[('dtor',n) for n in (0,1,3)]
        for mode,value in inputs:
            m=u.Uc(u.UC_ARCH_ARM,u.UC_MODE_ARM);pages=set()
            for seg in elf.iter_segments():
                if seg['p_type']!='PT_LOAD':continue
                for page in range(seg['p_vaddr']&~4095,(seg['p_vaddr']+seg['p_memsz']+4095)&~4095,4096):
                    if page not in pages:m.mem_map(page,4096);pages.add(page)
                m.mem_write(seg['p_vaddr'],seg.data())
            for address,size in ((OBJ,4096),(ATTR,4096),(LOOK,4096),(STOP,4096),(STACK,65536),(DATA,65536)):
                m.mem_map(address,size)
            for i in range(1,4):m.mem_map(OBJ+i*4096,4096)
            m.mem_map(0x26000000,4096)
            m.mem_write(OBJ,b'\xa5'*512);m.mem_write(ATTR,struct.pack('<I',VT));m.mem_write(VT,struct.pack('<II',LOOK,STORE))
            cursor=DATA;trace=[];calls=[];deleted=[];attrs={};active='';callback_trace=[];writes=[]
            def memory_write(_,access,address,width,value,arg):
                if OBJ<=address<OBJ+4*4096:writes.append(dict(address=address,width=width,value=value))
            m.hook_add(u.UC_HOOK_MEM_WRITE,memory_write)
            def alloc(data):
                nonlocal cursor
                p=cursor;cursor+=len(data)+8;m.mem_write(p,data+b'\0');return p
            def string(p):
                if not p:return b''
                b=bytearray()
                while True:
                    x=m.mem_read(p+len(b),1)[0]
                    if not x:return bytes(b)
                    b.append(x);assert len(b)<10000
            def wrstr(p,text):m.mem_write(p,text+b'\0')
            def ret(n=None):
                if n is not None:m.reg_write(UC_ARM_REG_R0,n&0xffffffff)
                m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
            def hook(_,pc,size,arg):
                nonlocal attrs
                a,b,c,d=[m.reg_read(r) for r in REGS]
                if pc==LOOK:
                    key=string(b).decode();trace.append('lookup:'+key);ret(alloc(attrs[key].encode()) if key in attrs else 0);return
                if pc==STORE:
                    key=string(b).decode();trace.append('store:'+key);attrs[key]=string(c).decode();ret();return
                n=names.get(pc)
                if not n:return
                if n.startswith('_ZN4Core'):
                    calls.append([n,a,b])
                    if 'VectorIPN8Presonus2UC7ElementEE6resizeEi' in n:
                        assert b==0
                        actual=subprocess.check_output([str(exe),'vector','0'],text=True).strip()
                        assert actual=='1 0 0';m.mem_write(a+4,b'\0'*12);ret(1);return
                    if 'VectorIPN8Presonus2UC7ElementEED1Ev' in n or 'VectorIPN8Presonus2UC7ElementEED2Ev' in n:
                        items,count,capacity=struct.unpack('<III',m.mem_read(a+4,12))
                        actual=subprocess.check_output([str(exe),'vector',str(count)],text=True).strip()
                        assert actual=='1 0 0'
                        if items:assert items==0x26000000;m.mem_unmap(items,4096)
                        m.mem_write(a+4,b'\0'*12);ret();return
                    import re
                    match=re.search(r'CStringBufferILi(\d+)EE',n)
                    if match and ('C1E' in n or 'C2E' in n or 'aSEPKc' in n):
                        new=provider(int(match[1]),'text',string(b).decode());calls.append(['pinned_string',int(match[1]),string(b).decode(),new.decode()]);wrstr(a,new);ret(a);return
                    if 'appendFormat' in n:
                        fmt=string(b)
                        data=struct.unpack('<Q',struct.pack('<II',c,d))[0] if fmt==b'%lf' else ctypes.c_int32(c).value
                        old=string(a).decode();new=provider(32,'double' if fmt==b'%lf' else 'int',data,old);calls.append(['pinned_append',old,new.decode()]);wrstr(a,new);ret(a);return
                    raise AssertionError(('unhandled Core boundary',n,hex(pc)))
                if n=='_ZN8Presonus2UC7ElementC2ERKNS0_11MetaElementE':
                    calls.append(['base_ctor',a,b]);return
                if n=='_ZN8Presonus2UC7ElementD2Ev':calls.append(['base_dtor',a]);return
                if n=='_ZN8Presonus2UC7Element4loadERKNS0_17ElementAttributesE':
                    trace.append('lookup:id');wrstr(a+4,provider(64,'text',attrs.get('id','')));ret(1);return
                if n=='_ZNK8Presonus2UC7Element4saveERNS0_17ElementAttributesE':
                    trace.append('store:id');attrs['id']=string(a+4).decode();ret(1);return
                if n.startswith('_ZdlPv'):
                    assert a in [OBJ+i*4096 for i in range(4)];deleted.append(a);m.mem_unmap(a,4096);ret();return
                if n.startswith('strchr'):
                    text=string(a);i=text.find(bytes([b&255]));ret(a+i if i>=0 else 0);return
                if n.startswith('strlen'):ret(len(string(a)));return
                if n.startswith('strncpy') or n.startswith('memcpy'):
                    text=bytes(m.mem_read(b,c));m.mem_write(a,text);ret(a);return
                if n.startswith('sscanf'):
                    fmt=string(b);text=string(a)
                    if fmt==b'%llx':
                        out=ctypes.c_ulonglong(struct.unpack('<Q',m.mem_read(c,8))[0]);count=LIBC.sscanf(text,fmt,ctypes.byref(out));m.mem_write(c,struct.pack('<Q',out.value))
                    else:
                        assert fmt==b'%lf';out=ctypes.c_double();count=LIBC.sscanf(text,fmt,ctypes.byref(out));m.mem_write(c,struct.pack('<d',out.value))
                    ret(count);return
                raise AssertionError(('unhandled PLT',n,hex(pc)))
            m.hook_add(u.UC_HOOK_CODE,hook)
            def run(address,*args):
                for r,v in zip(REGS,args):m.reg_write(r,v)
                m.reg_write(UC_ARM_REG_SP,STACK+65536-16);m.reg_write(UC_ARM_REG_LR,STOP)
                m.emu_start(address,STOP,count=20000);assert m.reg_read(UC_ARM_REG_PC)==STOP,(hex(m.reg_read(UC_ARM_REG_PC)),name)
                return m.reg_read(UC_ARM_REG_R0)
            def init():
                constructor='_ZN8Presonus2UC'+str(len(cls))+cls+'C1ERKNS0_11MetaElementE'
                run(symbols[constructor]['st_value'],OBJ,ATTR+0x300)
            def range_text():
                v=struct.unpack('<QQQQi',m.mem_read(OBJ+96,36));flags=struct.unpack('<I',m.mem_read(OBJ+260,4))[0]
                return ' '.join(map(str,(*v,flags)))+' '+(string(OBJ+132).hex() or '-')+' '+(string(OBJ+196).hex() or '-')
            def tr():return ''.join(x+',' for x in trace)
            if mode=='parse':
                m.mem_write(DATA+60000,struct.pack('<d',123.5));out=run(o['address'],OBJ,DATA+60000,0 if value is None else alloc(value.encode()));output=f'{out} {struct.unpack("<Q",m.mem_read(DATA+60000,8))[0]}'
            elif mode in ('ctor','dtor'):
                if mode=='ctor':run(o['address'],OBJ,ATTR+0x300);output=range_text() if cls=='ParamRangeElement' else (string(OBJ+96).hex() or '-') if cls=='StringElement' else str(struct.unpack('<I',m.mem_read(OBJ+84,4))[0])
                else:
                    init()
                    children=[]
                    for i in range(value):
                        child=OBJ+(i+1)*4096;children.append(child)
                        child_ctor=symbols['_ZN8Presonus2UC13StringElementC1ERKNS0_11MetaElementE']['st_value']
                        run(child_ctor,child,ATTR+0x300)
                    if children:
                        m.mem_write(0x26000000,b''.join(struct.pack('<I',p) for p in children));m.mem_write(OBJ+80,struct.pack('<III',0x26000000,len(children),5))
                    calls.clear();run(o['address'],OBJ);base=[x for x in calls if x[0]=='base_dtor']
                    assert [x[1] for x in base]==[OBJ,*children]
                    assert deleted==children+([OBJ] if 'D0E' in name else [])
                    output=f'{len(base)} {len(deleted)}'
            elif mode=='range':
                init();attrs=dict(value);trace.clear();run(symbols['_ZN8Presonus2UC17ParamRangeElement4loadERKNS0_17ElementAttributesE']['st_value'],OBJ,ATTR);output=range_text()+' | '+tr();trace.clear();run(symbols['_ZNK8Presonus2UC17ParamRangeElement4saveERNS0_17ElementAttributesE']['st_value'],OBJ,ATTR);output+=' | '+tr()+' | '+''.join(k+'='+hx(attrs[k])+',' for k in ('min','max','mid','def','steps','units','curve','id'))
            elif mode=='string':
                init();attrs={'id':'item'};attrs.update({} if value is None else {'text':value});trace.clear();run(symbols['_ZN8Presonus2UC13StringElement4loadERKNS0_17ElementAttributesE']['st_value'],OBJ,ATTR);output=(string(OBJ+96).hex() or '-')+' | '+tr();trace.clear();run(symbols['_ZNK8Presonus2UC13StringElement4saveERNS0_17ElementAttributesE']['st_value'],OBJ,ATTR);output+=' | '+tr()+' | '+hx(attrs['text'])+' '+hx(attrs['id'])
            else:
                init();children=[]
                for text in value:
                    p=alloc(b'\0'*96+provider(128,'text',text));children.append(p)
                vector=alloc(b''.join(struct.pack('<I',p) for p in children));m.mem_write(OBJ+80,struct.pack('<II',vector,len(children)))
                count=run(symbols['_ZNK8Presonus2UC17StringListElement12countStringsEv']['st_value'],OBJ);output=str(count)
                for i in range(count):
                    p=run(symbols['_ZNK8Presonus2UC17StringListElement9getStringEi']['st_value'],OBJ,i);assert p==children[i]+96;output+=' '+(string(p).hex() or '-')
                # Observe excluded invalid pointer tokens, never dereference them.
                invalid=[]
                if 'getString' in name:
                    for i in (-1,count,count+10):invalid.append([i,run(o['address'],OBJ,i&0xffffffff)])
                    tokens=[]
                    m.mem_write(OBJ+80,struct.pack('<II',vector,1))
                    for token in (0,0xffffffa0,OBJ):
                        m.mem_write(vector,struct.pack('<I',token))
                        tokens.append(dict(kind='stored_child',input=token,result=run(o['address'],OBJ,0)))
                    error_address=struct.unpack('<I',body[-4:])[0]
                    for token in (0,0xffffffa0,0x12340000):
                        m.mem_write(error_address,struct.pack('<I',token))
                        tokens.append(dict(kind='static_error',input=token,result=run(o['address'],OBJ,0xffffffff)))
                    callback_trace.append(dict(invalid_native_tokens=invalid,excluded_pointer_tokens=tokens,domain='excluded from typed pointer equivalence; numeric observation only, never dereferenced'))
            argv=[mode]
            if mode=='parse':argv+=[] if value is None else [hx(value)]
            elif mode=='range':
                for k,v in value.items():argv.extend([k,hx(v)])
            elif mode=='string':argv+=[] if value is None else [hx(value)]
            elif mode=='list':argv += [hx(v) for v in value]
            elif mode=='ctor':argv+=[cls]
            elif mode=='dtor':argv+=[cls,'D0' if 'D0E' in name else 'D1',str(value)]
            cases.append(dict(argv=argv,output=output,provider_calls=calls,native_receiver_writes=writes,deallocated=deleted,exclusions=callback_trace))
        result.append(dict(task_id=context['task']['id'],original=o,range_verified=True,supplement_sha256=sha(SUPPLEMENT),verified_application_dependencies=verified_dependencies,cases=cases))
    return dict(targets=result,oracle='Exact original ARM instructions; explicit real pinned CCL host provider bridge; original numeric helpers; libc scan boundary; original native Element constructors/destructors and child D0 dispatch executed; Element attribute boundaries modeled; host actual providers exercised separately.')
