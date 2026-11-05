"""Replay approved observations against a supplied canonical executable."""
import json
import subprocess
import sys
from pathlib import Path


def expected(case):
    lines=[f"R {case['result']}",f"P {case['packet']}",f"F {case['cancel_final']}"]
    for event in case['trace']:
        kind=event[0]
        if kind in ['format','clock','divide']: continue
        if kind in ['command','ack']:
            lines.append(f"{'C' if kind=='command' else 'A'} {event[1]} {event[2]}")
        elif kind in ['char','address']:
            lines.append(f"{'B' if kind=='char' else 'S'} {event[1]}")
        elif kind=='packet': lines.append('T '+event[1])
        elif kind=='progress': lines.append('G '+event[1].encode().hex()+' '+str(event[2]))
        elif kind=='debug': lines.append('D '+event[1].encode().hex())
        elif kind=='overwrite': lines.append('O 0')
        elif kind=='cancel': lines.append('X 1')
        else: raise ValueError(kind)
    if 'epoch_memory' in case: lines.append('E '+str(int.from_bytes(bytes.fromhex(case['epoch_memory']),'little')))
    return lines


def main():
    exe,fixture=sys.argv[1:]
    cases=json.loads(Path(fixture).read_text())['cases']
    for index,case in enumerate(cases):
        args=[exe,case['method'],str(case['length']),str(case['cancel']),str(case['fail']),str(case.get('cancel_after',-1)),str(int(case.get('overwrite',False))),'epoch' if 'epoch_memory' in case else 'bounded']
        actual=subprocess.run(args,check=True,text=True,capture_output=True,timeout=10).stdout.splitlines()
        want=expected(case)
        if actual!=want:
            print(json.dumps({'index':index,'case':case,'actual':actual,'expected':want},indent=2));return 1
    print(json.dumps({'cases':len(cases),'status':'passed','domain':'four methods; memory and scripted high-level provider boundaries; no hardware/ABI verification'}))
    return 0

if __name__=='__main__': sys.exit(main())
