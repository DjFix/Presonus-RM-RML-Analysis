"""Read-only fixture verification and exact compiled symbol identity checks."""
import argparse,pathlib,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('mode',choices=['symbols','oracle']);a=p.parse_args()
if a.mode=='symbols':
 text=subprocess.check_output(['nm','--defined-only','temp/recovery-work/graph-live-trial-08/dspcomponent-worker/source.o'],text=True)
 tokens={line.split()[-1] for line in text.splitlines() if line.split()}
 target='_ZN8Presonus12DspComponentC1EPKcPNS_3Dsp11IControllerE'
 if target not in tokens:raise SystemExit('Exact C1 compiled symbol absent')
 print('Exact nm symbol token matches selected original C1; C2 not credited')
else:
 fresh='temp/recovery-work/graph-live-trial-08/dspcomponent-worker/native-c1-replayed.json'
 subprocess.run([sys.executable,'uc-library/tests/recovery/trial08/dspcomponent/oracle_c1.py','--out',fresh],check=True)
 bound=pathlib.Path('uc-library/tests/recovery/trial08/dspcomponent/native-c1.json')
 if pathlib.Path(fresh).read_bytes()!=bound.read_bytes():raise SystemExit('Fresh original observation differs from bound fixture; fixture preserved')
 print('Fresh original observation bytes equal bound native C1 fixture')
