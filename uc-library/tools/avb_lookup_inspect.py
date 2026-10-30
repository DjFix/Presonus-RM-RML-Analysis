#!/usr/bin/env python3
"""Bounded application-owned AVB lookup/caller inspection, no Core bodies."""
from metering_inspect import main

NAMES = {
    "Presonus::AVB::AvbManagerBase::findListener(unsigned char)",
    "Presonus::AVB::AvbManagerBase::findTalker(unsigned char)",
    "Presonus::AVB::AvbManagerBase::lookupNextTalkerIndex()",
    "Presonus::AVB::AvbManagerBase::AvbManagerBase(unsigned long long, Presonus::AVB::AvbNoticeListener*, unsigned char, unsigned char)",
    "Presonus::AVB::AvbManagerBase::addTalker(unsigned char)",
    "Presonus::AVB::AvbManagerBase::resizeListener(unsigned char, unsigned char)",
    "Presonus::AVB::AvbManagerBase::resizeTalker(unsigned char, unsigned char)",
}

if __name__ == "__main__":
    main(NAMES, "avb-lookup-candidate/inspection")
