from pathlib import Path
import json
R=Path.cwd();A=Path(__file__).resolve().parent;E=R/'evidence/recovery/2026-11-05/rolling200-02/stage03-w04'
cases=json.loads((E/'native-attrs/cases.json').read_text());idle=json.loads((E/'native-idle/cases.json').read_text());s='#pragma once\n#include <cstdint>\nstruct AttributeCase {const char *text; int base,parsed,count; const std::uint32_t *bits;};\n'
accepted=[x for x in cases if x['failed_growth']==0]
for i,x in enumerate(accepted):s+='static const std::uint32_t b%d[]={%s};\n'%(i,','.join(str(v)+'U' for v in x['threshold_bits']) or '0')
s+='static const AttributeCase attributeCases[]={\n'
for i,x in enumerate(accepted):s+='{%s,%d,%d,%d,b%d},\n'%(json.dumps(x['text']) if x['text'] is not None else 'nullptr',x['base'],x['parsed'],len(x['threshold_bits']),i)
s+='};\nstruct IdleCase {bool elapsed,dirty,after,invalidate;};\nstatic const IdleCase idleCases[]={\n'
for x in idle:s+='{%d,%d,%d,%d},\n'%(x['elapsed'],x['dirty'],x['dirty_after'],any(c['call']=='View::invalidate' for c in x['calls']))
s+='};\n';(A/'fixtures.hpp').write_text(s)
