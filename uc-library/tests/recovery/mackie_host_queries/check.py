import json,subprocess,sys
from pathlib import Path
BASE=Path('uc-library/tests/recovery/mackie_host_queries')
SCRATCH=Path('temp/recovery-work/mackie-queries-local')
EXE=SCRATCH/'replay'
SOURCES=['uc-library/src/Presonus/MackieControlModelHostConnection.cpp','uc-library/src/Presonus/MackieControlModel.cpp',str(BASE/'Replay.cpp')]
def run(argv):
    p=subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);print(p.stdout,end='');p.check_returncode();return p.stdout
mode=sys.argv[1]
if len(sys.argv)>2: EXE=Path(sys.argv[2])
if mode=='compile':
    SCRATCH.mkdir(parents=True,exist_ok=True)
    run(['g++','-std=c++17','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework',*SOURCES,'-Wl,--gc-sections','-Wl,--wrap=rand','-o',str(EXE)])
elif mode=='symbols':
    output=run(['nm','--defined-only',str(EXE)])
    for name in ['_ZN8Presonus18MackieControlModel34sendHostConnectionQueryAlternativeEv','_ZN8Presonus18MackieControlModel23sendHostConnectionQueryEv']:assert name in output
elif mode=='replay':
    count=0
    for case in json.loads((BASE/'fixtures.json').read_text())['cases']:
        for real in ([0,1] if case['seed'] is not None else [0]):
            argv=[str(EXE),str(int(case['alternative'])),str(real),str(case['seed'] or 0),*map(str,case['identity']),*map(str,case['raw'])]
            result=subprocess.run(argv,text=True,capture_output=True,check=True)
            expected=case['expected'];assert list(map(int,result.stdout.split()))==expected['challenge']+expected['sent'][0]['bytes'],(case,result.stdout)
            count+=1
    print('portable comparisons',count,'each repeated twice; prescribed rand and genuine host libc seeded paths; typed positive sink; exact challenge/payload/port/call-order checks')
else:raise ValueError(mode)
