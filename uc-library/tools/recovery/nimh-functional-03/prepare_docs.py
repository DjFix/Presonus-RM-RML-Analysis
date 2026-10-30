"""Hash-bound local manuals; no firmware execution."""
import hashlib
import json
import urllib.request
from pathlib import Path
from pypdf import PdfReader

ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
OUT = Path('/home/rs/projects/opencs/ai-line-analysis/uc-library/validation/nimh-functional-03/operator-inputs/inputs/docs')
OUT.mkdir(parents=True, exist_ok=True)
downloads = {
    'UG384.pdf': 'https://docs.amd.com/api/khub/documents/rwv96epRtR2oqLtHAG1jyQ/content',
    'RM0008.pdf': 'https://www.st.com/resource/en/reference_manual/cd00171190-stm32f101xx-stm32f102xx-stm32f103xx-stm32f105xx-and-stm32f107xx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf',
}
records = []
paths = []
for name, url in downloads.items():
    p = OUT / name
    if not p.exists():
        try:
            with urllib.request.urlopen(url, timeout=45) as r:
                data = r.read()
            assert data.startswith(b'%PDF')
            p.write_bytes(data)
        except Exception as e:
            print(name, type(e).__name__, str(e)[:120])
            continue
    paths.append((p, url))
for name in ['TCD3040-CG.pdf'] + ['DICE_III_User_Guide_' + n + '.pdf' for n in
        ['ETH','Router','AIO','InS','ClockController','MemoryMap','SysCtrl','JetPLL','1394LLC']]:
    paths.append((ROOT / 'doc/DICE_III_User_Guide' / name, None))
for p, url in paths:
    reader = PdfReader(p)
    pages = [{'page': i+1, 'text': page.extract_text() or ''} for i, page in enumerate(reader.pages)]
    dst = OUT / (p.stem + '.pages.json')
    dst.write_text(json.dumps(pages, indent=2))
    records.append({'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                    'url': url, 'pages': len(pages), 'text': dst.name})
    print(p.name, len(pages), 'pages')
(OUT / 'manifest.json').write_text(json.dumps(records, indent=2)+'\n')
