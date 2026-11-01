#!/usr/bin/env python3
"""Compare explicit C++ executable state/traces with independent ARM fixtures."""
import argparse,datetime,json,subprocess,sys,time
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--executable',required=True);parser.add_argument('--fixtures',required=True);parser.add_argument('--report');args=parser.parse_args()
    fixtures=json.loads(Path(args.fixtures).read_text());counts={};executions=[];start=time.monotonic();start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
    for case in fixtures['cases']:
        argv=[args.executable,case['method'],*[str(x) for x in case['values']],case['name'],case['input']]
        case_start=datetime.datetime.now(datetime.timezone.utc).isoformat();case_clock=time.monotonic()
        result=subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        executions.append({'case':case['id'],'method':case['method'],'start_utc':case_start,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seconds':time.monotonic()-case_clock,'argv':argv,'returncode':result.returncode})
        if result.returncode:raise RuntimeError(f"case {case['id']}: {result.returncode}: {result.stderr}")
        actual=json.loads(result.stdout)
        if actual != case['expected']:
            print(json.dumps({'case':case,'actual':actual},indent=2),file=sys.stderr)
            raise RuntimeError(f"case {case['id']}: native/C++ difference")
        counts[case['method']]=counts.get(case['method'],0)+1
    report={'start_utc':start_utc,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,'executions':executions,'cases':len(fixtures['cases']),'per_method':counts,'seconds':time.monotonic()-start,'executable':args.executable,'fixtures':args.fixtures,'domain':'Original ARM application instructions, explicit external dependency hooks; portable C++ actual pinned CCL providers. Compare item list, offsets, all slot originals/enabled flags, text, navigation, event reset, selection and app call order.'}
    if args.report:Path(args.report).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='executions'}))

if __name__=='__main__':main()
