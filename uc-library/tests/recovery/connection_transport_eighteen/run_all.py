"""Bounded Connection18 worker build/replay entry point; never changes CMake."""
import argparse,json,pathlib,subprocess,sys,shlex,time,datetime,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[4]
HERE=pathlib.Path(__file__).resolve().parent
WORK=ROOT/'temp/recovery-work/connection18-build'
REPLAY_EXE=WORK/'Replay'
PACKET_ROOT=ROOT/'temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/connection_eighteen_sol61/eventitem-periodic-provenance01/support-sixpaths02'
PRODUCTION=['ConnectionLifetime','ConnectionTransport','ConnectionTransportProvider','SocketConnectionLifecycle','SocketConnectionProtocol','OutgoingConnection','ExternalConnectionLifecycle','SocketConnectionIdentity','connection','connection_receive','socket_channel','external_connection','basic_connection','MulticastDatagramProvider','MulticastConnectionLifecycle','MulticastConnectionProcess','UDPDiscoveryProtocol','UDPDiscoveryLifecycle','ConnectionHandlerQueries','BasicConnectionLifetime','ClientEventValues','EventDispatcherLifetime','EventFactoryLifetime','EventQueueLifetime','NetworkManagerNextServices','RemoteEventSender','ccl_bindings','dispatcher_registration','event_dispatcher','event_factory','event_queue','MulticastSocketServices','NetworkManagerServices','NetworkActivityManager','NetworkActivityBootstrap']
RESIDUAL_SOURCES = ['uc-library/src/Presonus/Dsp/EqSourceProviders.cpp', 'uc-library/src/Presonus/Mixer/AutoFilterGroupManager.cpp', 'uc-library/src/Presonus/Mixer/GroupChangeObserver.cpp', 'uc-library/src/Presonus/Surface/GeqPresetsPageComponent.cpp', 'uc-library/src/Presonus/Surface/PresetsPageComponent.cpp', 'uc-library/src/Presonus/UC/AdapterHandlerLifetime.cpp', 'uc-library/src/Presonus/UC/AdapterServices.cpp', 'uc-library/src/Presonus/UC/BasicConnectionQueueStorage.cpp', 'uc-library/src/Presonus/UC/DiscoveryAttributes.cpp', 'uc-library/src/Presonus/UC/EventItem.cpp', 'uc-library/src/Presonus/UC/NetworkActivityBootstrap.cpp', 'uc-library/src/Presonus/UC/NetworkActivityManager.cpp', 'uc-library/src/Presonus/UC/NetworkManagerConfiguration.cpp', 'uc-library/src/Presonus/UC/NetworkManagerDiscoveryCallbacks.cpp', 'uc-library/src/Presonus/UC/NetworkManagerListeners.cpp', 'uc-library/src/Presonus/UC/NetworkManagerMulticastCallback.cpp', 'uc-library/src/Presonus/UC/NetworkManagerServices.cpp', 'uc-library/src/Presonus/UC/ReportFunctions.cpp', 'uc-library/src/Presonus/UC/ServerComponent.cpp', 'uc-library/src/Presonus/UC/ServerLifetime.cpp', 'uc-library/src/Presonus/UC/ServerMetadata.cpp', 'uc-library/src/Presonus/UC/ServerRegistrarListeners.cpp', 'uc-library/src/Presonus/UC/ServerRegistrarServices.cpp', 'uc-library/src/Presonus/UC/UDPDiscoveryServices.cpp', 'uc-library/src/Presonus/UC/discovery_events.cpp', 'uc-library/src/Presonus/UC/events.cpp', 'uc-library/src/Presonus/UC/file_control_events.cpp', 'uc-library/src/Presonus/UC/file_data_events.cpp', 'uc-library/src/Presonus/UC/meter_events.cpp', 'uc-library/src/Presonus/UC/misc_events.cpp', 'uc-library/src/Presonus/UC/no_member_events.cpp', 'uc-library/src/Presonus/UC/parameter_events.cpp', 'uc-library/src/Presonus/UC/primitive_dispatch.cpp', 'uc-library/src/Presonus/UC/transport_events.cpp', 'uc-library/src/core_uc/buffer.cpp', 'uc-library/src/mixer_dsp/AdditionalFormatters.cpp', 'uc-library/src/mixer_dsp/Formatters.cpp', 'uc-library/src/mixer_dsp/Interpolators.cpp', 'uc-library/src/mixer_dsp/Logarithm.cpp', 'uc-library/src/mixer_dsp/Power.cpp']
SOURCE_PATHS = {pathlib.Path(p).stem:p for p in RESIDUAL_SOURCES}
SOURCE_PATHS.update({n:"uc-library/src/Presonus/UC/"+n+".cpp" for n in PRODUCTION})
PRODUCTION = list(SOURCE_PATHS)
def run(args,**kw):
 args=list(map(str,args));print(shlex.join(args),flush=True)
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic();code=None
 try:
  result=subprocess.run(args,check=True,**kw);code=result.returncode;return result
 except subprocess.CalledProcessError as error:
  code=error.returncode;raise
 finally:
  WORK.mkdir(parents=True,exist_ok=True)
  with (WORK/'COMMANDS.jsonl').open('a') as f:f.write(json.dumps({'argv':args,'started':started,'elapsed_seconds':time.monotonic()-tick,'exit_code':code})+'\n')
def settings():
 build=next(p/'temp/core-upstream/root-integration-01' for p in (ROOT,*ROOT.parents) if (p/'temp/core-upstream/root-integration-01/libpresonus_uc.a').is_file());sdk=build/'upstream-core/sdk'
 compiler=['/usr/bin/c++','-std=c++17','-DCORE_USE_OPENSSL=1','-DNDEBUG=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-I',ROOT/'uc-library/src/mixer_dsp','-I',ROOT/'uc-library/include','-isystem',ROOT/'temp/core-upstream/root-integration-01/upstream-core/sdk/include/presonus-core-5','-isystem',ROOT/'third_party/ccl-framework','-pthread','-Ulinux','-O2','-g']
 external=build.parent/'external-dev/usr/lib/x86_64-linux-gnu';lib=sdk/'lib'
 libraries=[lib/'libcorelib.a',lib/'libpresonus_core_allocator.a',lib/'libpresonus_png.a',lib/'libpresonus_zlib.a','-lssl','-lcrypto','-Wl,-rpath,'+str(external),external/'libdns_sd.so','-ldl',build/'private-glibc29-provider/libpresonus_private_glibc29.a','-lm']
 return compiler,libraries
