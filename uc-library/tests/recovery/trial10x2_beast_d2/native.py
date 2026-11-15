"""Execute only the exact original Beast destructor; real host base/free RPC."""
import hashlib,json,pathlib,struct,subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ROOT=pathlib.Path(__file__).resolve().parents[4]
BASE=pathlib.Path(__file__).parent
SNAP=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/trial10x2-20261115/prepared01/snapshot')
ELF=SNAP/'rootfs/RML16AI_Rack_13731/home/root/mixer'
ELFHASH='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
SPECS=[('D2',500040,76,'a64eb00f8bdec5b6414e28279640cfa02f9a6bc8c981ff10940c334f6669cd81'),('D0',500124,84,'f8e20bf691874d06e7ba8f416efa3efb3dedbe43208b32521efa7fbac11ae890')]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def generate(exe):
 assert sha(ELF)==ELFHASH
 contracts=[]
 for task in ['trial10x2_beast_d2','trial10x2_beast_d0']:
  packet=ROOT/'temp/recovery-work/trial10x2-20261115/prepared01/packets'/task
  req=json.loads((packet/'request.json').read_text());c=req['reconstruction_contract'];cp=SNAP/c['path'];assert sha(cp)==c['sha256']
  contract=json.loads(cp.read_text());evidence=[e for e in contract['requirements']['providers']['evidence'] if e['kind']=='native_observation']
  for e in evidence:assert sha(SNAP/e['path'])==e['sha256']
  contracts.append(dict(task_id=task,contract_path=c['path'],contract_sha256=c['sha256'],native_evidence=evidence))
 raw=ELF.read_bytes();ranges=[];cases=[]
 with ELF.open('rb') as f:
  elf=ELFFile(f);sec=elf.get_section(12);assert sec.name=='.text'
  symbols={s.name:s for s in elf.get_section_by_name('.symtab').iter_symbols()}
  for variant,address,size,digest in SPECS:
   name='_ZN8Presonus5Mixer19BeastMixerComponent'+variant+'Ev'
   sym=symbols[name];assert sym['st_value']==address and sym['st_size']==size and sym['st_shndx']==12
   offset=sec['sh_offset']+address-sec['sh_addr'];body=raw[offset:offset+size];assert hashlib.sha256(body).hexdigest()==digest
   r=dict(mangled=name,address=address,size=size,section='.text',section_index=12,file_offset=offset,bytes_sha256=digest);ranges.append(r)
   for count in [1,2,7,32]:
    for pattern in [0,165,255]:
     proc=subprocess.Popen([str(exe),'boundary'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,cwd=ROOT)
     proc.stdin.write(str(count)+'\n');proc.stdin.flush();rpc_trace=[]
     def rpc(cmd):
      proc.stdin.write(cmd+'\n');proc.stdin.flush();result=proc.stdout.readline().strip();assert result,(cmd,proc.poll());rpc_trace.append([cmd,result]);return result
     u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
     def put(a,b):
      for page in range(a&~4095,(a+len(b)+4095)&~4095,4096):
       if page not in pages:u.mem_map(page,4096);pages.add(page)
      u.mem_write(a,b)
     obj=0x1000000;sp=0x1100000;stop=0x1200000
     put(address,body);put(obj,bytes([pattern])*0x1000);put(sp-4096,bytes(8192));put(stop,bytes(4))
     for a in [0x2dd94,0xac10]:put(a,bytes(4))
     writes=[];calls=[];pcs=[]
     def hook(uc,pc,size,_):
      pcs.append(pc)
      if pc in [0x2dd94,0xac10]:
       assert uc.reg_read(UC_ARM_REG_R0)==obj
       calls.append(pc);assert rpc('BASE' if pc==0x2dd94 else 'FREE')=='1'
       uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
     def write(uc,access,a,size,value,_):
      if obj<=a<obj+0x1000:writes.append([a-obj,size,value])
     u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
     u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop)
     u.emu_start(address,stop,count=200)
     assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_R0)==obj
     report=rpc('REPORT');assert report==('1 1 0' if variant=='D0' else '0 1 0');assert rpc('CLEAN')=='1';proc.stdin.close();assert proc.wait(timeout=10)==0
     assert calls==([0x2dd94,0xac10] if variant=='D0' else [0x2dd94])
     assert writes==[[4,4,0x3483e8+0xe0],[0x88,4,0x3483e8+0xf0],[0x104,4,0x3483e8+0x130],[0x45c,4,0x3483e8+0x144],[0,4,0x3483e8]]
     cases.append(dict(variant=variant,count=count,pattern=pattern,calls=calls,writes=writes,return_identity=True,provider_rpc=rpc_trace,product_report=report,cleanup='1',instruction_addresses=pcs))
 return dict(version=1,sealed_contracts=contracts,elf_sha256=ELFHASH,ranges=ranges,cases=cases,scope='24 cases: exact D2 and D0 original ARM ranges, 1/2/7/32 repeated borrowed real Channel pointers, actual Core parameter value/observer lifetime, 3 native memory fills; actual canonical base destructor RPC and actual unsized delete/free RPC. Native vptr writes observed separately; no original base/Core instruction emulation or ARM layout claim.')
if __name__=='__main__':
 import sys
 print(json.dumps(generate(pathlib.Path(sys.argv[1]).resolve()),indent=2))
