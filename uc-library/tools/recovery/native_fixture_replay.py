"""Replay hash-bound ARM observations through actual compiled source ports."""
import argparse
import hashlib
import json
import pathlib
import subprocess


def main():
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=('book','beast'),required=True)
    p.add_argument('--executable',required=True);p.add_argument('--fixtures',type=pathlib.Path,required=True)
    p.add_argument('--sha256',required=True);a=p.parse_args()
    raw=a.fixtures.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=a.sha256:raise ValueError('Native fixture digest mismatch')
    fixtures=json.loads(raw);cases=0
    if a.kind=='book':
        for group in fixtures:
            rows=group['rows'];text=''.join(' '.join(map(str,row))+'\n' for row in rows)
            subprocess.run([a.executable],input=text,text=True,check=True);cases+=len(rows)
    else:
        for row in fixtures['cases']:
            result=subprocess.check_output([a.executable,str(row['group']),str(row['initial_count'])],text=True)
            actual=list(map(int,result.split()));expected=[int(bool(row['native_r0'])),row['count'],*row['tag_words_u32']]
            if actual!=expected:raise ValueError('Compiled/native fixture mismatch: '+repr(row))
            cases+=1
    print(json.dumps({'native_fixture_replay_passed':True,'cases':cases,'kind':a.kind}))


if __name__=='__main__':main()
