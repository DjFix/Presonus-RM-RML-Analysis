#!/usr/bin/env python3
"""Inspect original global integer packing helpers used by DICE control."""
from metering_inspect import main

if __name__ == "__main__":
    main({"pack32(unsigned int, unsigned char*)", "unpack32(unsigned char const*)",
          "pack16(unsigned short, unsigned char*)", "unpack16(unsigned char const*)"},
         "dice-codec")
