"""Exact ARM app execution; external Core/libc/allocator boundaries explicit."""
import ctypes, hashlib, json, struct, re
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4]; T=Path(__file__).resolve().parent
DISPATCH=Path('/home/rs/projects/opencs/ai-line-analysis')/'temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/avb_stream_control_sol61/packet-sol61/DISPATCH.json'

def catalog():
 assert hashlib.sha256(DISPATCH.read_bytes()).hexdigest()=='3111cefeaffd1a7ca6adc8419e5c6a162af95523ce302bb8855fdac9616b4655'
 d=json.loads(DISPATCH.read_text()); rows=[]
 message=d['workers'][0]['arguments']['message']
 assert hashlib.sha256(message.encode()).hexdigest()=='e5367f048e113d8980e9e1669f263938e8a0f55ce88488e1fd86b14b00f3938a'
 hashes=dict(re.findall(r'(temp/\S+/CONTEXT.json) ([a-f0-9]{64})',message))
 for p in d['workers'][0]['packets']:
  assert hashlib.sha256((R/p).read_bytes()).hexdigest()==hashes[p]
  c=json.loads((R/p).read_text())
  for x in c['originals']:rows.append((c['task']['id'],x['original']))
 return rows

def cases(op,capacity):
 base=dict(op=op,listeners=[],talkers=[],args=[],processing=2,status=1)
 def c(**kw):return dict(base,**kw)
 if op=='sendAvbSysex':return [c(args=[0x23,1,-1],payload=[0x5a])] + [c(args=[cmd,n,status],payload=[(i*17+cmd)&255 for i in range(max(n,0))]) for cmd in [0x23,0x31] for n in [0,1,15,30,31] for status in [0,1,2]]
 if op=='accepts':return [c(args=[n,cmd]) for n in [0,1,2,3,255] for cmd in range(256)]
 if op=='macAddressToString':return [c(text=prefix,args=[v]) for prefix in ['', 'prefix:', 'x'*250] for v in [0,1,0x112233445566,0xffffffffffff,0xffff112233445566]]
 if op=='macAddressStringToLong':return [c(text=s) for s in ['', '01:23:45:67:89:AB','ab-cd-ef-01-23-45','FF','1:2:3:4:5:6','ZZ:AA: 1:-1:+1:0x','01:02','12x34x56x78x9AxBC']]
 if op=='resizeListener':return [c(args=[i,ch]) for i in [0,3,255] for ch in [0,1,16,255]]
 if op=='resizeTalker':return [c(args=[i,ch],talkers=ts) for i in [0,255] for ch in [0,16,255] for ts in [[],[[2,8]],[[0,255],[2,2]],[[4,-1]]]]
 if op=='setAudioClockToListener':return [c(args=[i],listeners=[[i,0,0,0]] if i>=0 else []) for i in [-1,0,3,248,255]]
 if op=='publish':return [c(args=[i,b]) for i in [0,255] for b in [0,1]]
 if op=='subscribe':return [c(args=[i,v]) for i in [0,255] for v in [0,1,0x1122334455667788,0xffffffffffffffff]]
 if op=='configureMasterFirewireRecording':return [c(args=[0]),c(args=[1])]
 if op=='startAvb':return [c(processing=p,args=[i,255,b]) for p in [-1,0,1,2] for i in [0,255] for b in [0,1]]
 if op=='stopAvb':return [c(processing=p) for p in [-1,0,1,2]]
 if op=='removeAllListeners':return [c(listeners=ls) for ls in [[],[[0,1,2,3]],[[0,1,2,3],[2,4,5,6],[0,7,8,9]]]]
 if op=='removeListener':return [c(listeners=ls,args=[i]) for ls in [[],[[0,1,2,3]],[[0,1,2,3],[2,4,5,6],[0,7,8,9]]] for i in [-1,0,1,2,99]]
 if op=='removeTalker':return [c(talkers=ls,args=[i]) for ls in [[],[[0,3]],[[0,3],[2,6],[0,9]]] for i in [-1,0,1,2,99]]
 if op=='addListener':return [c(listeners=ls,args=[0x112233445566,0x7788,ch]) for ls in [[],[[1,1,2,3]],[[0,1,2,3],[0,4,5,6]],[[i,i,i,2] for i in range(capacity)],[[i,i,i,2] for i in range(capacity+1)]] for ch in [0,8,255]]
 if op=='addTalker':return [c(talkers=ts,args=[ch]) for ts in [[],[[1,3]],[[0,3],[0,5]],[[i,2] for i in range(capacity)],[[i,2] for i in range(capacity+1)]] for ch in [0,8,255]]
 raise ValueError(op)

