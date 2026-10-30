#!/usr/bin/env python3
"""Original DICE app response waits only; never inspect Core bodies."""
from metering_inspect import main

NAMES = {
    "Presonus::DICE::SysexReceiver::waitAck(long long)",
    "Presonus::DICE::SysexReceiver::waitResponseSet(unsigned int&, long long)",
    "Presonus::DICE::SysexReceiver::post(Presonus::DICE::SysexPacket&)",
    "Presonus::DICE::SysexReceiver::SysexReceiver()",
    "Presonus::NOAA::SysexReceiver::waitAck(long long)",
    "Presonus::NOAA::SysexReceiver::waitResponseSet(unsigned int&, long long)",
}

if __name__ == "__main__":
    main(NAMES, "dice-response-candidate/inspection")
