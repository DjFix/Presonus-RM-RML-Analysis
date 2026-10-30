"""Extract local architectural references with PDF-page and hash provenance."""
from pathlib import Path
import hashlib,json,re,sys
from pypdf import PdfReader
root=Path(sys.argv[1]).resolve()
out=root/'evidence/recovery/2026-10-27/nimh-command-map/docs'
out.mkdir(parents=True,exist_ok=True)
paths=[root/'doc/DICE_III_User_Guide'/n for n in (
    'TCD30xx - Firmware Development.pdf','DICE_III_User_Guide_MemoryMap.pdf',
    'DICE_III_User_Guide_Mixer.pdf','DICE_III_User_Guide_Router.pdf',
    'DICE_III_User_Guide_ClockController.pdf','DICE_III_User_Guide_SPI.pdf',
    'Digital IO and Networking Engine Hardware Guide.pdf')]
paths.append(root/'doc/AVB Card/AVB-Proxy.pdf')
index=[]
for p in paths:
    reader=PdfReader(p)
    pages=[page.extract_text() or '' for page in reader.pages]
    target=p.stem+'.txt'
    (out/target).write_text('\n'.join(f'\n=== PDF PAGE {i+1} ===\n{s}' for i,s in enumerate(pages)))
    hits=[]
    for i,s in enumerate(pages):
        if re.search(r'eCos|DAL|abstraction|application|routing|clock source|gain|32.?bit|SPI slave|SPI master|0xC400|firmware architecture',s,re.I):
            hits.append(i+1)
    index.append(dict(path=str(p.relative_to(root)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                      pages=len(pages),text=target,architecture_keyword_pages=hits))
    print(p.name,'PDF pages',len(pages),'relevant pages',hits)
(out/'sources.json').write_text(json.dumps(index,indent=2)+'\n')
