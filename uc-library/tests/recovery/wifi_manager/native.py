#!/usr/bin/env python3
"""Offline ARM range oracle. Core/libc and effect boundaries are intercepted.
No original Core bodies, process commands, firmware file access or devices run.
Fixtures record bounded state and control/command observations, not full hardware.
"""
import hashlib,json,pathlib,struct,sys,re
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
PACKETS=ROOT/'temp/recovery-work/sqlite-issued/packet-sol61'
ELFS={'client':ROOT/'rootfs/CS18_v13840/home/root/surface','server':ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer'}
REG=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
CACHE={}
class Oracle:
 def __init__(self,role):
  self.role=role;self.raw=ELFS[role].read_bytes();self.elf=ELFFile(open(ELFS[role],'rb'));self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);self.u.mem_map(0x8000,0x800000);self.u.mem_map(0x10000000,0x400000);self.u.mem_map(0x20000000,0x1000)
  for s in self.elf.iter_segments():
   if s['p_type']=='PT_LOAD':self.u.mem_write(s['p_vaddr'],s.data())
  if role in CACHE:
   self.symbols,self.names,self.records,self.symbol_ranges=CACHE[role]
  else:
   self.symbols={};self.names={};self.symbol_ranges={}
   for section in self.elf.iter_sections():
    if section['sh_type'] in ('SHT_SYMTAB','SHT_DYNSYM'):
     for s in section.iter_symbols():
      if s['st_value'] and s.name:self.symbols[s.name.split('@')[0]]=s['st_value'];self.names.setdefault(s['st_value'],[]).append(s.name.split('@')[0])
      if s['st_value'] and 'WIFIManager' in s.name:self.symbol_ranges.setdefault(s.name.split('@')[0],[]).append((s['st_value'],s['st_size'],s['st_shndx']))
   self.records=[]
   full_digest=hashlib.sha256(self.raw).hexdigest()
   for f in sorted(PACKETS.glob('*/CONTEXT.json')):
    d=json.loads(f.read_text())
    for row in d['originals']:
     o=row['original']
     if o['role']==role:
      assert full_digest==o['elf'];assert (o['address'],o['size'],o['section']) in self.symbol_ranges[o['mangled']],('ELF symbol-table identity mismatch',o['mangled'])
      section=self.elf.get_section(o['section']);off=section['sh_offset']+o['address']-section['sh_addr'];assert off==o['file_offset'];b=self.raw[off:off+o['size']];assert b.hex()==o['range_hex'] and hashlib.sha256(b).hexdigest()==o['range_sha256'];self.records.append(o)
   CACHE[role]=(self.symbols,self.names,self.records,self.symbol_ranges)
  self.targets={o['mangled']:o for o in self.records};self.obj=0x10010000;self.task=0x10011000;self.heap=0x10100000;self.trace=[];self.file_buffers={};self.file_handles={};self.mode={};self.u.hook_add(UC_HOOK_CODE,self.hook)
  self.write(self.obj,b'\0'*0x400);self.write(self.obj+0x130,b'None\0');self.write(self.obj+0x25c,b'169.254.0.100\0');self.write(self.obj+0x30,b'Store to Join\0');self.put(self.obj+0x258,0x10018000);self.put(0x10018000,self.symbols['_ZTVN4Core8Portable16BackgroundWorkerE']+8)
  self.put(self.symbols['_ZN4Core8Portable9SingletonIN8Presonus11WIFIManagerEE11theInstanceE'],self.obj)
  # Runtime filename produced by original constructor for fixed test temp directory.
  self.scratch=self.symbols.get('_ZZN8Presonus11WIFIManagerC4EvE',0)
  self.write(0x26cf74 if role=='client' else 0x497c78,b'temp/wifi/scan.txt\0')
 def write(self,a,b):self.u.mem_write(a,b)
 def put(self,a,n):self.write(a,struct.pack('<I',n&0xffffffff))
 def get(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def string(self,a):
  if not a:return ''
  b=bytearray()
  for i in range(8192):
   c=self.u.mem_read(a+i,1)[0]
   if not c:break
   b.append(c)
  return b.decode('utf8','surrogateescape')
 def copystr(self,a,s,size):self.write(a,s.encode('utf8','surrogateescape')[:size-1]+b'\0')
 def alloc(self,n):p=self.heap;self.heap+=(n+15)&~15;self.write(p,b'\0'*n);return p
 def ret(self,n=0):self.u.reg_write(UC_ARM_REG_R0,n&0xffffffff);self.u.reg_write(UC_ARM_REG_PC,self.u.reg_read(UC_ARM_REG_LR))
 def hook(self,u,a,size,_):
  if a==0x20000000:u.emu_stop();return
  names=self.names.get(a,[]);name=next((n for n in names if not n.startswith('$')),None)
  if not name:
   ranges=self.records+getattr(self,'native_app_ranges',[])
   if not any(row['address']<=a<row['address']+row['size'] for row in ranges):raise RuntimeError('Execution left verified application ranges at '+hex(a))
   return
  if a==self.entry:return
  # Only native application state bodies explicitly allowed to run transitively.
  if name in self.allow or (self.mode.get('native_commands') and ('8PipeTask9doCommand' in name or '8PipeTask6pipeOK' in name)):return
  r=[u.reg_read(x) for x in REG];s=lambda i:self.string(r[i]);result=0
  if name.startswith('_ZN4Core8Portable9SingletonIN8Presonus11WIFIManagerEE8instance'):result=self.obj
  elif 'Core' in name and ('CoreLock' in name or 'ScopedLock' in name):pass
  elif name in ('strlen',):result=len(s(0))
  elif name in ('strcmp','strcasecmp'):
   x,y=s(0),s(1);x,y=(x.lower(),y.lower()) if name=='strcasecmp' else (x,y);result=(x>y)-(x<y)
  elif name=='strstr':
   k=s(0).find(s(1));result=r[0]+k if k>=0 else 0
  elif name=='strncpy':self.write(r[0],s(1).encode()[:r[2]].ljust(r[2],b'\0'));result=r[0]
  elif name=='strncat':self.write(r[0]+len(s(0)),s(1).encode()[:r[2]]+b'\0');result=r[0]
  elif name in ('memcpy','memmove'):self.write(r[0],bytes(u.mem_read(r[1],r[2])));result=r[0]
  elif name.startswith('_Znwj'):result=self.alloc(r[0])
  elif name.startswith('_ZdlPv'):self.trace.append(['delete',0 if r[0] in (self.task,self.obj) else 'owned'])
  elif 'CStringBufferILi' in name and ('C1E' in name or 'C2E' in name):
   import re
   n=int(re.search(r'CStringBufferILi(\d+)E',name).group(1));self.copystr(r[0],s(1),n);result=r[0]
  elif 'MutableCStringTraits' in name and '4initEPKc' in name:
   import re
   n=int(re.search(r'CStringBufferILi(\d+)E',name).group(1));self.copystr(r[0],s(1),n);result=r[0]
  elif 'MutableCStringTraits' in name and '6appendEPKci' in name:
   import re
   n=int(re.search(r'CStringBufferILi(\d+)E',name).group(1));text=s(1);self.copystr(r[0],s(0)+(text if r[2]==0xffffffff else text[:r[2]]),n);result=r[0]
  elif 'appendFormat' in name:
   # Native printf format lives in sealed ELF, operands in original registers.
   import re
   fmt=s(1);values=iter(r[2:]);signed=lambda v:v if v<0x80000000 else v-0x100000000;text=re.sub(r'%([ds])',lambda m:self.string(next(values)) if m[1]=='s' else str(signed(next(values))),fmt);n=int(re.search(r'CStringBufferILi(\d+)E',name).group(1));self.copystr(r[0],s(0)+text,n);result=r[0]
  elif 'Vector' in name and '6resizeEi' in name:
   count=r[1];old=self.get(r[0]+4);oldcap=self.get(r[0]+12);p=self.alloc(max(count,1)*4)
   if old:self.write(p,bytes(u.mem_read(old,min(oldcap,count)*4)))
   self.put(r[0]+4,p);self.put(r[0]+12,count);result=1
  elif 'Vector' in name and ('D1Ev' in name or 'D2Ev' in name):pass
  elif 'sleepEj' in name:self.trace.append(['sleep',r[0]])
  elif '9FileUtils10deleteFile' in name:self.trace.append(['remove',s(0)]);result=1
  elif name=='system':
   self.trace.append(['command',s(0)]);result=self.mode.get('system',0)
   if s(0).startswith('wpa_cli '):
    seq=self.mode.get('responses',[]);self.mode['current_response']=seq.pop(0) if seq else True
  elif '9FileUtils10fileExists' in name:result=int(self.mode.get('exists',False))
  elif '16BackgroundWorker7addTask' in name:
   v=self.get(r[1]);kind=next((k for k in ['ScanWIFITask','ActiveNetworkTask','ReconnectTask','DisconnectTask','JoinNetworkTask','ConfigNetworkTask','StaticIpFailoverTask'] if any(k in n and a+8==v for n,a in self.symbols.items() if n.startswith('_ZTV'))),'unknown');self.trace.append(['queued',kind]);result=0
  elif '16BackgroundWorker9terminate' in name:self.trace.append(['terminate'])
  elif 'MemoryStreamC' in name:pass
  elif 'SimpleReaderC' in name:pass
  elif 'SimpleReader17advanceToNextChar' in name:result=int(bool(self.mode.get('words')))
  elif 'SimpleReader11getNextLine' in name:
   lines=self.mode.get('read_lines',[]);result=int(bool(lines))
   if lines:self.copystr(r[1],lines.pop(0),256)
  elif 'SimpleReader11getNextWord' in name:
   words=self.mode.get('words',[]);result=int(bool(words))
   if words:self.copystr(r[1],words.pop(0),64)
  elif '2IO6BufferD' in name:pass
  elif name=='__aeabi_ldivmod':
   numerator=r[0]+(r[1]<<32);denominator=r[2]+(r[3]<<32);result=numerator//denominator;u.reg_write(UC_ARM_REG_R1,result>>32);result&=0xffffffff
  elif 'FileUtils10getTempDir' in name:result=0x1001d000;self.copystr(result,'temp/wifi',128)
  elif '16BackgroundWorkerC' in name:
   self.put(r[0],self.symbols['_ZTVN4Core8Portable16BackgroundWorkerE']+8);result=r[0]
  elif '16BackgroundWorkerD' in name:self.trace.append(['worker-delete'])
  elif 'getLocalIPAddressList' in name:result=0
  elif name=='__cxa_guard_acquire':result=1
  elif name=='__cxa_guard_release':self.put(r[0],1)
  elif 'FileStreamC' in name:self.mode['read_lines']=['OK' if self.mode.get('current_response',True) else 'FAIL']
  elif 'FileStream4open' in name:result=int(self.mode.get('exists',False))
  elif 'FileStreamD' in name:pass
  elif name=='fopen':
   path=s(0);result=0 if self.mode.get('write_fail') else 0x1001e000;self.file_buffers[result]='';self.file_handles[result]=path
  elif name=='fputs':self.file_buffers[r[1]]+=s(0)
  elif name=='fprintf':self.file_buffers[r[0]]+=s(2)+'\n'
  elif name=='fclose':self.trace.append(['write',self.file_handles[r[0]],self.file_buffers[r[0]]])
  elif name=='popen':self.trace.append(['pipe',s(0)]);result=0
  elif 'GetAbsoluteTime' in name:u.reg_write(UC_ARM_REG_R1,0);result=0
  elif 'DebugPrintf' in name:pass
  elif name in self.mode.get('hooks',{}):
   result=self.mode['hooks'][name];self.trace.append(['boundary',name,s(1) if r[1] else '',r[2]])
  elif 'WIFIManager8PipeTask9doCommand' in name:self.trace.append(['task-command',s(1),r[2] if r[2]<0x80000000 else r[2]-0x100000000]);result=self.mode.get('command_result',0)
  elif 'WIFIManager8PipeTask6pipeOK' in name:result=self.mode.get('pipe_result',0)
  else:raise RuntimeError('Unintercepted boundary '+name+' at '+hex(a))
  self.ret(result)
 def call(self,name,args=(),mode=None):
  self.entry=self.targets[name]['address'];self.mode=mode or {};self.trace=[];self.allow={n for n in self.targets if any(v in n for v in ('16setStatusMessage','14resetStatusMsg','16setActiveNetwork','9getWifiIP','13getEthernetIP','5getIPEv','7setNoneEv','8PipeTask9setStatus','6doScanEb','17ConfigNetworkTask6config','4findEPKc'))}
  self.u.reg_write(UC_ARM_REG_SP,0x103f0000);self.u.reg_write(UC_ARM_REG_LR,0x20000000)
  for i,v in enumerate(args):
   if i<4:self.u.reg_write(REG[i],v)
   else:self.put(0x103f0000+(i-4)*4,v)
  self.u.emu_start(self.entry,0,count=100000)
  assert self.u.reg_read(UC_ARM_REG_PC)==0x20000000
  return self.u.reg_read(UC_ARM_REG_R0)
def generate():
 rows=[];ranges=[]
 for role in ELFS:
  o=Oracle(role);ranges.extend(o.records)
  for method,offset in [('setStatusMessage',0x30),('setActiveNetwork',0x130),('setStaticIp',0x25c)]:
   name=next(n for n in o.targets if method in n)
   for value in ['', 'None','Ethernet','hello','x'*31,'x'*32,'x'*63,'x'*127,'x'*255,'x'*256,'x'*300,None]:
    q=Oracle(role);q.write(0x10012000,(value or '').encode()+b'\0');q.call(name,[q.obj,0 if value is None else 0x10012000]);rows.append({'role':role,'method':method,'value':value,'result':q.string(q.obj+offset),'dirty':bool(q.u.mem_read(q.obj+0x24,1)[0]),'trace':q.trace,'mangled':name})
  for value in ['None','','Ethernet','wifi']:
   q=Oracle(role);q.copystr(q.obj+0x130,value,256);name=next(n for n in q.targets if '8isActiveEv' in n);r=q.call(name,[q.obj]);rows.append({'role':role,'method':'isActive','value':value,'result':r,'mangled':name})
  for kind in ['ReconnectTask','DisconnectTask']:
   name=next(n for n in o.targets if kind in n and '4workEv' in n)
   for result in [0,1]:
    q=Oracle(role);q.put(q.obj+0x20,9);q.call(name,[q.task],{'command_result':result});rows.append({'role':role,'method':kind,'command_result':result,'result':q.get(q.obj+0x20),'status':q.string(q.obj+0x30),'trace':q.trace,'mangled':name})
  name=next(n for n in o.targets if '8PipeTask9doCommand' in n)
  for command,n in [('status',-1),('scan',0),('x'*63,1234),('x'*80,-1),('x'*60,-123),('',-1)]:
   q=Oracle(role);q.write(0x10012000,command.encode()+b'\0');r=q.call(name,[q.task,0x10012000,n&0xffffffff]);rows.append({'role':role,'method':'doCommand','value':command,'n':n,'result':r,'trace':q.trace,'mangled':name})
  for marker,method in [('14resetStatusMsg','resetStatusMsg'),('15adaptersChanged','adaptersChanged'),('7doAdHoc','doAdHoc'),('4findE','find'),('9terminateEv','terminate'),('6onIdleEv','onIdle'),('7setNoneEv','setNone'),('8PipeTask9setStatus','setStatus'),('6pipeOKEi','pipeOK'),('9getWifiIP','getWifiIP'),('13getEthernetIP','getEthernetIP'),('5getIPEv','getIP')]:
   q=Oracle(role);name=next(n for n in q.targets if marker in n);q.copystr(q.obj+0x30,'changed',256);q.write(0x10012000,b'test-status\0');r=q.call(name,[q.task if method in ('setNone','setStatus','pipeOK') else q.obj,0x10012000]);rows.append({'role':role,'method':method,'result':q.string(r) if method.startswith('get') else (r if method in ('doAdHoc','find','pipeOK') else 0),'status':q.string(q.obj+0x30),'active':q.string(q.obj+0x130),'adapter_dirty':bool(q.u.mem_read(q.obj+0x25,1)[0]),'trace':q.trace,'mangled':name})
  for marker,method in [('17ActiveNetworkTask4work','ActiveNetworkTask'),('12ScanWIFITask4work','ScanWIFITask'),('20StaticIpFailoverTask4work','StaticIpFailoverTask')]:
   q=Oracle(role);name=next(n for n in q.targets if marker in n);q.call(name,[q.task],{'native_commands':True});rows.append({'role':role,'method':method,'status':q.string(q.obj+0x30),'active':q.string(q.obj+0x130),'trace':q.trace,'mangled':name})
  for n in o.targets:
   if any(x in n for x in ('D0Ev','D1Ev','D2Ev')) and 'WIFIManagerD' not in n:
    q=Oracle(role);q.copystr(q.obj+0x30,'changed',256);q.call(n,[q.task]);rows.append({'role':role,'method':'destructor','status':q.string(q.obj+0x30),'trace':q.trace,'mangled':n})
  for n in o.targets:
   if 'WIFIManagerC1Ev' in n or 'WIFIManagerC2Ev' in n:
    q=Oracle(role);q.call(n,[q.obj]);rows.append({'role':role,'method':'constructor','status':q.string(q.obj+0x30),'active':q.string(q.obj+0x130),'static_ip':q.string(q.obj+0x25c),'scratch':q.string(0x26cf74 if role=='client' else 0x497c78),'trace':q.trace,'mangled':n})
  name=next(n for n in o.targets if '11NetworkItem7hasFlag' in n)
  for flags,word in [('', 'WEP'),('[WEP][ESS]','WEP'),('[WPA2-PSK-CCMP][ESS]','PSK'),('[ESS]','WEP'),('[ESS]',None)]:
   import re
   q=Oracle(role);q.copystr(q.task+0xc0,flags,64);q.copystr(0x10012000,word or '',64);r=q.call(name,[q.task,0 if word is None else 0x10012000],{'words':re.findall(r'\[([^]]*)\]',flags)});rows.append({'role':role,'method':'hasFlag','flags':flags,'value':word,'result':r,'status':q.string(q.obj+0x30),'trace':q.trace,'mangled':name})
  name=next(n for n in o.targets if '15JoinNetworkTask4work' in n)
  for wep,encrypted,responses in [(False,False,[0,1,1,1,1]),(False,False,[1,1,0]),(False,False,[0,0]),(False,False,[0,1,0]),(False,False,[0,1,1,0]),(True,True,[0,1,1,0]),(False,True,[0,1,0]),(False,True,[0,1,1,0]),(True,True,[0,1,1,1,1,1]),(False,True,[0,1,1,1,1,1])]:
   q=JoinPositive(role,{});q.copystr(q.task+0x10,'Test SSID',64);q.copystr(q.task+0x50,'Test key',64);q.write(q.task+0x90,bytes([wep,encrypted]));q.call(name,[q.task],{'native_commands':True,'exists':True,'responses':responses.copy()});rows.append({'role':role,'method':'joinWork','original_parser_ranges':q.native_app_ranges,'original_parser_entries':q.executed_apps,'wep':wep,'encrypted':encrypted,'responses':responses,'result':q.get(q.obj+0x20),'status':q.string(q.obj+0x30),'active':q.string(q.obj+0x130),'trace':q.trace,'mangled':name})
  for marker,method in [('9reconnectEv','reconnect'),('10disconnectEv','disconnect'),('9probeEth0Ev','probeEth0'),('7addTaskE','addTask'),('6doScanEb','doScan'),('12resetNetworkE','resetNetwork'),('13configNetworkE','configNetwork'),('6doJoinE','doJoin'),('10updateListE','updateList'),('15setNetworkItemsE','setNetworkItems'),('11addDelegateE','addDelegate'),('14removeDelegateE','removeDelegate'),('10isEthernetEv','isEthernet'),('17ConfigNetworkTask4work','configWork')]:
   q=Oracle(role);name=next(n for n in q.targets if marker in n);q.put(q.task,q.symbols['_ZTVN8Presonus11WIFIManager13ReconnectTaskE']+8);q.copystr(0x10012000,'test',64)
   args=[q.obj,0x10012000,0x10012000,0x10012000,0x10012000,0,0]
   if method=='doScan':args=[q.obj,1]
   if method=='addTask':args=[q.obj,q.task]
   if method=='resetNetwork':args=[q.obj,0x10012000,0x10012000,1]
   if method=='updateList':args=[q.obj,0,0,0,0]
   if method=='setNetworkItems':args=[q.obj,0x10015000]
   if method in ('isEthernet','configWork'):args=[q.task];q.write(q.task,b'\0'*0x200)
   r=q.call(name,args,{'write_fail':True});rows.append({'role':role,'method':method,'result':r if method in ('doJoin','resetNetwork','isEthernet') else 0,'status':q.string(q.obj+0x30),'active':q.string(q.obj+0x130),'trace':q.trace,'mangled':name,'adapter_dirty':bool(q.u.mem_read(q.obj+0x25,1)[0]),'delegates':q.get(q.obj+0x24c)})
  for n in o.targets:
   if any(t in n for t in ('WIFIManagerD0Ev','WIFIManagerD1Ev','WIFIManagerD2Ev')):
    q=Oracle(role);q.call(n,[q.obj]);rows.append({'role':role,'method':'managerDestructor','status':q.string(q.obj+0x30),'active':q.string(q.obj+0x130),'trace':q.trace,'mangled':n})
  name=next(n for n in o.targets if '17ConfigNetworkTask6config' in n)
  for dynamic in [False,True]:
   for gateway in ['', '10.0.0.1']:
    for fail in [False,True]:
     q=Oracle(role);q.copystr(q.task+0x10,'eth0',32);q.copystr(q.task+0x30,'10.0.0.2',32);q.copystr(q.task+0x50,'',32);q.copystr(q.task+0x70,gateway,32);q.write(q.task+0x90,bytes([dynamic,0]));q.call(name,[q.task],{'write_fail':fail});rows.append({'role':role,'method':'config','dynamic':dynamic,'gateway':gateway,'write_fail':fail,'status':q.string(q.obj+0x30),'trace':q.trace,'subnet':q.string(q.task+0x50),'mangled':name})
 return {'version':1,'domain':'Original ARM execution for state setters, active predicate, reconnect/disconnect control and command serialization. File-exists boundary false; Core and libc intercepted, no Core body execution. No host effects.','ranges':[{k:v for k,v in row.items() if k!='range_hex'} for row in ranges],'cases':rows,'producer_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}

import types
base=types.SimpleNamespace(Oracle=Oracle,REG=REG,ELFS=ELFS)
PARSER_RANGES={}
class Positive(base.Oracle):
 def __init__(self,role,files,addresses=()):
  super().__init__(role);self.files=files;self.streams={};self.addresses=list(addresses);self.iprefs={};self.published=[];self.native_app_ranges=[];self.executed_apps={}
  for offset,address in [(8,0x10081000),(12,0x10081004),(16,0x10081008)]:self.put(0x10080000+offset,address)
  if role in PARSER_RANGES:self.native_app_ranges=PARSER_RANGES[role];return
  for section in self.elf.iter_sections():
   if section['sh_type']=='SHT_SYMTAB':
    for sym in section.iter_symbols():
     if 'Presonus12SimpleReader' in sym.name and any(k in sym.name for k in ('C1E','C2E','11getNextLine','11getNextWord','17advanceToNext')):
      a=sym['st_value'];n=sym['st_size'];section=self.elf.get_section(sym['st_shndx']);offset=section['sh_offset']+a-section['sh_addr'];self.native_app_ranges.append({'mangled':sym.name,'address':a,'size':n,'file_offset':offset,'section':sym['st_shndx'],'range_sha256':hashlib.sha256(self.raw[offset:offset+n]).hexdigest()})
  PARSER_RANGES[role]=self.native_app_ranges
 def hook(self,u,a,size,_):
  r=[u.reg_read(x) for x in base.REG];names=self.names.get(a,[]);name=next((n for n in names if not n.startswith('$')),None)
  if a==self.entry:return
  if a in (0x10081000,0x10081004,0x10081008):
   state=self.streams[r[0]]
   if a==0x10081000:u.reg_write(UC_ARM_REG_R1,0);self.ret(state['position'])
   elif a==0x10081004:
    mode=self.get(u.reg_read(UC_ARM_REG_SP));offset=r[2]+(r[3]<<32);offset=offset if offset<(1<<63) else offset-(1<<64);state['position']=offset+(0 if mode==0 else state['position'] if mode==1 else len(state['data']));u.reg_write(UC_ARM_REG_R1,0);self.ret(state['position'])
   else:
    data=state['data'][state['position']:state['position']+r[2]];self.write(r[1],data);state['position']+=len(data);self.ret(len(data))
   return
  if name and 'Presonus12SimpleReader' in name:self.executed_apps[name]=self.executed_apps.get(name,0)+1;return # actual original application instructions
  if name and ('15setNetworkItems' in name or '17ActiveNetworkTask10isEthernet' in name):return
  if name and 'FileStreamC' in name:
   self.put(r[0],0x10080000);self.streams[r[0]]={'data':b'','position':0};self.ret(r[0]);return
  if name and 'FileStream4open' in name:
   data=self.files.get(self.string(r[1]));self.streams[r[0]]={'data':(data or '').encode(),'position':0};self.ret(data is not None);return
  if name and '9FileUtils10fileExists' in name:self.ret(self.string(r[0]) in self.files);return
  if name=='sscanf':
   import re
   match=re.match(r'\s*([+-]?\d+)',self.string(r[0]));result=0
   if match:self.write(r[2],struct.pack('<q',int(match[1])));result=1
   self.ret(result);return
  if name and 'CStringTraits' in name and '7compare' in name:
   s,t=self.string(r[0]),self.string(r[1]);self.ret((s>t)-(s<t));return
  if name and 'getLocalIPAddressList' in name:
   for i,item in enumerate(self.addresses[:r[1]]):self.iprefs[r[0]+i*36]=item
   self.ret(min(len(self.addresses),r[1]));return
  if name and 'getInterfaceNameForIP' in name:self.copystr(r[0],self.iprefs[r[1]][0],32);self.ret(1);return
  if name and 'getAddressString' in name:self.copystr(r[0],self.iprefs[r[1]][1],256);self.ret(1);return
  super().hook(u,a,size,_)
 def snapshot(self):
  p=self.get(self.obj+0x234);n=self.get(self.obj+0x238);return [[self.string(self.get(p+i*4)+off) for off in (0,64,128,192,256)] for i in range(n)]
def generate_positive():
 out=[]
 scratch='temp/wifi/scan.txt';ifconfig='temp/wifi/ifconfig_tmp.txt'
 scan_inputs=[
 'bssid / frequency / signal level / flags / ssid\n00:11:22:33:44:55\t2412\t-42\t[WPA2-PSK-CCMP][ESS]\tStudio\n66:77:88:99:aa:bb\t5200\t-50\t[ESS]\tGuest\n',
 '00:11:22:33:44:55\t2412\t-42\t[ESS]\tStudio\n66:77:88:99:aa:bb\t5200\t-80\t[ESS]\tStudio\n',
 'not-a-network\n00:11:22:33:44:55\t2412\t-42\t[ESS]\tRoom\n',
 '00:11:22:33:44:55\t2412\t-42\t[ESS]\t\n',
 '00:11:22:33:44:55\t2412\t-42\t[ESS]\t'+'x'*70+'\n']
 for role in base.ELFS:
  for text in scan_inputs:
   q=Positive(role,{scratch:text});name=next(n for n in q.targets if '12ScanWIFITask4work' in n);q.call(name,[q.task],{'native_commands':True});out.append({'role':role,'method':'scanPositive','mangled':name,'input':text,'published':q.snapshot(),'status':q.string(q.obj+0x30),'trace':q.trace,'original_parser_ranges':q.native_app_ranges})
  for status,iftext,addresses in [('wpa_state=COMPLETED\nssid=Studio\n','inet addr:10.0.0.2 Bcast:10.0.0.255\n',[('wlan0','10.0.0.2')]),('wpa_state=COMPLETED\nssid=Studio\n','inet addr:10.0.0.3 Bcast:10.0.0.255\n',[('wlan0','10.0.0.2')]),('ssid=Studio\n','inet addr:10.0.0.3 Bcast:10.0.0.255\n',[('eth0','10.0.0.3')]),('wpa_state=DISCONNECTED\n','',[]),('wpa_state=DISCONNECTED\n','inet addr:10.0.0.3 Bcast:10.0.0.255\n',[('wlan0','10.0.0.2')]),('ssid=\n','inet addr:10.0.0.3 Bcast:10.0.0.255\n',[('wlan0','10.0.0.2')]),('xssid=Wrong\nssid=First\nssid=Second\n','inet addr:10.0.0.3 Bcast:10.0.0.255\n',[('wlan0','10.0.0.2')]),('ssid=CR Name\r\n','inet addr:10.0.0.3 Bcast:10.0.0.255\n',[('wlan0','10.0.0.2')]),('ssid=No Newline','inet addr:10.0.0.3 Bcast:10.0.0.255\n',[('wlan0','10.0.0.2')])]:
   q=Positive(role,{scratch:status,ifconfig:iftext},addresses);name=next(n for n in q.targets if '17ActiveNetworkTask4work' in n);q.call(name,[q.task],{'native_commands':True});out.append({'role':role,'method':'activePositive','mangled':name,'input':status,'ifconfig':iftext,'addresses':addresses,'active':q.string(q.obj+0x130),'status':q.string(q.obj+0x30),'trace':q.trace,'original_parser_ranges':q.native_app_ranges})
  for iftext,addresses in [('inet addr:10.0.0.20 Bcast:test\n',[('wlan0','10.0.0.2')]),('inet addr:0.0 Bcast:test\n',[('wlan0','10.0.0.2')]),('inet addr:x10.0.0.2 Bcast:test\n',[('wlan0','10.0.0.2')]),('inet addr:10.0.0.2 Bcast:test\n',[]),('missing marker\n',[]),('missing marker\n',[('wlan0','10.0.0.2')]),('',[])]:
   q=Positive(role,{ifconfig:iftext},addresses);name=next(n for n in q.targets if '17ActiveNetworkTask10isEthernet' in n);result=q.call(name,[q.task],{'native_commands':True});out.append({'role':role,'method':'isEthernetPositive','mangled':name,'input':'','ifconfig':iftext,'addresses':addresses,'result':result,'active':q.string(q.obj+0x130),'status':q.string(q.obj+0x30),'trace':q.trace,'original_parser_ranges':q.native_app_ranges})
 return out

class JoinPositive(Positive):
 def hook(self,u,a,size,unused):
  name=next((n for n in self.names.get(a,[]) if not n.startswith('$')),None)
  if name=='system':
   command=self.string(u.reg_read(UC_ARM_REG_R0))
   if command.startswith('wpa_cli '):
    responses=self.mode.get('responses',[]);ok=responses[0] if responses else True;self.files['temp/wifi/scan.txt']='OK\n' if ok else 'FAIL\n'
  super().hook(u,a,size,unused)

class Network(Positive):
 def hook(self,u,a,size,_):
  names=self.names.get(a,[]);name=next((n for n in names if not n.startswith('$')),None);r=[u.reg_read(x) for x in REG]
  if name and '11NetworkItem7hasFlag' in name:return
  if name and 'MemoryStreamC' in name:
   self.put(r[0],0x10080000);self.streams[r[0]]={'data':bytes(u.mem_read(r[1],r[2])),'position':0};self.ret(r[0]);return
  if name=='popen':self.trace.append(['pipe',self.string(r[0]),self.string(r[1])]);self.ret(0 if self.mode.get('pipe_fail') else 0x1001f000);return
  if name=='pclose':self.trace.append(['pipe-close']);self.ret(0);return
  if name=='fgets':
   text=self.mode.get('pipe_data','');self.copystr(r[0],text,r[1]);self.ret(r[0] if text else 0);return
  if name and '16BackgroundWorker7addTask' in name:
   v=self.get(r[1]);kind=next((k for k in ('JoinNetworkTask','ActiveNetworkTask') if self.symbols.get('_ZTVN8Presonus11WIFIManager'+str(len(k))+k+'E',0)+8==v),'unknown')
   row=['queued',kind]
   if kind=='JoinNetworkTask':row += [self.string(r[1]+0x10),self.string(r[1]+0x50),list(u.mem_read(r[1]+0x90,2))]
   self.trace.append(row);self.ret(0);return
  super().hook(u,a,size,_)
def generate_network_positive():
 rows=[];ranges=[]
 for role in ELFS:
  for marker in ('9getWifiIP','13getEthernetIP','5getIPEv'):
   for active in ('Ethernet','Studio'):
    for ips in ([('eth0','10.0.0.2'),('wlan0','10.0.0.3')],[('wlan0','10.0.0.3'),('eth0','10.0.0.2')],[('lo','127.0.0.1'),('wlan0','10.0.0.3')]):
     q=Network(role,{},ips);n=next(n for n in q.targets if marker in n);q.copystr(q.obj+0x130,active,256);v=q.call(n,[q.obj]);rows.append({'role':role,'method':{'9getWifiIP':'getWifiIPPositive','13getEthernetIP':'getEthernetIPPositive','5getIPEv':'getIPPositive'}[marker],'mangled':n,'active':active,'addresses':ips,'result':q.string(v),'status':q.string(q.obj+0x30),'trace':q.trace})
  for flags in ('[ESS]','[WEP][ESS]','[WPA2-PSK-CCMP][ESS]','[WPA-PSK-TKIP][ESS]'):
   q=Network(role,{});n=next(n for n in q.targets if '6doJoinE' in n);item=q.alloc(320);q.copystr(item+0xc0,flags,64);q.copystr(item+0x100,'Studio',64);vec=q.alloc(4);q.put(vec,item);q.put(q.obj+0x234,vec);q.put(q.obj+0x238,1);q.copystr(0x10012000,'Studio',64);q.copystr(0x10013000,'Password',64);v=q.call(n,[q.obj,0x10012000,0x10013000]);rows.append({'role':role,'method':'doJoinPositive','mangled':n,'flags':flags,'status':q.string(q.obj+0x30),'result':v,'trace':q.trace,'original_parser_entries':q.executed_apps})
  for pipe,writefail,pfail in [('',False,False),('10.0.0.2\n',False,False),('',True,False),('',False,True)]:
   q=Network(role,{});n=next(n for n in q.targets if '20StaticIpFailoverTask4work' in n);q.copystr(q.task+0x10,'eth0',32);q.copystr(q.task+0x30,'169.254.2.3',32);q.call(n,[q.task],{'pipe_data':pipe,'write_fail':writefail,'pipe_fail':pfail});rows.append({'role':role,'method':'failoverPositive','mangled':n,'pipe_data':pipe,'write_fail':writefail,'pipe_fail':pfail,'delegates':0,'status':q.string(q.obj+0x30),'adapter_dirty':bool(q.u.mem_read(q.obj+0x25,1)[0]),'trace':q.trace})
  ranges += [{k:v for k,v in o.items() if k!='range_hex'} for o in q.records if any(m in o['mangled'] for m in ('6doJoinE','20StaticIpFailoverTask4work','9getWifiIP','13getEthernetIP','5getIPEv'))]
 return rows

class Lists(Positive):
 def __init__(self,role):
  super().__init__(role,{});self.lists={};self.events=[];self.now=0;self.deletes=[]
  self.put(0x10082000+0x5c,0x10083000)
  self.put(0x10084000,0x10085000);self.put(0x10084004,0x10085004)
 def hook(self,u,a,size,_):
  r=[u.reg_read(x) for x in base.REG];name=next((n for n in self.names.get(a,[]) if not n.startswith('$')),None)
  if a==0x10083000:self.events.append(['param-setValue',r[0],r[1]]);self.ret();return
  if a in (0x10085000,0x10085004):self.events.append(['delegate-state' if a==0x10085000 else 'delegate-adapters',r[0],r[1],self.u.mem_read(self.obj+0x24,2).hex()]);self.ret();return
  if name and 'MemoryStreamC' in name:
   self.put(r[0],0x10080000);self.streams[r[0]]={'data':bytes(u.mem_read(r[1],r[2])),'position':0};self.ret(r[0]);return
  if name and any(k in name for k in ['11NetworkItem7hasFlag','6doScanEb']):return
  if name and 'ListParam9removeAll' in name:self.lists[r[0]]=[];self.events.append(['removeAll',r[0]]);self.ret();return
  if name and 'ListParam12appendString' in name:self.lists.setdefault(r[0],[]).append(self.string(r[1]));self.events.append(['append',r[0],self.string(r[1])]);self.ret();return
  if name and ('Parameter7changed' in name or 'Parameter12rangeChanged' in name):self.events.append(['changed' if '7changed' in name else 'rangeChanged',r[0]]);self.ret();return
  if name and 'GetAbsoluteTime' in name:u.reg_write(UC_ARM_REG_R1,self.now>>32);self.ret(self.now);return
  if name and name.startswith('_ZdlPv'):self.deletes.append(r[0])
  super().hook(u,a,size,_)
 def item(self,fields):
  p=self.alloc(320)
  for i,x in enumerate(fields):self.copystr(p+64*i,x,64)
  return p
 def vector(self,p,items,delta=5):
  q=self.alloc(max(1,len(items))*4)
  for i,x in enumerate(items):self.put(q+4*i,x)
  for off,x in [(4,q),(8,len(items)),(12,len(items)),(16,delta)]:self.put(p+off,x)
 def method(self,token):return next(n for n in self.targets if token in n)

def generate_lists_positive():
 out=[]
 for role in ELFS:
  for label,flags in [('populated',['[WPA2-PSK-CCMP][ESS]','[ESS]','[WEP][ESS]']),('all_open',['[ESS]'])]:
   q=Lists(role);items=[q.item([f'00:11:22:33:44:{i:02x}','2412',str(-40-i),f,['Studio Main','Guest','Legacy'][i]]) for i,f in enumerate(flags)];q.vector(q.obj+0x230,items)
   params=[0x10090000+i*0x100 for i in range(3)]
   for p in params:q.put(p,0x10082000);q.lists[p]=['OLD']
   n=q.method('10updateList');q.call(n,[q.obj,*params,0]);out.append({'role':role,'status':q.string(q.obj+0x30),'active':q.string(q.obj+0x130),'method':'updateListPositive','label':label,'input_flags':flags,'lists':[q.lists[p] for p in params],'events':q.events,'native_range':q.targets[n],'parser_ranges':q.native_app_ranges,'parser_entries':q.executed_apps})
  q=Lists(role);old=q.item(['old','','','','Previous']);q.vector(q.obj+0x230,[old]);new=[q.item(['b','','','','Zulu']),q.item(['a','','','','Alpha'])];v=0x10090000;q.vector(v,new,17);n=q.method('15setNetworkItems');q.call(n,[q.obj,v]);out.append({'role':role,'status':q.string(q.obj+0x30),'active':q.string(q.obj+0x130),'method':'setNetworkItemsPositive','input_names':['Zulu','Alpha'],'published':q.snapshot(),'input_ptrs':new,'output_ptrs':[q.get(q.get(q.obj+0x234)+4*i) for i in range(q.get(q.obj+0x238))],'deleted':q.deletes,'old_ptr':old,'delta':q.get(q.obj+0x240),'dirty':q.u.mem_read(q.obj+0x24,1)[0],'source_count_after':q.get(v+8),'native_range':q.targets[n]})
  for dirty,adapters,deadline,now in [(1,1,0,0),(1,0,0,0),(0,1,0,0),(0,0,1000,999000000),(0,0,1000,1000000000),(0,0,1000,1001000000)]:
   q=Lists(role);delegates=[q.alloc(4),q.alloc(4)]
   for p in delegates:q.put(p,0x10084000)
   q.vector(q.obj+0x244,delegates);q.write(q.obj+0x24,bytes([dirty,adapters]));q.put(q.obj+0x28,deadline);q.now=now;n=q.method('6onIdle');q.call(n,[q.obj]);out.append({'role':role,'status':q.string(q.obj+0x30),'active':q.string(q.obj+0x130),'method':'onIdlePositive','input':{'dirty':dirty,'adapters':adapters,'deadline':deadline,'now':now},'events':q.events,'flags_after':q.u.mem_read(q.obj+0x24,2).hex(),'deadline_after':q.get(q.obj+0x28),'trace':q.trace,'native_range':q.targets[n]})
 for case in out:
  case['mangled']=case['native_range']['mangled'];case['native_range']={k:v for k,v in case['native_range'].items() if k!='range_hex'}
  case['events_normalized']=[]
  if case['method']=='updateListPositive':
   for row in case['events']:case['events_normalized'].append([row[0],str((row[1]-0x10090000)//0x100),*[str(v) for v in row[2:]]])
  elif case['method']=='onIdlePositive':
   ids=sorted({row[1] for row in case['events']})
   for row in case['events']:case['events_normalized'].append([row[0],str(ids.index(row[1])),'manager',row[3]])
  if 'trace'not in case:case['trace']=[]
 return out

def fval(v):return struct.unpack('<f',struct.pack('<I',v))[0]
def fbits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
class Auto(Oracle):
 def hook(self,u,a,size,unused):
  names=self.names.get(a,[]);name=next((n for n in names if not n.startswith('$')),None)
  if a==getattr(self,'entry',None):return
  r=[u.reg_read(x) for x in REG]
  if name=='system':
   command=self.string(r[0]);result=(self.mode['probes'].pop(0) if command.startswith('ping ') else 0);self.trace.append(['command',command,result]);self.ret(result);return
  if name and 'appendFormat' in name:
   values=r[2:]+[self.get(u.reg_read(UC_ARM_REG_SP)+i*4) for i in range(4)];it=iter(values);fmt=self.string(r[1]);signed=lambda v:v if v<0x80000000 else v-0x100000000
   text=re.sub(r'%([ds])',lambda x:self.string(next(it)) if x[1]=='s' else str(signed(next(it))),fmt);n=int(re.search(r'CStringBufferILi(\d+)E',name)[1]);self.copystr(r[0],self.string(r[0])+text,n);self.ret(r[0]);return
  if name and 'AbsoluteTimeToSeconds' in name:
   bits=struct.unpack('<Q',struct.pack('<d',1000.0))[0];u.reg_write(UC_ARM_REG_R1,bits>>32);self.ret(bits&0xffffffff);self.trace.append(['clock-seconds',1000]);return
  if '__aeabi_d2uiz' in names or '__fixunsdfsi' in names:
   value=struct.unpack('<d',struct.pack('<II',r[0],r[1]))[0];self.ret(int(value));return
  if name=='srand':self.trace.append(['srand',r[0]]);self.ret();return
  if name=='rand':value=self.mode['rng'].pop(0);self.trace.append(['rand',value]);self.ret(value);return
  if '__aeabi_i2f' in names or '__floatsisf' in names:self.ret(fbits(r[0] if r[0]<2**31 else r[0]-2**32));return
  if '__aeabi_fmul' in names or '__mulsf3' in names:self.ret(fbits(fval(r[0])*fval(r[1])));return
  if '__aeabi_f2iz' in names or '__fixsfsi' in names:self.ret(int(fval(r[0])));return
  return super().hook(u,a,size,unused)
def generate_auto_positive():
 rows=[]
 for role in ELFS:
  for case,probes,rng in [('existing-available',[1],[]),('occupied-candidate',[0,0,1],[0,1073741824]),('twenty-occupied',[0]*21,[0]*20)]:
   q=Auto(role);q.write(q.task,b'\0'*0x200)
   for off,text in [(0x10,'eth0'),(0x30,'169.254.1.77'),(0x50,'old-mask'),(0x70,'old-gateway')]:q.copystr(q.task+off,text,32)
   q.write(q.task+0x90,b'\0\1');name='_ZN8Presonus11WIFIManager17ConfigNetworkTask6configEv';before=bytes(q.u.mem_read(q.task,0x100)).hex()
   q.call(name,[q.task],{'probes':probes.copy(),'rng':rng.copy()})
   rows.append({'role':role,'method':'configAutoPositive','mangled':name,'status':q.string(q.obj+0x30),'active':q.string(q.obj+0x130),'case':case,'input_probe_returns':probes,'input_rand_returns':rng,'before_hex':before,'after_hex':bytes(q.u.mem_read(q.task,0x100)).hex(),'address':q.string(q.task+0x30),'mask':q.string(q.task+0x50),'gateway':q.string(q.task+0x70),'flags':bytes(q.u.mem_read(q.task+0x90,2)).hex(),'trace':q.trace,'unused_probes':q.mode['probes'],'unused_rng':q.mode['rng'],'original':{k:v for k,v in q.targets[name].items() if k!='range_hex'}})
 return rows

def generate_repeated_positive():
 rows=[]
 for role in ELFS:
  for scenario in ['add','remove_first','remove_unknown','remove_last','remove_all']:
   q=Oracle(role);add=next(n for n in q.targets if '11addDelegateE' in n);remove=next(n for n in q.targets if '14removeDelegateE' in n);A,B,C=0x1001a000,0x1001a010,0x1001a020
   for p in [A,A,B]:q.call(add,[q.obj,p])
   actions=[]
   if scenario!='add':actions=[A]
   if scenario=='remove_unknown':actions=[C]
   if scenario=='remove_last':actions=[B]
   if scenario=='remove_all':actions=[A,A,B]
   for p in actions:q.call(remove,[q.obj,p])
   p=q.get(q.obj+0x248);values=[q.get(p+4*i) for i in range(q.get(q.obj+0x24c))];rows.append({'role':role,'method':'delegatePositive','scenario':scenario,'mangled':add if scenario=='add' else remove,'delegate_ids':[str([A,B,C].index(x)) for x in values],'status':q.string(q.obj+0x30),'active':q.string(q.obj+0x130),'trace':q.trace})
  for method,offset in [('setStatusMessage',0x30),('setActiveNetwork',0x130)]:
   for value in ['hello','x'*255,'x'*300]:
    q=Oracle(role);name=next(n for n in q.targets if method in n);q.copystr(0x10012000,value,512);q.call(name,[q.obj,0x10012000]);q.write(q.obj+0x24,b'\0');q.call(name,[q.obj,0x10012000]);rows.append({'role':role,'method':'repeatSetterPositive','setter':method,'value':value,'mangled':name,'result':q.string(q.obj+offset),'dirty':bool(q.u.mem_read(q.obj+0x24,1)[0]),'trace':q.trace})
 return rows
if __name__=='__main__':
 out=generate();out['cases'].extend(generate_positive());out['cases'].extend(generate_network_positive());out['cases'].extend(generate_lists_positive());out['cases'].extend(generate_auto_positive());out['cases'].extend(generate_repeated_positive());out['positive_domain']='Actual original Scan/Active/isEthernet AND SimpleReader app instructions, synthetic read/seek stream and source-provided Core/libc/effect boundaries. Positive publication fields, SSID updates and asymmetric prefix/empty/missing-marker paths.';path=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path(__file__).with_name('fixtures.json');path.write_text(json.dumps(out,indent=2)+'\n');print('native cases',len(out['cases']),'range checks',len(out['ranges']))
