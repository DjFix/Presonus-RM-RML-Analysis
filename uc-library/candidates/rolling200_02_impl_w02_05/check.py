#!/usr/bin/env python3
"""Local hash-bound NOAA receive checks; no registry or shared build writes."""
import argparse
import json
from pathlib import Path
import subprocess
import os

ROOT = Path(__file__).resolve().parents[3]
CAND = Path(__file__).resolve().parent
SCRATCH = ROOT / 'temp/recovery-work/rolling200-02/rolling200_02_impl_w02_05'
BUILD = ROOT / 'temp/core-upstream/root-integration-01'
SOURCES = ['uc-library/include/presonus/avb/protocol.hpp', 'uc-library/src/Presonus/AVB/AvbManagerReceive.cpp', str((CAND/'receive_tests.cpp').relative_to(ROOT))]
WRAPS = ['_ZN8Presonus3AVB14AvbManagerBase15unpackAvbSpiMsgEPhPKhi', '_ZN8Presonus3AVB11AvbListener6updateEhhh', '_ZN8Presonus3AVB9AvbTalker6updateEhh']
TARGET = '_ZN8Presonus3AVB14AvbManagerBase7receiveERKNS_4NOAA11SysexPacketE'
DICE = '_ZN8Presonus3AVB14AvbManagerBase7receiveERKNS_4DICE11SysexPacketE'
FIXTURE = ROOT / 'evidence/recovery/2026-11-05/rolling200-02/rolling200_02_impl_w02_05/native02/receive-vectors.txt.gz'

def run(argv):
    print(json.dumps(argv), flush=True)
    return subprocess.check_output(argv, cwd=ROOT, env=dict(os.environ, TMPDIR=str(SCRATCH)), stderr=subprocess.STDOUT, text=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode', choices=['format', 'compile', 'symbols', 'replay'])
    parser.add_argument('--executable', type=Path)
    args=parser.parse_args()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    exe=args.executable or SCRATCH/'receive-tests'
    if args.mode=='format':
        formatter=str(ROOT/'uc-library/.venv/bin/clang-format')
        print(run([formatter, '--version']))
        print(run([formatter, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror', *SOURCES]))
    elif args.mode=='compile':
        argv=['/usr/bin/c++','-std=c++17','-O2','-pthread','-Ulinux','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Iuc-library/include','-I'+str(BUILD/'upstream-core/sdk/include/presonus-core-5'), 'uc-library/src/Presonus/AVB/AvbManagerReceive.cpp','uc-library/src/Presonus/AVB/Protocol.cpp','uc-library/src/Presonus/AVB/Streams.cpp',str(CAND/'receive_tests.cpp'), *['-Wl,--wrap='+x for x in WRAPS],str(BUILD/'upstream-core/sdk/lib/libpresonus_core_allocator.a'),'-lz','-o',str(exe)]
        print(run(['/usr/bin/c++', '--version']))
        print(run(argv))
    elif args.mode=='symbols':
        output=run(['nm','--defined-only',str(exe)])
        symbols={line.split()[-1] for line in output.splitlines() if line.split()}
        assert {TARGET,DICE,*WRAPS} <= symbols
        print('PASS original NOAA and DICE symbols, helper and real stream providers')
        print(output)
    else:
        print(run([str(exe),str(FIXTURE)]))

if __name__=='__main__':
    main()
