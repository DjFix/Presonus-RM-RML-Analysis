"""Original ARM removal observations; no expected values from port or pseudocode."""
import hashlib, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MEM_READ
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
ROOT=Path(__file__).resolve().parents[5]
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
MANGLED='_ZN8Presonus5Mixer18MixerComponentBase14removeDelegateERNS1_8DelegateE'
def generate():
    assert hashlib.sha256(ELF.read_bytes()).hexdigest()==SHA
    with ELF.open('rb') as f:
        elf=ELFFile(f); sym=next(s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name==MANGLED)
        sec=elf.get_section(sym['st_shndx']); off=sec['sh_offset']+sym['st_value']-sec['sh_addr']
        f.seek(off); body=f.read(sym['st_size'])
        assert off==0x2731c and len(body)==204
        assert hashlib.sha256(body).hexdigest()=='c128e6fe473dea83c59394927cb6b7f2c10b51655bb8913c9390221b3b029bb5'
        error=next(s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name=='_ZN4Core11ConstVectorIPN8Presonus5Mixer18MixerComponentBase8DelegateEE5errorE')
        assert error['st_value']==4799576 and elf.get_section(error['st_shndx'])['sh_type']=='SHT_NOBITS'
    cases=[]
    for items in [[],[0],[0,1],[0,1,2],[0,1,0,2],[3,2,1,0]]:
      for target in range(5):
       for sentinel in [-1,6]:
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM); u.mem_map(0x20000,0x10000); u.mem_write(0x2f31c,body)
        u.mem_map(0x490000,0x10000); u.mem_map(0x600000,0x10000); u.mem_map(0x700000,0x10000)
        obj=0x600000; arr=0x601000; stop=0x20f00
        word=lambda x: struct.pack('<I',x)
        ptr=lambda i: 0 if i==-1 else 0x602000+i*16
        u.mem_write(obj+0x370,word(arr)+word(len(items)))
        u.mem_write(arr,b''.join(word(ptr(i)) for i in items) or word(0))
        u.mem_write(4799576,word(ptr(sentinel)))
        accesses=[]
        def record(emu,kind,address,size,value,_):
            if address==4799576 or obj<=address<obj+0x400 or arr<=address<arr+4*len(items):
                accesses.append({'kind':kind,'address':address,'size':size,'value':int.from_bytes(emu.mem_read(address,size),'little') if kind==UC_MEM_READ else value})
        u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,record)
        for reg,val in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,ptr(target)),(UC_ARM_REG_SP,0x708000),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,val)
        u.emu_start(0x2f31c,stop,count=10000)
        assert u.reg_read(UC_ARM_REG_PC)==stop
        result_count=struct.unpack('<I',u.mem_read(obj+0x374,4))[0]
        backing=[struct.unpack('<I',u.mem_read(arr+i*4,4))[0] for i in range(len(items))]
        decode=lambda p: -1 if p==0 else (p-0x602000)//16
        cases.append({'items':items,'target':target,'sentinel':sentinel,'count':result_count,'backing':[decode(p) for p in backing],'accesses':accesses})
    return {'elf_sha256':SHA,'mangled':MANGLED,'address':0x2f31c,'size':204,'section':'.text','file_offset':off,'body_sha256':hashlib.sha256(body).hexdigest(),'oracle':'Unicorn original ARM instructions; mapped controlled state; no external stubs','error_data':{'address':4799576,'storage':'SHT_NOBITS','initial':0,'perturbed_nonnull':6,'scope':'explicit initialized/perturbed memory, no startup execution'},'cases':cases}

def generate_solo():
    """Execute original target plus its original soft-float comparison helpers."""
    from unicorn import UC_HOOK_CODE
    with ELF.open('rb') as f:
        elf=ELFFile(f)
        segments=[(seg['p_vaddr'],seg.data()) for seg in elf.iter_segments() if seg['p_type']=='PT_LOAD']
        symbol=next(s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name=='_ZN8Presonus5Mixer15OutputComponent10soloUpdateERNS_3Dsp18MultiParamPropertyE')
        sec=elf.get_section(symbol['st_shndx']);offset=sec['sh_offset']+symbol['st_value']-sec['sh_addr']
        f.seek(offset);body=f.read(symbol['st_size'])
        assert hashlib.sha256(body).hexdigest()=='4e4b0ba3980e4caa2e8ae3eae7cdc6d36120c368f72d6a9aa6e003e3262d99bd'
    pairs=[([0,0],[0,0]),([0x3f800000,0x40000000],[0,0]),([0x3f800000,0x40000000],[0x3f800000,0]),([0x80000000,0],[0,0x80000000]),([0x7fc01234,0x3f800000],[0x7fc01234,0x3f800000]),([0x7f800000,0xff800000],[0x7f800000,0xff800000]),([1,0x80000001],[0,0]),([0xff800000,0x7f800000],[0,0]),([0x3f800000,0x7fc01234],[0,0x7fc01234])]
    cases=[]
    for coefficients,cached in pairs:
      for count in [0,1,58,59,60,61]:
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x500000)
        for address,data in segments:u.mem_write(address,data)
        u.mem_map(0x600000,0x10000);u.mem_map(0x700000,0x10000)
        obj=0x600000;prop=0x601000;stop=0x20f00;word=lambda x:struct.pack('<I',x&0xffffffff)
        u.mem_write(obj+0x15c,b''.join(word(x) for x in coefficients));u.mem_write(obj+0x1c8,b''.join(word(x) for x in cached))
        for i in range(60):u.mem_write(prop+12+i*8,word(-7)+word(0x12345678))
        u.mem_write(prop+0x1ec,word(count))
        calls=[];writes=[];executed=set()
        def code(emu,address,size,_):
            assert 0x45e4c<=address<0x45f3c or 0x157858<=address<0x1578b8 or 0x1578c8<=address<0x1578f8,hex(address)
            executed.add(address)
            if address==0x1578e0:calls.append([emu.reg_read(UC_ARM_REG_R0),emu.reg_read(UC_ARM_REG_R1)])
        def write(emu,kind,address,size,value,_):
            if obj<=address<obj+0x200 or prop<=address<prop+0x200:writes.append([address,size,value])
        u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
        for reg,val in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,prop),(UC_ARM_REG_SP,0x708000),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,val)
        u.emu_start(0x45e4c,stop,count=10000);assert u.reg_read(UC_ARM_REG_PC)==stop
        read=lambda addr:struct.unpack('<I',u.mem_read(addr,4))[0]
        entries=[[struct.unpack('<i',u.mem_read(prop+12+i*8,4))[0],read(prop+16+i*8)] for i in range(60)]
        cases.append({'coefficients':coefficients,'cached_before':cached,'count_before':count,'count':read(prop+0x1ec),'cached':[read(obj+0x1c8),read(obj+0x1cc)],'entries':entries,'float_calls':calls,'writes':writes,'executed_addresses':sorted(executed)})
    return cases

