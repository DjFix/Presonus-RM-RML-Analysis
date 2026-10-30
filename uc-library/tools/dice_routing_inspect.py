#!/usr/bin/env python3
"""Inspect original DICE manager routing tuple construction only."""
from metering_inspect import main

if __name__ == "__main__":
    main({"Presonus::DICE::Dice3Manager::setDiceRoutingProfile(Presonus::DICE::Dice3RoutingProfile)",
          "Presonus::DICE::Dice3Manager::setDiceMonitorSource(int, int, int)"}, "dice-routing")
