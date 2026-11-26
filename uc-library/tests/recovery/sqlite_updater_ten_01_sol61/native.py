"""Execute hash/range verified app bodies; all external/provider effects captured."""
import argparse,hashlib,io,json,pathlib,re,struct,functools
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_INTR
from unicorn.arm_const import *
BASE=pathlib.Path(__file__).parent
PACKETS=pathlib.Path('temp/recovery-work/sqlite-issued/packet')
R=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
OBJ=0x4001000; STACK=0x40ff000; STOP=0x4000100; LISTENER=0x4002000; VT=0x4002100; TEMP=0x4003000; PARAM=0x4004000; TASK=0x4005000

@functools.lru_cache(None)
def load(path,sha):
 b=pathlib.Path(path).read_bytes();assert hashlib.sha256(b).hexdigest()==sha
 e=ELFFile(io.BytesIO(b));ss=list(e.get_section_by_name('.symtab').iter_symbols());sym={s.name:s for s in ss}
 return b,e,ss,sym

def execute(o,c):
 b,e,ss,sym=load(o['elf_path'],o['elf']);s=sym[o['mangled']];sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];raw=b[off:off+s['st_size']]
 assert (s['st_value'],s['st_size'],s['st_shndx'],off)==(o['address'],o['size'],o['section'],o['file_offset']);assert hashlib.sha256(raw).hexdigest()==o['range_sha256']
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x1000000)
 for seg in e.iter_segments():
  if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 u.mem_map(0x4000000,0x100000);u.mem_write(OBJ,bytes([0xa5])*0x1000)
 def word(a,v=None):
  if v is None:return struct.unpack('<I',u.mem_read(a,4))[0]
  u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def string(a):
  if not a:return ''
  z=bytearray()
  for i in range(4096):
   v=bytes(u.mem_read(a+i,1))
   if v==b'\0':return z.decode('latin1')
   z+=v
  raise AssertionError('unterminated')
 def put(a,v,cap=4096):u.mem_write(a,v.encode('latin1')[:cap-1]+b'\0')
 def ret(v=0):u.reg_write(R[0],v&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 calls=[];files={};attrs={};vt={}
 for i,kind in [(0,'alert'),(4,'dismiss'),(8,'progress')]:word(VT+i,0x4006000+i);vt[0x4006000+i]=kind
 word(LISTENER,VT)
 for i in [0x44,0x58,0x5c]:word(VT+0x100+i,0x4006100+i);vt[0x4006100+i]=['value','set','enable'][[0x44,0x58,0x5c].index(i)]
 word(PARAM,VT+0x100);word(PARAM+12,TEMP+0x200);word(TEMP+0x204,c.get('tag',0))
 def config():
  for a,v in [(5,''),(0x45,'Power Cycle the Mixer'),(0x85,'/media/sda1/upgrade.bin'),(0x185,'https://user.presonus.com/upgrade'),(0x285,'rm32'),(0x2c5,'RM3E42'),(0x305,'aa:bb:cc:dd:ee:ff'),(0x345,'13840' if o['role']=='client' else '13731'),(0x385,'0123456789abcdef0123456789abcdef'),(0x3c5,'1234')]:put(OBJ+a,v)
  word(OBJ+0x408,LISTENER if c.get('listener',True) else 0);u.mem_write(OBJ+4,b'\1')
 config();word(OBJ+0x90,TASK);word(TASK,VT+0x200);word(VT+0x204,0x4006200)
 word(OBJ+0x94,0);word(OBJ+0x88,25);word(OBJ+0x8c,42)
 # Surface state overlaps UUX only in separate target executions.
 name=o['mangled'];surface='Surface' in name
 if surface:
  for a,v in [(OBJ+0x94,0),(OBJ+0x90,TASK),(OBJ+0x88,25),(OBJ+0x8c,42)]:word(a,v)
 if 'EN11UpgradeTask' in name:
  word(OBJ+0x10,25);word(OBJ+0x14,42);word(OBJ+0x18,LISTENER);word(OBJ+0x1c,PARAM if c.get('trigger',True) else 0)
 api={int(s['st_value']):s.name.split('@@')[0] for s in ss if s.name and s['st_value']}
 # Branch targets in static evidence resolve PLT aliases as well.
 for p in ['UUX_REMAINDER_NATIVE_R1','SURFACE_UPDATER_REMAINDER_NATIVE_R1']:
  data=json.loads(pathlib.Path('temp/recovery-work/rolling-c001-20261124/selection/reserve-intake-sol61-1518/'+p+'.json').read_text())
  for item in data['items']:
   if item['elf']==o['elf']:
    for ins in item['instructions']:
     if ins['target'] and ins['operands'].startswith('#0x'):api[int(ins['operands'][1:],16)]=ins['target'].split('@@')[0]
 def hook(uc,pc,n,d):
  if pc==STOP:return
  a=[uc.reg_read(r) for r in R];f=api.get(pc,'')
  if pc==o['address']:return
  if pc in vt:
   k=vt[pc]
   if k=='alert':calls.append(['alert',string(a[1]),string(a[2]),string(a[3])]);ret()
   elif k=='dismiss':calls.append(['dismiss']);ret()
   elif k=='progress':calls.append(['progress',string(a[1]),string(a[2])]);ret()
   elif k=='value':ret(struct.unpack('<I',struct.pack('<f',c.get('value',0.)))[0])
   elif k=='set':calls.append(['set',struct.unpack('<f',struct.pack('<I',a[1]))[0],bool(a[2])]);ret()
   elif k=='enable':calls.append(['enable',bool(a[1])]);ret()
   return
  if pc==0x4006200:calls.append(['worker-delete']);ret();return
  if f in ['strlen','strncpy','strncat','memcpy','strrchr','strstr','memset']:
   if f=='strlen':ret(len(string(a[0])))
   elif f=='strncpy':u.mem_write(a[0],string(a[1]).encode()[:a[2]].ljust(a[2],b'\0'));ret(a[0])
   elif f=='strncat':put(a[0],string(a[0])+string(a[1])[:a[2]]);ret(a[0])
   elif f=='memcpy':u.mem_write(a[0],bytes(u.mem_read(a[1],a[2])));ret(a[0])
   elif f=='memset':u.mem_write(a[0],bytes([a[1]&255])*a[2]);ret(a[0])
   else:
    pos=string(a[0]).rfind(chr(a[1])) if f=='strrchr' else string(a[0]).find(string(a[1]));ret(a[0]+pos if pos>=0 else 0)
   return
  if f.startswith('_ZN4Core') and ('CStringBuffer' in f or 'MutableCStringTraits' in f):
   m=re.search(r'ILi(\d+)EE',f);cap=int(m[1]) if m else 64
   if 'appendFormat' in f:
    fmt=string(a[1]);vals=[a[2],a[3],word(uc.reg_read(UC_ARM_REG_SP)),word(uc.reg_read(UC_ARM_REG_SP)+4)];j=0
    def sub(m):
     nonlocal j
     v=vals[j];j+=1
     if m[0]=='%s':return string(v)
     return str(v if m[0]=='%u' or v<0x80000000 else v-2**32)
    put(a[0],string(a[0])+re.sub('%[sdu]',sub,fmt),cap)
   elif '6insert' in f:put(a[0],string(a[0])[:a[1]]+string(a[2])+string(a[0])[a[1]:],cap)
   else:put(a[0],string(a[1]),cap)
   ret(a[0]);return
  if 'DebugPrintf' in f:ret();return
  if 'GetAbsoluteTime' in f:ret(1234);return
  if 'Threads' in f and 'sleep' in f:calls.append(['sleep',a[0]]);ret();return
  if 'FileStream' in f:
   if 'C1E' in f:
    files[a[0]]=''
    if name=='_ZL19curlRequestCallbackPvjjS_':calls.append(['stream-ctor'])
    ret(a[0])
   elif '4open' in f:
    path=string(a[1]);files[a[0]]=path;calls.append(['open',path]);ret(int(c.get('hash_open',True) if path=='md5scratch' else c.get('mac_open',True)))
   elif '6create' in f:files[a[0]]=string(a[1]);calls.append(['create',string(a[1])]);ret(int(c.get('create',True)))
   elif '10writeBytes' in f:calls.append(['write',bytes(u.mem_read(a[1],a[2])).decode('latin1')]);ret(c.get('write_result',a[2]))
   else:
    if name=='_ZL19curlRequestCallbackPvjjS_' and ('5close' in f or 'D1E' in f):calls.append(['close' if '5close' in f else 'stream-dtor'])
    ret()
   return
  if 'SimpleReaderC' in f:word(a[0],a[1]);ret(a[0]);return
  if 'SimpleReader11getNextWord' in f:
   p=files[word(a[0])];put(a[1],'aa:bb:cc:dd:ee:ff' if p!="md5scratch" else '0123456789abcdef0123456789abcdef',64);ret(1);return
  if 'FileUtils10deleteFile' in f:calls.append(['delete',string(a[0])]);ret(1);return
  if 'FileUtils10getTempDir' in f:put(TEMP,c.get('temp','/offline/'));ret(TEMP);return
  if f=='system':calls.append(['system',string(a[0])]);ret();return
  if f.startswith('curl_'):
   if f=='curl_global_init':calls.append(['global-init']);ret(c.get('global',0))
   elif f=='curl_easy_init':calls.append(['easy-init']);ret(0 if c.get('easy_fail') else 0x4007000)
   elif f=='curl_easy_setopt':
    if a[1] in [10002,10015]:calls.append(['option',a[1],string(a[2])])
    else:calls.append(['option',a[1],a[2] if a[1] not in [20011] else 'callback'])
    ret()
   elif f=='curl_easy_perform':calls.append(['perform']);ret(c.get('curl_result',0))
   elif f=='curl_easy_cleanup':calls.append(['easy-cleanup']);ret()
   elif f=='curl_global_cleanup':calls.append(['global-cleanup']);ret()
   else:raise AssertionError(f)
   return
  if 'prepareFirmwareRequestFields' in f:
   calls.append(['prepare']);ret(c.get('prepare',0));return
  if 'ArchiveUtils12loadFromFile' in f:calls.append(['archive',string(a[1])]);ret(int(c.get('archive',True)));return
  if 'AttributeAllocator10getDefault' in f:ret(TEMP);return
  if 'Attributes' in f:
   if '6getInt' in f:ret(c.get('code',0))
   elif '9getString' in f:put(TEMP,c.get('uri','https://example.invalid/fw.bin'));ret(TEMP)
   else:ret(a[0])
   return
  if 'doLocalFirmwareUpdate' in f:calls.append(['local']);ret(c.get('local',2));return
  if 'doUsbFirmwareUpdate' in f:calls.append(['usb']);ret(c.get('usb',2));return
  if 'doNetworkFirmwareUpdate' in f:calls.append(['network']);ret(c.get('network',0));return
  if 'executeBashUpgradeScript' in f:calls.append(['execute',string(a[1])]);ret(123);return
  if 'spinUpgradeDisplay' in f:calls.append(['spin',a[1]]);ret(c.get('script',0));return
  if 'FirmwareUpdaterC1' in f:calls.append(['updater-ctor',a[1],a[2]]);ret(a[0]);return
  if 'FirmwareUpdater14updateFirmware' in f:calls.append(['update',string(a[0]+5),bool(u.mem_read(a[0]+4,1)[0])]);ret();return
  if 'FirmwareUpdaterD1' in f:calls.append(['updater-dtor']);ret(a[0]);return
  if 'Component17getParameterByTag' in f:calls.append(['get-param',a[1]]);ret(PARAM);return
  if 'FirmwareUpdateComponent8doUpdate' in f:calls.append(['do-update']);ret();return
  if 'Component12paramChanged' in f:calls.append(['base-changed']);ret();return
  if 'BackgroundWorker7addTask' in f:
   calls.append(['add-task',word(a[1]+0x10),word(a[1]+0x14)]);ret();return
  if 'BackgroundWorker9terminate' in f:calls.append(['terminate']);ret();return
  if 'ComponentD2' in f:calls.append(['component-dtor']);ret();return
  if f.startswith('_Zn'):calls.append(['new',a[0]]);ret(TASK);return
  if f.startswith('_Zdl'):calls.append(['delete-object']);ret();return
  if f.startswith('__aeabi_fcmp'):
   x,y=[struct.unpack('<f',struct.pack('<I',v))[0] for v in a[:2]];ret(int(x==y if 'eq' in f else x>y));return
  if pc>=0x4000000:raise AssertionError(('unknown callback',hex(pc)))
  # No unmodeled external/native functions may execute. Target instructions only.
  if not o['address']<=pc<o['address']+o['size']:raise AssertionError((hex(pc),f))
 next_hook=u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_INTR,lambda *args: (_ for _ in ()).throw(AssertionError('native syscall forbidden')))
 values=[OBJ,c.get('product',23),42,LISTENER if c.get('listener',True) else 0]
 if name=='_ZL19curlRequestCallbackPvjjS_':
  put(OBJ,'abcdef');values=[OBJ,c.get('size',2),c.get('count',3),0]
 if 'paramChanged' in name:values=[OBJ,PARAM,c.get('msg',2),0]
 for reg,v in zip(R,values):u.reg_write(reg,v)
 u.reg_write(UC_ARM_REG_SP,STACK);u.reg_write(UC_ARM_REG_LR,STOP)
 for repeat in range(c.get('repeat',1)):
  if repeat:
   for reg,v in zip(R,values):u.reg_write(reg,v)
   u.reg_write(UC_ARM_REG_SP,STACK);u.reg_write(UC_ARM_REG_LR,STOP)
  u.emu_start(o['address'],STOP,count=20000);assert u.reg_read(UC_ARM_REG_PC)==STOP and u.reg_read(UC_ARM_REG_SP)==STACK
 result={'calls':calls}
 if 'FirmwareUpdaterC' in name or 'FirmwareUpdaterD' in name or 'FirmwareUpdateComponentD' in name or 'EN11UpgradeTaskD' in name:
  result['_native_state']={'entry_word':word(OBJ),'returned_r0':u.reg_read(R[0]),'stack_restored':True}
  if 'FirmwareUpdaterC' in name:result['_native_state'].update(animate=bool(u.mem_read(OBJ+4,1)[0]),listener=word(OBJ+0x408),request_fields=[string(OBJ+a) for a in [5,0x305,0x345,0x385,0x3c5]])
 if name=='_ZL19curlRequestCallbackPvjjS_':result['result']=u.reg_read(R[0])
 if 'FirmwareUpdaterC' in name:result.update(product=string(OBJ+0x285),serial=string(OBJ+0x2c5),completion=string(OBJ+0x45),usb=string(OBJ+0x85),url=string(OBJ+0x185))
 elif 'prepareFirmware' in name:result.update(mac=string(OBJ+0x305),firmware=string(OBJ+0x345),key=string(OBJ+0x385),timestamp=string(OBJ+0x3c5),result=u.reg_read(R[0]))
 elif 'updateFirmwareEv' in name or 'doNetworkFirmware' in name:result['result']=u.reg_read(R[0])
 u.hook_del(next_hook)
 u.mem_unmap(0x8000,0x1000000);u.mem_unmap(0x4000000,0x100000)
 return result

