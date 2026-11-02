"""Supported native-index build entrypoint, serialized with context builders.

Both this compatibility coordinator and the native_graph direct CLI acquire
the same exclusive lock. Historical reports retain their original producer hashes.
"""
import argparse
import pathlib
from context_writer_lock import exclusive_writer
from native_graph import ROOT, build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--manifest", action="append", type=pathlib.Path)
    args = parser.parse_args()
    with exclusive_writer(ROOT):
        build(ROOT / args.out, args.manifest)


if __name__ == "__main__":
    main()
