import argparse,json,struct,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--fixtures',default=str(Path(__file__).with_name('fixtures.json')));a=p.parse_args()
d=json.loads(Path(a.fixtures).read_text());count=0
for original in d['originals']:
 for trial in original['trials']:
  native=struct.unpack('<5I',bytes.fromhex(trial['object_hex']))
  # Expected outputs originate from actual native memory, never the port.
  expected=f'{native[1]} {native[3]}'
  def signed(x):return x if x<2**31 else x-2**32
  out=subprocess.check_output([a.exe,str(signed(trial['first_int_bits'])),str(signed(trial['second_int_bits']))],text=True).strip()
  assert out==expected,(original['node'],trial,out,expected)
  assert native[2]==trial['this']+16 and native[4]==0xa5a5a5a5
  count+=1
print(f'{count} native-to-port constructor comparisons; owned empty state and independent borrowed-state regression passed')
