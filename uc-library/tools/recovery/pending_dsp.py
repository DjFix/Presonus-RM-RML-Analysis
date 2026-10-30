import json
from pathlib import Path
root=Path('/home/rs/projects/opencs/ai-line-analysis')
lib=root/'uc-library'
done={r['mangled'] for r in json.loads((lib/'validation/ready-functions.json').read_text())['functions']}
rows=[]
for role in ('server','client'):
    for s in json.loads((lib/f'recovered-all/{role}/symbols.json').read_text()):
        if s['kind']=='STT_FUNC' and isinstance(s['section'],int) and s['size']>0 and s['mangled'].startswith(('_ZN8Presonus3Dsp','_ZNK8Presonus3Dsp')) and s['mangled'] not in done:
            rows.append(dict(role=role,**s))
seen=set()
for s in rows:
    name=s['demangled']
    if s['mangled'] in seen or '~' in name or 'Formatter::' in name or name.split('::')[-1].split('(')[0] == name.split('::')[-2]:
        continue
    seen.add(s['mangled'])
    print(s['role'],hex(s['address']),s['size'],name)
