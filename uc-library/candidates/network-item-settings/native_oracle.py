#!/usr/bin/env python3
"""Original ARM callers in private Unicorn memory; actual pinned CCL boundaries.
No Core instructions, hardware, sockets or host syscall passthrough execute.
"""
import argparse, hashlib, json, struct, subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR,UC_ARM_REG_SP
BASE=Path('uc-library/candidates/network-item-settings')
PACKETS=Path('temp/recovery-work/rolling200-02/implementation-plan01/packets-current-network-items02/packets')
ELF=Path('rootfs/CS18_v13840/home/root/surface')
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
REG=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]

def cases():
 rows=[]
 def add(method, **kw):
  c=dict(method=method,section=1,value_present=1,flags=2,live=1,dirty=0,section_name='networksetup',key='selectedMixer',saved='previous',identity='Mixer')
  c.update(kw);rows.append(c)
 for n in range(64):
  identity='x'*n
  for section in (0,1):
   for dirty in (0,1): add(1,identity=identity,section=section,dirty=dirty)
  for saved in (identity,identity+'z',identity.upper()):add(2,identity=identity,saved=saved)
 for flags in (0,1,2,3,4,6,7,-1,-2,2147483647,-2147483648):
  for section in (0,1):
   for live in (0,1):add(1,flags=flags,section=section,live=live)
 for dirty in (0,1):
  for section in (0,1):
   for value_present in (0,1):
    add(2,section=section,value_present=value_present,saved='',live=0,dirty=dirty)
    add(2,section=section,value_present=value_present,saved='',live=1,dirty=dirty)
 for n in (63,64,65,80,127):
  add(2,identity='x'*63,saved='x'*n)
  add(2,identity='x'*62+'y',saved='x'*n)
 for method in (1,2):
  for key in ('selectedDAW','Key with spaces','K'*31,'K'*32):
   add(method,key=key,identity='Device A:1',saved='Device A:1')
 return rows

