"""Execute exact original application constructors; pinned CCL string boundaries.
Core firmware and target libc are never executed. Native strings are initialized
by a model of the pinned CStringBuffer(nullptr) source: write one zero byte.
"""
import argparse, hashlib, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'uc-library/tools/recovery/accept_worker.py').is_file())
PACKETS=ROOT/'temp/recovery-work/large02-network-owning03/batch02/packets'
OBJ=0x1001000;SP=0x1009000;STOP=0x100f000

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def observe():
 ranges=[];cases=[];bindings=[];mapping_ranges=[]
 for index in [1,2]:
  packet=PACKETS/f'large02_net_adapter01_0{index}'
  context=packet/'native-context.json';d=json.loads(context.read_text());req=json.loads((packet/'request.json').read_text())
  bindings.append(dict(path=str(context.relative_to(ROOT)),sha256=sha(context)))
  for key in d['roots']:
   body=d['bodies'][key];node=d['nodes'][key];elfsha=node['elf'];original=next(o['original'] for o in req['originals'] if o['original']['elf']==elfsha)
   path=ROOT/('rootfs/CS18_v13840/home/root/surface' if original['role']=='client' else 'rootfs/RML16AI_Rack_13731/home/root/mixer')
   assert sha(path)==elfsha
   raw=path.read_bytes()
   with path.open('rb') as f:
    e=ELFFile(f);sec=e.get_section(body['section_index']);offset=sec['sh_offset']+body['address']-sec['sh_addr'];assert offset==body['file_offset'];assert sec.name==body['section']
    symbols={s.name:s for s in e.get_section_by_name('.symtab').iter_symbols()}
    symbol=symbols[original['mangled']];assert symbol['st_value']==body['address'] and symbol['st_size']==body['size']
    assert hashlib.sha256(raw[offset:offset+body['size']]).hexdigest()==body['bytes_sha256']
    segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
    providers={symbols[f'_ZN4Core13CStringBufferILi{n}EEC1EPKc']['st_value']:n for n in [32,256]}
    process=symbols['_ZN8Presonus2UC14AdapterHandler7processEv'];psec=e.get_section(process['st_shndx']);poff=psec['sh_offset']+process['st_value']-psec['sh_addr']
    process_range=dict(elf_sha256=elfsha,mangled=process.name,address=process['st_value'],size=process['st_size'],section=psec.name,file_offset=poff,bytes_sha256=hashlib.sha256(raw[poff:poff+process['st_size']]).hexdigest())
    assert process_range['size']==60
    if process_range not in mapping_ranges:mapping_ranges.append(process_range)
   record=dict(elf_sha256=elfsha,elf_path=str(path.relative_to(ROOT)),firmware=original['firmware'],role=original['role'],mangled=original['mangled'],demangled=original['demangled'],address=body['address'],size=body['size'],section=body['section'],section_index=body['section_index'],file_offset=offset,bytes_sha256=body['bytes_sha256'])
   ranges.append(record)
   for fill in [0,0x5a,0xa5,0xff]:
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    pages=set()
    for address,n,data in segments:
     for page in range(address&~4095,(address+n+4095)&~4095,4096):
      if page not in pages:u.mem_map(page,4096);pages.add(page)
     u.mem_write(address,data)
    u.mem_map(0x1000000,0x10000);u.mem_write(OBJ,bytes([fill])*0x2ac)
    calls=[];writes=[]
    def ret(value):u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def code(uc,a,n,user):
     if a==STOP:uc.emu_stop();return
     if a in providers:
      dest=uc.reg_read(UC_ARM_REG_R0);src=uc.reg_read(UC_ARM_REG_R1);assert src==0
      calls.append(dict(provider=f'CCL_CStringBuffer_{providers[a]}_nullptr',receiver_offset=dest-OBJ,argument=src))
      uc.mem_write(dest,b'\0');ret(dest);return
     assert body['address']<=a<body['address']+body['size'] or process_range['address']<=a<process_range['address']+process_range['size'],f'unbound app execution {a:x}'
    def write(uc,access,a,n,v,user):
     if OBJ<=a<OBJ+0x2ac:writes.append([a-OBJ,n,v])
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
    u.reg_write(UC_ARM_REG_SP,SP);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,OBJ)
    u.emu_start(body['address'],STOP,count=10000);assert u.reg_read(UC_ARM_REG_PC)==STOP
    data=bytes(u.mem_read(OBJ,0x2ac));read=lambda off:struct.unpack_from('<I',data,off)[0]
    assert u.reg_read(UC_ARM_REG_R0)==OBJ
    expected=dict(suffix_empty=int(data[0]==0),primary_empty=int(data[0x30]==0),multi=data[0x20],suspended=data[0x21],valid=data[0x2a4],changed=data[0x130],interval=read(0x28),counter=read(0x2a8),count=read(0x138),addresses=data[0x13c:0x2a4].hex())
    cases.append(dict(original=record,fill=fill,argv=['C2' if index==1 else 'C1'],expected=expected,app_writes=list(writes),provider_calls=list(calls),receiver_after_hex=data.hex(),array_pointer_offset=read(0x134)-OBJ,result_offset=u.reg_read(UC_ARM_REG_R0)-OBJ))
    if fill==0xa5:
     writes.clear();call_count=len(calls)
     for tick in range(101):
      u.reg_write(UC_ARM_REG_SP,SP);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,OBJ)
      u.emu_start(process_range['address'],STOP,count=1000);assert u.reg_read(UC_ARM_REG_PC)==STOP
     assert len(calls)==call_count
     data=bytes(u.mem_read(OBJ,0x2ac));ticks=dict(expected);ticks['counter']=read(0x2a8);ticks['changed']=data[0x130]
     assert ticks['counter']==101 and ticks['changed']==0
     cases.append(dict(original=record,process_dependency=process_range,fill=fill,argv=['ticks-C2' if index==1 else 'ticks-C1'],expected=ticks,app_writes=list(writes),provider_calls=[],iterations=101,receiver_after_hex=data.hex()))
 return dict(version=1,ranges=ranges,mapping_ranges=mapping_ranges,bound_context=bindings,cases=cases,unicorn_version=__import__('unicorn').__version__,boundary='Only original application target instructions; source CCL CStringBuffer(nullptr) adapters, no Core firmware or target libc execution. Private layout and uninitialized padding excluded from host equivalence.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();result=observe();Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(cases=len(result['cases']),ranges=len(result['ranges']))))
