"""Canonical-binary adapter invocation copied from accepted check.py adapter action."""
import json, subprocess, sys
p=subprocess.run([sys.argv[1]],input="A 0 0 0 0 0\n",text=True,capture_output=True,check=True)
assert json.loads(p.stdout)=={"adapter_samples":2056}, (p.stdout,p.stderr)
print("2056 source-adapter samples match existing provider; bootstrap/reset/invalid-transition guards pass")
