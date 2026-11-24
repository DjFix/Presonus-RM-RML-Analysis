"""Verify native fixture equality and run the portable dispatch replay."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

mode = sys.argv[1]
if mode == "symbols":
    lines = subprocess.check_output(["nm", "--defined-only", sys.argv[2]], text=True)
    names = {line.split()[-1] for line in lines.splitlines() if line.strip()}
    for variant in (1, 2):
        symbol = f"_ZN8Presonus17BackgroundPainterC{variant}Ev"
        if symbol not in names:
            raise SystemExit(f"Missing {symbol}")
        print(symbol)
elif mode == "native":
    producer = Path(__file__).with_name("native.py")
    spec = importlib.util.spec_from_file_location("native", producer)
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    fixture = json.loads(Path(sys.argv[4]).read_text())
    observation = module.observe(Path(sys.argv[2]), Path(sys.argv[3]))
    if observation != fixture:
        raise SystemExit("Native replay diverged from fixture")
    print(f"{len(observation['cases'])} native cases for {observation['original']['mangled']}")
elif mode == "portable":
    subprocess.run([sys.argv[2]], check=True)
else:
    raise SystemExit(f"Unknown mode {mode}")
