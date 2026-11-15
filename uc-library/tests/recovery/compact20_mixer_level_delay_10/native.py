"""Independent execution of exact original application bytes; no C++ expected values."""
import argparse, hashlib, json, platform, random, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
TASK_INDEX = 10
ELF_SHA = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
IDENTITIES = {10: ('_ZN8Presonus5Mixer14DelayComponent6mapIDsEi',240388,152),11:('_ZN8Presonus5Mixer14DelayComponent16getSelectTypeMapEv',240540,24),12:('_ZN8Presonus5Mixer14DelayComponent21getEffectTypeInternalENS_10EffectTypeE',248232,20)}
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate(elf_path):
    elf_path = Path(elf_path)
    assert digest(elf_path) == ELF_SHA, 'Wrong ELF input'
    mangled, address, size = IDENTITIES[TASK_INDEX]
    with elf_path.open('rb') as stream:
        elf = ELFFile(stream)
        def region(a,n):
            section = next(s for s in elf.iter_sections() if s['sh_type'] != 'SHT_NOBITS' and int(s['sh_addr']) <= a and a+n <= int(s['sh_addr'])+int(s['sh_size']))
            offset = int(section['sh_offset'])+a-int(section['sh_addr'])
            stream.seek(offset)
            data = stream.read(n)
            assert len(data) == n
            return data, {'address':a,'size':n,'section':section.name,'section_index':next(k for k,s in enumerate(elf.iter_sections()) if s.name==section.name),'file_offset':offset,'sha256':hashlib.sha256(data).hexdigest()}
        code, original_range = region(address,size)
        rng=random.Random(0xD31A+TASK_INDEX)
        inputs=sorted(set([x & 0xffffffff for x in range(-32,65)]+[0x80000000,0x7fffffff,0x7ffffff6,0x7ffffff7,0xfffffff7]+[rng.getrandbits(32) for _ in range(256)])) if TASK_INDEX != 11 else [0]
        cases=[]
        for x in inputs:
            machine=Uc(UC_ARCH_ARM,UC_MODE_ARM)
            machine.mem_map(address&~4095,4096)
            machine.mem_write(address,code)
            machine.mem_map(0x70000000,65536)
            machine.reg_write(UC_ARM_REG_SP,0x70008000)
            machine.reg_write(UC_ARM_REG_LR,0x60000000)
            machine.reg_write(UC_ARM_REG_R0,0x12340000) # deliberately unmapped: methods must not dereference this
            machine.reg_write(UC_ARM_REG_R1,x)
            external_writes=[]
            def write_hook(uc,access,a,n,v,user):
                if not 0x70000000 <= a < a+n <= 0x70010000: external_writes.append([a,n,v])
            machine.hook_add(UC_HOOK_MEM_WRITE,write_hook)
            machine.emu_start(address,0x60000000,count=200)
            assert machine.reg_read(UC_ARM_REG_PC)==0x60000000
            assert not external_writes
            cases.append({'input_r1_u32':x,'output_r0_u32':machine.reg_read(UC_ARM_REG_R0),'nonstack_writes':external_writes})
        result={'version':1,'original_elf_sha256':ELF_SHA,'mangled':mangled,'firmware':'RM/RML mixer 13731','role':'server','original_range':original_range,'cases':cases,'oracle':{'engine':'Unicorn ARM32','unicorn_version':unicorn.__version__,'python_version':platform.python_version(),'producer_sha256':digest(__file__),'instruction_limit':200,'stubs':[],'memory_assumptions':'Exact target bytes, mapped local stack, unmapped receiver0x12340000; no providers/Core/native syscalls/hardware executed.'}}
        if TASK_INDEX==11:
            table_address=cases[0]['output_r0_u32']
            data,table_range=region(table_address,420)
            rows=[];strings={}
            for k in range(21):
                family,index,effect,value,text_address=struct.unpack_from('<iiIII',data,k*20)
                text=bytearray()
                while True:
                    byte,_=region(text_address+len(text),1)
                    if byte==b'\0':break
                    text.extend(byte)
                    assert len(text)<256
                _,string_range=region(text_address,len(text)+1)
                strings[str(text_address)]=string_range
                rows.append({'family':family,'index':index,'effect_type_bits':effect,'value_bits':value,'name':text.decode('utf8'),'original_string_address':text_address})
            result.update(table_range=table_range,rows=rows,string_ranges=strings)
        return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--out');p.add_argument('--verify');a=p.parse_args()
    value=generate(a.elf)
    if a.verify:
        assert value==json.loads(Path(a.verify).read_text()),'Native fixture differs from freshly executed original'
        print('Fresh original fixture verified:',len(value['cases']),'cases')
    elif a.out:
        path=Path(a.out);assert not path.exists(),'Refuse fixture overwrite';path.write_text(json.dumps(value,indent=2)+'\n')
    else: print(json.dumps(value))
