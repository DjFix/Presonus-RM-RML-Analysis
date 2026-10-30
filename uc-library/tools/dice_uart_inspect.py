#!/usr/bin/env python3
"""Bounded original DICE application UART assembly/dependency inspection."""
from metering_inspect import main

NAMES = {
    "Presonus::DICE::Dice3Uart::assembleSYSEX(unsigned char*, int)",
    "Presonus::DICE::Dice3Uart::registerReceiver(Presonus::DICE::ISysexReceiver*)",
    "Presonus::DICE::Dice3Uart::unRegisterReceiver(Presonus::DICE::ISysexReceiver*)",
    "Presonus::DICE::Dice3Uart::Dice3Uart()",
    "Presonus::DICE::Dice3Uart::post(Presonus::DICE::SysexPacket&)",
    "Presonus::DICE::Dice3Uart::idleRead()",
    "Presonus::DICE::Dice3Uart::onIdle()",
}

if __name__ == "__main__":
    main(NAMES, "dice-uart-candidate/inspection")
