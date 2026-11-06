"""Execute exact UCNet ARM ranges, with named actual application/CCL providers.
No Core binary instruction execution, guest syscall or host device passthrough.
Every deallocation event is reached by an executed native delete call.
"""
from pathlib import Path
import hashlib,json,struct,subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
P=R/'temp/recovery-work/rolling200-02/next-implementation148/prepared148/packets'
ELF=R/'rootfs/RML16AI_Rack_13731/home/root/mixer';SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
EXE=R/'temp/recovery-work/ucnet148-local/replay'
OBJ=0x1000000;ENDPOINT=0x1010000;SPI=0x1020000;STACK=0x1100000;STOP=0x1200000
SINGLETON=0x495368

def digest(b):return hashlib.sha256(b).hexdigest()
def ranges():
 raw=ELF.read_bytes();assert digest(raw)==SHA
 result=[]
 with ELF.open('rb') as f:
  elf=ELFFile(f);symbols={s.name:s for s in elf.get_section_by_name('.symtab').iter_symbols()}
  def record(name):
   s=symbols[name];sec=elf.get_section(s['st_shndx']);offset=sec['sh_offset']+s['st_value']-sec['sh_addr']
   return dict(mangled=name,address=s['st_value'],size=s['st_size'],section=sec.name,section_index=s['st_shndx'],file_offset=offset,sha256=digest(raw[offset:offset+s['st_size']]))
  for packet in sorted(P.glob('rolling200_02_ucnet148_*')):
   req=json.loads((packet/'request.json').read_text());context=json.loads((packet/'native-context.json').read_text())
   for item in req['originals']:
    o=item['original'];b=record(o['mangled']);bound=next(v for v in context['bodies'].values() if v['address']==o['address'])
    assert (b['address'],b['size'],b['section_index'])==(o['address'],o['size'],12)
    assert b['sha256']==bound['bytes_sha256'] and b['file_offset']==bound['file_offset'];result.append(b)
  endpoint=record('_ZN8Presonus2UC12DiceEndPointD0Ev')
  slot=json.loads((R/'evidence/recovery/2026-11-06/rolling200-02/ucnet-lifecycle147/ENDPOINT_SLOT148.json').read_text())
  assert digest(raw[slot['file_offset']:slot['file_offset']+slot['size']])==slot['sha256']
  assert struct.unpack_from('<I',raw,slot['file_offset']+40)[0]==endpoint['address']
  plt=elf.get_section_by_name('.plt');rel=elf.get_section_by_name('.rel.plt');dyn=elf.get_section(rel['sh_link']);index=(0xac10-plt['sh_addr']-20)//12;reloc=list(rel.iter_relocations())[index]
  assert dyn.get_symbol(reloc['r_info_sym']).name=='_ZdlPv'
  binding={'entry':0xac10,'mangled':'_ZdlPv','relocation_index':index,'got':reloc['r_offset'],'plt_sha256':digest(raw[0xac10-0x8000:0xac10-0x8000+12])}
 return raw,result,endpoint,slot,binding
