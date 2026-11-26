import argparse,hashlib,importlib.util,json,subprocess
from pathlib import Path
from native import observe,PACKET,TASK
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).parent
WORK=ROOT/'temp/recovery-work/sol61-lifecycle'/TASK
SOURCES=['uc-library/include/presonus/MappableMixer.hpp','uc-library/src/Presonus/MappableMixer.cpp']
def run(argv):
 p=subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 print(p.stdout,end='');assert p.returncode==0,(argv,p.returncode)
 return p.stdout
def commands():
 flags=['g++','-std=c++17','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework']
 define=('-DSENDER' if 'object_change' in TASK else '-DVARIANT_C2' if '_c2_' in TASK else '-DVARIANT_D2' if '_d2_' in TASK else '-DLIFECYCLE')
 return [flags+['-c',SOURCES[1],'-o',str(WORK/'model.o')],flags+[define,str(HERE/'Replay.cpp'),str(WORK/'model.o'),'uc-library/src/Presonus/Surface/SLMixerHandler.cpp','-Wl,--gc-sections','-o',str(WORK/'Replay')]]
def main():
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['compile','symbols','replay']);a.add_argument('--exe',type=Path);args=a.parse_args();WORK.mkdir(parents=True,exist_ok=True)
 if args.mode=='compile':
  for cmd in commands():run(cmd)
 elif args.mode=='symbols':
  syms=run(['nm','--defined-only',str(WORK/'model.o')]); names={x.split()[-1] for x in syms.splitlines()}
  for row in json.loads(PACKET.read_text())['originals']:assert row['original']['mangled'] in names
 else:
  actual=observe();assert actual==json.loads((HERE/'fixtures.json').read_text())['observations']
  for row in actual:
   got=run([str((args.exe or WORK/'Replay').resolve()),*map(str,row['args'])]);events=[list(map(int,x.split())) for x in got.splitlines()]
   assert events==row['events'],(row,events)
  print(json.dumps({'cases':len(actual),'native_ranges':2,'passed':True}))
if __name__=='__main__':main()
