#!/usr/bin/env python3
"""Bounded non-Core AVB receive/packing inspection."""
from metering_inspect import main

NAMES = {
    "Presonus::AVB::AvbManagerBase::accepts(Presonus::DICE::SysexPacket const&)",
    "Presonus::AVB::AvbManagerBase::unpackAvbSpiMsg(unsigned char*, unsigned char const*, int)",
    "Presonus::AVB::AvbManagerBase::reverseEndian(unsigned long long)",
    "Presonus::AVB::AvbManagerBase::char2Nibble(unsigned char const*, unsigned char*, int)",
    "Presonus::AVB::AvbManagerBase::nibble2Char(unsigned char const*, unsigned char*, int)",
}

if __name__ == "__main__":
    main(NAMES, "avb-protocol/inspection")
