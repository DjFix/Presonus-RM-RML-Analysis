#!/usr/bin/env python3
"""Compile, exact-symbol and original-fixture replay checks; outputs stay scratch."""
import argparse,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[4]
HERE=pathlib.Path(__file__).parent
SOURCES=['uc-library/src/Presonus/Network/WIFIManager.cpp','uc-library/src/Presonus/Network/WIFITasks.cpp','uc-library/src/application/SimpleReader.cpp','uc-library/tests/recovery/wifi_manager/Replay.cpp']
BUILD=ROOT/'temp/recovery-work/wifi-manager'
EXPECTED_ARCHIVES={'/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/build/artifacts/linux/Release/libcorelib.a': '5a2c8bbb20d8d194ff4f5047118696afa918a046b01739c4257416044e83f5f3', '/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/build/libpresonus_core_allocator.a': '69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d', '/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/build/libpresonus_png.a': '99514af041c29b5aa782c14718794453b13841f99b7de584db3f3f89bf68ecc1', '/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/build/libpresonus_zlib.a': '9095c54154b7617d8f283d7858ae45218cad1ba92e54e04f983dc0a7151c6c93', '/usr/lib/x86_64-linux-gnu/libpng16.so.16': '89c0c6569a8c00480d451401ad4c0a74942e62dc57f229a970592fdc5adb29e8', '/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so': '28b67af5dddb8eef17b77280db249c50344554c82226705733b1912a30c114a5'}
def run(argv):subprocess.run([str(x) for x in argv],cwd=ROOT,check=True)
def compile_():
 BUILD.mkdir(parents=True,exist_ok=True)
 base=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core')
 libs=[base/'build/artifacts/linux/Release/libcorelib.a',base/'build/libpresonus_core_allocator.a',base/'build/libpresonus_png.a',base/'build/libpresonus_zlib.a',pathlib.Path('/usr/lib/x86_64-linux-gnu/libpng16.so.16'),pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so')]
 for path,expected in EXPECTED_ARCHIVES.items():assert hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()==expected,'Changed linked provider: '+path
 common='-std=c++17 -fno-rtti -Wno-multichar -pthread -Iuc-library/include -Ithird_party/ccl-framework'
 objects=[BUILD/(str(i)+'.o') for i in range(len(SOURCES))]
 lines=['.PHONY: all','all: '+str(BUILD/'Replay')]
 for source,obj in zip(SOURCES,objects):
  lines.extend([str(obj)+': '+source+' '+str(BUILD/'Makefile')+' /usr/bin/c++','\tc++ '+common+' -MMD -MP -c '+source+' -o '+str(obj)])
 lines.extend([str(BUILD/'Replay')+': '+' '.join(map(str,[*objects,*libs])), '\tc++ -pthread -Wl,--wrap=_ZN4Core8Portable16BackgroundWorker9terminateEv -Wl,--wrap=_ZN4Core8Portable16BackgroundWorker7addTaskEPNS0_14BackgroundTaskE -Wl,--wrap=_ZN4Core8Portable9ListParam9removeAllEv -Wl,--wrap=_ZN4Core8Portable9ListParam12appendStringEPKc -Wl,--wrap=_ZN4Core8Portable9Parameter7changedEv -Wl,--wrap=_ZN4Core8Portable9Parameter12rangeChangedEv -Wl,--wrap=rand -Wl,--wrap=srand '+' '.join(map(str,objects))+' -Wl,--start-group '+' '.join(map(str,libs))+' -Wl,--end-group -lz -ldl -o '+str(BUILD/'Replay'),'-include '+' '.join(str(o.with_suffix('.d')) for o in objects)])
 makefile=BUILD/'Makefile';contents='\n'.join(lines)+'\n'
 if not makefile.exists() or makefile.read_text()!=contents:makefile.write_text(contents)
 run(['make','-f',makefile,'-j2','all'])
def symbols():
 names=subprocess.check_output(['nm','--defined-only',BUILD/'Replay'],text=True)
 data=json.loads((HERE/'fixtures.json').read_text());missing=sorted({x['mangled'] for x in data['ranges']} - {line.split()[-1] for line in names.splitlines() if line.split()})
 assert not missing,missing
 print('exact original compiled manglings',len({x['mangled'] for x in data['ranges']}))
def provider():
 out=subprocess.check_output([str(BUILD/'Replay'),'providerQueue'],cwd=ROOT,text=True,timeout=10);assert out=='CCL queue work=3 destroy=3 status=Store to Join\n',out;print(out.strip())
def replay(executable=None,task=None):
 data=json.loads((HERE/'fixtures.json').read_text());assert data['producer_sha256']==hashlib.sha256((HERE/'native.py').read_bytes()).hexdigest(),'Changed native fixture producer';cases=data['cases'];count=0
 for c in cases:
  if task and c['mangled']!=task:continue
  op=c['method'];args=[str(executable or BUILD/'Replay'),op]
  if 'value'in c:args.append('<NULL>' if c['value'] is None else c['value'])
  if op=='doCommand':args.append(str(c['n']))
  if op in ('ReconnectTask','DisconnectTask'):args.append(str(c['command_result']))
  if op=='config':args.extend([str(int(c['dynamic'])),c['gateway'],str(int(c['write_fail']))])
  if op in ('destructor','managerDestructor'):args.append(c['mangled'])
  if op=='hasFlag':args.append(c['flags'])
  if op=='configAutoPositive':args.extend([','.join(map(str,c['input_probe_returns'])),','.join(map(str,c['input_rand_returns']))])
  if op=='delegatePositive':args.append(c['scenario'])
  if op=='repeatSetterPositive':args.append(c['setter'])
  if op=='updateListPositive':args.append(c['label'])
  if op=='onIdlePositive':args.extend(str(c['input'][k]) for k in ('dirty','adapters','deadline','now'))
  if op in ('getWifiIPPositive','getEthernetIPPositive','getIPPositive'):args.extend([c['active'],*[v for pair in c['addresses'] for v in pair]])
  if op=='doJoinPositive':args.append(c['flags'])
  if op=='failoverPositive':args.extend([c['pipe_data'],str(int(c['write_fail'])),str(int(c['pipe_fail']))])
  if op in ('scanPositive','activePositive','isEthernetPositive'):
   args.append(c['input'])
   if op!='scanPositive':args.extend([c['ifconfig'],*[v for pair in c['addresses'] for v in pair]])
  if op=='joinWork':args.extend([str(int(c['wep'])),str(int(c['encrypted'])),''.join(str(int(x)) for x in c['responses'])])
  out=subprocess.check_output(args,text=True,cwd=ROOT).splitlines()
  if op in ('setStatusMessage','setActiveNetwork','setStaticIp','repeatSetterPositive'):assert bytes.fromhex(out[0]).decode()==c['result'] and int(out[1])==c['dirty'],(c,out)
  elif op=='isActive':assert int(out[0])==c['result'],(c,out)
  elif op=='doCommand':
   assert int(out[0])==c['result'],(c,out)
   traces=[]
   for line in out[1:]:
    k,_,v=line.partition(' ');traces.append([k,bytes.fromhex(v).decode()])
   assert traces==c['trace'],(c,traces)
  elif op in ('ReconnectTask','DisconnectTask'):assert int(out[0])==0 and bytes.fromhex(out[1]).decode()==c['status'],(c,out)
  else:
   if 'result'in c:assert (bytes.fromhex(out[0]).decode() if op.startswith('get') else int(out[0]))==c['result'],(c,out)
   assert bytes.fromhex(out[1]).decode()==c['status'],(c,out)
   if 'active'in c:assert bytes.fromhex(out[2]).decode()==c['active'],(c,out)
   if 'subnet'in c:assert bytes.fromhex(out[3]).decode()==c['subnet'],(c,out)
   if op=='constructor':
    assert bytes.fromhex(out[3]).decode()==c['static_ip'] and bytes.fromhex(out[4]).decode()==c['scratch'],(c,out)
   if 'delegates'in c:
    adapter,delegates=map(int,out[4].split());assert adapter==c['adapter_dirty'] and delegates==c['delegates'],(c,out)
   actual=[];published=[];events=[];lists=[];meta=[];providers=[];auto=[];delegates=[]
   for line in out[5:] if op=='constructor' or 'delegates'in c else out[4:]:
    parts=line.split('\t')
    if parts[0]=='AUTO':auto=parts[1:];continue
    if parts[0]=='DELEGATES':delegates=parts[1:];continue
    if parts[0]=='EVENT':events.append([parts[1],*[bytes.fromhex(v).decode() for v in parts[2:]]]);continue
    if parts[0]=='LIST':lists.append([bytes.fromhex(v).decode() for v in parts[1:]]);continue
    if parts[0]=='META':meta=parts[1:];continue
    if parts[0]=='PROVIDER':providers.append(parts[1:]);continue
    if parts[0]=='ITEM':published.append([bytes.fromhex(v).decode() for v in parts[1:-1]]);continue
    actual.append([parts[0],*[bytes.fromhex(v).decode() for v in parts[1:]]])
   if op=='configAutoPositive':assert auto==[c['address'],c['mask'],c['gateway'],c['flags'],str(len(c['unused_probes'])),str(len(c['unused_rng']))],(c,auto)
   if op=='delegatePositive':assert delegates==c['delegate_ids'],(c,delegates)
   if 'events_normalized'in c:assert events==c['events_normalized'],(c,events)
   if 'lists'in c:
    assert lists==c['lists'],(c,lists)
    # Pinned Core ListParam::setMax signals each remove/append; the app then
    # calls setValue(0),changed(),rangeChanged() for levels,icons,names.
    expected_provider=[[str(i),'3'] for i in range(3)]
    expected_provider += [[str(i),'3'] for _ in range(len(c['lists'][0])) for i in range(3)]
    expected_provider += [[str(i),msg] for i in (1,2,0) for msg in ('3','3','4')]
    assert providers==expected_provider,(c,providers,expected_provider)
   if op=='setNetworkItemsPositive':assert meta==[str(c['delta']),str(c['source_count_after']),'1',str(c['dirty']),str(len(c['deleted']))],(c,meta)
   if op=='onIdlePositive':assert meta==[c['flags_after'],str(c['deadline_after'])],(c,meta)
   if 'published'in c:assert published==c['published'],(c,published)
   expected=[[str(x) for x in line] for line in c['trace']]
   assert actual==expected,(c,actual)

  count+=1
 assert count
 print('passed',count,'original ARM fixture cases; offline providers only')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['compile','symbols','replay','provider']);p.add_argument('--executable');p.add_argument('--mangled');a=p.parse_args();{'compile':compile_,'symbols':symbols,'provider':provider,'replay':lambda:replay(a.executable,a.mangled)}[a.mode]()
