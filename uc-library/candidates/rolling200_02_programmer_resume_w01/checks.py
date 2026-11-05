import json
import subprocess
import sys
from pathlib import Path

BASE=Path('uc-library/candidates/rolling200_02_programmer_resume_w01')
SCRATCH=Path('temp/recovery-work/rolling200-02/programmer-resume-w01')
SOURCE='uc-library/src/Presonus/NOAA/TCardProgrammerUpdate.cpp'
NAMES=['_ZN8Presonus4NOAA15TCardProgrammer10writeImageEv','_ZN8Presonus4NOAA15TCardProgrammer6updateEv','_ZN8Presonus4NOAA15TCardProgrammer8eraseAllEv','_ZN8Presonus4NOAA15TCardProgrammer9unprotectEv']

def main():
    mode=sys.argv[1]
    if mode=='compile':
        SCRATCH.mkdir(parents=True,exist_ok=True)
        commands=[['g++','-std=c++17','-Ulinux','-Iuc-library/include','-Ithird_party/ccl-framework','-c',SOURCE,'-o',str(SCRATCH/'update.o')],['g++','-std=c++17','-Ulinux','-Iuc-library/include','-Ithird_party/ccl-framework',str(BASE/'replay.cpp'),str(SCRATCH/'update.o'),'-o',str(SCRATCH/'replay')]]
        for argv in commands: subprocess.run(argv,check=True)
        print(json.dumps({'compile_commands':commands,'status':'passed'}))
    elif mode=='symbols':
        argv=['nm','--defined-only',str(SCRATCH/'update.o')]
        text=subprocess.run(argv,check=True,capture_output=True,text=True).stdout
        defined={line.split()[-1] for line in text.splitlines() if line.split()}
        assert set(NAMES)<=defined, set(NAMES)-defined
        print(json.dumps({'argv':argv,'mangled':NAMES,'object_format':'Linux ELF x86_64; no decoration adjustment','status':'passed'}))
    else: raise ValueError(mode)

if __name__=='__main__': main()
