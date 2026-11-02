"""Execute exact original ARM ranges. No recovered C++ imports or expected algorithm."""
import hashlib,json,struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[5]
PACKETS=ROOT/'temp/recovery-work/ranked-trial-09-small01/batch02/packets'
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(case,meta):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
 with ELF.open('rb') as f:
  elf=ELFFile(f)
  for seg in elf.iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 u.mem_map(0x1000000,0x20000)
 def wr(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def rd(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 obj=0x1000000;arr=obj+0x1000;rows=obj+0x2000;stop=obj+0x8000
 mode=case['mode'];n=len(case['values']);arg=case['arg'];selected=case['selected'];sentinel=case['sentinel']
 off={0:0,1:0xc8,2:0xd0,3:0x24,4:0}[mode]
 wr(obj+off,arr);wr(obj+off+4,n)
 cell={0:2528604,1:2533816,2:2533812,3:2534976,4:2528604}[mode]
 if mode==3:
  wr(obj+0x34,selected)
  for i,v in enumerate(case['values']):
   wr(arr+4*i,rows+0x100*i if v else 0);wr(rows+0x100*i+0x80,v)
  err=rows+0x1000 if sentinel else 0;wr(rows+0x1080,sentinel)
  wr(cell,err)
 else:
  for i,v in enumerate(case['values']):wr(arr+4*i,v)
  wr(cell,sentinel)
 trace=[];writes=[];pcs=[]
 def mem(u,access,a,size,value,_):
  if a==cell or obj<=a<obj+0x4000:
   target=writes if access==17 else trace
   target.append({'pc':u.reg_read(UC_ARM_REG_PC),'address':a,'size':size,'value':value if access==17 else rd(a)})
 def code(u,a,size,_):
  pcs.append(a)
  if a==stop:u.emu_stop()
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,mem)
 u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,arg&0xffffffff)
 u.reg_write(UC_ARM_REG_SP,obj+0x18000);u.reg_write(UC_ARM_REG_LR,stop)
 u.emu_start(meta['address'],stop,count=10000)
 assert u.reg_read(UC_ARM_REG_PC)==stop
 if mode in [0,3]:out=[u.reg_read(UC_ARM_REG_R0)]
 else:out=[rd(obj+off+4)]+[rd(arr+i*4) for i in range(n)]
 return out,{'reads':trace,'writes':writes,'executed_addresses':pcs,'external_calls':[]}
def main():
 assert digest(ELF)==SHA
 metas=[]
 with ELF.open('rb') as f:
  e=ELFFile(f)
  for i in range(1,6):
   packet=PACKETS/f'rank09_handlers_{i:02}'
   c=json.loads((packet/'native-context.json').read_text());req=json.loads((packet/'request.json').read_text())
   target=req['targets'][0];body=next(b for b in c['bodies'].values() if b['address']==target['address'])
   sec=e.get_section(body['section_index']);offset=sec['sh_offset']+body['address']-sec['sh_addr']
   assert offset==body['file_offset'];f.seek(offset);data=f.read(body['size']);assert hashlib.sha256(data).hexdigest()==body['bytes_sha256']
   sym=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==target['mangled'])
   assert sym['st_value']==body['address'] and sym['st_size']==body['size'] and sym['st_shndx']==12
   metas.append({k:body[k] for k in ['address','size','file_offset','bytes_sha256','section_index']})
 cases=[]
 for mode in range(5):
  for values in [[],[1],[0],[1,2,3],[1,1,2,1],[0,2,0],[3,2,1,3,0,2]]:
   for arg in [-2147483648,-1,0,1,2,3,6,2147483647]:
    for selected in ([0,1,2,4,9] if mode==3 else [0]):
     for sentinel in [0,9]:
      case=dict(mode=mode,values=values,arg=arg,selected=selected,sentinel=sentinel)
      out,audit=run(case,metas[mode]);cases.append(dict(input=case,expected=out,native=audit))
 dest=Path(__file__).with_name('fixtures.json')
 result=dict(elf_sha256=SHA,ranges=metas,cases=cases,oracle_sha256=digest(Path(__file__)))
 if '--verify' in sys.argv:
  assert json.loads(dest.read_text())==result, 'fresh original execution fixture mismatch'
 else: dest.write_text(json.dumps(result,indent=2)+'\n')
 print('original ARM executions',len(cases),'Unicorn',__import__('unicorn').__version__)
if __name__=='__main__':main()
