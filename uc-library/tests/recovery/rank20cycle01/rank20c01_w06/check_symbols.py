import subprocess,sys
symbols=subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True)
for s in ['_ZN8Presonus11GridPainter18setGridOrientationENS0_4AxisENS0_16LabelOrientationEPKc','_ZNK8Presonus12MappingTable20getHardwareParameterEPKc','_ZN8Presonus5Panel14PanelComponent8runTestsEiiPPc']:
 assert any(x.split()[-1]==s for x in symbols.splitlines() if x.split()),s
 print(s)
