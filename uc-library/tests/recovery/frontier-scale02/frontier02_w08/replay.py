import json,subprocess,sys
from pathlib import Path
fixture=json.loads(Path(sys.argv[2]).read_text())
assert len(fixture['cases'])==12
subprocess.run([sys.argv[1]],check=True)