RAW,RANGES,ENDPOINT_RANGE,SLOT,DELETE_BINDING=ranges()
def execute(body,c):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x800000)
 with ELF.open('rb') as f:
  for s in ELFFile(f).iter_segments():
   if s['p_type']=='PT_LOAD':u.mem_write(s['p_vaddr'],s.data())
 for a,n in [(OBJ,0x1000),(ENDPOINT,0x1000),(SPI,0x1000),(STACK,0x10000),(STOP,0x1000)]:u.mem_map(a,n)
 def w(a,v):u.mem_write(a,struct.pack('<I',v))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def ret(value=0):u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 w(OBJ+0x5c,ENDPOINT if c['endpoint'] else 0);w(ENDPOINT,SLOT['address']+8);w(SINGLETON,SPI if c['existing'] or c['registered'] else 0)
 service=subprocess.Popen([str(EXE),'provider',c['variant'],str(c['endpoint']),str(c['populated']),str(c['existing']),str(c['registered']),str(c.get('failure',0))],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=R)
 trace=[];pcs=[];writes=[];calls=[];unwind=[];live={OBJ:'self'}
 if c['endpoint']:live[ENDPOINT]='endpoint'
 def query(op):
  service.stdin.write(op+'\n');service.stdin.flush();line=service.stdout.readline();assert line,(op,service.poll(),service.stderr.read());return line.strip().split()
 def write(uc,access,a,n,value,unused):
  assert STACK<=a and a+n<=STACK+0x10000 or OBJ<=a and a+n<=OBJ+0x1000 or ENDPOINT<=a and a+n<=ENDPOINT+0x1000 or SPI<=a and a+n<=SPI+0x1000 or a==SINGLETON,(hex(a),n)
  if not STACK<=a<STACK+0x10000:writes.append([a,n,value])
 def code(uc,a,size,unused):
  if a==STOP:uc.emu_stop();return
  x=uc.reg_read(UC_ARM_REG_R0);y=uc.reg_read(UC_ARM_REG_R1)
  if a==0xa7e4:
   assert x==456
   if c.get('failure')==1:
    observed=query('L');assert observed==['THROW'];calls.append(['actual_source_allocation_failure',observed])
    # Explicit probe: no native unwinder/personality execution is claimed.
    landing=body['address']+(204 if c['variant']=='D0' else 196)
    unwind.append({'injected_at':a,'landing':landing,'scope':'forced application cleanup probe, not real native unwinding'})
    uc.reg_write(UC_ARM_REG_R0,0x1234);uc.reg_write(UC_ARM_REG_PC,landing);return
   live[SPI]='spi';calls.append(['allocate_spi',x]);ret(SPI);return
  if a==0xa2e64:
   assert x==SPI;observed=query('L')
   if c.get('failure'):
    assert observed==['THROW','SPI_DELETE'];calls.append(['actual_source_spi_construction_failure',observed])
    landing=body['address']+(160 if c['variant']=='D0' else 152)
    unwind.append({'injected_at':a,'landing':landing,'scope':'forced application cleanup probe, not real native unwinding'})
    uc.reg_write(UC_ARM_REG_R0,0x1234);uc.reg_write(UC_ARM_REG_PC,landing);return
   assert observed==['L'];calls.append(['actual_source_spi_singleton_construction']);ret(SPI);return
  if a==0x126cfc:
   assert x==SPI;calls.append(['pinned_CCL_Deletable_registration_in_source_provider']);ret();return
  if a==0xa2fe0:
   assert x==SPI and y==OBJ
   values=query('U');assert values==['U'];trace.extend(values);calls.append(['actual_source_SPI_unregister']);ret();return
  if a==0x1046c8:
   assert x in (OBJ+0x34,OBJ+0xc)
   values=query('O' if x==OBJ+0x34 else 'I');trace.extend(values);calls.append(['actual_source_PacketQueue_destructor',x-OBJ]);ret();return
  if a==0xacd0:
   assert c.get('failure') and x==0x1234
   calls.append(['observed_native_cxa_end_cleanup_boundary',x]);uc.reg_write(UC_ARM_REG_PC,STOP);uc.emu_stop();return
  if a==0xac10:
   assert x in live,(hex(x),live)
   kind=live.pop(x)
   if kind=='endpoint':
    values=query('E');assert values==['E'];trace.extend(values)
   elif kind=='self':trace.append('S')
   else:trace.append('SPI_DELETE')
   calls.append(['observed_native_operator_delete',kind]);u.mem_unmap(x,0x1000);ret();return
  assert body['address']<=a<a+size<=body['address']+body['size'] or ENDPOINT_RANGE['address']<=a<a+size<=ENDPOINT_RANGE['address']+ENDPOINT_RANGE['size'],('unexpected PC',hex(a))
  pcs.append(a)
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_SP,STACK+0xff00);u.reg_write(UC_ARM_REG_LR,STOP)
 try:
  u.emu_start(body['address'],STOP,count=10000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 finally:
  service.stdin.close();assert service.wait(timeout=10)==0,service.stderr.read()
 if c.get('failure'):
  assert (ENDPOINT in live)==bool(c['endpoint']) and OBJ in live and SPI not in live
  assert trace==(['SPI_DELETE'] if c['failure']>1 else [])+['QO']+['P']*c['populated']+['QI']+['P']*c['populated']
 else:
  assert ENDPOINT not in live
  assert (OBJ not in live)==(c['variant']=='D0')
  assert trace==['U']+(['E'] if c['endpoint'] else [])+['QO']+['P']*c['populated']+['QI']+['P']*c['populated']+(['S'] if c['variant']=='D0' else [])
 return {**c,'mangled':body['mangled'],'trace':trace,'executed_instructions':len(pcs),'pc_sequence_sha256':digest(b''.join(struct.pack('<I',p) for p in pcs)),'writes':writes,'provider_calls':calls,'self_deallocated':OBJ not in live,'endpoint_retained':ENDPOINT in live,'forced_cleanup_probe':unwind}
def generate():
 cases=[]
 for b in RANGES:
  variant=next(v for v in ['D0','D1','D2'] if v+'Ev' in b['mangled'])
  for endpoint in [0,1]:
   for populated in [0,1,3]:
    for existing,registered in [(0,0),(1,0),(1,1)]:
     c={'id':f'{variant}-ep{endpoint}-n{populated}-spi{existing}-reg{registered}','variant':variant,'endpoint':endpoint,'populated':populated,'existing':existing,'registered':registered}
     cases.append(execute(b,c))
 probes=[]
 for b in RANGES:
  variant=next(v for v in ['D0','D1','D2'] if v+'Ev' in b['mangled'])
  for failure in [1,2,3]:
   c={'id':f'{variant}-forced-landing-allocation-{failure}','variant':variant,'endpoint':1,'populated':2,'existing':0,'registered':0,'failure':failure,'probe':True}
   probes.append(execute(b,c))
 return {'cleanup_probes':probes,'version':1,'elf_sha256':SHA,'ranges':RANGES,'endpoint_native_D0_range':ENDPOINT_RANGE,'endpoint_slot_binding':SLOT,'delete_binding':DELETE_BINDING,'cases':cases,'policy':'Full original UCNet target instructions and real endpoint D0; actual existing SPI/queue/endpoint/CCL providers independently service native boundaries. Native self deletion removes and unmaps live guest allocation only when executed _ZdlPv entry is reached, not an appended event. No native allocator implementation, Core binary, hardware or ARM ABI claim. Exception probes are separate from normal equivalence.'}
if __name__=='__main__':
 d=generate();(T/'fixtures.json').write_text(json.dumps(d,indent=2)+'\n');print(len(d['cases']),'separate native variant/provider executions')
