"""Exact application ARM instructions with named provider boundaries.
No Core instruction execution, guest syscall, hardware or system passthrough.
Actual CCL Stream and canonical queue providers execute in a separate host
process which never calls reconstructed DiceEndPoint::test.
"""
from pathlib import Path
import hashlib,json,struct,subprocess
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
P=R/'temp/recovery-work/rolling200-02/next-implementation65/prepared-dice65-v2/packets'
ELF=R/'rootfs/RML16AI_Rack_13731/home/root/mixer';SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
EXE=R/'temp/recovery-work/dice-endpoint22-local/replay'
OBJ=0x1000000;IN=OBJ+0x100;OUT=OBJ+0x200;STREAM=OBJ+0x300;VTABLE=OBJ+0x400;SVTABLE=OBJ+0x500;STACK=0x1100000;STOP=0x1200000;READ=STOP+0x100;SEEK=STOP+0x200;ENDREAD=STOP+0x300
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def digest(b):return hashlib.sha256(b).hexdigest()
def ranges():
 raw=ELF.read_bytes();assert digest(raw)==SHA
 out=[]
 with ELF.open('rb') as f:
  elf=ELFFile(f);symbols={s.name:s for s in elf.get_section_by_name('.symtab').iter_symbols()}
  for packet in sorted(P.glob('rolling200_02_dice_endpoint22_*')):
   req=json.loads((packet/'request.json').read_text());context=json.loads((packet/'native-context.json').read_text())
   for orig in req['originals']:
    o=orig['original'];s=symbols[o['mangled']];sec=elf.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr']
    b=next(x for x in context['bodies'].values() if x.get('address')==s['st_value'])
    assert (s['st_value'],s['st_size'],s['st_shndx'])==(o['address'],o['size'],12)
    assert off==b['file_offset'] and digest(raw[off:off+s['st_size']])==b['bytes_sha256']
    out.append(dict(mangled=s.name,address=s['st_value'],size=s['st_size'],section=sec.name,section_index=s['st_shndx'],file_offset=off,sha256=b['bytes_sha256']))
 return raw,out
RAW,RANGES=ranges()
def delete_binding():
 with ELF.open('rb') as f:
  e=ELFFile(f);p=e.get_section_by_name('.plt');r=e.get_section_by_name('.rel.plt');d=e.get_section(r['sh_link']);address=0xac10
  assert (address-p['sh_addr']-20)%12==0
  index=(address-p['sh_addr']-20)//12;rel=list(r.iter_relocations())[index];name=d.get_symbol(rel['r_info_sym']).name
  assert name=='_ZdlPv'
  return {'entry':address,'mangled':name,'relocation_index':index,'got_address':rel['r_offset'],'plt_range_sha256':digest(p.data()[address-p['sh_addr']:address-p['sh_addr']+12]),'scope':'Exact ELF PLT relocation binds native D0 branch to operator delete(void*); provider boundary removes live guest allocation and unmaps it.'}
