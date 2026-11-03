"""Compare observed app state; provider semantics are pinned-source smoke checks.
Native inline pointer/layout relation is excluded from portable differential.
"""
import argparse,json,subprocess
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixture',required=True);a=p.parse_args();rows=json.load(open(a.fixture))
for case in rows:
 calls=case['provider_calls'];assert [x['provider'] for x in calls]==['Core::Portable::Component::C2','Core::Portable::AttributeAllocator::getDefault','Core::Portable::Attributes::C1']
 assert calls[0]['r0']==0x1000000 and calls[0]['r1']==0x1002000 and calls[0]['name']==case['name']
 assert calls[2]['r0']==0x1000090 and calls[2]['r1']==0x1003000
 actual=json.loads(subprocess.check_output([a.executable,'c1',('1' if case['controller'] else '0')+':'+case['name']],text=True));expected={k:v for k,v in case['state'].items() if k!='readoutInline'}
 assert actual==expected,(case,actual)
print(f'{len(rows)} C1 app-state/provider-forwarding cases matched; actual CCL name copy/truncation, attrs allocation and child destructor smoke passed; native Core excluded')
