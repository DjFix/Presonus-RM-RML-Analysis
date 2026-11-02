import argparse,subprocess
p=argparse.ArgumentParser();p.add_argument('--object',required=True);a=p.parse_args()
out=subprocess.check_output(['/usr/bin/nm','--defined-only',a.object],text=True)
names={line.split()[-1] for line in out.splitlines()}
for name in ['_ZN8Presonus16MainLCDComponent11popBackPageEv','_ZN8Presonus16MainLCDComponent12pushBackPageEPNS_13PageComponentE']:assert name in names,name
print('Two exact original mangled identities present; native Linux ELF has no Mach-O decoration')
