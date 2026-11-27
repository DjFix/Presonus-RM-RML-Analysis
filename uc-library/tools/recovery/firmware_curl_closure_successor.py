#!/usr/bin/env python3
"""Generate a separate versioned firmware checker; canonical checker unchanged."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT/'temp/recovery-work/rolling-c001-20261124/integration/sqlite-cycle02/wave16-preflight01/TRANSITIVE-CURL-CODEC-BINDING02.json'
CHECK = ROOT/'uc-library/tests/recovery/rolling10_next100_surface_firmware_c1/check_current104_static.py'
ALLOWED = {'libgssapi_krb5.so.2','libkrb5.so.3','libk5crypto.so.3','libkrb5support.so.0'}

def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def ref(p): return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}

def put(p,x):
    with p.open('x') as f: json.dump(x,f,indent=2); f.write('\n')

def capture(argv,p):
    output=subprocess.check_output(argv,text=True);p.write_text(output);return output

def main():
    a=argparse.ArgumentParser();a.add_argument('--out',required=True,type=Path);args=a.parse_args()
    out=args.out.resolve();assert out.is_relative_to(ROOT/'evidence/recovery');out.mkdir(parents=True,exist_ok=False)
    contract=json.loads(OLD.read_text());provider_path=ROOT/contract['curl_provider']['path'];assert sha(provider_path)==contract['curl_provider']['sha256'];provider=json.loads(provider_path.read_text())
    preserved=[]
    for p in [OLD,provider_path,CHECK,ROOT/'uc-library/tools/recovery/pinned_codec_replay_binding_curl_scope.py']:
        q=out/('historical-'+p.name);shutil.copyfile(p,q);assert sha(p)==sha(q);preserved.append({'original':ref(p),'preserved':ref(q)})
    exe=ROOT/'temp/core-upstream/root-integration-01'/contract['target'];link=ROOT/contract['link']['path'];curl=Path(provider['runtime']['path']).resolve(strict=True)
    assert sha(exe)==contract['executable_sha256'] and sha(link)==contract['link']['sha256'] and sha(curl)==provider['runtime']['sha256']
    capture(['/usr/bin/ldd',str(exe)],out/'application-ldd.log')
    runtime=capture(['/usr/bin/ldd',str(curl)],out/'ldd.log')
    loaded={Path(x).resolve(strict=True) for x in re.findall(r'=>\s+(/\S+)',runtime)}|{Path(x).resolve(strict=True) for x in re.findall(r'^\s*(/\S+)\s+\(',runtime,re.M)}
    old_paths={Path(x['path']).resolve(strict=True) for x in provider['runtime_dependency_closure']};assert loaded|{curl}==old_paths
    changes=[]
    for row in provider['runtime_dependency_closure']:
        actual=sha(row['path'])
        if actual!=row['sha256']:
            assert Path(row['path']).name in ALLOWED;changes.append({'path':row['path'],'previous_sha256':row['sha256'],'current_sha256':actual});row['sha256']=actual
    assert {Path(x['path']).name for x in changes}==ALLOWED
    def needed(p,label):return re.findall(r'NEEDED.*\[(.*?)\]',capture(['/usr/bin/readelf','-d',str(p)],out/(label+'.log')))
    direct=needed(exe,'application-dynamic');curl_needed=needed(curl,'curl-dynamic');assert 'libcurl.so.4' in direct and not any(x.startswith(('libz.so','libpng')) for x in direct) and 'libz.so.1' in curl_needed
    z,=[x for x in provider['runtime_dependency_closure'] if Path(x['path']).name=='libz.so.1'];assert sha(z['path'])==z['sha256']
    capture(['dpkg-query','-W','-f=${Package} ${Version}\n','libgssapi-krb5-2','libkrb5-3','libk5crypto3','libkrb5support0'],out/'packages.log')
    provider['previous_provider']=ref(provider_path);provider['closure_changes']=changes
    provider_new=out/'CURL-PROVIDER-CLOSURE-SUCCESSOR.json';put(provider_new,provider)
    contract['previous_contract']=ref(OLD);contract['curl_provider']=ref(provider_new)
    contract_new=out/'TRANSITIVE-CURL-CODEC-BINDING03.json';put(contract_new,contract)
    text=CHECK.read_text();assert str(OLD.relative_to(ROOT)) in text and sha(OLD) in text
    # Preserve original TASK/BASE despite the separate successor's evidence location.
    text=text.replace('TASK=pathlib.Path(__file__).parent.name',"TASK='rolling10_next100_surface_firmware_c1'")
    text=text.replace(str(OLD.relative_to(ROOT)),str(contract_new.relative_to(ROOT))).replace(sha(OLD),sha(contract_new))
    successor=out/'check_current104_static_curl_successor.py';successor.write_text(text)
    put(out/'TRANSITION.json',{'passed_preparation':True,'producer':ref(Path(__file__)),'preserved':preserved,'changes':changes,'provider':ref(provider_new),'contract':ref(contract_new),'successor_checker':ref(successor),'canonical_checker_unchanged':ref(CHECK),'executable':ref(exe),'link':ref(link),'direct_needed':direct,'curl_needed':curl_needed,'unchanged_zlib':z,'affected_registered_tests':['rolling10_next100_surface_firmware_c1_replay'],'scope':'Four current Kerberos dependency hashes only. Curl/zlib/application executable/link and all archives unchanged. Constructor fields/lifetime; no network/authentication/codec behavior or exclusive symbol-origin claim. No canonical checker edit or readiness mutation.'})

if __name__=='__main__':main()
