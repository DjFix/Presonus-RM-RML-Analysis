#!/usr/bin/env python3
"""Inspect DICE packet/layout and call boundaries; never inspect Core bodies."""
from metering_inspect import main

if __name__ == "__main__":
    main({"Presonus::DICE::SysexPacket::SysexPacket(unsigned char const*, unsigned char)",
          "Presonus::DICE::SysexReceiver::receive(Presonus::DICE::SysexPacket const&)",
          "Presonus::DICE::Dice3Subsystem::receive(Presonus::DICE::SysexPacket const&)",
          "Presonus::DICE::Dice3Subsystem::uiSetCmd(int, int)",
          "Presonus::DICE::Dice3Subsystem::setRate(Presonus::DICE::Dice3SampleRate)",
          "Presonus::DICE::Dice3Subsystem::setClockSource(Presonus::DICE::Dice3ClockSource)",
          "Presonus::DICE::Dice3Subsystem::setRoute(Presonus::DICE::Dice3AudioSinkDevice, Presonus::DICE::Dice3AudioSink, Presonus::DICE::Dice3AudioSourceDevice, Presonus::DICE::Dice3AudioSource)"},
         "dice-routing/packet-layout")
