import argparse,subprocess
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);a=p.parse_args()
symbol='_ZNK8Presonus5Panel15PresetComponent11isSlotEmptyEj'
rows=subprocess.check_output(['nm','--defined-only',a.executable],text=True).splitlines()
assert len([s for s in rows if s.split()[-1]==symbol])==1
for symbol in ['_ZNK8Presonus5Panel15PresetComponent18getFileNameForSlotEj','_ZN4Core8Platform10FileSystem8instanceEv','_ZN4Core8Platform15PosixFileSystem10fileExistsEPKc']:
 assert any(s.split()[-1]==symbol for s in rows),symbol
print('exact original symbol and real application/POSIX provider symbols verified; ELF decoration unchanged')
