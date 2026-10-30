#!/usr/bin/env python3
"""Bounded AVB listener/talker state inspection."""
from metering_inspect import main

NAMES = {
    "Presonus::AVB::AvbListener::AvbListener(unsigned char, unsigned long long, unsigned short, int)",
    "Presonus::AVB::AvbListener::~AvbListener()",
    "Presonus::AVB::AvbListener::update(unsigned char, unsigned char, unsigned char)",
    "Presonus::AVB::AvbTalker::AvbTalker(unsigned char, int)",
    "Presonus::AVB::AvbTalker::~AvbTalker()",
    "Presonus::AVB::AvbTalker::update(unsigned char, unsigned char)",
}

if __name__ == "__main__":
    main(NAMES, "avb-streams/inspection")
