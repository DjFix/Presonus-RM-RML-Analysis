import subprocess, sys
symbol='_ZN8Presonus5Mixer18MixerComponentBase14removeDelegateERNS1_8DelegateE'
output=subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True)
assert sum(line.split()[-1]==symbol for line in output.splitlines())==1
print(symbol, 'present exactly once; Linux ELF no decoration; return/layout not established')

solo='_ZN8Presonus5Mixer15OutputComponent10soloUpdateERNS_3Dsp18MultiParamPropertyE'
assert sum(line.split()[-1]==solo for line in output.splitlines())==1
print(solo, 'present exactly once; original return/layout remain unresolved')

pair='_ZNK8Presonus5Mixer18MixerComponentBase22getLinkableChannelPairEPNS0_16ChannelComponentE'
assert sum(line.split()[-1]==pair for line in output.splitlines())==1
print(pair, 'present exactly once; independent type/index query binding')
