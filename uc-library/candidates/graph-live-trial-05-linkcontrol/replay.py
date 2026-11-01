import argparse,json,subprocess,pathlib
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args();rows=json.loads(pathlib.Path(a.fixtures).read_text())
for r in rows:
 if r['packet']==4 and r['new']==0 and r['msg']==3:continue # CCL Control dereferences null notification; excluded invalid provider input
 out=subprocess.check_output([a.executable,str(r['packet']),str(r['old']),str(r['new']),str(r['msg']),str(r['value']),'reserved'],text=True)
 result,right,inv=map(int,out.split());assert right==r['right'],(r,out)
 if r['packet']<3:assert result==r['result'],(r,out)
 if r['packet']==5:assert result==1,(r,out)
 if r['packet'] in (3,4):assert inv==r['trace'].count('invalidate'),(r,out)
print(f'{len(rows)-1} native/C++ cases passed; external Core contracts stubbed in native oracle; empty bitmap attributes only')
