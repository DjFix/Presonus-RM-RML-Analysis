"""Original ARM application execution; Core is intercepted, never recovered."""
import hashlib,json,struct,pathlib,argparse
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ROOT=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis')
REVIEW=ROOT/'temp/recovery-work/trial10x2-20261115/root-review/ctor-contracts'
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
def sha(b):return hashlib.sha256(b).hexdigest()
def observe(variant):
 data=ELF.read_bytes();assert sha(data)=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
 with ELF.open('rb') as f:
  elf=ELFFile(f);symbols=list(elf.get_section_by_name('.symtab').iter_symbols());sections=[(s['sh_addr'],s['sh_size'],s['sh_offset'],s['sh_type']) for s in elf.iter_sections()];segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
 def read(a,n):
  for base,size,off,typ in sections:
   if base<=a and a+n<=base+size and typ!='SHT_NOBITS':return data[off+a-base:off+a-base+n]
  raise ValueError(hex(a))
 ev=json.loads((REVIEW/'GLOBAL_DESCRIPTOR_EVIDENCE.json').read_text());nat=json.loads((REVIEW/f'native/trial10x2_global_{variant}.json').read_text());ranges=[nat['body'],nat['original_nonCore_helper_closure']['ServerComponent_char_constructor']['range'],ev['table'],ev['constructor_literal_table_pointer']]+[x['range'] for x in ev['pointer_payloads'].values()]
 symbols=[s for s in symbols if s.name==nat['target']['mangled']];assert len(symbols)==1 and symbols[0]['st_value']==nat['body']['address'] and symbols[0]['st_size']==172 and symbols[0]['st_shndx']==12
 assert struct.unpack('<I',read(nat['body']['address']+164,4))[0]==0x176ba8
 name_bytes=read(0x159e14,7);assert name_bytes==b'global\0';ranges.append({'address':0x159e14,'size':7,'section':'.rodata','section_index':14,'file_offset':0x159e14-0x8000,'bytes_sha256':sha(name_bytes)})
 for r in ranges:assert sha(read(r['address'],r['size']))==r['bytes_sha256']
 def string(a):
  if not a:return None
  b=bytearray()
  while read(a+len(b),1)!=b'\0':b+=read(a+len(b),1)
  return b.decode('ascii')
 rows=[]
 for i in range(53):
  v=struct.unpack('<ii32s5fi5I',read(0x176ba8+i*84,84));typ,tag,name,*_=v;ptr=v[9:14];lst=[]
  if ptr[2]:lst=[string(struct.unpack('<I',read(ptr[2]+4*j,4))[0]) for j in range(int(v[4])+1)]
  row={'index':i,'type':typ,'tag':tag,'name':name.split(b'\0')[0].decode(),'min':v[3],'max':v[4],'mid':v[5],'default':v[6],'delta':v[7],'flags':v[8],'mapped_literal_fields':dict(zip(['unitName','curveName','title','shortTitle'],[string(ptr[0]),string(ptr[1]),string(ptr[3]),string(ptr[4])])),'string_list':lst,'original_pointer_words':list(ptr)}
  assert row==ev['descriptors'][i],(i,row,ev['descriptors'][i]);rows.append(row)
 results=[]
 for fill in [0,0x55,0xaa,0xff]:
  for mixer in [0x3100000,0x3100100]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);mapped=set()
   for base,size,body in segments:
    for page in range(base&~4095,(base+size+4095)&~4095,4096):
     if page not in mapped:u.mem_map(page,4096);mapped.add(page)
    u.mem_write(base,body)
   obj,stack,stop=0x3000000,0x3200000,0x3300000
   for a in [obj,stack,stop]:u.mem_map(a,0x10000)
   u.mem_write(obj,bytes([fill])*0x100);u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,mixer);u.reg_write(UC_ARM_REG_SP,stack+0x8000);u.reg_write(UC_ARM_REG_LR,stop)
   calls=[];writes=[]
   def code(uc,a,size,_):
    if a==stop:uc.emu_stop();return
    regs=[uc.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
    if a==0x119e8c:
     assert regs[0]==obj and string(regs[1])=='global';calls.append({'boundary':'actual CCL Component constructor','name':string(regs[1])});uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    elif a==0x11ec54:
     assert regs[:3]==[obj+0x28,0x176ba8,53] and regs[3]==0;assert uc.mem_read(obj+0x28,1)==b'\x01';calls.append({'boundary':'actual CCL ParamList add','count':53,'ownsInfo':False,'feedback':True});uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    elif a==0x11d250:
     assert regs[0]==obj+0x28 and regs[1] in [20,21];calls.append({'boundary':'actual CCL byTag','tag':regs[1]});uc.reg_write(UC_ARM_REG_R0,0x3400000+regs[1]*16);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   def write(uc,access,a,size,value,_):
    if obj<=a<obj+0x100:writes.append([a-obj,size,value])
   u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write);u.emu_start(nat['body']['address'],stop,count=300)
   assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_R0)==obj
   assert struct.unpack('<III',u.mem_read(obj+0x88,12))==(mixer,0x3400140,0x3400150)
   assert len(calls)==4 and [x.get('tag') for x in calls[-2:]]==[20,21]
   assert [w for w in writes if w[0] in [0,4]][-2:]==[[0,4,0x176b00],[4,4,0x176b3c]]
   results.append({'prefill':fill,'mixer':mixer,'return_this':True,'calls':calls,'writes':writes})
 return {'variant':variant,'elf_sha256':sha(data),'ranges':ranges,'descriptors':rows,'native_cases':results,'limits':'Core boundary calls intercepted, actual provider behavior tested separately; normal path only; no Core ARM execution, EH, original layout or ABI claim.'}
def write_provider(rows,path):
 with open(path,'w') as f:
  for r in rows:
   vals=[r[k] for k in ['type','tag','name','min','max','mid','default','delta','flags']]+[r['mapped_literal_fields'][k] for k in ['unitName','curveName','title','shortTitle']]+[len(r['string_list'])]+r['string_list']
   f.write(' '.join(json.dumps(v if v is not None else '<null>') for v in vals)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--variant',choices=['c1','c2'],required=True);p.add_argument('--out',required=True);a=p.parse_args();o=pathlib.Path(a.out);o.mkdir(parents=True,exist_ok=True);r=observe(a.variant);(o/'native.json').write_text(json.dumps(r,indent=2)+'\n');write_provider(r['descriptors'],o/'provider.txt');print('native ARM cases:',len(r['native_cases']))
