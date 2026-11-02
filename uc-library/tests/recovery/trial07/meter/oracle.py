"""Execute original CS18AI MeterControl ARM ranges; provider calls are captured boundaries."""
import argparse, hashlib, itertools, json, struct, time, datetime
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[5]
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
REG=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
OBJ=0x300000; STACK=0x410000; STOP=0x500000; IPOL=0x301000; PV=0x302000; PP=0x303000; VT=0x304000; OUT=0x305000; ARG=0x306000; STYLE=0x307000; GFX=0x308000
FILL=0x500100; INTERP=0x500104; ENABLED=0x500108; NORMAL=0x50010c; INVALIDATE=0x500110
ADDR=[0x65620,0x64f2c,0x667e0,0x65190,0x656e0,0x67610,0x650d4,0x65010,0x67154,0x64894]
def bits(v): return struct.unpack('<I',struct.pack('<f',v))[0]
def fval(v): return struct.unpack('<f',struct.pack('<I',v))[0]
def signed(v): return v if v<2**31 else v-2**32

def run(c):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x600000)
 with ELF.open('rb') as f:
  e=ELFFile(f)
  for s in e.iter_segments():
   if s['p_type']=='PT_LOAD':u.mem_write(s['p_vaddr'],s.data())
 def put(a,*v):u.mem_write(a,struct.pack('<'+'I'*len(v),*[x&0xffffffff for x in v]))
 def get(a,n=1):return list(struct.unpack('<'+'I'*n,u.mem_read(a,4*n)))
 trace=[]
 put(OBJ,VT); put(VT+0x1c,INVALIDATE);put(IPOL,VT+0x100);put(VT+0x10c,INTERP)
 put(PV,VT+0x200);put(PP,VT+0x200);put(VT+0x220,ENABLED);put(VT+0x260,NORMAL)
 put(GFX,VT+0x300);put(VT+0x314,FILL)
 put(OBJ+0x2c,*c['size']);put(OBJ+0x48,PV if c['primary'] else 0)
 u.mem_write(OBJ+0x58,bytes([c['reverse'],c['immediate'],c['hide_peak']]))
 put(OBJ+0x5c,IPOL if c['interpolator'] else 0);put(OBJ+0x60,PP if c['peak_param'] else 0)
 put(OBJ+0x64,*[bits(x) for x in c['values']]);put(OBJ+0x74,*c['dirty']);put(OBJ+0x84,*c['peak_dirty'])
 put(STYLE,0x11223344,0x55667788,0x99999999,0xaaaaaaaa,0xbbccddee)
 put(ARG,*c['a']);put(ARG+16,*c['b'])
 put(OUT,0,0,0,0)
 def ret(v=None):
  if v is not None:u.reg_write(UC_ARM_REG_R0,v&0xffffffff)
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def hook(uc,a,z,d):
  r=[u.reg_read(x) for x in REG]
  allowed = [(x,x+n) for x,n in zip(ADDR,[192,228,552,156,220,76,188,196,152,320])] + [(0x64ed8,0x64f10)]
  boundaries = {STOP,0xacb4,0x18714c,0x187314,0x1873f0,0x1877f8,0x187780,0x10e9a8,0x10e9bc,0x10f4b4,0x10e9fc,0xf8588,0xf8768,0x10ea7c,0x11e2e0,0x11f4f0,INTERP,ENABLED,NORMAL,INVALIDATE,FILL}
  if not any(lo<=a<hi for lo,hi in allowed) and a not in boundaries:
   raise RuntimeError(f'execution outside selected app ranges/captured boundaries: {a:#x}')
  if a==STOP:u.emu_stop()
  elif a==0x18714c:ret(bits(fval(r[0])-fval(r[1])))
  elif a==0x187314:ret(bits(float(signed(r[0]))))
  elif a==0x1873f0:ret(bits(fval(r[0])*fval(r[1])))
  elif a==0x1877f8:ret(int(fval(r[0])))
  elif a==0x187780:ret(int(fval(r[0])==fval(r[1])))
  elif a==0xacb4:u.mem_write(r[0],bytes(u.mem_read(r[1],r[2])));ret(r[0])
  elif a==0x10e9a8:ret(OBJ+0x2c)
  elif a==0x10e9bc:put(r[1],0,0,c['size'][2]-c['size'][0],c['size'][3]-c['size'][1]);ret(r[1])
  elif a==0x10f4b4:ret(STYLE)
  elif a==0x10e9fc:trace.append(['invalidate',0,0,c['size'][2]-c['size'][0],c['size'][3]-c['size'][1]]);ret()
  elif a==0xf8588:trace.append(['base_idle']);ret()
  elif a==0xf8768:trace.append(['base_param',c['param_choice'],signed(r[2])]);ret()
  elif a==0x10ea7c:trace.append(['enable',r[1]]);ret()
  elif a in (0x11e2e0,0x11f4f0):trace.append(['remove' if a==0x11e2e0 else 'add',1 if r[0]==PP else 2,r[1]-OBJ]);ret()
  elif a==INTERP:
   x=fval(r[1]);trace.append(['interpolate',r[1]]);ret(bits(x if c['interpolator']==1 else x*x))
  elif a==ENABLED:ret(c['enabled'])
  elif a==NORMAL:ret(bits(c['param_value']))
  elif a==INVALIDATE:trace.append(['invalidate',*[signed(x) for x in get(r[1],4)]]);ret()
  elif a==FILL:trace.append(['fill',*[signed(x) for x in get(r[1],4)],get(r[2])[0]]);ret()
 u.hook_add(UC_HOOK_CODE,hook)
 u.reg_write(UC_ARM_REG_SP,STACK);u.reg_write(UC_ARM_REG_LR,STOP)
 i=c['target'];r=[OBJ,bits(c['input']),0,0]
 if i in (3,6):r=[OUT,OBJ,bits(c['input']),0]
 elif i==1:r=[OUT,OBJ,ARG,ARG+16]
 elif i==2:pass
 if i==2:put(ARG,GFX,*c['clip']);r=[OBJ,ARG,0,0]
 if i==5:r=[OBJ,PP if c['new_peak']==1 else PV if c['new_peak']==2 else 0,0,0]
 if i==8:r=[OBJ,PV if c['param_choice']==1 else PP if c['param_choice']==2 else IPOL,c['msg'],0]
 for reg,v in zip(REG,r):u.reg_write(reg,v&0xffffffff)
 u.emu_start(ADDR[i],STOP,count=50000)
 if u.reg_read(UC_ARM_REG_PC)!=STOP:raise RuntimeError('did not reach return')
 return {'return':signed(u.reg_read(UC_ARM_REG_R0)) if i==7 else None,'rect':[signed(x) for x in get(OUT,4)] if i in (1,3,6) else None,'values_bits':get(OBJ+0x64,4),'dirty':[signed(x) for x in get(OBJ+0x74,4)],'peak_dirty':[signed(x) for x in get(OBJ+0x84,4)],'peak_param':1 if get(OBJ+0x60)[0]==PP else 2 if get(OBJ+0x60)[0]==PV else 0,'trace':trace}

