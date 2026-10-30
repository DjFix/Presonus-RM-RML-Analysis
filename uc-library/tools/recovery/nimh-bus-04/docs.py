from pathlib import Path
import hashlib,json,urllib.request
from pypdf import PdfReader
OUT=Path('/home/rs/projects/opencs/ai-line-analysis/uc-library/validation/nimh-bus-04/operator-inputs/docs');OUT.mkdir(exist_ok=True)
sources={'UG381':'https://docs.amd.com/api/khub/documents/gH5gMPLNAbJLLp3kVnnO5w/content',
         'UG383':'https://docs.amd.com/api/khub/documents/Xs~b~O94R6gZSgSD34Yh5Q/content'}
records=[]
for name,url in sources.items():
    p=OUT/(name+'.pdf')
    if not p.exists():
        with urllib.request.urlopen(url,timeout=45) as f:data=f.read()
        assert data.startswith(b'%PDF');p.write_bytes(data)
    pages=[dict(page=i+1,text=p.extract_text() or '') for i,p in enumerate(PdfReader(p).pages)]
    (OUT/(name+'.pages.json')).write_text(json.dumps(pages,indent=2)+'\n')
    records.append(dict(name=name,url=url,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),pages=len(pages)))
    print(name,len(pages),'pages')
(OUT/'manifest.json').write_text(json.dumps(records,indent=2)+'\n')
