"""Compare actual canonical provider observation with bound recorded fixture."""
import pathlib, subprocess, sys
p=subprocess.run([sys.argv[1]],text=True,capture_output=True,check=True)
assert p.stdout == pathlib.Path(sys.argv[2]).read_text(), (p.stdout, p.stderr)
print("PASS actual pinned CCL provider observations")
