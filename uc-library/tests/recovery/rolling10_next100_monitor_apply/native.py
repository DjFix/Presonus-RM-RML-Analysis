"""Verified original ARM application/runtime; actual CCL providers over RPC."""
import collections,ctypes,hashlib,itertools,json,struct,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[4];BASE=Path(__file__).parent;TASK=BASE.name;CASE=6
PREFIX=Path('temp/recovery-work/rolling10x10-20261114/prepared-next-flow01');PACKET=ROOT/PREFIX/'packets'/TASK;SNAPSHOT=Path('/home/rs/projects/opencs/ai-line-analysis')/PREFIX/'snapshot'
def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def generate(exe):
 r=json.loads((PACKET/'request.json').read_text());t=r['targets'][0];reads=json.loads((ROOT/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared-next-flow01-rolling10_pages.json').read_text());ep=Path(next(v['frozen_read_path'] for k,v in reads.items() if k.startswith('rootfs/') and v['sha256']==t['original_elf_sha256']));assert hashlib.sha256(ep.read_bytes()).hexdigest()==t['original_elf_sha256']
 contract=json.loads((SNAPSHOT/r['reconstruction_contract']['path']).read_text());records={};literals=[]
 def find(obj):
  if isinstance(obj,dict):
   if set(('address','size','file_offset','bytes_sha256')).issubset(obj):records[(obj['address'],obj['size'])]=obj
   if 'literal_records' in obj:literals.extend(obj['literal_records'])
   for k,v in obj.items():
    if k not in ('vtables','string_vtable'):find(v)
  elif isinstance(obj,list):
   for v in obj:find(v)
 for gr in list(contract['requirements'].values())+contract['dependencies']:
  for ref in gr.get('evidence',[]):
   if ref['kind'] in ('native_observation','review_record') and ref['path'].endswith('.json'):find(json.loads((SNAPSHOT/ref['path']).read_text()))
 with ep.open('rb') as stream:
  elf=ELFFile(stream);symbols=elf.get_section_by_name('.symtab');sec=elf.get_section(12);sym=symbols.get_symbol_by_name(t['mangled'])[0];assert (sym['st_value'],sym['st_size'],sym['st_shndx'])==(t['address'],t['size'],12)
  offset=sec['sh_offset']+t['address']-sec['sh_addr'];stream.seek(offset);body=stream.read(t['size'])
  sections=[(s['sh_addr'],s.data()) for s in elf.iter_sections() if s['sh_flags']&2 and s['sh_type']=='SHT_PROGBITS']
  funcs={s['st_value']:s.name for s in symbols.iter_symbols() if s['st_info']['type']=='STT_FUNC'}
  checked=[];allowed=[]
  for rec in records.values():
   stream.seek(rec['file_offset']);b=stream.read(rec['size']);assert hashlib.sha256(b).hexdigest()==rec['bytes_sha256']
   # Only the target, original app accessor and original non-Core math are executed.
   name=funcs.get(rec['address'],'')
   if rec['address']==t['address'] or name.startswith('__aeabi') or name in ('__nesf2','__eqsf2','__cmpsf2') or ('SurfaceInputComponent11getPotValue' in name):allowed.append((rec['address'],rec['address']+rec['size']))
   checked.append({k:rec[k] for k in ('address','size','file_offset','bytes_sha256')})
  allowed.append((t['address'],t['address']+t['size']))
  libc=ctypes.CDLL(None);libc.strcmp.argtypes=[ctypes.c_char_p,ctypes.c_char_p];libc.strcmp.restype=ctypes.c_int
  cases=[]
  if CASE==1:inputs=[[mask,0,0,0,0,0,0,h] for mask in (0,1,2) for h in ('-','68656c6c6f','d0bcd0b8d0ba')]
  elif CASE==2:inputs=[[mask,index&0xffffffff,sense&0xffffffff,hw,0,0,0,'-'] for mask,index,sense,hw in itertools.product(range(4),(-2147483648,-1,7,8,9,2147483647),(-1,0,1),(0,8,0xffffffff))]
  elif CASE==3:inputs=[[0,bits(maximum),0,0,msg,0,match,'-'] for maximum,msg,match in itertools.product((-1.,0.,1.),(0,3,4),(0,1))]
  elif CASE==4:inputs=[[mask,bits(value),bits(.25),0,0,0,0,'-'] for mask,value in itertools.product(range(4),(-2.,-0.,0.,.5,1.,2.))]
  elif CASE==5:inputs=[[mask,bits(value),bits(option),0,0,0,0,'-'] for mask,value,option in itertools.product(range(4),(-1.,0.,1.,2.),(-2.,.25,3.))]
  elif CASE==6:inputs=[[dest,bits(positive),0,0,0,stop,gap,'-'] for dest,positive,stop,gap in itertools.product((0,1),(1.,.25),(101,103,104),(0,1))]
  else:inputs=[[1,bits(v),0,0,0,0,0,'-'] for v in (-100.,-1.,0.,1.,2.,3.,4.,5.,6.,7.,8.,9.,10.,11.,12.,14.,16.,20.,25.,30.,40.,41.02,50.,100.,200.)]+[[present,bits(7.),0,mode,0,0,0,'-'] for present,mode in itertools.product((0,1),(0,1,0xffffffff))]
  for c in inputs:
   mask,a,b,mode,msg,stop,typ,text=c;p=subprocess.Popen([str(Path(exe).resolve()),'--provider'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True);p.stdin.write(' '.join(map(str,c))+'\n');p.stdin.flush()
   def rpc(s):p.stdin.write(s+'\n');p.stdin.flush();out=p.stdout.readline().strip();assert out,('provider failure',s,p.poll());return out
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);mapped=set()
   def maprange(a,n):
    for page in range(a&~4095,(a+n+4095)&~4095,4096):
     if page not in mapped:u.mem_map(page,4096);mapped.add(page)
   for addr,data in sections:maprange(addr,len(data));u.mem_write(addr,data)
   for addr,n in ((0x1000000,0x40000),(0x1100000,0x40000),(0x1200000,0x40000),(0x2000000,0x10000),(0x3000000,0x10000)):maprange(addr,n)
   obj=0x1000000;u.mem_write(obj,struct.pack('<I',0x3002000));u.mem_write(0x3002000+24,struct.pack('<I',0x3003000));u.mem_write(0x3002000+168,struct.pack('<I',0x3003100))
   # Typed ARM layout bridge only, actual virtual services execute in CCL RPC.
   for i in range(20):
    ptr=0x1100000+i*4096;u.mem_write(ptr,struct.pack('<I',0x3000000));u.mem_write(ptr+12,struct.pack('<I',0x1200000+i*4096))
   for slot,addr in ((0x44,0x3001000),(0x3c,0x3001100),(0x58,0x3001200),(0x74,0x3001300)):u.mem_write(0x3000000+slot,struct.pack('<I',addr))
   u.mem_write(0x1001000,bytes.fromhex(text) + b'\0' if text!='-' else b'\0')
   u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,0x1001000 if CASE==1 else a if CASE==4 else 0x1002000);u.reg_write(UC_ARM_REG_R2,17 if CASE==1 else a if CASE==2 else msg);u.reg_write(UC_ARM_REG_R3,b)
   if CASE==3:
    u.reg_write(UC_ARM_REG_R1,0x1100000);name=bytes.fromhex(rpc('NAME '+str(0x1100000)));u.mem_write(0x1200000+8,name+b'\0')
   if CASE==2:u.mem_write(obj+0x134,struct.pack('<II',0x1003000,1 if mask else 0));u.mem_write(0x1003000,struct.pack('<I',0 if mask==1 else 0x1004000))
   if CASE==7:u.reg_write(UC_ARM_REG_R1,a);u.mem_write(obj+0x88,struct.pack('<I',mode))
   u.reg_write(UC_ARM_REG_SP,0x2008000);u.reg_write(UC_ARM_REG_LR,0x1008000)
   trace=[];counts=collections.Counter();writes=[]
   def readstring(address):
    data=bytearray()
    for i in range(512):
     byte=bytes(u.mem_read(address+i,1))
     if byte==b'\0':return bytes(data)
     data+=byte
    raise AssertionError('unterminated string')
   def code(uc,address,size,data):
    if any(lo<=address<hi for lo,hi in allowed):counts[address]+=1;return
    r0,r1,r2,r3=[uc.reg_read(reg) for reg in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)];name=funcs.get(address,'');op='';out=0
    if address==0x3003000:op='FIND '+readstring(r1).hex()
    elif address==0x3003100:op='HW'
    elif address==0x3001000:op=f'VAL {r0}'
    elif address==0x3001100:op=f'MAX {r0}'
    elif address==0x3001200:op=f'SET {r0} {r1} {r2}'
    elif address==0x3001300:op=f'STR {r0} {readstring(r1).hex() or "-"} {r2}'
    elif 'Component17getParameterByTag' in name:op=f'TAG {r1}'
    elif 'Component12paramChanged' in name:op=f'BASE {r1} {r2}'
    elif name.startswith('__dynamic_cast'):op=f'CAST {r0}'
    elif name.startswith('strcmp'):out=libc.strcmp(readstring(r0),readstring(r1))&0xffffffff
    elif 'Parameter8getTitle' in name:
     h=rpc(f'TITLE {r0}');data=bytes.fromhex(h) if h!='-' else b'';out=r0+1024;u.mem_write(out,data+b'\0')
    else:raise AssertionError(('unbound original execution',hex(address),name,CASE))
    if op:out=int(rpc(op))
    trace.append(dict(site=uc.reg_read(UC_ARM_REG_LR)-4,address=address,symbol=name,operation=op,args=[r0,r1,r2,r3],return_word=out));uc.reg_write(UC_ARM_REG_R0,out);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,lambda uc,access,addr,size,value,unused:writes.append([addr,size,value]))
   u.emu_start(t['address'],0x1008000,count=150000);assert u.reg_read(UC_ARM_REG_PC)==0x1008000,('instruction limit',CASE,c)
   if CASE==7:rpc('RETURN '+str(u.reg_read(UC_ARM_REG_R0)))
   if CASE==6:assert bytes(u.mem_read(obj+0xc8,1))==b'\0'
   report=rpc('REPORT');p.stdin.close();assert p.wait(timeout=5)==0
   assert all(0x2000000<=addr<0x2010000 or (CASE==6 and addr==obj+0xc8 and size==1) for addr,size,value in writes)
   cases.append(dict(inputs=c,expected=report,calls=trace,executed_counts={str(a):n for a,n in sorted(counts.items())},memory_writes=writes,return_word=u.reg_read(UC_ARM_REG_R0)))
 return dict(elf_sha256=t['original_elf_sha256'],mangled=t['mangled'],address=t['address'],size=t['size'],section=12,file_offset=offset,range_sha256=hashlib.sha256(body).hexdigest(),verified_ranges=checked,unicorn_version=unicorn.__version__,cases=cases,domain=contract['domain'],limitations=['Actual pinned CCL RPC replaces Core execution at typed ARM boundary; no original Core binary/layout equivalence.','Input domains finite, metadata/registry stable, no callback mutation, hardware, allocation failure, exception or race claims.'])
if __name__=='__main__':
 import sys
 Path(sys.argv[2]).write_text(json.dumps(generate(sys.argv[1]),indent=2)+'\n')