def generate(provider, task_filter=None):
 bridge=ctypes.CDLL(str(provider));bridge.avb_clock_bridge.argtypes=[ctypes.c_longlong];bridge.avb_clock_bridge.restype=ctypes.c_longlong;bridge.avb_format_bridge.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint];bridge.avb_scan_bridge.argtypes=[ctypes.c_char_p];bridge.avb_scan_bridge.restype=ctypes.c_ulonglong
 fixtures=[];ranges=[];loaded={}
 for task,o in catalog():
  if task_filter and task != task_filter:continue
  role=o['role'];p=R/o['elf_path']; data=p.read_bytes()
  if o['elf'] not in loaded:
   assert hashlib.sha256(data).hexdigest()==o['elf']
   with p.open('rb') as f:
    e=ELFFile(f);symbols={s.name:dict(s.entry) for s in e.get_section_by_name('.symtab').iter_symbols()};segs=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD'];secs=[dict(s.header) for s in e.iter_sections()]
   loaded[o['elf']]=(symbols,segs,secs)
  symbols,segs,secs=loaded[o['elf']];s=symbols[o['mangled']];sec=secs[s['st_shndx']];off=sec['sh_offset']+s['st_value']-sec['sh_addr'];body=data[off:off+s['st_size']]
  assert (off,len(body),body.hex(),hashlib.sha256(body).hexdigest())==(o['file_offset'],o['size'],o['range_hex'],o['range_sha256'])
  assert s['st_shndx']==o['section']
  op=next(k for k in ['removeAllListeners','removeListener','removeTalker','resizeListener','resizeTalker','setAudioClockToListener','addListener','addTalker','sendAvbSysex','macAddressStringToLong','macAddressToString','configureMasterFirewireRecording','subscribe','publish','startAvb','stopAvb','accepts'] if k in o['mangled'])
  ranges.append(dict(o,task_id=task,section_verified=True))
  assigned=[(x['address'],x['address']+x['size']) for _,x in catalog() if x['elf']==o['elf']]
  extra=[(v['st_value'],v['st_value']+v['st_size']) for k,v in symbols.items() if k.startswith('_ZN8Presonus3AVB') and any(z in k for z in ['AvbListenerC','AvbTalkerC','AvbListenerD','AvbTalkerD','reverseEndian'])]
  byaddress={v['st_value']:k for k,v in symbols.items() if v['st_value']}
  for inp in cases(op,16 if role=='client' else 4):
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
   for addr,b in segs:u.mem_write(addr,b)
   obj=0x600000;payload=0x650000;stack=0x8ff000;sentinel=0xf00000;heap=[0x700000];deleted=[];allocations=[];packets=[];visited=set();boundary=[]
   def rd(a,n=4):return int.from_bytes(u.mem_read(a,n),'little')
   def wr(a,v,n=4):u.mem_write(a,int(v & ((1<<(n*8))-1)).to_bytes(n,'little'))
   def reg(i):return u.reg_read(UC_ARM_REG_R0+i)
   def ret(v=None):
    if v is not None:u.reg_write(UC_ARM_REG_R0,v&0xffffffff)
    u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   def nodes(which,ls):
    head=0x80 if which=='l' else 0x74;start=0x610000 if which=='l' else 0x611000;ss=0x620000 if which=='l' else 0x630000
    for i,st in enumerate(ls):
     a=ss+i*64;node=start+i*16;wr(node,a);wr(node+4,start+(i+1)*16 if i+1<len(ls) else 0);wr(node+8,start+(i-1)*16 if i else 0);wr(a,st[0],1)
     if which=='l':wr(a+8,st[1],8);wr(a+16,(st[1]<<16)|st[2],8);wr(a+24,st[2],2);wr(a+28,st[3])
     else:wr(a+8,st[1])
    wr(obj+head,start if ls else 0);wr(obj+head+4,start+(len(ls)-1)*16 if ls else 0)
   nodes('l',inp['listeners']);nodes('t',inp['talkers']);wr(obj+0x6c,inp['processing']);wr(obj+5,0,1);wr(obj,0x640000);wr(0x640008,0xe00000)
   args=inp['args'];u.reg_write(UC_ARM_REG_R0,obj)
   for i,v in enumerate(args[:3]):u.reg_write(UC_ARM_REG_R1+i,v&0xffffffff)
   if op=='addListener':
    v,suffix,ch=args;u.reg_write(UC_ARM_REG_R2,v&0xffffffff);u.reg_write(UC_ARM_REG_R3,v>>32);wr(stack,suffix);wr(stack+4,ch)
   if op=='subscribe':u.reg_write(UC_ARM_REG_R2,args[1]&0xffffffff);u.reg_write(UC_ARM_REG_R3,args[1]>>32)
   if op=='setAudioClockToListener':u.reg_write(UC_ARM_REG_R1,0x620000 if args[0]>=0 else 0)
   if op in ['removeListener','removeTalker']:
    index=args[0];ss=0x620000 if op=='removeListener' else 0x630000;u.reg_write(UC_ARM_REG_R1,0 if index<0 else ss+index*64)
   if op=='sendAvbSysex':
    u.mem_write(payload,bytes(inp['payload']) or b'\0');u.reg_write(UC_ARM_REG_R1,args[0]);u.reg_write(UC_ARM_REG_R2,payload);u.reg_write(UC_ARM_REG_R3,args[1])
   if op=='accepts':
    wr(payload+0x108,args[0],1);wr(payload+9,args[1],1);u.reg_write(UC_ARM_REG_R1,payload)
   if op.startswith('macAddress'):
    u.mem_write(payload,inp['text'].encode()+b'\0');u.reg_write(UC_ARM_REG_R0,payload)
    if op=='macAddressToString':u.reg_write(UC_ARM_REG_R2,args[0]&0xffffffff);u.reg_write(UC_ARM_REG_R3,args[0]>>32)
   def string(a):return bytes(u.mem_read(a,256)).split(b'\0',1)[0]
   def code(uc,pc,n,_):
    visited.add(pc)
    name=byaddress.get(pc,'')
    if 'sendAvbSysex' in name and op!='sendAvbSysex':
     packets.append([reg(1),list(u.mem_read(reg(2),reg(3))) if reg(3) else []]);boundary.append('sendAvbSysex');ret(-1 if op=='startAvb' and inp['processing']<=0 else 0);return
    if any(lo<=pc<hi for lo,hi in assigned+extra):return
    boundary.append(name or hex(pc))
    if pc==0xe00000:
     packet=reg(1);length=rd(packet+0x108,1);packets.append(list(u.mem_read(packet+8,length)));ret();return
    if name=='_Znwj' or pc==(0xa90c if role=='client' else 0xa7e4):
     a=heap[0];allocations.append([reg(0),a]);heap[0]+=0x100;u.mem_write(a,b'\0'*256);ret(a);return
    if name=='_ZdlPv' or pc==(0xad5c if role=='client' else 0xac10):deleted.append(reg(0));ret();return
    if 'LinkedList' in name and 'remove' in name:
     base=reg(0);target=rd(reg(1));node=rd(base+4)
     while node and rd(node)!=target:node=rd(node+4)
     if node:
      nxt=rd(node+4);prev=rd(node+8);wr(prev+4 if prev else base+4,nxt);wr(nxt+8 if nxt else base+8,prev)
     ret(1 if node else 0);return
    if pc in [0xaba0,0xaa60]:u.mem_write(reg(0),bytes([reg(1)&255])*reg(2));ret(reg(0));return
    if pc in [0xaffc,0xae68]:u.mem_write(reg(0),bytes(u.mem_read(reg(1),reg(2))));ret(reg(0));return
    if pc in [0x1178a4,0x116908]:u.reg_write(UC_ARM_REG_R1,0);ret(123000000);return
    if pc in [0x1878a8,0x157a08]:v=reg(0)|(reg(1)<<32);assert (reg(2)|(reg(3)<<32))==1000000;q=bridge.avb_clock_bridge(v);u.reg_write(UC_ARM_REG_R1,q>>32);ret(q);return
    if 'waitAck' in name or pc in [0xcd5e0,0xa4ce4]:wr(obj+5,max(args[2],0),1);ret(0 if args[2]<0 else 0x23);return
    if pc in [0xb02c,0xae98]:ret(len(string(reg(0))));return
    if pc in [0xb164,0xafdc] and op=='macAddressStringToLong':
     assert string(reg(1))==b'%llx'
     wr(reg(2),bridge.avb_scan_bridge(string(reg(0))),8);ret(1);return
    if 'appendFormat' in name or pc in [0x24490]:
     buf=ctypes.create_string_buffer(string(reg(0)),256);bridge.avb_format_bridge(buf,string(reg(1)),reg(2));u.mem_write(reg(0),buf.raw);ret(reg(0));return
    raise RuntimeError((op,role,hex(pc),name,[reg(i) for i in range(4)]))
   u.hook_add(UC_HOOK_CODE,code);u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,sentinel)
   u.emu_start(o['address'],sentinel,count=20000)
   assert u.reg_read(UC_ARM_REG_PC)==sentinel,(op,role,'instruction budget')
   def states(which):
    a=rd(obj+(0x80 if which=='l' else 0x74));out=[]
    while a:
     st=rd(a);out.append([rd(st,1),rd(st+8,8),rd(st+24,2),ctypes.c_int32(rd(st+28)).value] if which=='l' else [rd(st,1),ctypes.c_int32(rd(st+8)).value]);a=rd(a+4)
    return out
   result=ctypes.c_int32(reg(0)).value
   if op in ['addListener','addTalker']:result=rd(reg(0),1) if reg(0) else -1
   if op=='macAddressStringToLong':result=(reg(0)|(reg(1)<<32))&0xffffffffffff
   if op in ['removeListener','removeTalker','removeAllListeners','stopAvb','macAddressToString']:result=None
   fixtures.append(dict(task_id=task,elf=o['elf'],role=role,input=inp,output=dict(result=result,deleted_streams=sum(1 for p in deleted if 0x620000<=p<0x620000+64*len(inp['listeners']) or 0x630000<=p<0x630000+64*len(inp['talkers'])),packets=packets,listeners=states('l'),talkers=states('t'),processing=ctypes.c_int32(rd(obj+0x6c)).value,text=string(payload).decode() if op.startswith('macAddress') else None),native_allocations=allocations,native_deletes=deleted,native_sites=len(visited),target_sites=sorted(pc for pc in visited if o['address']<=pc<o['address']+o['size']),boundaries=sorted(set(boundary))))
 return dict(version=1,ranges=ranges,cases=fixtures,limitations=['Core linked-list removal boundary is a transparent valid-list test model, not original Core execution; source uses real pinned CCL.','Core formatting boundary invokes actual pinned CCL appendFormat in independent provider bridge; libc scan bridge is actual host sscanf with native format.','Native send virtual post and waitAck are explicit typed captures: packet bytes and status0/1/2 or timeout0 observed, not original receiver/wait execution. Portable replay executes actual canonical receivers/CCL waits and UART/SPI IO providers offline. Other callers capture send as an explicit boundary; exact send body is tested separately.',
 'Allocator/delete calls captured offline; no host commands, networking or device IO. App constructors/destructors and reverseEndian execute original instructions.','Uninitialized MAC parser upper16 return bits excluded; explicit source zero initialization. Unsafe negative send lengths and malformed native states excluded.'])
if __name__=='__main__':
 import sys
 Path(sys.argv[2]).write_text(json.dumps(generate(Path(sys.argv[1])),indent=2)+'\n')
