#!/usr/bin/env python3
"""Fetch a pinned Core source mirror and verify every original Git blob ID."""
import argparse
import concurrent.futures
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree',type=Path,required=True)
    parser.add_argument('--commit',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    args=parser.parse_args()
    root=args.output.resolve();root.mkdir(parents=True,exist_ok=True)
    records=[]
    for line in args.tree.read_text().splitlines():
        metadata,name=line.split('\t',1);mode,kind,oid=metadata.split()
        if kind=='blob':records.append(dict(path=name,git_blob_sha1=oid,mode=mode))
    def fetch(record):
        path=(root/record['path']).resolve()
        assert path.is_relative_to(root)
        url=f'https://raw.githubusercontent.com/cclsoftware/ccl-framework/{args.commit}/'+urllib.parse.quote(record['path'])
        for attempt in range(3):
            try:
                data=path.read_bytes() if path.exists() else urllib.request.urlopen(url,timeout=45).read()
                actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
                assert actual==record['git_blob_sha1'],f'Git blob mismatch: {path}'
                if not path.exists():
                    path.parent.mkdir(parents=True,exist_ok=True)
                    temporary=path.with_name(path.name+'.partial')
                    temporary.write_bytes(data);os.replace(temporary,path)
                return dict(record,sha256=hashlib.sha256(data).hexdigest(),size=len(data),url=url)
            except Exception as error:
                if attempt==2:return dict(record,error=repr(error),url=url)
                time.sleep(attempt+1)
    output=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for record in pool.map(fetch,records):
            output.append(record)
            if len(output)%25==0:print(f'{len(output)}/{len(records)} verified/downloaded',flush=True)
    failures=[item for item in output if 'error' in item]
    args.manifest.parent.mkdir(parents=True,exist_ok=True)
    args.manifest.write_text(json.dumps(dict(commit=args.commit,tree_sha256=hashlib.sha256(args.tree.read_bytes()).hexdigest(),files=output,failures=len(failures)),indent=2)+'\n')
    print(json.dumps(dict(files=len(output),failures=len(failures))))
    if failures:raise SystemExit(1)


if __name__=='__main__':main()
