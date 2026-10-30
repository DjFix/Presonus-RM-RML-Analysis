"""Regenerate and compile private GNU math only from hash-verified archive members."""
import argparse
import datetime
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import tarfile
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('repository',type=Path)
p.add_argument('--archive',required=True,type=Path)
p.add_argument('--signature',required=True,type=Path)
p.add_argument('--manifest',required=True,type=Path)
p.add_argument('--output',required=True,type=Path)
p.add_argument('--cc',default='/usr/bin/cc')
p.add_argument('--ar',default='/usr/bin/ar')
p.add_argument('--nm',default='/usr/bin/nm')
a=p.parse_args();repo=a.repository.resolve();out=a.output.resolve()
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
manifest=json.loads(a.manifest.read_text())
assert sha(a.archive)==manifest['archive_sha256']
assert sha(a.signature)==manifest['signature_sha256']
assert out.is_relative_to(repo/'temp') and out.name=='private-glibc29-provider'
assert len(out.relative_to(repo/'temp').parts)>=2
owner='presonus-dsp-single-pole-private-glibc29'
marker='.presonus-vendor-owner.json'
previous_generation=None
if out.exists():
    assert (out/marker).is_file(),'Refuse to remove an unowned output directory'
    previous=json.loads((out/marker).read_text())
    assert previous['owner']==owner and previous['archive_sha256']==manifest['archive_sha256']
    # Preserve every earlier build's logs/objects and any edited cache inputs.
    # History is evidence only, never a source of compilation inputs.
    history=out.parent/'private-glibc29-provider-history'
    history.mkdir(exist_ok=True)
    previous_generation=history/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.rename(previous_generation)
out.mkdir(parents=True,exist_ok=False)
(out/marker).write_text(json.dumps(dict(owner=owner,archive_sha256=manifest['archive_sha256']),indent=2)+'\n')
tree=out/'source';tree.mkdir()
members={r['member']:r for r in manifest['members']}
expected={}
with tarfile.open(a.archive,'r:bz2') as archive:
    for name,row in members.items():
        path=Path(name);assert not path.is_absolute() and '..' not in path.parts
        member=archive.getmember(name);assert member.isfile()
        data=archive.extractfile(member).read();assert hashlib.sha256(data).hexdigest()==row['sha256']
        target=tree/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        expected[target.resolve()]=row

def verify_tree():
    assert {x.resolve() for x in tree.rglob('*') if x.is_file()}==set(expected)
    for path,row in expected.items():assert sha(path)==row['sha256'],str(path)

verify_tree()
scratch=out/'scratch';scratch.mkdir();commands=[]

def run(label,argv):
    print(shlex.join(map(str,argv)),flush=True)
    result=subprocess.run(list(map(str,argv)),cwd=repo,env=dict(os.environ,TMPDIR=str(scratch)),
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (out/(label+'.log')).write_text(result.stdout)
    commands.append(dict(label=label,argv=list(map(str,argv)),returncode=result.returncode))
    (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    if result.returncode:raise SystemExit(result.returncode)
    return result.stdout

run('compiler-version',[a.cc,'--version'])
run('archiver-version',[a.ar,'--version'])
root=tree/'glibc-2.9'
renames=['-D__ieee754_expf=presonus_glibc29_expf',
         '-D__exp_atable=presonus_glibc29_exp_atable','-D__exp_deltatable=presonus_glibc29_exp_deltatable']
flags=['-std=c99','-fgnu89-inline','-O3','-fno-lto','-fno-fast-math','-ffp-contract=off',
       '-frounding-math','-fexcess-precision=standard','-fno-builtin',*renames,
       '-I'+str(root/'sysdeps/ieee754'),'-I'+str(root/'math'),'-I'+str(root/'sysdeps/generic')]
objects=[];compiler_vendor_inputs={};system_inputs={}
for label,source in [('expf',root/'sysdeps/ieee754/flt-32/e_expf.c'),('tables',root/'sysdeps/ieee754/dbl-64/t_exp.c')]:
    verify_tree();obj=out/(label+'.o');dep=out/(label+'.d')
    run(label+'-compile',[a.cc,*flags,'-MD','-MF',dep,'-c',source,'-o',obj]);verify_tree()
    for token in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
        path=Path(token).resolve();assert path.is_file(),str(path)
        if path.is_relative_to(tree):
            assert path in expected and sha(path)==expected[path]['sha256']
            row=expected[path]
            compiler_vendor_inputs[str(path.relative_to(tree))]=dict(archive_member=row['member'],sha256=sha(path),
                checked_before_compile=True,checked_after_compile=True)
        else:system_inputs[str(path)]=sha(path)
    objects.append(obj)
text=run('defined-symbols',[a.nm,'-g','--defined-only',*objects])
names={line.split()[-1] for line in text.splitlines() if len(line.split())>=3}
assert names=={'presonus_glibc29_expf','presonus_glibc29_exp_atable','presonus_glibc29_exp_deltatable'},names
undefined=run('undefined-symbols',[a.nm,'-u',*objects])
assert not any(line.split() and line.split()[-1] in ('expf','exp','__ieee754_expf') for line in undefined.splitlines())
library=out/'libpresonus_private_glibc29.a'
run('archive',[a.ar,'rcs',library,*objects]);verify_tree()
receipt=dict(build_passed=True,owner=owner,archive_sha256=sha(a.archive),signature_sha256=sha(a.signature),
    member_manifest_sha256=sha(a.manifest),guard_sha256=sha(Path(__file__)),
    generated_source_is_disposable=True,regenerated_from_archive_this_build=True,
    previous_generation_preserved=str(previous_generation) if previous_generation else None,
    mutable_library_headers_used=False,upstream_files_modified=False,private_symbol_renames=renames,
    compiler_vendor_inputs=compiler_vendor_inputs,compiler_system_inputs=system_inputs,
    generated_member_hashes={str(path.relative_to(tree)):sha(path) for path in expected},
    objects={x.name:sha(x) for x in objects},library_sha256=sha(library),
    host_expf_interposition=False,signature_trust_verified=False,commands=commands)
(out/'provider-validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(build_passed=True,library=str(library),library_sha256=sha(library),
    vendor_compiler_inputs=len(compiler_vendor_inputs),regenerated=True)),flush=True)
