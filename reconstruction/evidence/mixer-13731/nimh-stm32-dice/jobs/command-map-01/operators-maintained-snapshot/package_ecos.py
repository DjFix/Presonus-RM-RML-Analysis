"""Package pinned, unmodified public reference source; not an exact TCAT source claim."""
from pathlib import Path
import hashlib,json,subprocess,tarfile
root=Path('/home/rs/projects/opencs/ai-line-analysis')
repo=Path('/home/rs/projects/opencs/ai-line-analysis/uc-library/validation/nimh-command-map/operator-inputs/upstream/ecos-community')
pin='2580ee933ff5bed1f39c18c882f2e1593d980ef6'
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==pin
assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True).strip()
out=root/'evidence/recovery/2026-10-27/nimh-command-map'
out.mkdir(parents=True,exist_ok=True)
selected=[]
for p in ('README','COPYING','COPYING.ecos','packages/hal/cortexm','packages/hal/common',
          'packages/kernel','packages/infra','packages/io','packages/error',
          'packages/services/memalloc','packages/language/c/libc','packages/pkgconf',
          'packages/devs/flash/cortexm','packages/devs/serial/cortexm',
          'packages/devs/spi/cortexm','packages/net/lwip_tcpip'):
    if subprocess.run(['git','-C',str(repo),'cat-file','-e',pin+':'+p],capture_output=True).returncode==0:
        selected.append(p)
archive=out/'ecos-reference-2580ee933ff5.tar.gz'
subprocess.run(['git','-C',str(repo),'archive','--format=tar.gz','--prefix=ecos-reference/',
                '--output='+str(archive),pin,*selected],check=True)
files=[]
with tarfile.open(archive) as t:
    for m in t.getmembers():
        assert not m.name.startswith('/') and '..' not in Path(m.name).parts
        if m.isfile():
            data=t.extractfile(m).read()
            files.append(dict(path=m.name,size=len(data),sha256=hashlib.sha256(data).hexdigest()))
        else:
            assert m.isdir(), 'reference archive contains unsupported links/special files'
old='ecos-v3_0-branchpoint:packages/hal/cortexm/arch/current/src/hal_misc.c'
baseline=subprocess.check_output(['git','-C',str(repo),'show',old])
(out/'ecos-3.0-branchpoint-hal_misc.c').write_bytes(baseline)
current=(repo/'packages/hal/cortexm/arch/current/src/hal_misc.c').read_bytes()
(out/'ecos-reference-hal_misc.c').write_bytes(current)
meta=dict(origin='https://github.com/kaos/ecos.git',upstream_family='public eCos community source mirror',
          commit=pin,commit_timestamp='2012-10-04T07:40:45Z',selected_paths=selected,
          archive=archive.name,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=files,
          notices='Source and embedded license notices preserved unmodified; see source headers and README.',
          identification=dict(rtos_family='eCos',exact_tcat_ecos_release=None,exact_tcat_vendor_revision=None,
                              tcat_sdk_banner='1.0.0.0 local beta',application_banner='1.5.5.0',
                              caveat='Neither banner is an eCos version. Reset control flow matches the public Cortex-M HAL family. The selected commit is a reference baseline, not proven original firmware source.'),
          reset_reference=dict(path='packages/hal/cortexm/arch/current/src/hal_misc.c',
                               sha256=hashlib.sha256(current).hexdigest(),
                               release_comparison_tag='ecos-v3_0-branchpoint',
                               release_reference_sha256=hashlib.sha256(baseline).hexdigest(),
                               relevant_fix='162c34ae36f8f0492f1d6da15b3d47c1099f721c',
                               caveat='2012 VSR loop-bound fix is a useful candidate fingerprint, not an exact revision proof; vendor backports/configuration remain possible.'))
(out/'ecos-source.json').write_text(json.dumps(meta,indent=2)+'\n')
print('Packaged source files:',len(files),'archive bytes:',archive.stat().st_size,'SHA256:',meta['archive_sha256'])
