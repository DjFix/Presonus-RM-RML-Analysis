"""Reproducible full SL49 source-port local gates; never edits shared CMake/registry."""
import argparse,datetime,hashlib,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
TEST=Path('uc-library/tests/recovery/sl_channel49')
FIXTURE=Path('uc-library/tests/recovery/sqlite_sl49_56037a1b73e65ecc/fixtures.json')
SELECTOR_FIXTURE=Path('uc-library/tests/recovery/sqlite_sl49_channel_selected01/fixtures.json')
SCRATCH=Path('temp/recovery-work/sl_channel49/final-local01')
CANDIDATE=Path('uc-library/candidates/sl_channel49')
BUILD=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
ARCHIVES=[BUILD/'libpresonus_uc.a',BUILD/'upstream-core/sdk/lib/libcorelib.a',BUILD/'upstream-core/sdk/lib/libpresonus_core_allocator.a']
NAMES=['SLChannel','SLChannelLifecycle','SLChannelInitialization','SLChannelLinking','SLChannelMetering','SLStereoChannel','SLCascadeMeteringChannel','SLRackFXBusComponent','SLRackFXReturnComponent','SLRackMonoBusComponent','SLRackMonoMainComponent','SLRackStereoLineComponent','SLRackStereoMainComponent','SLRackTalkbackComponent','MixerClientSelection','MixerClientComponentBase','MappableMixer','MeterBallistics','MeterBallisticsIdle','MeterMaid','GRMeterMaid','DelayTimer']
SOURCES=[Path('uc-library/src/Presonus')/(n+'.cpp') for n in NAMES]+[Path('uc-library/src/Presonus/UC')/n for n in ['ClientComponent.cpp','ClientRootComponent.cpp','ClientParameterChanges.cpp','ClientRootParameterChanges.cpp']]
HEADERS=[Path('uc-library/include/presonus')/(n+'.hpp') for n in ['SLChannel','SLStereoChannel','SLCascadeMeteringChannel','SLRackFXBusComponent','SLRackFXReturnComponent','SLRackMonoBusComponent','SLRackMonoMainComponent','SLRackStereoLineComponent','SLRackStereoMainComponent','SLRackTalkbackComponent','MeterBallistics']]+[Path('uc-library/include/presonus/uc')/n for n in ['ClientComponent.hpp','ClientRootComponent.hpp']]+[Path('uc-library/include/presonus/mixer_state/MixerState.hpp')]
FORMAT_SOURCES=SOURCES[:15]+SOURCES[24:26]+[TEST/'Shared.cpp',TEST/'Shared.hpp']
FLAGS=['-std=c++20','-O0','-fno-sized-deallocation','-Ulinux','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework']
PACKETS=Path('temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/sl_channel49_sol61/packet-r4/tasks')
MODES=['lifecycle','metering','init','linking','callbacks','owned']
TIMES=[]
def digest(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def bind(p):return dict(path=str(p),sha256=digest(p))
def run(argv,input=None):
 argv=list(map(str,argv));start=datetime.datetime.now(datetime.timezone.utc).isoformat();before=time.monotonic();p=subprocess.run(argv,cwd=ROOT,text=True,input=input,capture_output=True);TIMES.append(dict(argv=argv,start_utc=start,seconds=time.monotonic()-before,returncode=p.returncode))
 if p.returncode:raise RuntimeError(str(argv)+'\n'+p.stdout+p.stderr)
 return p.stdout

def native():
 result={}
 for mode in MODES:result[mode]=json.loads(run([sys.executable,'-B',TEST/'native_common.py',mode]))
 return result

def compile_local():
 objects=[]
 for i,src in enumerate([*SOURCES,TEST/'Shared.cpp']):
  obj=SCRATCH/f'{i}.o';run(['c++',*FLAGS,'-MMD','-MF',SCRATCH/f'{i}.d','-c',src,'-o',obj]);objects.append(obj)
 before=[bind(p) for p in ARCHIVES]
 run(['c++','-Wl,--gc-sections','-Wl,--wrap=_ZdlPv','-Wl,--wrap=_ZN8presonus4dice19packetClockRawTicksEv','-Wl,--wrap=_ZN8Presonus24MixerClientComponentBase15channelSelectedEPNS_13SLChannelBaseE',*objects,'-Wl,--start-group',*ARCHIVES,'-Wl,--end-group','-lm','-pthread','-ldl','-lz','-o',SCRATCH/'replay'])
 assert before==[bind(p) for p in ARCHIVES]
 receipt=SCRATCH/('compile-execution-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json')
 (ROOT/receipt).write_text(json.dumps(dict(commands=TIMES,archives=before,sources=[bind(p) for p in SOURCES],executed_checker=bind(TEST/'run_all.py')),indent=2)+'\n')
 (ROOT/SCRATCH/'LAST-COMPILE.json').write_text(json.dumps(bind(receipt),indent=2)+'\n')

def symbols():
 names=set();observed={}
 for i in range(len(SOURCES)):
  output=run(['nm','--defined-only',SCRATCH/f'{i}.o']);observed[str(SOURCES[i])]=output;names.update(line.split()[-1] for line in output.splitlines() if line.split())
 originals=[r['original'] for p in sorted((ROOT/PACKETS).glob('*/CONTEXT.json')) for r in json.loads(p.read_text())['originals']]
 ordinary=[o for o in originals if not o['mangled'].startswith('_ZTh')];assert all(o['mangled'] in names for o in ordinary)
 assert '_ZN8Presonus24MixerClientComponentBase15channelSelectedEPNS_13SLChannelBaseE' in names
 thunks=sorted(n for n in names if n.startswith('_ZTh') and 'paramChanged' in n and any(c in n for c in ['13SLChannelBase','15ClientComponent','9SLChannel']))
 assert all(n.startswith('_ZThn8_') for n in thunks)
 return dict(original_ordinary_names_matched=len(ordinary),extra_selector_names_matched=1,host_thunks=thunks,original_sub4_thunks='six exact original identities retained unresolved/pending ARM ABI; no fabricated aliases',production_symbols=observed)

def compare(bundle,selector,exe):
 output={mode:run([exe,mode]).splitlines() for mode in ['names','lifecycle','metering','init','callbacks','positive','selector','cascade']};counts={}
 got={tuple(line.split('\t')[1:4]):line.split('\t')[4] for line in output['names']};count=0
 for row in bundle['lifecycle']['originals']:
  cls=__import__('re').match(r'_ZN8Presonus\d+(.+)[CD][012]Ev$',row['original']['mangled'])[1]
  for c in row['name_cases']:assert got[(cls,c['prefix'],str(c['number']))]==c['value'];count+=1
  if 'D0Ev' in row['original']['mangled']:assert not row['receiver_mapped_after']
  elif 'D1Ev' in row['original']['mangled'] or 'D2Ev' in row['original']['mangled']:assert row['receiver_mapped_after']
 counts['native_constructed_name_cases']=count
 assert len(output['lifecycle'])==11 and all(line.endswith('\t1\t0') for line in output['lifecycle'])
 count=0
 for row in bundle['metering']['originals']:
  name=row['operation_original']['mangled']
  if 'SLCascadeMeteringChannel' in name:
   method='aggregate' if 'updateAggregateMeter' in name else 'slave' if 'updateSlaveChannelLevel' in name else 'changed'
   for c in row['meter_cases']:
    line='\t'.join(map(str,['cascade',method,*c['input'],c['local_bits'],c['slave_bits'],c['peer_slave_bits'],*c['values']]));assert line in output['cascade'],line;count+=1
  else:
   kind=('stereo' if 'SLStereoChannel' in name else 'base')+('-periodic' if '6onIdle' in name else '-idle' if 'idleMeters' in name else '-update')
   for c in row['meter_cases']:
    line='\t'.join(map(str,[kind,*c['input'],*c['values']]));assert line in output['metering'],line;count+=1
 counts['native_meter_cascade_periodic_cases']=count
 count=0
 for row in bundle['init']['originals']:
  name=row['operation_original']['mangled'];cls=__import__('re').match(r'_ZN8Presonus\d+([^0-9]+)4init',name)[1];c=row['init_cases'][0]
  fields=['init',cls,*c['rates'],c['right_rate'] if c['right_rate'] is not None else -1,int(c['linker_present']),int(c['mixer_binding']),c['color_index_tag'],c['selection_tag'] if c['selection_tag'] is not None else -1,int(c['selection_public']) if c['selection_public'] is not None else -1,c['neighbour_selection_tag'] if c['neighbour_selection_tag'] is not None else -1,c['on_left_bits'],len(c['observed_adds']),len(c['observed_removes'])]
  assert '\t'.join(map(str,fields)) in output['init'],fields;count+=1
 counts['native_init_cases']=count
 bit=lambda f:__import__('struct').unpack('<I',__import__('struct').pack('<f',f))[0]
 count=0
 for row in bundle['callbacks']['originals']:
  name=row['operation_original']['mangled']
  if name.startswith('_ZTh'):continue
  kind='linked' if 'updateLinkedSelection' in name else 'base' if '13SLChannelBase' in name else 'channel';c=row['init_cases'][0];m=c['input'];local=[];master=[];calls=0
  for event in c['events']:
   if event[0]=='Mappable_message_boundary':(master if event[1]=='master' else local).append(event[2])
   elif event[0]=='actual_selector_dependency_boundary':calls+=1;(master if m.get('master') else local).extend([-1,13])
  msg=lambda a:','.join(map(str,a)) if a else 'none'
  fields=['callback',kind,m.get('tag',0),m.get('msg',0),int(m.get('master',False)),bit(m.get('selection',1.)),bit(m.get('link',1.)),int(m.get('missing_linked',False)),m.get('notify',0),c['selection_bits'],c['linked_selection_bits'],calls,msg(local),msg(master)]
  assert '\t'.join(map(str,fields)) in output['callbacks'],fields;count+=1
 counts['native_callback_cases']=count
 for row in bundle['linking']['originals']:
  name=row['operation_original']['mangled'];c=row['init_cases'][0]
  if '8isLinked' in name:
   m=c['input'];key='null' if m.get('missing_link') else str(bit(m['link']));assert '\t'.join(map(str,['linked',key,c['linked_boolean']])) in output['init']
  if 'ParamLinkerD' in name:assert c['observed_removes']==c['observed_adds'];assert c['linker_mapped_after']==('D0' not in name)
  if 'getSlowLinkParams' in name:assert c['slow_tags']==[17,20,18,224,225,226,227,228,229,230,231,232,233,234,235,236,237,238,239,300,301,302,303]
 counts['native_linker_variant_getter_cases']=len(bundle['linking']['originals'])
 for row in bundle['owned']['originals']:
  events=row['init_cases'][0]['events'];assert any(e[0]=='actual_delete_unmap' and e[1]==0x3000000 for e in events)
  if 'D0' in row['operation_original']['mangled']:assert not row['receiver_mapped_after']
 counts['native_owned_destructor_cases']=len(bundle['owned']['originals'])
 for row in selector['originals']:
  for case in row['cases']:
   c=case['input'];fields=['selector',c['depth'],int(c['slave']),c['transition'],c['relation'],int(c['mutate']),*case['values'],','.join(case['callbacks']) if case['callbacks'] else 'none',','.join(str(x[0]) for x in case['parameter_writes']) if case['parameter_writes'] else 'none'];assert '\t'.join(map(str,fields)) in output['selector'];assert case['cache_matches']
 counts['native_selector_cases']=sum(len(row['cases']) for row in selector['originals'])
 assert output['positive']==['positive initialized CCL trees, real sender queue/cache, paired observer edits/removal, selection master/slave, real Mappable notifications, 25ms timer/ballistic pipeline passed']
 return output,counts

def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['format','compile','symbols','native','replay']);ap.add_argument('--out',type=Path);ap.add_argument('--exe',type=Path);args=ap.parse_args();(ROOT/SCRATCH).mkdir(parents=True,exist_ok=True)
 if args.out:
  (ROOT/args.out).parent.mkdir(parents=True,exist_ok=True)
  if (ROOT/args.out).exists():raise FileExistsError('Preserve old proof; choose a new output path')
 if args.mode=='native':
  data=native();(ROOT/FIXTURE).parent.mkdir(parents=True,exist_ok=True);(ROOT/FIXTURE).write_text(json.dumps(data,indent=2)+'\n');selector=json.loads(run([sys.executable,'-B','uc-library/tests/recovery/sqlite_sl49_channel_selected01/native.py']));(ROOT/SELECTOR_FIXTURE).write_text(json.dumps(selector,indent=2)+'\n');print('Fresh exact native fixtures saved; no C++ expected-value generation');return
 run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*HEADERS,*FORMAT_SOURCES])
 if args.mode=='format':return
 if args.mode=='compile':compile_local();return
 syms=symbols()
 if args.mode=='symbols':print(syms['original_ordinary_names_matched'],'ordinary original names; extra selector and natural host sub8 thunks verified');return
 fixture=json.loads((ROOT/FIXTURE).read_text());fresh=native();assert fresh==fixture
 selector=json.loads((ROOT/SELECTOR_FIXTURE).read_text());assert json.loads(run([sys.executable,'-B','uc-library/tests/recovery/sqlite_sl49_channel_selected01/native.py']))==selector
 exe=args.exe or (ROOT/SCRATCH/'replay');outputs,counts=compare(fresh,selector,exe)
 deps=set()
 for i in range(len(SOURCES)+1):
  deps.update((ROOT/SCRATCH/f'{i}.d').read_text().replace('\\\n',' ').split()[1:])
 deps=sorted({str((ROOT/p).resolve().relative_to(ROOT)) for p in deps})
 proof=dict(version=1,observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),format_check_passed=True,formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler=run(['c++','--version']).splitlines()[0],cpp_differential_passed=True,compiled_mangled_names_matched=True,compiled_symbols=syms,counts=counts,cpp_outputs=outputs,native_fixture=bind(FIXTURE),selector_fixture=bind(SELECTOR_FIXTURE),native_producer=bind(TEST/'native_common.py'),selector_native_producer=bind(Path('uc-library/tests/recovery/sqlite_sl49_channel_selected01/native.py')),checker=bind(TEST/'run_all.py'),sources=[bind(p) for p in [*HEADERS,*SOURCES]],compiler_inputs=[bind(p) for p in deps],local_archives=[bind(p) for p in ARCHIVES],compile_record=json.loads((ROOT/SCRATCH/'LAST-COMPILE.json').read_text()),executable=bind(SCRATCH/'replay'),tool_timings=TIMES,limitations=['Portable source port, not ARM layout/calling convention/binary ABI/hardware verification. Unencoded return declarations remain pending.','All Core implementations use pinned actual source providers on host; native Core parameter/container/component/string/clock operations are explicit captured boundaries, never recovered firmware Core bodies.','Original sub4 callback thunk identities remain pending; natural host CCL secondary base uses sub8 and no alias is fabricated.','Accepted GR/Mappable/Meter/Delay/Client bodies reused; four independently accepted idle/client methods receive zero duplicate credit. Extra selector is a separate prerequisite, outside original49 denominator.','Natural borrowed Mappable/ClientImplementation/codecs/rate/state inspection adapters carry zero original credit. Native cascade uninitialized original level words are initialized through real original setters before use; portable constructor zero fallbacks are independent policy.','All changed canonical shared-provider versions require fresh explicit rebind/replay. Historical proofs and old source snapshots remain preserved; global Linux/role/installed/compile-once/readiness/mirror gates remain Root-owned.'])
 if args.out:(ROOT/args.out).write_text(json.dumps(proof,indent=2)+'\n')
 print('Full exact native/source/provider replay passed',json.dumps(counts,sort_keys=True))
if __name__=='__main__':main()
