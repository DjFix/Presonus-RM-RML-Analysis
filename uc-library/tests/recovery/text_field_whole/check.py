"""Frozen inputs, separate mutable outputs; canonical executable supported by --exe."""
import argparse,importlib.util,json,subprocess,sys
from pathlib import Path
TEST=Path(__file__).parent;BUILD=Path('temp/recovery-work/sol61-local/text_field_whole')
SOURCES=[Path('uc-library/src/Presonus/Panel')/(n+'.cpp') for n in ['Element','OffscreenElement','FieldElement','TextEntryElement']]
HEADERS=[Path('uc-library/include/presonus/panel')/(n+'.hpp') for n in ['ElementInfo','Element','OffscreenElement','FieldElement','TextEntryElement']]
CORE=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a')
FLAGS=['g++','-std=c++17','-O2','-fno-sized-deallocation','-Ulinux','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework']
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','replay']);p.add_argument('--exe',type=Path);p.add_argument('--task-id');a=p.parse_args();BUILD.mkdir(parents=True,exist_ok=True);commands=[]
 def call(argv):
  argv=list(map(str,argv));r=subprocess.run(argv,text=True,capture_output=True);commands.append(dict(argv=argv,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));(BUILD/(a.mode+'.json')).write_text(json.dumps(commands,indent=2)+'\n');assert r.returncode==0,(r.stdout,r.stderr);return r.stdout
 if a.mode=='format':
  print(call(['uc-library/.venv/bin/clang-format','--version']));call(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*HEADERS,*SOURCES,TEST/'Replay.cpp'])
 elif a.mode=='compile':
  objs=[]
  for source in [*SOURCES,Path('uc-library/src/Presonus/Panel/LCDManager.cpp'),TEST/'Replay.cpp']:
   obj=BUILD/(source.stem+'.o');call([*FLAGS,'-MMD','-c',source,'-o',obj]);objs.append(obj)
  call(['g++',*objs,CORE,CORE.with_name('libpresonus_core_allocator.a'),'-pthread','-Wl,--gc-sections','-Wl,--wrap=_ZdlPv','-o',BUILD/'Replay'])
 elif a.mode=='symbols':
  syms={line.split()[-1] for line in call(['nm','--defined-only',*[BUILD/(s.stem+'.o') for s in SOURCES]]).splitlines() if line.split()};fixture=json.loads((TEST/'fixtures.json').read_text());assert all(row['original']['mangled'] in syms for row in fixture);print('24 ABI tasks / 48 ELF identities have exact compiled mangling; no layout/ARM ABI claim.')
 else:
  spec=importlib.util.spec_from_file_location('text_field_native',TEST/'native.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native);target=None
  if a.task_id:
   tasks=json.loads((native.PACKET/'CONTEXT.json').read_text())['tasks'];target=next(t['originals'][0]['mangled'] for t in tasks if t['id']==a.task_id)
  observed=native.run(target);expected=json.loads((TEST/'fixtures.json').read_text());expected=[r for r in expected if target is None or r['original']['mangled']==target];assert observed==expected
  exe=(a.exe or BUILD/'Replay').resolve();assert call([exe]).strip()=='lifecycle-provider-copy-delete-ok';count=0
  for row in observed:
   n=row['original']['mangled']
   if row['original']['role']=='server':continue
   mode=next((v for k,v in [('12deltaEncoder','delta'),('14setCurrentChar','set'),('14getCurrentChar','current'),('7getChar','char'),('3tap','tap'),('4next','next'),('12paramChanged','changed')] if k in n),None)
   if '13getDrawStringEPK' in n:mode='helper'
   elif '13getDrawString' in n:mode='fieldformat' if '12FieldElement' in n else 'textformat'
   elif '6render' in n:mode='fieldrender' if '12FieldElement' in n else 'textrender'
   elif '4draw' in n:mode='textdraw'
   if not mode:continue
   for case in row['cases']:
    inp=case.get('input',{});text=inp.get('text','abcdefghijklmnopqrstuvwxyz0123456789' if case.get('param') else 'abc');cursor=inp.get('cursor',1 if 'render' in mode or mode=='textdraw' else 0)
    actual=json.loads(call([exe,mode,text,cursor,inp.get('delta',0),inp.get('color',0),inp.get('force',0),int(case.get('param',mode=='changed')),int(case.get('enabled',True)),case.get('message',0),inp.get('repeat') or 'none']))
    if 'snapshot' in case:
     expected=case['snapshot'];assert {k:actual[k] for k in expected}==expected,(mode,case,actual)
    if 'return' in case:assert actual['return']==case['return'],(mode,case,actual)
    if 'text' in case:assert actual['formatted']==case['text'],(mode,case,actual)
    for key in ('current','previous'):
     if key in case:assert actual[key]==case[key],(mode,key,case,actual)
    count+=1
  print(f'{len(observed)} full native original ranges replayed; {count} portable cases and actual CCL/LCDManager/observer/copy/deallocation path passed.')
if __name__=='__main__':main()