def machine():
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x800000)
 with ELF.open('rb') as f:
  for seg in ELFFile(f).iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 u.mem_protect(0,0x800000,5);u.mem_map(OBJ,0x1000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
 u.reg_write(UC_ARM_REG_SP,STACK+0xff00);u.reg_write(UC_ARM_REG_LR,STOP)
 return u

def execute(body,case=None):
 u=machine();pcs=[];writes=[];trace=[];calls=[];allocated={OBJ};deleted=[]
 def w(a,v):u.mem_write(a,struct.pack('<I',v))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 u.mem_write(OBJ,b'\xa5'*0x80);w(OBJ,VTABLE);w(OBJ+4,IN);w(OBJ+8,OUT);w(VTABLE+8,ENDREAD);w(STREAM,SVTABLE);w(SVTABLE+16,READ);w(SVTABLE+12,SEEK)
 initial=bytes(u.mem_read(OBJ,0x80))
 service=None
 if case:
  service=subprocess.Popen([str(EXE),'provider',case['input'],str(case['negative']),str(case['preload'])],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=R)
 def query(line):
  service.stdin.write(line+'\n');service.stdin.flush();answer=service.stdout.readline().strip();assert answer,(line,service.poll());trace.append(answer);return answer.split()
 def ret(n=0):u.reg_write(UC_ARM_REG_R0,n&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def datahex(a,n):return bytes(u.mem_read(a,n)).hex() if n else '-'
 def write(uc,access,address,size,value,unused):
  assert STACK<=address and address+size<=STACK+0x10000 or OBJ<=address and address+size<=OBJ+0x80,(hex(address),size)
  if OBJ<=address<OBJ+0x80:writes.append([address-OBJ,size,value])
 def code(uc,address,size,unused):
  if address==STOP:uc.emu_stop();return
  regs=[uc.reg_read(x) for x in REGS];a,b,c,d=regs
  if case and address==READ:
   assert a==STREAM and 0<=c<=255
   answer=query(f'S {c}');result=int(answer[2]);buffer=bytes.fromhex(answer[3]) if answer[3]!='-' else b''
   assert STACK<=b and b+len(buffer)<=STACK+0x10000
   if buffer:u.mem_write(b,buffer)
   ret(result);return
  if case and address==SEEK:
   assert a==STREAM and c==d==0 and r(uc.reg_read(UC_ARM_REG_SP))==0
   answer=query('K');ret(int(answer[3]));uc.reg_write(UC_ARM_REG_R1,0);return
  if case and address==0x10475c:
   assert a==OUT and c<=255
   answer=query(f'W {c} {datahex(b,c)}');ret(int(answer[3]));return
  if case and address in (0x1038c0,0x1037d8):
   assert a==OUT;before=u.mem_read(c,1)[0];op='P' if address==0x1038c0 else 'R';answer=query(f'{op} {before}')
   length=int(answer[3]);u.mem_write(c,bytes([length]))
   if length:u.mem_write(b,bytes.fromhex(answer[4]))
   ret(int(answer[2]));return
  if case and address==0x1036f0:
   assert a==IN
   buf=bytes(u.mem_read(b,255));end=buf.find(b'\xf7');buf=buf[:end+1] if end>=0 else buf
   answer=query('M '+buf.hex());ret(int(answer[2]));return
  if case and address==ENDREAD:
   assert a==OBJ and c<=255 and bytes(u.mem_read(b,256))==b'\xfe'*256
   answer=query(f'E {c}');u.mem_write(b,bytes.fromhex(answer[3]));ret(int(answer[2]));return
  if case and address==0xaa60:
   assert c==256 and b in (0xfe,0xff) and STACK<=a and a+c<=STACK+0x10000
   u.mem_write(a,bytes([b])*c);ret(a);return
  if case and address==0x10459c:
   assert a in (IN,OUT);query('F '+('I' if a==IN else 'O'));ret();return
  if not case and address==0x1041a4:
   assert [a,b,c]==[OBJ,IN,OUT];calls.append({'boundary':'existing DataChannel(PacketQueue&,PacketQueue&)','receiver':a,'incoming':b,'outgoing':c})
   # Named source-port boundary only. Native base implementation is not executed.
   w(OBJ,0x3685c8);w(OBJ+4,b);w(OBJ+8,c);ret(OBJ);return
  if not case and address==0xac10:
   assert a==OBJ and a in allocated and r(a)==0x3685c8
   # Actual observed ARM branch reaches delete boundary. Remove the live guest
   # allocation and unmap it; any subsequent use faults. No appended delete event.
   allocated.remove(a);deleted.append(a);u.mem_unmap(OBJ,0x1000);ret();return
  assert body['address']<=address and address+size<=body['address']+body['size'],('unexpected PC',hex(address))
  assert size==4;pcs.append(address)
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,STREAM if case else IN);u.reg_write(UC_ARM_REG_R2,OUT)
 try:
  u.emu_start(body['address'],STOP,count=500000)
  assert u.reg_read(UC_ARM_REG_PC)==STOP
 finally:
  if service:
   service.stdin.close();assert service.wait(timeout=5)==0,service.stderr.read()
 result={'mangled':body['mangled'],'executed_instructions':len(pcs),'pc_sequence_sha256':digest(b''.join(struct.pack('<I',x) for x in pcs)),'native_object_writes':writes,'provider_calls':calls,'guest_live_allocation':OBJ in allocated,'observed_delete_addresses':deleted}
 if case:result['trace']=trace
 elif 'C1E' in body['mangled'] or 'C2E' in body['mangled']:
  assert r(OBJ)==0x368478 and r(OBJ+4)==IN and r(OBJ+8)==OUT and len(calls)==1
  assert bytes(u.mem_read(OBJ+12,0x80-12))==initial[12:];result['borrowed_queues_unchanged']=True
 else:
  assert writes==[[0,4,0x3685c8]]
  if 'D0E' in body['mangled']:assert deleted==[OBJ] and not allocated
  else:
   assert not deleted and bytes(u.mem_read(OBJ+4,0x7c))==initial[4:];result['no_queue_cleanup']=True
 return result

def generate():
 cases=[];body=next(b for b in RANGES if '4testE' in b['mangled'])
 lengths=[0,1,2,3,4,5,8,9,10,31,199,200,201,254,255,256,257,1000,32250,32640,33000]
 for n in lengths:
  c={'id':f'memory-{n}','input':bytes((i*37+11)&255 for i in range(n)).hex() or '-','negative':0,'preload':0}
  cases.append({**c,**execute(body,c)})
 for n in (0,3,256):
  c={'id':f'negative-initialized-{n}','input':bytes((i*13)&255 for i in range(n)).hex() or '-','negative':1,'preload':0};cases.append({**c,**execute(body,c)})
 for preload in (1,2):
  c={'id':f'nonpositive-front-packet-{preload}','input':'0102030405','negative':0,'preload':preload};cases.append({**c,**execute(body,c)})
 return {'version':1,'elf_sha256':SHA,'ranges':RANGES,'delete_binding':delete_binding(),'policy':'Exact original application ranges only. All native external calls intercepted; actual pinned CCL streams and existing canonical queue/MIDI/factory providers service calls independently of DiceEndPoint::test. Provider source behavior is not original queue ARM verification. Negative read precondition explicitly initializes256 source bytes; returns -1 then real MemoryStream. Initial native stack bytes outside initialized input are not compared. No original return/layout/ARM ABI or hardware claim. D0 delete is a bounded deallocation boundary, not native allocator implementation.','cases':cases,'lifecycle':[execute(b) for b in RANGES if '4testE' not in b['mangled']]}
if __name__=='__main__':
 data=generate();(T/'fixtures.json').write_text(json.dumps(data,indent=2)+'\n');print(len(data['cases']),'native test cases and',len(data['lifecycle']),'separately executed native lifecycle ranges')
