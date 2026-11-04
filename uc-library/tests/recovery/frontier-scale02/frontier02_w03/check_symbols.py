import subprocess,sys
symbols=subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True)
for symbol in ['_ZN8Presonus3Dsp18SLReverbControllerC1Ei','_ZN8Presonus3Dsp10ControllerC2EiPKNS0_19ParamDescriptorListE','_ZN3DSP10BiquadCalcIdLb0EEC1Ev']:
    assert any(line.split()[-1]==symbol for line in symbols.splitlines()),symbol
print('PASS exact target C1 and actual provider constructor symbols')
for line in symbols.splitlines():
    if 'SLReverbControllerC1Ei' in line or 'ControllerC2EiPKNS0_19ParamDescriptorListE' in line or 'BiquadCalcIdLb0EEC1Ev' in line:
        print(line)