def cases():
 base=dict(target=0,size=[7,9,107,49],reverse=0,immediate=0,hide_peak=0,interpolator=1,primary=1,peak_param=1,values=[.25,.5,.75,.5],dirty=[0,0,0,0],peak_dirty=[0,0,0,0],input=.125,a=[0,0,20,30],b=[0,0,10,15],clip=[5,6,80,35],new_peak=1,param_choice=1,msg=3,enabled=1,param_value=.375)
 for target in range(10):
  if target in (0,3,4,6,7):
   for size,rev,ip,v in itertools.product(([7,9,107,49],[7,9,27,109]),(0,1),(0,1,2),(-.25,0,.125,.5,.75,1,1.25)):
    c=dict(base,target=target,size=size,reverse=rev,interpolator=ip,input=v);yield c
   if target in (0,4):
    for imm,v in itertools.product((0,1),(.5,.75)):
     yield dict(base,target=target,immediate=imm,input=v)
  elif target==1:
   for size,rev,a,b in itertools.product(([0,0,100,40],[0,0,20,100]),(0,1),([0,0,10,20],[1,2,30,40],[-3,-5,2,1]),([0,0,5,10],[1,2,40,50],[-7,-9,0,0])):yield dict(base,target=target,size=size,reverse=rev,a=a,b=b)
  elif target==2:
   for size,rev,imm,hide,clip in itertools.product(([0,0,100,40],[0,0,20,100]),(0,1),(0,1),(0,1),([0,0,100,100],[15,7,60,25],[101,101,110,110])):yield dict(base,target=target,size=size,reverse=rev,immediate=imm,hide_peak=hide,clip=clip)
  elif target==5:
   for old,new in itertools.product((0,1),(0,1,2)):yield dict(base,target=target,peak_param=old,new_peak=new)
  elif target==8:
   for choice,msg,en,imm in itertools.product((1,2,3),(0,3,4),(0,1),(0,1)):yield dict(base,target=target,param_choice=choice,msg=msg,enabled=en,immediate=imm)
  elif target==9:
   for d,p in itertools.product(([0,0,0,0],[1,2,10,20],[5,6,5,8],[5,6,20,4]),([0,0,0,0],[3,4,30,40],[2,3,2,7],[3,9,8,2])):yield dict(base,target=target,dirty=d,peak_dirty=p)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--timing-output');args=ap.parse_args()
 assert hashlib.sha256(ELF.read_bytes()).hexdigest()==SHA
 result=[];timings=[]
 for i,c in enumerate(cases()):
  start=datetime.datetime.now(datetime.timezone.utc).isoformat(); t=time.monotonic()
  try:result.append({'case':c,'observed':run(c)})
  except Exception as e:raise RuntimeError(f'case {i} target {c["target"]} {c}') from e
  timings.append({'target':c['target'],'case_index':i,'started_at':start,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'duration_seconds':time.monotonic()-t})
 if args.timing_output:Path(args.timing_output).write_text(json.dumps(timings,indent=2)+'\n')
 Path(args.out).write_text(json.dumps({'version':1,'elf_sha256':SHA,'cases':result},indent=2)+'\n');print('original ARM cases',len(result))
if __name__=='__main__':main()
