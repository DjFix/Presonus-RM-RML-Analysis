import hashlib, json, pathlib, subprocess, sys, time
BASE=pathlib.Path('uc-library/candidates/graph-live-trial-03-pcm')
SCRATCH=pathlib.Path('temp/recovery-work/graph-live-trial-03/pcm-worker')
SOURCE='uc-library/src/Presonus/PCM4104/Pcm4104Spi.cpp'
HEADER='uc-library/include/presonus/pcm4104/Pcm4104Spi.hpp'
TEST='uc-library/tests/graph_trial03_pcm_tests.cpp'
EXE=str(SCRATCH/'pcm-replay')
SYMBOL='_ZN8Presonus7PCM410410Pcm4104Spi32lookupChannelAttenuationRegisterEi'
commands={
'format':['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',SOURCE,HEADER,TEST],
'compile':['c++','-std=c++17','-Wall','-Wextra','-Werror','-Iuc-library/include',SOURCE,TEST,'-o',EXE],
'symbols':['nm','--defined-only',EXE],
'replay':[EXE,str(BASE/'fixtures.txt')],
}
if len(sys.argv)==2:
    kind=sys.argv[1]
    result=subprocess.run(commands[kind],capture_output=True,text=True)
    print(result.stdout,end='');print(result.stderr,end='',file=sys.stderr)
    if result.returncode: sys.exit(result.returncode)
    if kind=='symbols' and not any(line.split()[-1:]==[SYMBOL] for line in result.stdout.splitlines()): sys.exit(7)
else:
    results=[]
    for kind,argv in commands.items():
        start=time.time()
        run=subprocess.run([sys.executable,__file__,kind],capture_output=True,text=True)
        (BASE/(kind+'.log')).write_text(run.stdout+run.stderr)
        results.append(dict(kind=kind,argv=argv,exit_code=run.returncode,start_unix=start,end_unix=time.time()))
        if run.returncode: raise RuntimeError(kind)
    sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
    proof=dict(version=1,source_sha256={p:sha(p) for p in [SOURCE,HEADER,TEST]},fixture_sha256=sha(BASE/'fixtures.txt'),producer_sha256=sha(__file__),native_proof_sha256=sha(BASE/'native-proof.json'),formatter=subprocess.check_output(['uc-library/.venv/bin/clang-format','--version'],text=True).strip(),compiler=subprocess.check_output(['c++','--version'],text=True).splitlines()[0],symbols_tool=subprocess.check_output(['nm','--version'],text=True).splitlines()[0],checks=results,scope='6149 independent original ARM cases; portable source port, not original declaration, layout or ARM ABI verification')
    (BASE/'local-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print('format, compile, original mangled symbol and native-fixture replay passed')
