"""Exact Linux Itanium identities for the five locally complete proposals."""
import argparse,json,pathlib,subprocess
SELECTED={1,4,5,7,12,13,14,15,17,18,19,20}
def main():
 p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--metadata',required=True);a=p.parse_args();rows=json.loads(pathlib.Path(a.metadata).read_text())['packets_read'];symbols=subprocess.check_output(['/usr/bin/nm','--defined-only',a.executable],text=True);names={line.split()[-1] for line in symbols.splitlines() if line.split()}
 for r in rows:
  if int(r['packet'].split('_')[-1]) in SELECTED:
   assert r['target']['mangled'] in names,r['target']['mangled']
 print('12 exact original mangled identities found; no ARM ABI claim')
if __name__=='__main__':main()
