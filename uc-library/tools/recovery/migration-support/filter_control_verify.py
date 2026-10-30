"""Compile and replay filter controllers, sealing original symbol identities."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('repository',type=Path)
    p.add_argument('--platform',choices=('mac','linux'),required=True)
    a=p.parse_args()
    repo=a.repository.resolve()
    lib=repo/('temp/recovery-package/uc-library' if a.platform=='mac' else 'uc-library')
    out=repo/'evidence/recovery/2026-10-27/filter-control'/a.platform
    out.mkdir(parents=True,exist_ok=True)
    scratch=repo/'temp/recovery-work/filter-control'/a.platform
    scratch.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,TMPDIR=str(scratch),TMP=str(scratch),TEMP=str(scratch))
    paths=['include/presonus/mixer_dsp/FilterControllers.hpp','src/mixer_dsp/FilterControllers.cpp','tests/filter_control_tests.cpp','tools/filter_control_oracle.py','tools/filter_control_verify.py','tools/mixer_dsp_oracle.py']
    fixture=lib/'validation/filter-control/arm-vectors.txt'
    oracle=json.loads((lib/'validation/filter-control/arm-oracle.json').read_text())
    assert sha(fixture)==oracle['fixtures_sha256']
    exe=scratch/'filter_control_tests'
    flags=['-std=c++17','-O3','-fno-fast-math','-ffp-contract=off']
    if a.platform=='mac': flags+=['-ffp-model=strict']
    commands=[('compile',['/usr/bin/c++',*flags,'-I'+str(lib/'include'),str(lib/paths[1]),str(lib/paths[2]),'-o',str(exe)]),('tests',[str(exe),str(fixture)]),('symbols',['/usr/bin/nm','-g',str(exe)])]
    results=[]
    for name,command in commands:
        result=subprocess.run(command,cwd=repo,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (out/(name+'.log')).write_text(result.stdout)
        results.append(dict(step=name,command=command,returncode=result.returncode))
        (out/'commands.json').write_text(json.dumps(results,indent=2)+'\n')
        assert result.returncode==0,result.stdout
    symbols=set()
    for line in (out/'symbols.log').read_text().splitlines():
        fields=line.split()
        if len(fields)>=3 and fields[-2] in ('T','W'):
            name=fields[-1]
            symbols.add(name[1:] if name.startswith('__Z') else name)
    functions=oracle['functions']
    assert all(s['mangled'] in symbols for s in functions.values())
    source_hashes={name:sha(lib/name) for name in paths}
    validation=dict(platform=a.platform,cpp_differential_passed=True,compiled_mangled_names_matched=True,
        mangled_names=[s['mangled'] for s in functions.values()],original_elf_sha256=oracle['original_elf_sha256'],
        functions=[dict(mangled=s['mangled'],original_elf_sha256=oracle['original_elf_sha256'],original_address=s['address']) for s in functions.values()],
        sources=source_hashes,fixture_sha256=sha(fixture),oracle_sha256=sha(lib/'validation/filter-control/arm-oracle.json'),cases=oracle['cases'],
        logs={str(f.relative_to(repo)):sha(f) for f in sorted(out.glob('*.log'))},
        domain=oracle['domain'],declaration_uncertainties=['Getter source return spelling float selected from observed raw binary32 parameter-value convention; non-template return type not mangled. Setter original return declaration unresolved, ignored machine R0; setters remain compiled/pending. Portable state/setup constructor is independent and does not establish original layout, inheritance or ownership.'],
        original_arm_abi_verified=False,hardware_verified=False)
    proof=out/'validation.json'
    proof.write_text(json.dumps(validation,indent=2)+'\n')
    if a.platform=='linux':
        target=lib/'validation/filter-control/validation.json'
        target.write_bytes(proof.read_bytes())
        ready=[]; pending=[]
        for op,s in functions.items():
            record=dict(mangled=s['mangled'],original_elf_sha256=oracle['original_elf_sha256'],original_address=s['address'],validation='validation/filter-control/validation.json',validation_sha256=sha(target),sources=source_hashes,domain=oracle['domain'],portable_ready=op.islower(),original_return_declaration_proven=False)
            if op.islower(): ready.append(record)
            else: pending.append(dict(record,cpp_compiled=True,mangling_namespace_checked=True))
        for name,records in [('ready-functions.fragment.json',ready),('compiled-functions.fragment.json',pending)]:
            (lib/'validation/filter-control'/name).write_text(json.dumps(dict(functions=records),indent=2)+'\n')
    print(json.dumps(dict(platform=a.platform,cases=oracle['cases'],mangled_names_matched=len(functions),proof_sha256=sha(proof))))

if __name__=='__main__':main()
