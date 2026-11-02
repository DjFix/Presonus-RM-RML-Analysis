import argparse
import subprocess
p=argparse.ArgumentParser();p.add_argument('--binary',required=True);a=p.parse_args()
names={line.split()[-1] for line in subprocess.check_output(['nm','--defined-only',a.binary],text=True).splitlines() if line.split()}
expected={'_ZN8Presonus3Dsp11getAudioHALEv','getSharedLink','getDSPState','isLinkReady','shutdownDSP'}
assert expected<=names, expected-names
print('PASS exact original ELF symbol identities (Linux ELF, no decoration)')
