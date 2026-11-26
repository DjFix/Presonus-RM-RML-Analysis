import pathlib,json,subprocess,hashlib,struct,sys,os
ROOT=pathlib.Path(__file__).resolve().parents[4];HERE=pathlib.Path(__file__).parent;BUILD=ROOT/'temp/recovery-work/wifi-ui-sol61/run'
WRAPS=['_ZN4Core8Portable12NumericParam8setValueEfb','_ZN4Core8Portable9Parameter17setFeedbackNeededEb','_ZN8Presonus13PageComponentC2EPKcS2_i','_ZN8Presonus10DelayTimerC1Ef','_ZN8Presonus10DelayTimerD1Ev','_ZN4Core8Portable9ParamList3addEPKNS0_9ParamInfoEib','_ZN8Presonus11WIFIManager11addDelegateEPNS_19WIFIManagerDelegateE','_ZN8Presonus11WIFIManager14removeDelegateEPNS_19WIFIManagerDelegateE','_ZN8Presonus11WIFIManager6doScanEb','_ZN8Presonus11WIFIManager6doJoinEPKcS2_','_ZN4Core8Portable9ComponentD2Ev','_ZN4Core8Portable16BackgroundWorker7addTaskEPNS0_14BackgroundTaskE']
SOURCES=['uc-library/src/Presonus/Surface/WifiSetupComponent.cpp','uc-library/src/Presonus/PageComponent.cpp','uc-library/src/Presonus/DelayTimer.cpp','uc-library/src/application/SimpleReader.cpp','uc-library/src/Presonus/Network/WIFIManager.cpp','uc-library/src/Presonus/Network/WIFITasks.cpp','uc-library/tests/recovery/wifi_ui/Replay.cpp']
def compile():
 base=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01');up=base/'upstream-core';libs=[base/'libpresonus_uc.a',up/'build/artifacts/linux/Release/libcorelib.a',up/'build/libpresonus_core_allocator.a',up/'build/libpresonus_png.a',up/'build/libpresonus_zlib.a','/usr/lib/x86_64-linux-gnu/libpng16.so.16','/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so'];args=['c++','-std=c++17','-fno-rtti','-Wno-multichar','-pthread','-Iuc-library/include','-Ithird_party/ccl-framework',*SOURCES,*['-Wl,--wrap='+x for x in WRAPS],'-Wl,--start-group',*map(str,libs),'-Wl,--end-group','-lz','-ldl','-o',str(BUILD/'Replay')];subprocess.run(args,cwd=ROOT,check=True,env={**os.environ,"TMPDIR":str(BUILD)})
def decode(s):return None if s=='NULL' else bytes.fromhex(s).decode()
def replay(mangled=None):
 data=json.loads((HERE/'fixtures.json').read_text());assert data['producer_sha256']==hashlib.sha256((HERE/'native.py').read_bytes()).hexdigest();n=0
 for c in data['cases']:
  if mangled and c['mangled']!=mangled:continue
  args=[str(BUILD/'Replay'),c['method']]
  if c['method']=='destructor':args.append('D0' if 'D0Ev' in c['mangled'] else 'D1')
  if c['method']=='textInputFinished':args.extend([str(int(c['cancel'])),c['password']])
  out=subprocess.check_output(args,cwd=ROOT,text=True).splitlines()
  if c['method']=='disconnect':
   action=out.pop(0).split(' ');assert float(action[1])==struct.unpack('<f',struct.pack('<I',c['parameter_value_bits']))[0] and decode(action[2])==c['text'],(c,action)
  state=list(map(int,out[0].split()[1:]));events=[];infos=[]
  for line in out[1:]:
   fields=line.split(' ')
   if fields[0]=='INFO':infos.append(fields[1:]);continue
   events.append([fields[0],*[decode(v) for v in fields[1:]]])
  # Compare observable app/effect boundaries; inline Core feedback and existing
  # getSelectedSSID/toString providers are checked through actual parameter state.
  expected=[]
  for row in c['trace']:
   if row[0] in ('selected-ssid','toString','setValue'):continue
   values=row[1:3] if row[0]=='parameters' else row[1:]
   expected.append([row[0],*[str(x) for x in values]])
  for rows in (events,expected):
   for row in rows:
    if row[0]=='timer-construct':row[1]=str(float(row[1]))
  assert events==expected,(c,events,expected)
  if c['method']=='constructor':
   assert state[:2]==[1,1] and state[4]==1 and len(infos)==26
   for actual,info in zip(infos,c['parameters']):
    target=[str(info['type']),str(info['tag']),info['name'],*[str(struct.unpack('<I',struct.pack('<f',v))[0]) for v in info['numeric']],str(info['flags']),*info['text'],info['initial_strings'][0] if info['initial_strings'] else None,info['title'],info['short_title']]
    actual=[*actual[:2],decode(actual[2]),*actual[3:9],*[decode(v) for v in actual[9:]]];assert actual==target,(actual,target)
  if c['method']=='destructor':assert state[1:3]==[0,26] and state[3]==('D0Ev' in c['mangled']),(c,state)
  n+=1
 assert n;print('passed',n,'native UI target cases')
def symbols():
 names=subprocess.check_output(['nm','--defined-only',BUILD/'Replay'],text=True);d=json.loads((ROOT/'temp/recovery-work/wifi-ui-sol61/CONTEXT.json').read_text());wanted={t['originals'][0]['original']['mangled'] for t in d['tasks']};assert wanted<={x.split()[-1] for x in names.splitlines() if x.split()};print('seven original UI ABI symbols matched')
if __name__=='__main__':
 {'compile':compile,'symbols':symbols,'replay':lambda:replay(sys.argv[2] if len(sys.argv)>2 else None),'integration':lambda:subprocess.run([str(BUILD/'Replay'),'integration'],cwd=ROOT,check=True)}[sys.argv[1]]()