def unit_options(source):
 path=next(p/'temp/core-upstream/root-integration-01/compile_commands.json' for p in (ROOT,*ROOT.parents) if (p/'temp/core-upstream/root-integration-01/libpresonus_uc.a').is_file())
 commands=json.loads(path.read_text())
 selected=next((x for x in commands if x['file'].endswith(str(source.relative_to(ROOT)))),None)
 required={'-fno-rtti','-fno-fast-math','-ffp-contract=off','-frounding-math','-fno-builtin','-fno-exceptions','-fno-strict-aliasing'}
 return list(dict.fromkeys(x for x in shlex.split(selected['command']) if x in required)) if selected else []
def build():
 compiler,libraries=settings();WORK.mkdir(parents=True,exist_ok=True);objs=[]
 for name in PRODUCTION:
  source=ROOT/SOURCE_PATHS[name];obj=WORK/f'{name}.o';run([*compiler,*unit_options(source),'-MD','-MF',obj.with_suffix('.d'),'-c',source,'-o',obj]);objs.append(obj)
 obj=WORK/'Shared.o';run([*compiler,'-MD','-MF',obj.with_suffix('.d'),'-c',HERE/'Shared.cpp','-o',obj]);objs.append(obj)
 run([*compiler,*objs,*libraries,'-Wl,--wrap=_ZdlPv','-Wl,--wrap=_ZdlPvm','-Wl,--wrap=getaddrinfo','-Wl,--wrap=connect','-Wl,--wrap=sendto','-Wl,--wrap=_ZN8Presonus2UC10Connection7processEb','-Wl,--wrap=select','-Wl,-Map,'+str(WORK/'link.map'),'-o',WORK/'Replay'])
def consumers():
 manifest=ROOT/'uc-library/candidates/connection_transport_eighteen/REMARKS.json'
 if manifest.is_file():
  for p,h in json.loads(manifest.read_text())['external_consumer_fixtures'].items():assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h,p
 compiler,libraries=settings();objects=[WORK/f'{n}.o' for n in PRODUCTION]
 tests=['outgoing_socket_identity_tests','basic_connection_lifecycle_tests','uc_socket_channel_virtual_tests','uc_ccl_provider_tests','uc_connection_receive_ccl_tests','uc_factory_ccl_tests','owned_data_factory_tests','client_event_values_tests']
 for test in tests:
  source=ROOT/'uc-library/tests'/f'{test}.cpp';obj=WORK/f'{test}.o';exe=WORK/test
  wrappers=[];args=[]
  if test=='outgoing_socket_identity_tests':
   relative='uc-library/validation/uc-outgoing-socket-identity/fixtures.stdin'
   candidates=[p/relative for p in (ROOT,*ROOT.parents) if (p/relative).is_file()]
   assert candidates,relative
   args=candidates[:1]
  elif test=='basic_connection_lifecycle_tests':
   wrappers=['_ZdlPv','_ZdlPvm','pthread_mutex_init','pthread_mutex_destroy','pthread_mutex_lock','pthread_mutex_unlock'];args=['functional']
  elif test=='client_event_values_tests':wrappers=['socket','connect','getaddrinfo','getifaddrs']
  elif test in ('uc_factory_ccl_tests','uc_connection_receive_ccl_tests'):
   relative='uc-library/validation/uc-factory/arm-vectors.bin' if test=='uc_factory_ccl_tests' else 'uc-library/candidates/uc-connection-transport/validation/arm-vectors.bin'
   args=[next(p/relative for p in (ROOT,*ROOT.parents) if (p/relative).is_file())]
  run([*compiler,'-UNDEBUG','-frtti','-fno-lto','-MD','-MF',obj.with_suffix('.d'),'-c',source,'-o',obj]);run([*compiler,obj,*objects,*['-Wl,--wrap='+x for x in wrappers],*libraries,'-Wl,-Map,'+str(WORK/(test+'.map')),'-o',exe])
  if test=='outgoing_socket_identity_tests':
   expected=args[0].with_name('expected.txt');run([ROOT/'uc-library/.venv/bin/python',ROOT/'uc-library/tools/source_port_replay.py','--executable',exe,'--fixtures',args[0],'--expected',expected,'--cases','180'])
  else:run([exe,*args])
 print('Actual affected source consumers replayed:',len(tests))
def old_tasks():
 import re
 return sorted(p.name for p in HERE.parent.iterdir() if re.fullmatch(r'sqlite_connection18_[0-9a-f]{16}',p.name))
def formatted_paths():
 paths=set()
 for f in (PACKET_ROOT/'tasks').glob('*/CONTEXT.json'):
  d=json.loads(f.read_text())
  paths.update(p for p in d['write_files'] if pathlib.Path(p).suffix in ('.cpp','.hpp','.h') and (ROOT/p).is_file())
 return sorted(paths)