def main():
 argv=__import__('sys').argv;task_filter=argv[argv.index('--task-id')+1] if '--task-id' in argv else None
 rows=[];ranges=[]
 for p in [*sorted(PACKETS.glob('sqlite_updater_ten_*_sol61/CONTEXT.json')),pathlib.Path('temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/updater_ten_sol61/SUPPLEMENT-curl-callback01/CONTEXT.json')]:
  d=json.loads(p.read_text())
  task_id=d['task']['id'] if 'task' in d else d['task_id']
  if task_filter and task_id!=task_filter:continue
  for item in d['originals']:
   o=item['original'];ranges.append(o);name=o['mangled'];cases=[{}]
   if name=='_ZL19curlRequestCallbackPvjjS_':cases=[{}, {'create':False}, {'write_result':1}, {'size':0,'count':5},{'size':65536,'count':65536},{'size':4294967295,'count':4294967295},{'temp':'x'*125},{'repeat':2}]
   if 'FirmwareUpdaterC' in name:cases=[{'product':p} for p in [19,20,21,22,23,24,25,26]]
   elif 'prepareFirmware' in name:cases=[{'mac_open':m,'hash_open':h} for m in [False,True] for h in [False,True]]
   elif 'doNetworkFirmware' in name:cases=[{'listener':False,'global':1},{'curl_result':7},{'global':1},{'prepare':-1},{'easy_fail':True},{'archive':False}]+[{'code':code,'uri':uri,'script':s} for code,uri,s in [(-1,'x',0),(2,'x',0),(0,'',0),(0,'x',0),(0,'https://example.invalid/fw.bin',0),(0,'https://example.invalid/fw.bin',1),(0,'fw.bin',0),(0,'https://x/fw.bin/fw.bin',0),(0,'https://x/',0)]]
   elif 'FirmwareUpdater14update' in name:cases=[{'local':0},{'local':2,'usb':0}]+[{'network':n} for n in range(12)]+[{'listener':False,'network':8}]
   elif 'EN11UpgradeTask4work' in name:cases=[{}, {'trigger':False}]
   elif 'paramChanged' in name:cases=[{'tag':t,'value':v,'msg':m} for t in [0,5,6,8] for v in [0.,1.] for m in [1,2]]
   for c in cases:
    result=execute(o,c);native=result.pop('_native_state',None);row={'task':(d['task']['id'] if 'task' in d else d['task_id']),'original':{'elf':o['elf'],'mangled':name},'input':c,'observed':result}
    if native:row['native_memory']=native
    rows.append(row)
 out={'ranges':ranges,'cases':rows,'scope':'Original app instructions only. All provider/libc/Curl/OS/thread boundaries captured, no native syscalls. Core bodies excluded. Independent host provider observations required for modeled boundaries. Exception landing pads excluded.'}
 text=json.dumps(out,indent=2)+'\n';dest=BASE/'fixtures.json'
 if '--verify' in argv:
  if task_filter:
   expected=json.loads(dest.read_text());ids={(o['elf'],o['mangled']) for o in ranges};assert rows and rows==[c for c in expected['cases'] if c['task']==task_filter];assert ranges==[o for o in expected['ranges'] if (o['elf'],o['mangled']) in ids]
  else:assert dest.read_text()==text
 else:dest.write_text(text)
 print(len(rows),'original cases')
if __name__=='__main__':main()
