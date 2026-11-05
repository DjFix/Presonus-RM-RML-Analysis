"""Execute only hash-bound PanControl instructions; all Core/runtime entries modeled."""
import pathlib,json,hashlib,struct,itertools
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=pathlib.Path(__file__).resolve().parents[5]
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
BASE=ROOT/'temp/recovery-work/rolling200-02'
PACK=BASE/'implementation-plan01/packets-stage04-01/packets'
SPECS={1:PACK/'rolling200_02_impl_w05_01',2:PACK/'rolling200_02_impl_w05_02','linked':BASE/'expand-stage04-w05_01-isLinked01','compute':BASE/'expand-stage04-w05_01-computeLinkedPanValue01','stereo':BASE/'expand-stage04-w05_02-isStereo01','side':BASE/'expand-stage04-w05_02-isRightSideOfLink01'}
RAW=ELF.read_bytes();assert hashlib.sha256(RAW).hexdigest()==SHA
RANGES={}
for key,path in SPECS.items():
 ctx=json.load(open(path/'native-context.json'));b=ctx['bodies'][ctx['roots'][0]]
 with ELF.open('rb') as f:
  sec=ELFFile(f).get_section(b['section_index']);off=sec['sh_offset']+b['address']-sec['sh_addr']
 assert off==b['file_offset'] and hashlib.sha256(RAW[off:off+b['size']]).hexdigest()==b['bytes_sha256']
 RANGES[key]={k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}
 RANGES[key]['binding']=str((path/'native-context.json').relative_to(ROOT));RANGES[key]['binding_sha256']=hashlib.sha256((path/'native-context.json').read_bytes()).hexdigest()