_original_generate=generate
def generate():
    result=_original_generate()
    result['solo_cases']=generate_solo()
    return result

def generate_pair():
    with ELF.open('rb') as f:
        elf=ELFFile(f);symbol=next(s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name=='_ZNK8Presonus5Mixer18MixerComponentBase22getLinkableChannelPairEPNS0_16ChannelComponentE')
        sec=elf.get_section(symbol['st_shndx']);offset=sec['sh_offset']+symbol['st_value']-sec['sh_addr'];f.seek(offset);body=f.read(symbol['st_size'])
        assert hashlib.sha256(body).hexdigest()=='cbe87fd086568dbd1499dd694b056f3ac276e96215d7b0b0f06008aa229f6e63'
        error=next(s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name=='_ZN4Core11ConstVectorIPN8Presonus5Mixer16ChannelComponentEE5errorE')
        assert error['st_value']==4798344 and elf.get_section(error['st_shndx'])['sh_type']=='SHT_NOBITS'
    cases=[]
    for inputs,mixes in [(0,0),(0,4),(4,0),(1,4),(4,1)]:
     for type_ in [0,4,1,-1]:
      for index in [-2,-1,0,1,3,4,-2147483648,2147483647]:
       for sentinel in [-1,6]:
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x20000,0x10000);u.mem_write(0x2f610,body);u.mem_map(0x490000,0x10000);u.mem_map(0x600000,0x10000);u.mem_map(0x700000,0x10000)
        obj=0x600000;channel=0x600800;arr0=0x601000;arr4=0x602000;stop=0x20f00;word=lambda x:struct.pack('<I',x&0xffffffff);ptr=lambda i:0 if i==-1 else 0x604000+i*16
        u.mem_write(obj+0x134,word(arr0)+word(inputs));u.mem_write(obj+0x170,word(arr4)+word(mixes));u.mem_write(channel+0x16c,word(type_)+word(index));u.mem_write(4798344,word(ptr(sentinel)))
        for i in range(inputs):u.mem_write(arr0+4*i,word(ptr(i)))
        for i in range(mixes):u.mem_write(arr4+4*i,word(ptr(i+4)))
        accesses=[]
        def observe(emu,kind,address,size,value,_):
            if address==4798344 or obj<=address<obj+0x200 or channel<=address<channel+0x200 or arr0<=address<arr0+16 or arr4<=address<arr4+16:
                accesses.append({'kind':kind,'address':address,'size':size,'value':int.from_bytes(emu.mem_read(address,size),'little') if kind==UC_MEM_READ else value})
        u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,observe)
        for reg,val in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,channel),(UC_ARM_REG_SP,0x708000),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,val)
        u.emu_start(0x2f610,stop,count=10000);assert u.reg_read(UC_ARM_REG_PC)==stop
        value=u.reg_read(UC_ARM_REG_R0);result=-1 if value==0 else (value-0x604000)//16
        cases.append({'inputs':inputs,'mixes':mixes,'type':type_,'index':index,'sentinel':sentinel,'result':result,'accesses':accesses})
    return cases

_generate_without_pair=generate
def generate():
    result=_generate_without_pair()
    result['pair_cases']=generate_pair()
    return result

def verify_helpers():
    manifest_path=ROOT/'temp/recovery-work/ranked-trial-09-small01/supplements/float-helper-closure/MANIFEST.json'
    manifest=json.loads(manifest_path.read_text())
    results=[]
    with ELF.open('rb') as stream:
        elf=ELFFile(stream)
        syms={s.name:s for s in elf.get_section_by_name('.symtab').iter_symbols()}
        for record in manifest['functions']:
            original=record['original'];symbol=syms[original['mangled']]
            section=elf.get_section(symbol['st_shndx'])
            offset=section['sh_offset']+symbol['st_value']-section['sh_addr']
            assert symbol['st_value']==original['address'] and symbol['st_size']==original['size']
            stream.seek(offset);body=stream.read(symbol['st_size'])
            digest=hashlib.sha256(body).hexdigest()
            assert digest==record['fresh_range_sha256']
            assert body==(ROOT/record['range_copy']).read_bytes()
            results.append({'mangled':original['mangled'],'address':symbol['st_value'],'size':symbol['st_size'],'section':section.name,'file_offset':offset,'body_sha256':digest})
    return results

_generate_without_helpers=generate
def generate():
    ranges=verify_helpers()
    result=_generate_without_helpers()
    result['compiler_helper_ranges']=ranges
    return result

if __name__=='__main__':
    import sys
    Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