def produce(executable):
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 originals={};ranges=[]
 with ELF.open('rb') as f:
  ef=ELFFile(f);sections=list(ef.iter_sections());segs=[(s['p_vaddr'],s.data()) for s in ef.iter_segments() if s['p_type']=='PT_LOAD']
  symbols={s.name:s for s in ef.get_section_by_name('.symtab').iter_symbols()}
  for i in (1,2):
   packet=PACKETS/f'rolling200_02_network_items_{i:02d}'
   req=json.loads((packet/'request.json').read_text());o=req['originals'][0]['original'];originals[i]=o
   sym=symbols[o['mangled']];assert sym['st_value']==o['address'] and sym['st_size']==o['size']
   sec=sections[int(o['section_json'])];offset=sec['sh_offset']+o['address']-sec['sh_addr'];body=data[offset:offset+o['size']]
   ranges.append(dict(original=o,section=sec.name,file_offset=offset,sha256=hashlib.sha256(body).hexdigest(),symbol_table_verified=True))
 provider=subprocess.Popen([executable,'--provider'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
 def ask(*args):
  line=' '.join(json.dumps(a) if isinstance(a,str) and j else str(a) for j,a in enumerate(args))
  provider.stdin.write(line+'\n');provider.stdin.flush();result=provider.stdout.readline();assert result,(line,provider.poll());return json.loads(result)
 outputs=[]
 try:
  for c in cases():
   ask('init',c['section_name'],c['key'],c['saved'],c['section'],c['value_present'],c['dirty'])
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x800000)
   for addr,b in segs:u.mem_write(addr,b)
   w=lambda a,v:u.mem_write(a,struct.pack('<I',v&0xffffffff))
   read=lambda a:struct.unpack('<I',u.mem_read(a,4))[0]
   def string(a):
    if not a:return ''
    out=bytearray()
    for _ in range(512):
     b=bytes(u.mem_read(a,1));a+=1
     if b==b'\0':return out.decode('ascii')
     out.extend(b)
    raise AssertionError('unterminated string outside bounded domain')
   def put(a,s):u.mem_write(a,s.encode('ascii')+b'\0')
   obj=0x400000;item=0x410000;key=0x420000;result=0x430000;section_obj=0x440000;attr=0x450000;root=0x26ae1c
   w(0x26ac08,1);w(0x26ae24,0x460000);w(0x26ac0c+0x20c,0xa0|(4 if c['dirty'] else 0))
   put(obj+8,c['section_name']);put(key,c['key']);put(item+0x18e,c['identity']);u.mem_write(item+0x18e+len(c['identity'])+1,b'Q'*(63-len(c['identity'])))
   calls=[];writes=[];pcs=set();start=originals[c['method']]['address'];end=start+originals[c['method']]['size']
   def ret(v=None):
    if v is not None:u.reg_write(UC_ARM_REG_R0,v&0xffffffff)
    u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   def write_hook(uc,access,a,size,v,user):
    assert 0x7e0000<=a and a+size<=0x7f0000 or (a==0x26ae18 and size==4),('unexpected native write',hex(a),size,c)
    writes.append([a,size,v])
   def hook(uc,a,size,user):
    pcs.add(a);r=[uc.reg_read(x) for x in REG]
    if a==0x600000:uc.emu_stop();return
    if a==0x3ae34:
     text=string(r[1]);value=ask('buffer',text);calls.append(['CStringBuffer64',text,value]);put(r[0],value);ret(r[0])
    elif a==0xaffc:
     assert r[1]==item+0x18e and r[2]==64 and 0x7e0000<=r[0]<0x7f0000
     calls.append(['memcpy',64]);u.mem_write(r[0],bytes(u.mem_read(r[1],64)));ret(r[0])
    elif a==0x124108:
     assert r[0]==root and string(r[1])==c['section_name'];v=ask('section',string(r[1]));calls.append(['getAttributes',c['section_name'],v]);ret(section_obj if v else 0)
    elif a==0x124ae8:
     assert r[0] in (root,section_obj);text=string(r[1]);is_root=int(r[0]==root);ask('lookup',is_root,text);calls.append(['lookupOrAdd',is_root,text]);ret(attr)
    elif a==0x1260ec:
     assert r[0]==attr and r[1]==0x460000;ask('make');calls.append(['makeAttributes']);ret(section_obj)
    elif a==0x1263cc:
     assert r[0]==attr and r[2]==0;text=string(r[1]);ask('set',text);calls.append(['set',text,False]);ret()
    elif a==0x124200:
     assert r[0]==section_obj;text=string(r[1]);v=ask('get',text);calls.append(['getString',text,v]);put(result,v);ret(result)
    elif a==0xb0f8:
     assert r[0]==item+0x18e and c['live'];x,y=string(r[0]),string(r[1]);v=ask('compare',x,y);calls.append(['strcmp',x,y,v]);ret(v)
    else:assert start<=a<end,('unexpected native PC',hex(a),c)
   u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write_hook)
   before_item=bytes(u.mem_read(item,0x200));before_obj=bytes(u.mem_read(obj,0x200))
   for reg,value in zip(REG,[obj,key,item if c['live'] else 0,c['flags']&0xffffffff]):u.reg_write(reg,value)
   u.reg_write(UC_ARM_REG_SP,0x7f0000);u.reg_write(UC_ARM_REG_LR,0x600000)
   u.emu_start(start,0x600004,count=2000)
   assert u.reg_read(UC_ARM_REG_PC)==0x600000
   assert before_item==bytes(u.mem_read(item,0x200)) and before_obj==bytes(u.mem_read(obj,0x200))
   dirty_word=read(0x26ae18);assert dirty_word&~4==0xa0
   result_value=-1 if c['method']==1 else u.reg_read(UC_ARM_REG_R0)
   observed=ask('state',int(bool(dirty_word&4)),result_value)
   outputs.append(dict(input=c,observed=observed,native_provider_calls=calls,native_writes=writes,native_pcs=sorted(pcs),object_and_identity_unchanged=True))
 finally:
  provider.stdin.close();assert provider.wait(timeout=10)==0
 return dict(version=1,elf_sha256=SHA,unicorn_version=unicorn.__version__,ranges=ranges,cases=outputs,limitations='Native target caller instructions only with initialized singleton and normal nonthrowing real CCL source provider boundaries; lookupOrAdd deferred into public makeAttributes/set. Identity strings terminated, lengths0..63; stored strings may truncate. Native lazy initialization, unwind, actual Core binaries, original returns/layout/ARM ABI, concurrency, allocation failures, hardware and invalid pointers excluded.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--verify',action='store_true');a=p.parse_args();result=produce(a.executable);path=BASE/'fixtures.json'
 if a.verify:assert result==json.loads(path.read_text())
 else:path.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'native_cases':len(result['cases']),'passed':True,'unicorn':unicorn.__version__}))
