"""Bound original ARM execution; external calls are explicit observation boundaries."""
import argparse,hashlib,json,pathlib,struct
from functools import cache
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=pathlib.Path(__file__).resolve().parents[5]
ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
PACK=ROOT/'temp/recovery-work/graph-live-trial-08/batch03/packets'

@cache
def verified_input(i):
 n=json.loads((PACK/f'trial08_mixer_{i}/native-context.json').read_text()); body=next(iter(n['bodies'].values()))
 raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 assert hashlib.sha256(raw[body['file_offset']:body['file_offset']+body['size']]).hexdigest()==body['bytes_sha256']
 with ELF.open('rb') as f:
  e=ELFFile(f)
  section=e.get_section(body['section_index'])
  assert section['sh_type']!='SHT_NOBITS'
  assert section['sh_offset']+body['address']-section['sh_addr']==body['file_offset']
  identity=n['nodes'][n['roots'][0]]['metadata']
  symbols=e.get_section_by_name('.symtab').get_symbol_by_name(identity['mangled'])
  assert any(v['st_value']==body['address'] and v['st_size']==body['size'] and v['st_shndx']==body['section_index'] for v in symbols)
  segments=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
 return body,segments

@cache
def runtime_ranges():
 supplement=ROOT/'evidence/recovery/2026-11-02/dependency-graph/live-trial-08-10x10/scoped-data/mixer-runtime-aliases02.json'
 receipt=json.loads((ROOT/'evidence/recovery/2026-11-02/dependency-graph/live-trial-08-10x10/context-expansions/mixer-fcmpeq.json').read_text())
 assert receipt['returncode']==0
 expansion=json.loads((ROOT/'temp/recovery-work/graph-live-trial-08/expansions/mixer-fcmpeq/native-context.json').read_text())
 body=next(iter(expansion['bodies'].values()))
 records=json.loads(supplement.read_text())['symbols']+[dict(mangled='__aeabi_fcmpeq',address=body['address'],size=body['size'],file_offset=body['file_offset'],bytes_sha256=body['bytes_sha256'])]
 raw=ELF.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 with ELF.open('rb') as f:
  elf=ELFFile(f);table=elf.get_section_by_name('.symtab')
  for rec in records:
   symbols=table.get_symbol_by_name(rec['mangled'])
   sym=next(x for x in symbols if x['st_value']==rec['address'] and x['st_size']==rec['size'])
   section=elf.get_section(sym['st_shndx'])
   assert section['sh_type']!='SHT_NOBITS'
   assert section['sh_offset']+rec['address']-section['sh_addr']==rec['file_offset']
   assert hashlib.sha256(raw[rec['file_offset']:rec['file_offset']+rec['size']]).hexdigest()==rec['bytes_sha256']
 return [(r['address'],r['address']+r['size']) for r in records]

