import subprocess,pathlib,json
root=pathlib.Path(__file__).resolve().parents[5]
obj=root/'temp/recovery-work/graph-live-trial-08/timeinfo-worker/timeinfo.o'
symbols=subprocess.check_output(['nm','--defined-only',str(obj)],text=True)
for n in range(1,11):
 p=root/f'temp/recovery-work/graph-live-trial-08/batch03/packets/trial08_timeinfo_{n}/context.json'
 # Original identities are independently bound in per-packet HANDOFFs.
 import re
 text=(p.parent/'ELF_CONTEXT.md').read_text(); name=re.search(r'original `([^`]+)`',text)[1];assert name in symbols,name
print('10 exact original ELF mangled names present')
