"""Rebuild/replay against independently decoded original data, no function credit."""
import argparse, hashlib, json, subprocess
from pathlib import Path
from native import collect

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); ap.add_argument('--core-dir',required=True); args=ap.parse_args()
    root=Path(__file__).resolve().parents[4]; out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=True)
    core=Path(args.core_dir).resolve(); base=Path(__file__).resolve().parent
    inputs=[core/'libcorelib.a',core/'libpresonus_core_allocator.a']; before={str(p):sha(p) for p in inputs}
    fixtures=collect(root)
    assert json.loads((base/'fixtures.json').read_text())==fixtures
    commands=[]
    def run(argv):
        r=subprocess.run(list(map(str,argv)),cwd=root,text=True,capture_output=True)
        commands.append(dict(argv=list(map(str,argv)),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
        (out/'commands.json').write_text(json.dumps(commands,indent=2))
        assert r.returncode==0, r.stderr
        return r.stdout
    sources=[root/'uc-library/include/presonus/mixer/DynamicsParameterInfo.hpp',root/'uc-library/src/Presonus/Mixer/DynamicsParameterInfo.cpp',base/'Replay.cpp']
    fmt=root/'uc-library/.venv/bin/clang-format'
    version=run([fmt,'--version']).strip()
    run([fmt,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',*sources])
    common=['/usr/bin/c++','-std=c++17','-Ulinux','-DCORE_USE_OPENSSL=1','-pthread','-I'+str(root/'uc-library/include'),'-I'+str(root/'third_party/ccl-framework')]
    run([*common,'-M',sources[1],sources[2]])
    run([*common,'-c',root/'third_party/ccl-framework/core/portable/coreparams.cpp','-o',out/'coreparams.o'])
    run([*common,'-c',sources[1],'-o',out/'provider.o'])
    run([*common,sources[2],out/'provider.o',out/'coreparams.o','-Wl,--start-group',*inputs,'-Wl,--end-group','-ldl','-lrt','-o',out/'replay'])
    symbols=run(['/usr/bin/nm','-C',out/'provider.o'])
    assert 'presonus::mixer_parameter_info::Gate' in symbols and 'presonus::mixer_parameter_info::Compressor' in symbols
    lines=run([out/'replay']).splitlines(); expected=[]
    for obj in fixtures['objects'][:2]:
        for p in obj['entries']:
            def t(s): return 'null' if s is None else (s.encode()+b'\0').hex()
            expected.append([str(p['type']),str(p['tag']),p['name_bytes'],*p['float_bits'],str(p['flags']),*[t(p['texts'][k]) for k in ['unit','curve','labels','title','short_title']]])
    assert len(lines)==len(expected)==20
    observations=[]
    for line,want in zip(lines,expected):
        values=line.split(); assert values[:-2]==want,(values,want)
        observations.append(dict(formatter_present=values[-2]=='1',interpolator_present=values[-1]=='1'))
    assert before=={str(p):sha(p) for p in inputs}, 'provider archive changed during replay'
    proof=dict(kind='immutable_original_data_support_proof_v1',status='passed',function_credit=0,object_identities=6,selected_tables=4,records=20,formatter_version=version,provider_archives=before,consumer_observations=observations,domain='All bytes of six exact STT_OBJECT ranges; all 60 records and all referenced strings independently decoded; 20 host records all fields and float bits; real pinned ParamList.add, tag/name lookup, defaults, flags and title fallback. Duplicates compared, no ARM execution.',caveats=['Independent source-port data; no original local export or ARM ABI/layout claim.','Pinned CCL source selected by policy, not established as original firmware provider.','No application formatter/interpolator registrations are installed by this replay. Built-in linear interpolation resolves; app curves and all named formatters do not. Those consumers require explicit app adapters; no invented factory.','No original STT_FUNC, constructor, reconstructed-function or readiness credit.'],source_hashes={str(p.relative_to(root)):sha(p) for p in sources},fixtures_sha256=sha(base/'fixtures.json'),commands_sha256=sha(out/'commands.json'),pinned_core_commit='e8cbdea4a4a20e15111f5a690798a259c0374b31',provider_source_sha256=sha(root/'third_party/ccl-framework/core/portable/coreparams.cpp'))
    (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof,indent=2))
if __name__=='__main__': main()
