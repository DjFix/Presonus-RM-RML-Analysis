import argparse,subprocess
SYMBOLS=[
'_ZN8Presonus12MeterControl12setPeakValueEf',
'_ZNK8Presonus12MeterControl12subtractRectERKN4Core5TRectIiEES5_',
'_ZN8Presonus12MeterControl4drawERKN4Core8Portable9DrawEventE',
'_ZNK8Presonus12MeterControl10getLitRectEf',
'_ZN8Presonus12MeterControl8setValueEf',
'_ZN8Presonus12MeterControl16setPeakParameterEPN4Core8Portable9ParameterE',
'_ZNK8Presonus12MeterControl11getPeakRectEf',
'_ZNK8Presonus12MeterControl17normalizedToPixelEf',
'_ZN8Presonus12MeterControl12paramChangedEPN4Core8Portable9ParameterEi',
'_ZN8Presonus12MeterControl6onIdleEv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--executable',required=True);a=p.parse_args()
 out=subprocess.check_output(['nm','--defined-only','--extern-only',a.executable],text=True)
 names={x.split()[-1] for x in out.splitlines() if x.split()}
 assert '_ZNK8Presonus12MeterControl10isVerticalEv' not in names, 'unclaimed original isVertical export'
 assert all(s in names for s in SYMBOLS),[s for s in SYMBOLS if s not in names]
 print('PASS',len(SYMBOLS),'exact Linux ELF mangled identities; return/layout/ARM ABI unclaimed')
if __name__=='__main__':main()
