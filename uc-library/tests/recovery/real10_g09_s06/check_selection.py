"""Fresh phase08 seal; unchanged doLink checker plus bounded actual Delegate selection observation."""
import argparse
import hashlib
import json
import subprocess
import sys
import uuid
from pathlib import Path

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser()
    for name in ('exe','object','integration','out'):
        p.add_argument('--'+name,required=True)
    a=p.parse_args()
    out=Path(a.out)
    if out.exists():
        raise FileExistsError('Existing proof is immutable; supply NEW --out')
    here=Path(__file__).resolve().parent
    fixture=here.parent/'real10_g09_s04'/'fixtures.json'
    row=next(r for r in json.loads(fixture.read_text())['cases'] if r['input']==[0,0,0,0,0,0,2])
    assert row['calls']==[['debug'],['set',1,1065353216,0],['changed',1],['observer',0],['observer',1]]
    assert row['output']=={'selected':1,'cascadeSelected':0,'cascadeDirty':0}
    outputs=[]
    for mode in ('--selection','--selection-provider'):
        r=subprocess.run([str(Path(a.exe).resolve()),mode],input='0 0 0 2 0 0\n',text=True,capture_output=True,check=True)
        lines=[l for l in r.stdout.splitlines() if l.startswith('SELECT_RESULT ')]
        assert len(lines)==1
        outputs.append(lines[0])
    assert outputs[0]==outputs[1]=='SELECT_RESULT S:1:1065353216:0:0;S:1:1065353216:0:0;O:0:0;O:1:0;|0 0|1',outputs
    out.parent.mkdir(parents=True,exist_ok=True)
    base=out.parent/(out.stem+'-base-'+uuid.uuid4().hex+'.json')
    subprocess.run([sys.executable,str(here/'check.py'),'--exe',a.exe,'--object',a.object,'--integration',a.integration,'--out',str(base)],check=True)
    proof=json.loads(base.read_text())
    proof['preserved_base_proof']={'path':str(base),'sha256':sha(base)}
    proof['selection_observation']={'original_mangled':'_ZN8Presonus5Mixer14MixerComponent8doSelectEPNS0_16ChannelComponentE','fixture_sha256':sha(fixture),'native_input':row['input'],'native_calls':row['calls'],'actual_and_independent_provider':outputs,'scope':'One empty-channel/no-partner/non-slave/unguarded/zero-flags/two actual MixerComponentBase::Delegate case; actual Core parameter notifications; no additional target credit.'}
    proof['checker_sha256']=sha(__file__)
    with out.open('x') as f:
        json.dump(proof,f,indent=2)
        f.write('\n')
    print('actual Delegate selection/provider observation passed')
if __name__=='__main__':
    main()