OBJ=0x400000;PARAM=0x402000;VT=0x403000;EVENT=0x404000;GRAPH=0x405000;STYLE=0x406000;BITMAP=0x407000;STACK=0x500000;STOP=0x600000
ENTRY={0x187314:'i2f',0x1873f0:'fmul',0x1877f8:'f2iz',0x18714c:'fsub',0x187150:'fadd',0x187780:'fcmpeq',0x1877e0:'fcmpgt',0x1864b8:'idiv',0x186964:'f2d',0x186fc4:'dcmpge',0x10e9bc:'getClientRect',0x10f4b4:'getStyle',0x6994c:'getFrame',STOP+4:'normalized',STOP+8:'enabled',STOP+12:'value',STOP+16:'fill',STOP+20:'bitmap',STOP+24:'line'}
AUDIT={'elf_sha256':SHA,'ranges':{str(k):v for k,v in RANGES.items()},'intercepted_entries':{hex(k):v for k,v in ENTRY.items()},'pcs':{},'intercepts':{},'unexpected_pcs':[],'Core_body_instructions':0,'runtime_body_instructions':0}
def fb(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def bf(v):return struct.unpack('<f',struct.pack('<I',v))[0]
def signed(v):return v if v<0x80000000 else v-0x100000000

def execute(c):
 t=c['target'];u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000)
 with ELF.open('rb') as f:
  for s in ELFFile(f).iter_segments():
   if s['p_type']=='PT_LOAD':u.mem_write(s['p_vaddr'],s.data())
 u.mem_map(OBJ,0x10000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x10000)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def vec(a,n):return [signed(r(a+i*4)) for i in range(n)]
 for i in range(6):
  w(PARAM+i*0x100,VT);w(PARAM+i*0x100+4,i)
 w(VT+0x60,STOP+4);w(VT+0x20,STOP+8);w(VT+0x44,STOP+12)
 w(OBJ+0x48,PARAM if c['primary'] else 0);w(OBJ+0x58,BITMAP if c['image'] else 0);w(OBJ+0x60,c['mark']);w(OBJ+0x64,PARAM+0x100);w(OBJ+0x68,PARAM+0x200);w(OBJ+0x6c,PARAM+0x300);w(OBJ+0x70,PARAM+0x400);w(OBJ+0x74,PARAM+0x500 if c['aux'] else 0)
 w(BITMAP+8,c['frames']);w(BITMAP+12,c['bw']);w(BITMAP+16,c['bh']);w(EVENT,GRAPH);w(GRAPH,VT+0x100);w(VT+0x100+0x14,STOP+16);w(VT+0x100+0x28,STOP+20);w(VT+0x100+0x1c,STOP+24);w(STYLE+16,0x12345678);w(STYLE+4,0x23456789)
 trace=[];closure=[t,'linked','compute','side']+(['stereo'] if t==2 else [])
 def cb(uc,a,size,user):
  if a in ENTRY:
   key=f'{t}:{a:#x}';AUDIT['intercepts'][key]=AUDIT['intercepts'].get(key,0)+1
  elif any(b['address']<=a and a+size<=b['address']+b['size'] for b in [RANGES[k] for k in closure]):
   key=f'{t}:{a:#x}';AUDIT['pcs'][key]=AUDIT['pcs'].get(key,0)+1
   return
  else:
   AUDIT['unexpected_pcs'].append([t,a]);raise RuntimeError(f'Unbound PC {a:#x}')
  r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2);r3=uc.reg_read(UC_ARM_REG_R3);value=None
  kind=ENTRY[a]
  if kind=='normalized':value=fb(c['value'] if r(r0+4)==0 else c['other'])
  elif kind=='enabled':value=c['enabled']
  elif kind=='value':value=fb({1:c['link'],2:c['stereo'],4:c['side']}[r(r0+4)])
  elif kind=='i2f':value=fb(signed(r0))
  elif kind=='fmul':value=fb(bf(r0)*bf(r1))
  elif kind=='fsub':value=fb(bf(r0)-bf(r1))
  elif kind=='fadd':value=fb(bf(r0)+bf(r1))
  elif kind=='f2iz':value=int(bf(r0))
  elif kind=='fcmpeq':value=int(bf(r0)==bf(r1))
  elif kind=='fcmpgt':value=int(bf(r0)>bf(r1))
  elif kind=='idiv':value=int(signed(r0)/signed(r1))
  elif kind=='f2d':
   lo,hi=struct.unpack('<II',struct.pack('<d',bf(r0)));value=lo;uc.reg_write(UC_ARM_REG_R1,hi)
  elif kind=='dcmpge':value=int(struct.unpack('<d',struct.pack('<II',r0,r1))[0]>=struct.unpack('<d',struct.pack('<II',r2,r3))[0])
  elif kind=='getClientRect':
   for i,v in enumerate([0,0,c['width'],c['height']]):w(r1+4*i,v)
   value=r1
  elif kind=='getStyle':value=STYLE
  elif kind=='getFrame':
   height=c['bh']//c['frames'] if c['frames']>1 else c['bh']
   for i,v in enumerate([0,r2*height if c['frames']>1 else 0,c['bw'],(r2+1)*height if c['frames']>1 else height]):w(r0+4*i,v)
   value=r0
  elif kind=='fill':trace.append(['fill']+vec(r1,4)+[r(r2)]);value=1
  elif kind=='bitmap':trace.append(['bitmap']+vec(r1,2)+vec(r3,4));value=1
  elif kind=='line':trace.append(['line']+vec(r1,2)+vec(r2,2)+[r(r3)]);value=1
  else:raise RuntimeError(kind)
  if value is not None:uc.reg_write(UC_ARM_REG_R0,value&0xffffffff)
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,cb);u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,EVENT);u.reg_write(UC_ARM_REG_SP,STACK+0x8000);u.reg_write(UC_ARM_REG_LR,STOP)
 u.emu_start(RANGES[t]['address'],STOP,count=10000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 return trace

def cases():
 result=[]
 base=dict(width=100,height=20,mark=3,stereo=0,link=0,side=0,aux=0,primary=1,image=1,enabled=1,bw=50,bh=20,frames=2,value=0.5,other=0.25)
 for target in [1,2]:
  variants=[]
  if target==1:
   for mark,width,height,value,link,side in itertools.product([0,1,3,120],[0,100],[0,20],[0,.25,.5,1],[0,1],[0,1]):variants.append(dict(mark=mark,width=width,height=height,value=value,link=link,side=side))
  else:
   for stereo,link,side,aux,frames,value in itertools.product([0,1],[0,1],[0,1],[0,1],[1,2,4],[0,.25,.49,.5,.51,.75,1]):variants.append(dict(stereo=stereo,link=link,side=side,aux=aux,frames=frames,value=value))
   variants += [dict(primary=0),dict(image=0),dict(enabled=0)]
  for variant in variants:
   c={**base,**variant,'target':target};c['expected']=execute(c);result.append(c)
 return result
if __name__=='__main__':
 data=cases();out=pathlib.Path(__file__).parent; (out/'fixtures.json').write_text(json.dumps({'cases':data},indent=2)+'\n');(ROOT/'evidence/recovery/2026-11-05/rolling200-02/pan-drawing/native-pc-audit.json').write_text(json.dumps(AUDIT,indent=2)+'\n');print(len(data),'ARM cases, unknown PCs:',AUDIT['unexpected_pcs'])