def observe(i,c):
 body,segments=verified_input(i)
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x700000);u.mem_map(0x800000,0x300000)
 for address,data in segments:u.mem_write(address,data)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 T,V,A,P,F=0x800000,0x802000,0x803000,0x820000,0x804000
 trace=[];stubs={};stop=0x900ff0
 def stub(addr,name,fn):stubs[addr]=(name,fn)
 def ret(v=0):u.reg_write(UC_ARM_REG_R0,v)
 def ch(j):return 0x810000+j*0x1000
 count=c.get('count',0)
 w(T,0x830000);w(T+0x120,A);w(T+0x124,count);w(T+0x2b0,A);w(T+0x2b4,count)
 w(V+4,A);w(V+8,count)
 for j in range(count):
  w(A+4*j,ch(j));w(ch(j),0x831000);w(ch(j)+0xfc,0x840000+j*0x100);w(0x840000+j*0x100,0x832000)
 w(P+12,P+0x100);w(P+0x104,c.get('tag',42));w(F,c.get('filter',7))
 regs=[T,0,0,0]
 if i==1:
  regs=[T,P,c.get('flags',0),0];stub(0xf6c18,'server.paramChanged',lambda:ret())
 if i==2:
  w(0x830008,0x900000);stub(0x900000,'deleting-slot-request',lambda:ret())
 if i==3:
  regs=[T,P,0,0]
  stub(0x119c4c,'getParameterByTag',lambda:ret(P if u.reg_read(UC_ARM_REG_R0)==ch(c.get('match',-1)) else 0))
 if i in (4,10):
  regs=[T,V,F,0];w(V+0x14,c.get('attributes',0))
  w(0x830080,0x900080);w(0x830020,0x900020);w(0x830024,0x900024)
  stub(0x900080,'filter',lambda:ret(0))
  def visitor():
   a=u.reg_read(UC_ARM_REG_R1)
   trace.append(['visitor-state',u.mem_read(a,1).hex(),*[r(a+o) for o in ((32,36,40,44,48) if i==4 else (32,36,40,44))]])
   ret()
  stub(0x900020,'restore',visitor);stub(0x900024,'remember',visitor)
  stub(0x121a08,'provider.removeAll',lambda:ret());stub(0x117950,'provider.builder',lambda:ret());stub(0x2f178,'provider.vectorDestroy',lambda:ret())
 if i==5:
  regs=[T,ch(0),0,0]
  for off,key in [(0x364,'enabled'),(0x366,'active')]:u.mem_write(T+off,bytes([c.get(key,0)]))
  w(ch(0)+0x16c,c.get('excluded',0));w(ch(0)+0xf8,0x840000);w(ch(0)+0xe8,0x841000);w(0x840000,0x832000);w(0x841000,0x833000)
  w(0x833044,0x900044);w(0x832058,0x900058)
  stub(0x900044,'getValue',lambda:ret(c.get('bits',0)))
  runtime_ranges()
  stub(0x900058,'setValue',lambda:ret())
 if i==6:
  regs=[T,0x860000,c.get('index',0),0];w(0x860000,0x834000);w(0x83402c,0x90002c);w(0x830084,0x900084)
  stub(0x116a38,'provider.debug',lambda:ret());stub(0x90002c,'presetType',lambda:ret(0x861000 if c.get('type',0) else 0))
  u.mem_write(0x861000,(b'scene\0' if c.get('type')==1 else b'other\0'))
  stub(0xaf70,'strcmp',lambda:ret(0 if c.get('type')==1 else 1));stub(0x900084,'command',lambda:ret())
 if i==7:
  regs=[T,c.get('first',0),c.get('second',0),0];w(0x832058,0x900058);stub(0x900058,'select.setValue',lambda:ret())
 if i in (8,9):regs=[T,ch(c.get('match',-1)) if c.get('match',-1)>=0 else 0x880000,V,0]
 def hook(uc,address,size,data):
  if address==stop:uc.emu_stop();return
  if i==5 and address==0x1578e0:trace.append(['float.equalZero.native',uc.reg_read(UC_ARM_REG_R0),uc.reg_read(UC_ARM_REG_R1)])
  if address in stubs:
   name,fn=stubs[address];trace.append([name,*[uc.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]])
   fn();uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  assert body['address']<=address<body['address']+body['size'] or (i==5 and any(a<=address<b for a,b in runtime_ranges())),('out-of-scope native execution',hex(address))
 u.hook_add(UC_HOOK_CODE,hook)
 for reg,val in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),regs):u.reg_write(reg,val)
 u.reg_write(UC_ARM_REG_SP,0xa10000);u.reg_write(UC_ARM_REG_LR,stop)
 u.emu_start(body['address'],stop,count=10000)
 assert u.reg_read(UC_ARM_REG_PC)==stop
 return {'packet':i,'input':c,'r0':u.reg_read(UC_ARM_REG_R0),'trace':trace,'flags':[u.mem_read(T+x,1)[0] for x in (0x11a,0x36a)]}

def cases():
 yield 1,{'flags':17};yield 2,{}
 for count in (0,1,2,3,4,5):
  for match in range(-1,count):
   for i in (3,8,9):yield i,{'count':count,'match':match}
 for attrs in (0,1,3):yield 4,{'attributes':attrs}
 for enabled in (0,1):
  for active in (0,1):
   for excluded in (0,1):
    for bits in (0,0x80000000,0x3f800000,0xbf800000,0x7fc00000,0x7f800000,0xff800000,1):yield 5,dict(enabled=enabled,active=active,excluded=excluded,bits=bits)
 for t in (0,1,2):yield 6,{'type':t,'index':5}
 for count in (0,1,4):yield 7,{'count':count,'first':17,'second':-3}
 yield 10,{'attributes':3}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);args=a.parse_args()
 out=[observe(i,c) for i,c in cases()];pathlib.Path(args.out).write_text(json.dumps(out,indent=2)+'\n');print(len(out),'original ARM boundary observations')
