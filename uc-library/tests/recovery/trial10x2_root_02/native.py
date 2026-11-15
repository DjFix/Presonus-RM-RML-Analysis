"""Execute only original application instructions. CCL/application boundaries model calls;
CCL state effects are observed separately in actual compiled pinned providers."""
import pathlib,hashlib,json,io,struct,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
TASK=pathlib.Path(__file__).parent.name
MAP=json.load(open('temp/recovery-work/trial10x2-20261115/READ_INPUTS-prepared01-trial10x2_root.json'))
path=MAP['rootfs/CS18_v13840/home/root/surface']['frozen_read_path'];b=pathlib.Path(path).read_bytes();assert hashlib.sha256(b).hexdigest()==MAP['rootfs/CS18_v13840/home/root/surface']['sha256']
e=ELFFile(io.BytesIO(b));req=json.load(open('temp/recovery-work/trial10x2-20261115/prepared01/packets/'+TASK+'/request.json'));target=req['targets'][0]
sym=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name==target['mangled']);sec=e.get_section(sym['st_shndx']);assert sym['st_value']==target['address'] and sym['st_size']==target['size'] and sym['st_shndx']==12
assert sec['sh_addr']<=sym['st_value'] and sym['st_value']+sym['st_size']<=sec['sh_addr']+sec['sh_size']
off=sec['sh_offset']+sym['st_value']-sec['sh_addr'];code=b[off:off+sym['st_size']]
assert hashlib.sha256(code).hexdigest()==('f3ac3d28e25a9b9d89aafd6b60905679661b3b96c37efcb1d877a42da72d0de5' if TASK.endswith('01') else '813d9d7cd73a894f1a3162a2a4c917cebd997f69d3ffdd8eae1e330fc38cdce2')
def execute(args):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x10000,0x280000)
 # Only selected app body and bound static string/literals are loaded. No Core code.
 u.mem_write(sym['st_value'],code);u.mem_write(0x1e4178,b'SurfaceRootComponent::manageUtilPageObserver activeTestCount is negative!\n\0')
 u.mem_write(0x26b168,struct.pack('<I',0))
 calls=[];error=False;roots=[0x210000,0x211000];screen=[0x220000,0x221000];params={0x230000:[],0x231000:[],0x232000:[],0x233000:[]};ids={}
 if TASK.endswith('01'):
  flag,reg,missing,n=args;u.mem_write(roots[0]+0x130,bytes([flag]));u.mem_write(roots[0]+0x114,struct.pack('<I',0x240000 if reg else 0));params[0x230000]=[roots[0]+4]*n;params[0x231000]=[roots[0]+4]*n;ids={0x230000:38,0x231000:903};ops=[(0,False)]
 else:
  missing=args[0];ops=[(int(x[0]),x[1]=='+') for x in args[1].split(',')];ids={0x230000:2,0x231000:2};flag=1
 def hook(uc,pc,size,data):
  nonlocal error
  if pc not in [0xad000,0x11acf0,0x11e2e0,0x11f4f0,0xa61e0,0x1179d4]:return
  a=uc.reg_read(UC_ARM_REG_R0);c=uc.reg_read(UC_ARM_REG_R1);root=0 if a in [roots[0],screen[0]] else 1
  if pc==0xad000:uc.reg_write(UC_ARM_REG_R0,0 if missing==1 else screen[root])
  elif pc==0x11acf0:
   calls.append('tag'+str(c));param=0x230000 if c==38 else 0x231000 if c==903 else 0x230000+root*0x1000
   if not a or missing==(2 if c in [38,2] else 3):error=True;uc.emu_stop();return
   uc.reg_write(UC_ARM_REG_R0,param)
  elif pc in [0x11e2e0,0x11f4f0]:
   op='remove' if pc==0x11e2e0 else 'add';calls.append(op+str(ids.get(a,-1)))
   if not a:error=True;uc.emu_stop();return
   if op=='add':params[a].append(c)
   elif c in params[a]:params[a].remove(c)
  elif pc==0xa61e0:calls.append('run'+str(c)+'_'+str(uc.reg_read(UC_ARM_REG_R2)))
  else:calls.append('debug')
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook);rows=[]
 for root,enabled in ops:
  calls.clear();error=False;u.reg_write(UC_ARM_REG_R0,roots[root]);u.reg_write(UC_ARM_REG_R1,int(enabled));u.reg_write(UC_ARM_REG_SP,0x280000);u.reg_write(UC_ARM_REG_LR,0x10000)
  u.emu_start(sym['st_value'],0x10000,count=200);assert error or u.reg_read(UC_ARM_REG_PC)==0x10000
  state=[int.from_bytes(u.mem_read(roots[0]+0x130,1),'little'),len(params[0x230000]),len(params[0x231000]),int(error)] if TASK.endswith('01') else [len(params[0x230000]),len(params[0x231000]),int(error)]
  rows.append(dict(state=state,calls=list(calls)))
 return rows
if TASK.endswith('01'):
 cases=[dict(args=[f,r,m,n],rows=execute([f,r,m,n])) for f in [0,1] for r in [0,1] for m in range(4) for n in [0,1,2]]
else:
 cases=[dict(args=[m,s],rows=execute([m,s])) for m in [0,1,2] for s in ['0+','0-','0+,0-','0+,0+,0-,0-','0+,1+,0-,1-','0-,0-,0+,0-','0+,1-,0-','0+,0+,0+,0-,0-,0-']]
text=json.dumps(dict(elf_sha256=target['original_elf_sha256'],mangled=target['mangled'],address=sym['st_value'],size=sym['st_size'],section_index=12,file_offset=off,range_sha256=hashlib.sha256(code).hexdigest(),cases=cases,limitations='Only selected original ARM body executed. getMainScreen and CCL/provider boundaries modeled; provider effects separately executed. Invalid mandatory component/parameter modeled as boundary error, never valid empty-domain return.'),indent=2)+'\n'
p=pathlib.Path(__file__).with_name('fixtures.json')
if '--verify' in sys.argv:assert p.read_text()==text
else:p.write_text(text)
print(TASK,'native cases',len(cases))
