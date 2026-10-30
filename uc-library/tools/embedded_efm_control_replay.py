"""Lossless retained control records; no oracle or hardware execution."""
import argparse,gzip,hashlib,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--executable',required=True,type=Path)
p.add_argument('--fixtures',required=True,type=Path)
p.add_argument('--expected',required=True,type=Path)
a=p.parse_args()
assert hashlib.sha256(a.fixtures.read_bytes()).hexdigest()=='ce63cb4bb69990e44a3a4fbe4e77c24356487617c052debb3ccada1df6dc172c'
assert hashlib.sha256(a.expected.read_bytes()).hexdigest()=='a3c4e7113eb0dc8be16efa0284e5f22827bf5a4ee8bba1afe25a62f9bd167459'
stdin=gzip.decompress(a.fixtures.read_bytes());expected=gzip.decompress(a.expected.read_bytes())
assert len(stdin)==34786*4101 and len(expected)==34786*4122
r=subprocess.run([str(a.executable)],input=stdin,capture_output=True)
assert r.returncode==0,r.stderr.decode(errors='replace')
assert r.stdout==expected,'Retained control RAM/event records differ'
print('PASS34786 retained partial-control records; hardware/helper bodies not executed')
