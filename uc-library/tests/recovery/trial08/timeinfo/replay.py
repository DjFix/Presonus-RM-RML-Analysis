"""Compare explicit compiled executable observations with original ARM fixtures."""
import argparse,json,subprocess
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
fixtures=json.load(open(a.fixtures)); actual=subprocess.check_output([a.executable],text=True).splitlines();assert len(actual)==len(fixtures)==20
for row,line in zip(fixtures,actual):
 method,flag,musical,locating,millis,updates=map(int,line.split()); state=bytes.fromhex(row['state_after']);assert flag==row['flag'];assert (musical,locating,millis)==tuple(state[i] for i in (0x134,0x135,0x136))
 assert row['outcome']=='bounded-execution',row
 if method==0: assert updates==len(row['external_boundaries'])==2
 elif method==9: assert updates==bytes.fromhex(row['argument_after'])[0x14]
 else: assert updates==0
print('20 original ARM / C++ cases matched: explicit state bytes, context boundary counts, appended event counts; narrow null/empty/unchanged branches only')
