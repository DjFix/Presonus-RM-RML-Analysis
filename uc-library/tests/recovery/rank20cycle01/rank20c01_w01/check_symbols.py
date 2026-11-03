import pathlib,subprocess,sys
text=subprocess.check_output(['nm','--defined-only',sys.argv[1]],text=True)
names={line.split()[-1] for line in text.splitlines() if line.split()}
for symbol in ['_ZN8Presonus5Mixer15OutputComponent12paramChangedEPN4Core8Portable9ParameterEi','_ZN8Presonus5Mixer15OutputComponent22setSectionCoeffChangedEi']:
 assert symbol in names,symbol
 print(symbol)