def format_check():
 run([ROOT/'uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*[ROOT/p for p in formatted_paths()]])
def symbols():
 out=run(['nm','--defined-only',*[WORK/f'{n}.o' for n in PRODUCTION]],text=True,capture_output=True).stdout
 names={x.split()[-1] for x in out.splitlines() if len(x.split())>=3}
 expected={o['original']['mangled'] for f in (PACKET_ROOT/'tasks').glob('*/CONTEXT.json') for o in json.loads(f.read_text())['originals']}
 assert expected<=names,expected-names
 (WORK/'SYMBOLS.txt').write_text(out)
 print('All',len(expected),'original mangled identities present without forced aliases')
def main():
 global REPLAY_EXE
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['compile','symbols','replay','consumers','native','generate-native','format','seal']);p.add_argument('--exe',type=pathlib.Path);p.add_argument('--fixture-manifest',type=pathlib.Path);a=p.parse_args()
 if a.exe:REPLAY_EXE=a.exe
 if a.fixture_manifest:
  for f,h in json.loads(a.fixture_manifest.read_text())['fixtures'].items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h,f
 if a.phase=='compile':build()
 elif a.phase=='consumers':consumers()
 elif a.phase=='symbols':symbols()
 elif a.phase=='format':format_check()
 elif a.phase in ('native','generate-native'):
  for task in old_tasks():
   if task=='sqlite_connection18_be5c94da558595e4':
    run([ROOT/'uc-library/.venv/bin/python',HERE.parent/task/'native.py',*(['--verify'] if a.phase=='native' else [])])
   else:native(task,verify=a.phase=='native')
 elif a.phase=='seal':seal()
 else:
  run([REPLAY_EXE]);compare_native_frames();compare_native_resets();compare_native_outgoing_process()

def compare_native_frames():
 fixture=ROOT/'uc-library/tests/recovery/sqlite_connection18_07f3145575aca29a/fixtures.json'
 for observation in json.loads(fixture.read_text())['observations']:
  for case in observation['cases']:
   p=case['input'];expected=[case['result_bits'],case['writer_position']]
   expected += [case['counter_bytes'],case['counter_packets']]
   observers=[x['detail'] for x in case['calls'] if x['boundary']=='sentObserver']
   valid=all(x==[p['type'],12,20047,'127.0.0.1'] for x in observers)
   assert valid,observers
   expected += [len(observers),1]
   expected += [x['detail'][0] for x in case['calls'] if x['boundary']=='write']
   result=run([REPLAY_EXE,'frame',p['capacity'],p['position'],p['write_result'],p['payload'],p['type'],p['observers'],p['initial_bytes'],p['initial_packets']],text=True,capture_output=True)
   actual=list(map(int,result.stdout.split()));assert actual==expected,(actual,expected,p)
 print('Native frame return/position/counter/write-length projections match all role-specific cases')
def compare_native_outgoing_process():
 fixture=HERE.parent/'sqlite_connection18_be5c94da558595e4/fixtures.json'
 for observation in json.loads(fixture.read_text())['observations']:
  for case in observation['cases']:
   result=run([REPLAY_EXE,'process',case['input']['mode']],text=True,capture_output=True)
   actual=list(map(int,result.stdout.split()));expected=case['projection']
   assert actual==expected,(actual,expected,case['input'])
 print('Exact native->host inactive/noqueue, resolve-fail flush, immediate lazy send and post-base error projections passed')
def compare_native_resets():
 fixture=ROOT/'uc-library/tests/recovery/sqlite_connection18_a8c8f9e0b6bd6676/fixtures.json'
 for observation in json.loads(fixture.read_text())['observations']:
  for case in observation['cases']:
   p=case['input'];result=run([REPLAY_EXE,'reset',p['retry']],text=True,capture_output=True)
   assert list(map(int,result.stdout.split()))==[case['result_bits'],case['error_byte']]
 print('Native reset return/error-byte projections match all role-specific cases')

# Native observations execute only the selected exact ELF range. All external
# boundaries, including app providers and libc/socket/device operations, are
# intercepted. These are bounded call-contract observations, not full-system ARM
# executions, and expected results are never read from new C++ output.
def native(task, verify=False):
 import hashlib,io,struct
 from elftools.elf.elffile import ELFFile
 from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
 from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_PC,UC_ARM_REG_LR
 packet=ROOT/'temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/connection_eighteen_sol61/packet-r3/tasks'/task/'CONTEXT.json'
 context=json.loads(packet.read_text());digest=lambda b:hashlib.sha256(b).hexdigest()
 records=[];tables_cache={}
 for original in [x['original'] for x in context['originals']]:
  data=(ROOT/original['elf_path']).read_bytes();assert digest(data)==original['elf']
  elf=ELFFile(io.BytesIO(data));symtab=elf.get_section_by_name('.symtab')
  symbols=symtab.get_symbol_by_name(original['mangled']);assert len(symbols)==1
  sym=symbols[0];section=elf.get_section(sym['st_shndx']);offset=section['sh_offset']+sym['st_value']-section['sh_addr']
  assert (sym['st_value'],sym['st_size'],sym['st_shndx'],offset,section.name)==(original['address'],original['size'],original['section'],original['file_offset'],original['section_name'])
  assert digest(data[offset:offset+original['size']])==original['range_sha256']
  static=ROOT/'temp/recovery-work/rolling-c001-20261124/selection/reserve-intake-sol61-1518'/('CONNECTION_FAMILY_'+original['role'].upper()+'_NATIVE_R1.json')
  items=json.loads(static.read_text())['items'];body=next(x for x in items if x['mangled']==original['mangled'])
  assert body['range_sha256']==original['range_sha256'];instructions={i['address']:i for i in body['instructions']}
  address,size=original['address'],original['size'];name=original['mangled'];demangled=body['demangled']
  profiles=[{'active':0,'drain':0,'retry':0,'write_result':1,'read_result':1,'queue_count':0,'route':0,'internal':0,'update':0,'payload':6,'capacity':64,'position':0,'port':0,'resolve':0,'flags':0,'periodic_result':1,'observers':0,'type':2,'initial_bytes':0,'initial_packets':0,'host_length':9,'null_host':0}]
  def add(**kw):profiles.append({**profiles[0],**kw})
  if 'resetEv' in name:
   for retry in (1,2,3):add(active=1,retry=retry)
  elif 'deactivateEv' in name or 'D0Ev' in name or 'D1Ev' in name or 'D2Ev' in name:
   add(active=1)
  elif 'dispatchReceived' in name:
   for route,internal,update in ((0,1,0),(0,0,1),(47,0,0),(47,1,0)):add(route=route,internal=internal,update=update)
  elif '10writeEventE' in name:
   add(observers=1,type=3);add(observers=2,type=0);add(observers=1,type=1,initial_bytes=0xfffffffffffffff8,initial_packets=0xffffffffffffffff)
   for payload,capacity,position,write_result in ((0,64,0,1),(6,8,0,1),(6,16,12,1),(6,16,12,0),(6,16,0,0)):add(payload=payload,capacity=capacity,position=position,write_result=write_result)
  elif '11writeEventsEb' in name:
   add(active=1,queue_count=2,flags=1,periodic_result=1);add(active=1,queue_count=2,flags=1,periodic_result=0);add(active=1,queue_count=2,flags=2)
   for count,drain,write_result in ((2,0,1),(2,1,1),(2,0,0),(2,1,0)):add(active=1,queue_count=count,drain=drain,write_result=write_result)
  elif '7processEb' in name:
   add(active=0,queue_count=2)
   for active,drain,read_result,write_result in ((1,0,1,1),(1,0,0,1),(1,1,0,1),(1,1,1,0)):add(active=active,drain=drain,read_result=read_result,write_result=write_result)
  elif 'sendPeriodicEvent' in name:
   add(active=1);add(active=1,port=23456)
  elif 'handleInternal' in name:
   add(port=23456)
  elif 'activateEv' in name:add(active=1);add(resolve=1)
  elif 'OutgoingConnectionC' in name:
   add(null_host=1);add(host_length=0);add(host_length=255);add(host_length=300)
  if original['elf'] not in tables_cache:
   function_names={}
   for symbol in symtab.iter_symbols():
    if symbol['st_info']['type']=='STT_FUNC':function_names.setdefault(symbol['st_value'],[]).append(symbol.name)
   vtable_targets={}
   for class_name in ('16SocketConnection7Channel','16SocketConnection','18OutgoingConnection','18ExternalConnection'):
    rows=symtab.get_symbol_by_name('_ZTVN8Presonus2UC'+class_name+'E') or []
    if rows:
     table=rows[0];sec=elf.get_section(table['st_shndx']);off=sec['sh_offset']+table['st_value']-sec['sh_addr'];raw=data[off:off+table['st_size']]
     slots=struct.unpack('<'+'I'*((len(raw)-8)//4),raw[8:])
     targets=[]
     for value in slots:
      targets.append({'address':value,'names':sorted(function_names.get(value,[]))})
     vtable_targets[class_name]={'address':table['st_value'],'section':table['st_shndx'],'file_offset':off,'sha256':digest(raw),'slots':targets}
     d1=7 if 'Channel' in class_name else 2;d0=d1+1
     assert any(n.endswith('D1Ev') for n in targets[d1]['names'])
     assert any(n.endswith('D0Ev') for n in targets[d0]['names'])
   tables_cache[original['elf']]=vtable_targets
  vtable_targets=tables_cache[original['elf']]
  cases=[]
  for profile in profiles:
   cpu=Uc(UC_ARCH_ARM,UC_MODE_ARM);cpu.mem_map(0,0x1000000)
   for segment in elf.iter_segments():
    if segment['p_type']=='PT_LOAD':cpu.mem_write(segment['p_vaddr'],segment.data())
   receiver,item,event,channel,writer,buffer,activity,handler,dispatcher,socket,stack,stop=(0x800000,0x810000,0x811000,0x820000,0x830000,0x840000,0x850000,0x860000,0x870000,0x880000,0x901000,0xa00000)
   vtable,item_vtable,channel_vtable=0x890000,0x891000,0x892000
   u32=lambda a:struct.unpack('<I',cpu.mem_read(a,4))[0]
   def put(a,v):cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
   put(receiver,vtable);put(receiver+4,profile['type']);put(receiver+8,activity);put(receiver+0x134,handler);put(receiver+0x138,dispatcher);put(receiver+0x13c,channel if profile['active'] else 0);put(receiver+0x140,64);put(receiver+0x1b0,channel if profile['active'] else 0);put(receiver+0x1b8,profile['retry']);cpu.mem_write(receiver+0x30,b'\x01');cpu.mem_write(receiver+0x31,b'127.0.0.1\0');put(receiver+0x188,2);cpu.mem_write(receiver+0x190,struct.pack('<H',12345));cpu.mem_write(receiver+0x1ac,struct.pack('<H',profile['port']));put(handler+0x74,0x865000);cpu.mem_write(0x8d0000,b'a'*profile['host_length']+b'\0')
   put(item,item_vtable);put(item+12,profile['flags']);put(event,21837 if profile['port'] else 20047);put(event+8,profile['route']);cpu.mem_write(event+16,struct.pack('<H',profile['port']));put(channel,channel_vtable);put(channel+4,socket if profile['active'] else 0);put(socket,channel_vtable)
   cpu.mem_write(activity+profile['type']*32+24,struct.pack('<Q',profile['initial_bytes']));cpu.mem_write(activity+profile['type']*32+40,struct.pack('<Q',profile['initial_packets']))
   for n in range(1,max(profile['queue_count'],1)):
    cpu.mem_write(item+n*256,bytes(cpu.mem_read(item,16)));cpu.mem_write(event+n*256,bytes(cpu.mem_read(event,24)))
   put(writer,channel);put(writer+4,buffer);put(writer+8,profile['capacity']);put(writer+12,profile['position']);cpu.mem_write(buffer,b'B'*128)
   dynamic={};index=0
   def slot(table,offset,label):
    nonlocal index
    pc=0xb00000+index*4;index+=1;put(table+offset,pc);dynamic[pc]=label
   for off,label in ((0x20,'adjust'),(0x24,'internal'),(0x28,'periodic')):slot(vtable,off,label)
   for off,label in ((0,'itemD1'),(4,'itemD0'),(8,'data')):slot(item_vtable,off,label)
   for off,label in ((0,'readable'),(4,'available'),(8,'read'),(12,'writable'),(16,'granularity'),(20,'write'),(24,'errors'),(28,'channelD1'),(32,'channelD0')):slot(channel_vtable,off,label)
   for n in range(profile['observers']):
    slot(0x893000+n*16,0,'sentObserver');put(0x8b0000+n*16,0x893000+n*16);put(0x8c0000+n*4,0x8b0000+n*16)
   put(activity+0xac,0x8c0000);put(activity+0xb0,profile['observers'])
   registers={UC_ARM_REG_R0:receiver,UC_ARM_REG_R1:profile['drain'],UC_ARM_REG_R2:0,UC_ARM_REG_R3:0,UC_ARM_REG_SP:stack,UC_ARM_REG_LR:stop}
   if 'dispatchReceived' in name:registers[UC_ARM_REG_R1]=item
   elif '10writeEventE' in name:registers.update({UC_ARM_REG_R1:writer,UC_ARM_REG_R2:event})
   elif 'handleInternal' in name or 'sendPeriodicEvent' in name:registers[UC_ARM_REG_R1]=event
   elif 'C1ERNS0_17ConnectionHandlerE' in name or 'C2ERNS0_17ConnectionHandlerE' in name:
    registers.update({UC_ARM_REG_R1:handler,UC_ARM_REG_R2:channel if 'ExternalConnection' in name else ((0 if profile['null_host'] else 0x8d0000) if 'OutgoingConnection' in name else 2),UC_ARM_REG_R3:12345});put(stack,23456)
   elif 'ChannelD' in name:registers[UC_ARM_REG_R0]=channel
   for r,v in registers.items():cpu.reg_write(r,v)
   allocations=0
   calls=[];writes=[];remaining=profile['queue_count'];retrieved=0
   def hook(cpu,pc,width,_):
    nonlocal remaining,retrieved,allocations
    if address<=pc<address+size:return
    if pc==stop:return
    label=dynamic.get(pc)
    if label is None:
     caller=cpu.reg_read(UC_ARM_REG_LR)-4;instruction=instructions.get(caller)
     if instruction is None:
      # Tail calls preserve caller LR; identify direct target from source range.
      instruction=next((i for i in instructions.values() if i.get('target') and i['operands'].startswith('#') and int(i['operands'][1:],0)==pc),None)
     assert instruction is not None,('unexpected native edge',hex(pc),hex(caller),demangled)
     labels=instruction.get('target') or []
     label=next((x for x in labels if x!='$a'),hex(pc))
    r0,r1,r2,r3=[cpu.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
    result=0;detail=[]
    if label=='data':result=event+r0-item
    elif label=='internal':result=profile['internal']
    elif label=='periodic':result=profile['periodic_result']
    elif label=='sentObserver':
     name_address=u32(cpu.reg_read(UC_ARM_REG_SP));raw=bytes(cpu.mem_read(name_address,256)).split(b'\0')[0];detail=[r1,r3,u32(r2),raw.decode('ascii')]
    elif label=='writable':result=profile['write_result']
    elif label=='errors':result=0
    elif label=='write':
     detail=[r2,bytes(cpu.mem_read(r1,r2)).hex()];result=r2 if profile['write_result'] else 0
    elif 'EventFactory5writeEPci' in label:
     result=profile['payload'];cpu.mem_write(r1,bytes([0x4e,0x4f,0,0,0,0])[:result])
    elif ('ConnectionC2ERNS0_17ConnectionHandlerEi' in label):
     put(receiver+4,r2);cpu.mem_write(receiver+0x31,b'\0');result=receiver
    elif 'Connection10readEvents' in label:result=profile['read_result']
    elif 'Connection11writeEvents' in label:result=profile['write_result']
    elif 'Connection10writeEvent' in label:result=profile['write_result']
    elif 'EventQueue7isEmpty' in label:result=int(remaining==0)
    elif 'EventQueue13retrieveEvent' in label:
     if r0==receiver+0xc and remaining:result=item+retrieved*256;retrieved+=1;remaining-=1
     else:result=0
    elif 'EventDispatcher11updateEvent' in label:result=profile['update']
    elif 'Connection11makeLocalID' in label:result=777
    elif 'getAddressByHost' in label:result=profile['resolve']
    elif 'memcpy' in label:cpu.mem_write(r0,bytes(cpu.mem_read(r1,r2)));result=r0
    elif 'strlen' in label:result=len(bytes(cpu.mem_read(r0,512)).split(b'\0')[0])
    elif 'strncpy' in label:cpu.mem_write(r0,bytes(cpu.mem_read(r1,r2)));result=r0
    elif '_Znwj' in label:result=0x8a0000+allocations*0x100;allocations+=1
    elif '__cxa_guard_acquire' in label:result=0
    elif '__cxa' in label:raise AssertionError(('unmodeled exception',label))
    calls.append({'boundary':label,'r0':r0,'r1':r1,'r2':r2,'detail':detail})
    cpu.reg_write(UC_ARM_REG_R0,result);cpu.reg_write(UC_ARM_REG_PC,cpu.reg_read(UC_ARM_REG_LR))
   def write(cpu,access,a,width,value,_):
    if receiver<=a<receiver+0x1c0 or writer<=a<writer+16 or activity<=a<activity+0xc0 or event<=a<event+24:writes.append([a,width,value])
   cpu.hook_add(UC_HOOK_CODE,hook);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
   cpu.emu_start(address,stop,count=10000)
   assert cpu.reg_read(UC_ARM_REG_PC)==stop,('not terminated',name,profile,hex(cpu.reg_read(UC_ARM_REG_PC)))
   cases.append({'input':profile,'calls':calls,'writes':writes,'result_bits':cpu.reg_read(UC_ARM_REG_R0),'error_byte':cpu.mem_read(receiver+0x30,1)[0],'retry_bits':u32(receiver+0x1b8),'channel_bits':u32(receiver+0x13c),'periodic_port':int.from_bytes(cpu.mem_read(receiver+0x1ac,2),'little'),'writer_position':u32(writer+12),'constructor_name':bytes(cpu.mem_read(receiver+0x31,256)).split(b'\0')[0].decode('ascii'),'counter_bytes':int.from_bytes(cpu.mem_read(activity+profile['type']*32+24,8),'little'),'counter_packets':int.from_bytes(cpu.mem_read(activity+profile['type']*32+40,8),'little')})
  records.append({'original':original,'cases':cases,'static_context_sha256':digest(static.read_bytes()),'vtable_targets':vtable_targets})
 fixture=ROOT/'uc-library/tests/recovery'/task/'fixtures.json';fixture.parent.mkdir(parents=True,exist_ok=True)
 result=json.dumps({'kind':'exact ARM range execution with intercepted external boundaries','observations':records},indent=2)+'\n'
 if verify:assert fixture.read_text()==result
 else:fixture.write_text(result)
 print(task,len(records),'ranges',sum(len(x['cases']) for x in records),'native executions')



def input_bindings():
 """Capture actual compiler/source inputs; no graph/registry or source writes."""
 files={ROOT/p for p in SOURCE_PATHS.values()}
 files.update((HERE/'Shared.cpp',HERE/'Shared.hpp',pathlib.Path(__file__).resolve()))
 for dep in WORK.glob('*.d'):
  text=dep.read_text().replace('\\\n',' ')
  for value in shlex.split(text.split(':',1)[1]):
   f=pathlib.Path(value)
   if not f.is_absolute():f=ROOT/f
   if f.is_file():files.add(f)
 for task in old_tasks():
  files.update((HERE.parent/task/'native.py',HERE.parent/task/'fixtures.json'))
  files.add(ROOT/'temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/connection_eighteen_sol61/packet-r3/tasks'/task/'CONTEXT.json')
 for role in ('CLIENT','SERVER'):
  files.add(ROOT/'temp/recovery-work/rolling-c001-20261124/selection/reserve-intake-sol61-1518'/('CONNECTION_FAMILY_'+role+'_NATIVE_R1.json'))
 for p in formatted_paths():files.add(ROOT/p)
 if (ROOT/'.clang-format').is_file():files.add(ROOT/'.clang-format')
 files.update((PACKET_ROOT/'tasks').glob('*/CONTEXT.json'))
 local={};external={}
 for f in sorted(files):
  h=hashlib.sha256(f.read_bytes()).hexdigest()
  try:local[str(f.relative_to(ROOT))]=h
  except ValueError:external[str(f)]=h
 _,libs=settings()
 providers={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in libs if isinstance(f,pathlib.Path) and f.is_file()}
 consumer_fixtures={}
 for suffix in ('uc-library/validation/uc-outgoing-socket-identity/fixtures.stdin','uc-library/validation/uc-outgoing-socket-identity/expected.txt','uc-library/validation/uc-factory/arm-vectors.bin','uc-library/candidates/uc-connection-transport/validation/arm-vectors.bin'):
  f=next(p/suffix for p in (ROOT,*ROOT.parents) if (p/suffix).is_file());consumer_fixtures[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
 return {'repository':local,'system_headers':external,'actual_provider_archives':providers,'external_consumer_fixtures':consumer_fixtures}

def seal():
 """Seal only after complete real final checks; unchanged validator per seal."""
 import importlib.util
 checks=json.loads((WORK/'FINAL-CHECKS.json').read_text())
 assert checks['passed'] and all(x['exit_code']==0 for x in checks['checks'])
 now=input_bindings();assert now==checks['inputs'],'inputs changed after final checks'
 core=json.loads((WORK/'PINNED-CORE.json').read_text())
 assert core['head']=='e8cbdea4a4a20e15111f5a690798a259c0374b31' and core['object_type']=='commit'
 import posixpath
 sources={}
 for p,h in now['repository'].items():
  key=posixpath.normpath(p)
  assert key not in sources or sources[key]==h
  sources[key]=h
 artifacts={}
 def bind(path,kind):
  path=posixpath.normpath(path)
  f=ROOT/path;assert f.is_file(),path
  artifacts[path]={'kind':kind,'path':path,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
 for path in sources:bind(path,'source' if path in formatted_paths() and '/src/' in path else 'dependency')
 bind(str((HERE/'Shared.cpp').relative_to(ROOT)),'test')
 bind(str(pathlib.Path(__file__).resolve().relative_to(ROOT)),'replay')
 fixtures={}
 for task in old_tasks():
  path='uc-library/tests/recovery/'+task+'/fixtures.json';bind(path,'fixture');fixtures[path]=artifacts[path]['sha256']
  bind('uc-library/tests/recovery/'+task+'/native.py','replay')
 packet_files=[PACKET_ROOT/'PACKET.json',PACKET_ROOT/'DISPATCH.json',PACKET_ROOT/'OLD18-TO-NEW27.json',PACKET_ROOT/'SUPPLEMENT-DELIVERY.json',PACKET_ROOT.parent/'NECESSARY-PROVIDER-CONTEXT.json',PACKET_ROOT.parent/'CONTEXT.json',PACKET_ROOT.parent/'ACTIVITY-REGISTRATION-APP-NATIVE.json',PACKET_ROOT.parent/'MULTICAST-LAYOUT-REPROOF-OBLIGATION.json']
 for f in packet_files:bind(str(f.relative_to(ROOT)),'packet')
 for f in (PACKET_ROOT/'tasks').glob('*/CONTEXT.json'):bind(str(f.relative_to(ROOT)),'packet')
 for path in ['uc-library/tools/recovery/accept_worker.py','docs/worker-handoff.md','docs/core-framework-lineage.md','uc-library/tools/source_port_replay.py']:
  bind(path,'dependency')
 for name in ['FINAL-CHECKS.json','PINNED-CORE.json']:
  bind(str((WORK/name).relative_to(ROOT)),'evidence')
 for name in ['SYMBOLS.txt','link.map','COMMANDS.jsonl']:
  bind(str((WORK/checks['snapshot_directory']/name).relative_to(ROOT)),'evidence')
 bind(checks['producer']['path'],'producer')
 bind(checks['executed_runtime_producer']['snapshot'],'producer')
 for path in checks.get('provenance_artifacts',[]):bind(path,'evidence')
 if 'metadata_successor' in checks:
  bind(checks['metadata_successor']['record'],'producer')
  bind(checks['metadata_successor']['executed_checks_snapshot'],'evidence')
 for result in checks['checks']:
  bind(result['log'],'evidence')
 # Bind the real, unchanged canonical consumer fixtures actually replayed.
 for suffix in ['uc-library/validation/uc-outgoing-socket-identity/fixtures.stdin','uc-library/validation/uc-outgoing-socket-identity/expected.txt','uc-library/validation/uc-factory/arm-vectors.bin','uc-library/candidates/uc-connection-transport/validation/arm-vectors.bin']:
  f=next(p/suffix for p in (ROOT,*ROOT.parents) if (p/suffix).is_file())
  checks.setdefault('external_consumer_fixtures',{})[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
 mapping=json.loads((PACKET_ROOT/'OLD18-TO-NEW27.json').read_text())['mapping']
 new_to_old={new:old for old,news in mapping.items() for new in news}
 all_originals=[];proof_paths=[];domains={}
 limitations=[
  'Portable Linux C++ source port. Original private layouts, ARM32 calling convention/binary interoperability and hardware behavior are not established.',
  'Ordinary original return spellings remain unencoded; process bool is an explicit source-port transport-health result, not its incidental ARM r0 result.',
  'Every native external app/Core/libc/socket/device boundary is intercepted. No Core implementation is recovered; genuine pinned CCL providers are used by host replays.',
  'Original listener slot0 argument flow is observed; sourcePortEventSent is an explicit portable spelling. Original listener method name/return/full vtable remain unresolved.',
  'Serialized initialized state only. Concurrent/reentrant roster/topology mutation, invalid/shrinking registries, allocation failure equivalence and ARM exception unwinding are not established.',
  'Received activity remains within the existing readEvents source-provider domain; this work validates its actual factory/queue dispatch and existing receive observers, not a new original listener receive interface.',
  'Native callee contracts use controlled factory output and valid distinct item/virtual-provider responses. Positive host paths use genuine factory/dispatcher/queue/CCL I/O; this is not full-system ARM execution.',
  'Native constructor/destructor ranges and D1/D0 target identities are checked separately. Host compiler C1/C2 or D1/D2 aliases do not imply original native aliasing. No forced ABI alias is used.',
  'Exact host deleting-destructor deallocation is observed for concrete ExternalConnection, OutgoingConnection and Channel; abstract SocketConnection cleanup is exercised through a derived source fixture, with its original D0 independently observed natively.',
  'Sender5/11, tagged hasQueuedEvents correction, provider adapters and helpers receive zero new recovery credit. The assignment remains18 distinct methods/27 mangles/54 ELF identities.'
 ]
 for task in sorted(new_to_old):
  context_path=PACKET_ROOT/'tasks'/task/'CONTEXT.json';context=json.loads(context_path.read_text());old=new_to_old[task]
  observations=json.loads((HERE.parent/old/'fixtures.json').read_text())['observations']
  expected={(x['original']['elf'],x['original']['mangled']) for x in context['originals']}
  observations=[x for x in observations if (x['original']['elf'],x['original']['mangled']) in expected]
  assert len(observations)==len(expected)==2
  domain={'original_method':context['task']['objective'],'native':{'ranges':2,'executions':sum(len(x['cases']) for x in observations),'observations':observations},'host':'Shared real positive enqueue/query/process, raw-head/tagged/default queue regression, framing/partial-write/drain/read-error/lazy activation/retry, genuine registered sent-listeners/counter rollover, host64 typed query/reply deep copy, actual manager flags0/1/2/coalescence to actual dispatcher/sender/connection and real TCP/UDP loopback with real kernel deallocation/close. All8 affected actual consumers replay unchanged original fixtures, with only2 authorized abstractness assertions updated.'}
  domains[task]=domain
  originals=[]
  for x in context['originals']:
   o=x['original'];originals.append({'elf_sha256':o['elf'],'firmware':o['firmware'],'role':o['role'],'mangled':o['mangled'],'address':o['address'],'size':o['size'],'section':o['section']});all_originals.append(originals[-1])
  proof={'version':1,'task_id':task,'originals':originals,'namespace':context['task']['namespace'],'status':'locally-validated-source-port; declaration/ABI and canonical admission remain Root-owned','packet_manifest':str(context_path.relative_to(ROOT)),'original_ranges':observations,'validation_domain':domain,'limitations':limitations,'compiled_mangled_names_matched':True,'cpp_differential_passed':True,'original_return_declaration_proven':all(('C1E' in x['mangled'] or 'C2E' in x['mangled'] or x['mangled'].endswith(('D0Ev','D1Ev','D2Ev'))) for x in originals),'original_arm_object_layout_compatible':False,'original_function_fully_verified':False,'hardware_verified':False,'source_hashes':sources,'formatting':{'formatter':'uc-library/.venv/bin/clang-format','version':checks['formatter_version'],'style':'file; fallback LLVM','sources':{p:sources[p] for p in formatted_paths() if p in sources}},'core_dependencies':{p:h for p,h in sources.items() if p.startswith(('third_party/ccl-framework/','temp/core-upstream/'))},'pinned_core':core,'actual_compiled_provider_bindings':now,'local_execution':checks,'new_method_credit':'Only the original18 methods; helpers and prior accepted sender results are excluded.'}
  path='uc-library/candidates/'+task+'/worker-proof.json';f=ROOT/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(json.dumps(proof,indent=2)+'\n');proof_paths.append(path)
 for path in proof_paths:bind(path,'proof')
 resolved=[]
 for original in all_originals:
  if original['mangled']=='_ZN8Presonus2UC18OutgoingConnection7processEb':
   resolved.append({'elf_sha256':original['elf_sha256'],'mangled':original['mangled'],'status':'corrected; independent successor acceptance pending','observation':'Original native inactive branches always join Connection::process immediately after optional activation. Predecessor deferred Base and retained queued data after failed activation.','cause':'Native call trace already contained the join, but original host smoke expectations mirrored the erroneous implementation instead of comparing Base entry and queue/error effects.','decision_rule':{'trigger':'A reconstructed control-flow branch calls or rejoins an app provider method.','required':'Compare exact native caller/base control flow with real source entry, queue, error and I/O effects for every selected join branch.','prohibited':'Admit from source-only smoke expectations or unexamined native traces.','evidence':'Exact same-ELF caller and Base ARM execution, real-delegating Base wrapper, real CCL I/O and negative control that rejects exact predecessor CPP.'},'resolution':'Both inactive paths now call actual Base in the same cycle; queued resolvefail flushes, success sends immediately, post-base error marks failure.','evidence':['uc-library/tests/recovery/sqlite_connection18_be5c94da558595e4/native.py','temp/recovery-work/connection18-build/process-successor01/NEGATIVE-CONTROL.json','temp/recovery-work/connection18-build/process-successor01/predecessor/MANIFEST.json'],'retry_condition':'Root independently verifies successor coverage/current inputs and completes canonical gates.'})
 remarks={'version':1,'resolved_observations':resolved,'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'fixtures':fixtures,'originals':all_originals,'method_count':18,'mangle_count':27,'elf_identity_count':54,'status':'local C++ validation only; canonical acceptance/admission pending','remarks':limitations,'retry_condition':'Root independently reviews and accepts this bounded exact closure, performs full canonical Linux/integration/role/installed/compile-once/current-source/guarded SQLite gates; original declarations or hardware claims require independent evidence.','external_consumer_fixtures':now['external_consumer_fixtures'],'metadata_source':'Actual NetworkManager::sendEvent caller integer is stored in real source EventItem state, preserved across dispatcher/sender/public queue and coalescing, never inferred from event tags.'}
 remarks_path='uc-library/candidates/connection_transport_eighteen/REMARKS.json';(ROOT/remarks_path).parent.mkdir(parents=True,exist_ok=True);(ROOT/remarks_path).write_text(json.dumps(remarks,indent=2)+'\n');bind(remarks_path,'evidence')
 replay_cmake='uc-library/candidates/connection_transport_eighteen/replay.cmake';bind(replay_cmake,'build_metadata')
 common_checks=[{'kind':kind,'argv':['uc-library/.venv/bin/python',str(pathlib.Path(__file__).resolve().relative_to(ROOT)),phase,*extra],'timeout_seconds':1800} for kind,phase,extra in [('format','format',[]),('compile','compile',[]),('symbols','symbols',[]),('native','native',[]),('replay','replay',['--fixture-manifest',remarks_path]),('consumers','consumers',[])]]
 integration={'production_partition':'COMMON exactly once via Root-owned cmake/ProductionSourceGroups.cmake; no CPP on archive facade targets','production_sources':['uc-library/src/Presonus/UC/'+x+'.cpp' for x in ['ConnectionLifetime','ConnectionTransport','ConnectionTransportProvider','SocketConnectionLifecycle','SocketConnectionProtocol','OutgoingConnection','ExternalConnectionLifecycle']],'public_headers':['uc-library/include/presonus/uc/ConnectionTransportProvider.hpp'],'changed_existing_headers':['uc-library/include/presonus/uc/'+x for x in ['connection.hpp','socket_channel.hpp','outgoing_connection.hpp','external_connection.hpp','event_factory.hpp','network_activity_manager.hpp','network_manager_services.hpp']],'test_metadata':replay_cmake,'test_metadata_destination':'uc-library/cmake/tests/ConnectionTransport.cmake','test_target':'uc_connection_transport_tests','link_dependencies':['presonus::uc','actual pinned CCL core and existing transitive providers'],'link_options':['--wrap=_ZdlPv','--wrap=_ZdlPvm','--wrap=getaddrinfo','--wrap=connect','--wrap=sendto','--wrap=_ZN8Presonus2UC10Connection7processEb','--wrap=select'],'ctest':['uc-library/.venv/bin/ctest','--test-dir','temp/core-upstream/root-integration-01','-R','uc_connection_transport','--output-on-failure'],'fixture_bindings':fixtures,'dependency_reproof':'All actual selected application TUs are freshly compiled; linkmap has zero application archive members. Recompile all canonical EventItem/header-dependent consumers and preserve caller proofs.'}
 spec=importlib.util.spec_from_file_location('unchanged_accept_worker',ROOT/'uc-library/tools/recovery/accept_worker.py');validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)
 common_artifacts=sorted(artifacts.values(),key=lambda x:x['path']);index=[]
 for task in sorted(new_to_old):
  context_path=PACKET_ROOT/'tasks'/task/'CONTEXT.json';context=json.loads(context_path.read_text());proof=json.loads((ROOT/'uc-library/candidates'/task/'worker-proof.json').read_text())
  handoff={'version':1,'task_id':task,'namespace':context['task']['namespace'],'packet_manifest':str(context_path.relative_to(ROOT)),'originals':proof['originals'],'artifacts':common_artifacts,'checks':common_checks,'validation_domain':domains[task],'limitations':limitations,'build_integration':integration,'shared_execution_group':'Connection18 exact common closure;27 handoffs/18 methods/54 identities; one actual shared standard execution only when explicitly accepted by Root'}
  validator.validate(handoff) # mandatory unchanged validation BEFORE each seal
  path=ROOT/'uc-library/candidates'/task/'HANDOFF.json';path.write_text(json.dumps(handoff,indent=2)+'\n');validator.validate(json.loads(path.read_text()))
  index.append({'task_id':task,'handoff':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'old_native_task':new_to_old[task],'originals':proof['originals']})
 index_path=ROOT/'uc-library/candidates/connection_transport_eighteen/HANDOFF-INDEX.json';index_path.write_text(json.dumps({'version':1,'method_count':18,'mangle_count':27,'elf_identity_count':54,'handoffs':index,'shared_artifact_closure_sha256':hashlib.sha256(json.dumps(common_artifacts,sort_keys=True).encode()).hexdigest(),'checks':common_checks,'remarks':remarks_path,'prior_sender_and_helper_new_credit':0,'canonical_admission':False,'provenance_artifacts':checks.get('provenance_artifacts',[]),'executed_runtime_producer':checks['executed_runtime_producer'],'native_producers':checks.get('native_producers',{}),'semantic_successor':checks.get('semantic_successor')},indent=2)+'\n')
 print('Sealed27 exact-mangled handoffs /18 methods /54 original identities; unchanged validator passed before and after each seal')

if __name__=='__main__':main()
