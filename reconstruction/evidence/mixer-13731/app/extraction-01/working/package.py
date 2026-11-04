"""Create a project-scoped evidence package from verified extraction output."""
import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[2]
scratch = root/'temp/embedded-mcu'
out = root/'evidence/recovery/2026-10-27/xmen-stm32'
out.mkdir(parents=True, exist_ok=True)
records = json.loads((scratch/'manifest.json').read_text())
for rec in records:
    for obj in rec['objects']:
        src = root/obj['output']
        dest = out/'images'/src.parent.name/src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        obj['output'] = str(dest.relative_to(out))
for script in ('extract.py', 'package.py', 'linux_verify.py', 'extraction.log'):
    if (scratch/script).exists():
        shutil.copyfile(scratch/script, out/script)
(out/'manifest.json').write_text(json.dumps(records, indent=2)+'\n')
inputs = out/'inputs'
inputs.mkdir(exist_ok=True)
shutil.copyfile(root/'Cutter Analysis/mixer', inputs/'mixer-13731.elf')
shutil.copyfile(root/'Cutter Analysis/surface', inputs/'surface-13840.elf')
print(out)
print('Inputs:', len(records), 'objects:', sum(len(r['objects']) for r in records),
      'STM32 image instances:', sum(bool(o['analysis']['stm32_header']) for r in records for o in r['objects']))
