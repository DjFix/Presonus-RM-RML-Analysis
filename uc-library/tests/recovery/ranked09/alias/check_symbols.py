import subprocess
import sys

symbols = subprocess.check_output(['/usr/bin/nm', '--defined-only', sys.argv[1]], text=True)
for variant in ('C1', 'C2'):
    name = f'_ZN8Presonus14AliasComponent{variant}EPKc'
    assert any(line.split()[-1] == name for line in symbols.splitlines()), name
print(symbols)
