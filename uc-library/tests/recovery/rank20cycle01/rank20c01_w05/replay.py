import argparse, subprocess, sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("--executable",required=True);p.add_argument("--fixture",required=True);args=p.parse_args()
assert Path(args.fixture).resolve()==Path(__file__).with_name("fixtures.json").resolve()
subprocess.run([sys.executable,str(Path(__file__).with_name("oracle.py"))],check=True)
subprocess.run([args.executable],check=True)
