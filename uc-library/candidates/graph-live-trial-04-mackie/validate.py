import pathlib, hashlib, json, subprocess, sys, itertools, struct, datetime, time
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
P=pathlib.Path('uc-library/candidates/graph-live-trial-04-mackie'); S=pathlib.Path('temp/recovery-work/graph-live-trial-04/mackie-worker'); S.mkdir(parents=True,exist_ok=True)
ELF=pathlib.Path('rootfs/CS18_v13840/home/root/surface')
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
elf=ELF.read_bytes(); assert hashlib.sha256(elf).hexdigest()=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
ranges=[(0xc0480,48),(0xc0f24,160),(0xc0068,172),(0xc0114,96),(0xc0624,200)]
def run(case):
 method,tag,state,cached,note,index,count,omit,sink=case
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM); u.mem_map(0x10000,0x300000)
 for a,n in ranges: u.mem_write(a,elf[a-0x8000:a-0x8000+n])
 obj,entries,states,vt,svt,sobj,lv,lo=0x200000,0x210000,0x220000,0x230000,0x231000,0x232000,0x233000,0x234000
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 w(obj,vt);w(obj+4,entries);w(obj+8,count);w(obj+0xa64,states);w(obj+0xae0,sobj if sink else 0);w(obj+0xae4,lo)
 w(sobj,svt);w(svt,0x180000);w(lo,lv);w(lv+8,0x180030);w(vt+24,0x180010);w(vt+28,0x180020)
 u.mem_write(obj+0xadc,bytes([omit]));u.mem_write(states,bytes([cached])*16);u.mem_write(obj+0xb76,bytes([cached])*9)
 for i in range(9):w(obj+0xb80+4*i,123)
 for i in range(count):u.mem_write(entries+12*i,struct.pack('<iii',100+i,note,index))
 data=0x240000;u.mem_write(data,bytes([0x90,1,127])); trace=[]
 def hook(uc,a,size,user):
  if a==0x190000:uc.emu_stop();return
  if a==0xc0ed0:
   # Bounded lookup boundary; native mapping implementation not in initial packet.
   t=uc.reg_read(UC_ARM_REG_R1);r=next((entries+12*i for i in range(count) if 100+i==t),0);uc.reg_write(UC_ARM_REG_R0,r);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  if 0x180000<=a<=0x180030:
   t=uc.reg_read(UC_ARM_REG_R1);b=uc.reg_read(UC_ARM_REG_R2)
   if a==0x180000:trace.append('M%d:'%uc.reg_read(UC_ARM_REG_R3)+''.join(str(x)+',' for x in uc.mem_read(t,b))+';')
   else:trace.append({0x180010:'B',0x180020:'F',0x180030:'L'}[a]+str(t)+':'+str(b)+';')
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_SP,0x280000);u.reg_write(UC_ARM_REG_LR,0x190000);u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,data if method==1 else tag&0xffffffff);u.reg_write(UC_ARM_REG_R2,3 if method==1 else state)
 u.emu_start(ranges[method-1][0],0,count=10000)
 # C++ stream inserts R before evaluating the method; put it before trace.
 prefix=('R' if method==2 else '')+''.join(trace)+(str(u.reg_read(UC_ARM_REG_R0))+';' if method==2 else '')
 return prefix+' S'+''.join(str(x)+',' for x in u.mem_read(states,16))+' T'+''.join(str(x)+',' for x in u.mem_read(obj+0xb76,9))+' V'+''.join(str(x)+',' for x in struct.unpack('<9i',u.mem_read(obj+0xb80,36)))
def cases():
 for sink in [0,1]:yield [1,0,0,0,60,0,0,0,sink]
 for tag,state,cached,note,index,sink in itertools.product([99,100,101],[0,1],[0,1,2],[-1,60,300],[-1,0,15],[0,1]):yield [2,tag,state,cached,note,index,1,0,sink]
 for method,count,omit in itertools.product([3,4],[0,1,4],[0,1]):yield [method,0,0,0,60,0,count,omit,1]
 for tag,state,cached,sink in itertools.product([-2147483648,-1,0,0x1fff,0x2000,0x2001,0x2007,0x2008,0x9000,2147483647],[0,1],[0,1,2],[0,1]):yield [5,tag,state,cached,60,0,0,0,sink]
if sys.argv[1]=='compile':
 subprocess.run(['g++','-std=c++17','-Iuc-library/include','uc-library/src/Presonus/MackieControlModel.cpp','uc-library/tests/graph_trial04_mackie_tests.cpp','-o',str(S/'replay')],check=True)
elif sys.argv[1]=='symbols':
 out=subprocess.check_output(['nm',str(S/'replay')],text=True)
 for p in range(1,6):
  c=json.loads(pathlib.Path(f'temp/recovery-work/graph-live-trial-04/trial04_mackie_{p}-packet/context.json').read_text())
  # Exact names retained in sealed task, also explicit below.
 for name in ['_ZN8Presonus18MackieControlModel15sendMidiMessageEPKhj','_ZN8Presonus18MackieControlModel14setButtonStateEib','_ZN8Presonus18MackieControlModel17releaseAllButtonsEv','_ZN8Presonus18MackieControlModel9resetLedsEv','_ZN8Presonus18MackieControlModel10touchFaderEib']:assert name in out,name
 (S/'symbols.txt').write_text(out)
elif sys.argv[1]=='oracle':
 rows=[{'case':c,'observation':run(c)} for c in cases()];(P/'fixtures.json').write_text(json.dumps(rows,indent=2)+'\n');print(len(rows),'original ARM executions')
elif sys.argv[1]=='replay':
 rows=json.loads((P/'fixtures.json').read_text());out=subprocess.check_output([sys.argv[2] if len(sys.argv)>2 else str(S/'replay')],input='\n'.join(' '.join(map(str,r['case'])) for r in rows)+'\n',text=True).splitlines()
 for i,(row,actual) in enumerate(zip(rows,out)):assert row['observation']==actual,(i,row,actual)
 assert len(out)==len(rows);print(len(rows),'portable executions matched native boundary observations')
