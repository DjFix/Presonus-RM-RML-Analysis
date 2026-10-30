#!/usr/bin/env python3
"""Bounded non-Core DICE programmer state/progress inspection."""
from metering_inspect import main

NAMES = {
    "Presonus::DICE::Dice3Programmer::verify()",
    "Presonus::DICE::Dice3Programmer::printProgress(char const*, float, bool)",
    "Presonus::DICE::Dice3Programmer::Dice3Programmer(Presonus::UC::IFirmwareUpdateListener*, unsigned char const*, unsigned int)",
    "Presonus::DICE::SysexReceiver::SysexReceiver()",
    "Presonus::DICE::Dice3Programmer::~Dice3Programmer()",
    "Presonus::DICE::Dice3Manager::setDiceClockProfile(Presonus::DICE::Dice3ClockProfile)",
}

if __name__ == "__main__":
    main(NAMES, "dice-programmer/inspection")
