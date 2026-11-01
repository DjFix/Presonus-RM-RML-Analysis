#!/usr/bin/env python3
"""Original ARM target execution with explicit, bounded external-call capture."""
import json,hashlib,pathlib,struct,itertools,datetime,time
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
BASE=pathlib.Path('uc-library/candidates/graph-live-trial-05-permissions')
ELF=pathlib.Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
H=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
packets=[pathlib.Path(f'temp/recovery-work/graph-live-trial-05/trial05_permissions_{i}-packet') for i in range(1,6)]
S=0x10000000; OBJ=S+0x1000; OUT=S+0x2000; SELECT=S+0x3000; MIX=S+0x4000; OTHER=S+0x5000; VT=S+0x6000; CALLBACK=S+0x7000; STOP=S+0x8000; OWNER=S+0x9000
p32=lambda x:struct.pack('<I',x)
with ELF.open('rb') as f:
 e=ELFFile(f); segments=[(x['p_vaddr'],x['p_memsz'],x.data()) for x in e.iter_segments() if x['p_type']=='PT_LOAD']; sections=list(e.iter_sections()); symbols={s.name:s for tab in sections if tab['sh_type']=='SHT_SYMTAB' for s in tab.iter_symbols()}
 ranges=[]
 for p in packets:
  m=json.loads((p/'context.json').read_text()); o=m['originals'][0]['original']; assert H(ELF)==o['elf']; s=symbols[o['mangled']]; assert s['st_value']==o['address'] and s['st_size']==o['size']; sec=sections[s['st_shndx']]; off=sec['sh_offset']+o['address']-sec['sh_addr']; f.seek(off); data=f.read(o['size']); nc=json.loads((p/'native-context.json').read_text()); body=next(v for v in nc['bodies'].values() if v['address']==o['address']); assert hashlib.sha256(data).hexdigest()==body['bytes_sha256']; ranges.append(dict(o,file_offset=off,section_name=sec.name,range_sha256=hashlib.sha256(data).hexdigest()))
def execute(target,args):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 pages=set()
 for a,n,b in segments:
  for x in range(a&~4095,(a+n+4095)&~4095,4096):
   if x not in pages:u.mem_map(x,4096);pages.add(x)
  u.mem_write(a,b)
 u.mem_map(S,0x20000)
 def w(a,v):u.mem_write(a,p32(v))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def c(a):
  out=bytearray()
  for i in range(1024):
   b=u.mem_read(a+i,1)
   if b==b'\0':return out.decode('ascii')
   out+=b
  raise ValueError('unterminated')
 u.mem_write(OUT,b'keep\0'+b'\x7e'*123)
 w(OBJ+0x88,MIX);w(OBJ+0x8c,OTHER);w(MIX,VT);w(OTHER,VT);w(VT+0x70,CALLBACK);w(VT+0x74,CALLBACK+4);w(OBJ+0x94,OWNER)
 w(OBJ+0xf8,SELECT if args.get('selected') else 0);u.mem_write(SELECT+0xd8,args.get('name','client').encode()+b'\0')
 u.mem_write(OBJ+0x98,bytes([args.get('restricted',0)]));u.mem_write(OBJ+0x108,bytes([args.get('dirty',0)]))
 trace=[]
 def hook(uc,pc,size,data):
  if pc==STOP:uc.emu_stop();return
  r0,r1,r2=[uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]]
  if pc in (CALLBACK,CALLBACK+4):
   if pc==CALLBACK:
    trace.append(['toString','mix' if r0==MIX else 'other',r2]); payload=args['payload'].encode(); uc.mem_write(r1,payload[:r2-1]+b'\0')
   else:trace.append(['fromString','mix' if r0==MIX else 'other',c(r1),r2])
  elif pc==0x50bac:trace.append(['getFileName',r0==OBJ,r1==OUT,r2==SELECT+0xd8,c(r2)])
  elif pc==0x512b0:trace.append(['loadSelectedDevice',r0==OBJ,int(uc.mem_read(OBJ+0x108,1)[0])])
  elif pc==0x30a30:trace.append(['devicePermissionsChanged',r0==OWNER,r1==OBJ,int(uc.mem_read(OBJ+0x108,1)[0])])
  else:return
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook)
 u.reg_write(UC_ARM_REG_SP,S+0x1f000);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,args.get('enabled',0) if target==4 else OUT)
 u.emu_start(ranges[target]['address'],STOP+4,count=1000)
 assert u.reg_read(UC_ARM_REG_PC)==STOP
 return {'trace':trace,'output_hex':bytes(u.mem_read(OUT,128)).hex(),'dirty':int(u.mem_read(OBJ+0x108,1)[0])}
cases=[]
for selected,name in itertools.product([False,True],['client','', 'x'*63]):cases.append({'target':0,'input':dict(selected=selected,name=name)})
for t,payload in itertools.product([1,2],['','FOH','Aux 1/2','x'*127,'z'*180]):cases.append({'target':t,'input':dict(payload=payload)})
for dirty in [0,1,0x7f,0xff]:cases.append({'target':3,'input':dict(dirty=dirty)})
for enabled,restricted in itertools.product([False,True],[0,1,0x7f,0xff]):cases.append({'target':4,'input':dict(enabled=enabled,restricted=restricted)})
for i,x in enumerate(cases):
 x['case_id']=i;x['start_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic();x['observed']=execute(x['target'],x['input']);x['duration_seconds']=time.monotonic()-tick;x['end_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
proof={'producer_sha256':H(__file__),'unicorn_version':unicorn.__version__,'executed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elf_path':str(ELF),'elf_sha256':H(ELF),'ranges':ranges,'cases':cases,'boundaries':'External calls captured, toString provider stub writes caller-supplied payload with size bound. getFileName/loadSelectedDevice/devicePermissionsChanged captured and return without further behavior. No Core instructions recovered/executed.'}
(BASE/'native-fixtures.json').write_text(json.dumps(proof,indent=2)+'\n')
print('original ARM observations:',len(cases))
