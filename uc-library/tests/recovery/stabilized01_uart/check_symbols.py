import argparse,json,subprocess
from pathlib import Path
import oracle
p=argparse.ArgumentParser();p.add_argument('--driver',required=True);a=p.parse_args()
lines=subprocess.check_output(['nm','--defined-only',a.driver],text=True).splitlines();symbols={line.split()[-1]:line.split()[-2] for line in lines if len(line.split())>=3}
fixture=json.loads(Path(__file__).with_name('fixtures.json').read_text());fresh=oracle.ranges();assert fresh==fixture['ranges'];assert oracle.data_ranges()==fixture['data_ranges']
for row in fresh:
 name=row['original']['mangled'];assert name in symbols,name
 if name.startswith('_ZL'):assert symbols[name]=='t', (name,symbols[name])
print(json.dumps(dict(format='Linux ELF64; no leading underscore decoration',exact_original_symbols=[r['original']['mangled'] for r in fresh],independent_original_section_range_checks=len(fresh),limitations='Host symbol identity only; no original ordinary return/layout/ARM ABI verification'),indent=2))
