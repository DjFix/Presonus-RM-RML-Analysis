#!/usr/bin/env python3
"""Format maintained C++ and record the checked source/configuration hashes."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--library',type=Path,required=True)
    p.add_argument('--formatter',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--apply',action='store_true')
    p.add_argument('--path',type=Path,action='append',default=[],help='Explicit library-relative paths; preserve still-current prior checks')
    p.add_argument('--path-list',type=Path,help='JSON library-relative input list; check only C++ suffixes')
    a=p.parse_args()
    library=a.library.resolve()
    formatter=str(a.formatter.resolve())
    explicit=list(a.path)
    if a.path_list:
        listed=json.loads(a.path_list.read_text())
        assert isinstance(listed,list) and all(isinstance(name,str) for name in listed)
        explicit.extend(Path(name) for name in listed if Path(name).suffix in ('.cpp','.hpp','.h'))
    scoped=bool(a.path or a.path_list)
    paths=sorted({(library/path).resolve() for path in explicit}) if scoped else sorted(path for directory in ('src','include','tests','examples') for path in (library/directory).rglob('*') if path.is_file() and path.suffix in ('.cpp','.hpp','.h'))
    assert all(path.is_relative_to(library) and path.is_file() and path.suffix in ('.cpp','.hpp','.h') for path in paths)
    before={str(path.relative_to(library)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    version=subprocess.run([formatter,'--version'],check=True,text=True,capture_output=True).stdout.strip()
    flags=['--style=file','--fallback-style=LLVM']
    if a.apply:subprocess.run([formatter,*flags,'-i',*map(str,paths)],check=True)
    subprocess.run([formatter,*flags,'--dry-run','--Werror',*map(str,paths)],check=True)
    report=dict(formatter=version,configuration_sha256=hashlib.sha256(a.config.read_bytes()).hexdigest(),
                format_check_passed=True,files={str(path.relative_to(library)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})
    previous_path=library/'validation/formatting.json'
    if scoped and previous_path.exists():
        previous=json.loads(previous_path.read_text())
        if previous.get('formatter')==version and previous.get('configuration_sha256')==report['configuration_sha256']:
            retained={name:digest for name,digest in previous.get('files',{}).items() if (library/name).is_file() and hashlib.sha256((library/name).read_bytes()).hexdigest()==digest}
            report['files']={**retained,**report['files']}
    report['changed_files']=[name for name,digest in report['files'].items() if name in before and digest!=before[name]]
    (library/'validation/formatting.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'formatter':version,'checked_files':len(paths),'changed_files':len(report['changed_files']),'format_check_passed':True},indent=2))


if __name__=='__main__':main()
