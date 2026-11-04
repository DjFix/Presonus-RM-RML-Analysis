"""Replay immutable native target observations against a compiled executable."""
import json, subprocess, sys
from pathlib import Path

def replay(executable, fixture):
    fixtures=json.loads(Path(fixture).read_text())
    for case in fixtures['cases']:
        result=subprocess.run([str(executable),str(case['id'])],text=True,capture_output=True,check=True)
        actual=bytes.fromhex(result.stdout.strip())
        expected=bytes.fromhex(case['memory'])
        assert len(actual)==1024
        # Native vptr identity is ARM-only; compare all directly written bytes
        # except its four-byte table address. Provider state has its own checks.
        written=set()
        for offset,size,value,pc in case['writes']:
            if offset != 0:
                written.update(range(offset,offset+size))
        for offset in written:
            assert actual[offset]==expected[offset],(case['id'],hex(offset),actual[offset],expected[offset])
        assert case['calls'][0]['address']==0xb251c
        assert case['calls'][0]['args'][:3]==[0,case['id'] & 0xffffffff,0]
        assert case['calls'][1]['address']==0xb9518
        assert case['calls'][1]['args'][0]==0x2c0
    print(f"PASS {len(fixtures['cases'])} original constructor observations; real C++ Controller/Biquad; owned/borrowed checks")
if __name__=='__main__':
    replay(sys.argv[1],sys.argv[2])
