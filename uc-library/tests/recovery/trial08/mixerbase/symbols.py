#!/usr/bin/env python3
import subprocess
symbols = subprocess.check_output(['nm', '--defined-only', 'temp/recovery-work/graph-live-trial-08/mixerbase-worker/replay'], text=True)
for tail in ['K8Presonus5Mixer18MixerComponentBase18getSelectedChannelEv', 'K8Presonus5Mixer18MixerComponentBase10numClientsEv', 'K8Presonus5Mixer18MixerComponentBase14numHWMicLineInEv', 'K8Presonus5Mixer18MixerComponentBase14getCompanyNameEv', 'K8Presonus5Mixer18MixerComponentBase19getSpectrumSendSlotEv', '8Presonus5Mixer18MixerComponentBase15setTryingToQuitEv']:
    name = '_ZN' + tail
    assert any(line.split()[-1] == name for line in symbols.splitlines()), name
    print(name)
print('Linux ELF symbol identity only; declarations/layout/ARM ABI unresolved')
