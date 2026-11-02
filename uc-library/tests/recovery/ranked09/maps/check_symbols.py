import subprocess,sys
symbols=subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True)
for symbol in ['_ZNK8Presonus11DAWTimeInfo16TimeSignatureMap8findItemEd','_ZNK8Presonus11DAWTimeInfo8TempoMap8findItemEd']:
 assert any(line.split()[-1]==symbol for line in symbols.splitlines()),symbol
print('two exact original mangled names present; original declarations and ARM ABI remain unresolved')
