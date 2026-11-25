"""Compare the production C++ replay to observations from the ARM oracle."""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()

    lines = []
    expected = []
    for sequence in json.loads(args.fixture.read_text())["sequences"]:
        steps = sequence["steps"]
        lines.append(
            f"{sequence['sentinel']} {sequence['initial_mode']} "
            f"{sequence['initial_requested']} {len(steps)}"
        )
        lines.append(" ".join(str(step["input_mode"]) for step in steps))
        for step in steps:
            if not step["other_bytes_unchanged"] or step["calls"]:
                raise ValueError("Unexpected native receiver or call side effects")
            if step["receiver_writes"] != [[0x54, 1, 1], [0x50, 4, step["input_mode"]]]:
                raise ValueError(f"Unexpected native write trace: {step['receiver_writes']}")
            expected.append(
                f"{step['observed_mode']} {step['observed_requested']} "
                f"{step['observed_sentinel']} 1"
            )
    actual = subprocess.run(
        [str(args.binary.resolve())], input="\n".join(lines) + "\n",
        text=True, check=True, capture_output=True,
    ).stdout.splitlines()
    if actual != expected:
        raise ValueError(f"Portable result differs from ARM observations: {actual!r} != {expected!r}")
    print(f"Portable comparisons: {len(expected)}")


if __name__ == "__main__":
    main()
