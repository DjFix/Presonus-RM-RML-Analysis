#!/usr/bin/env python3
"""Inspect original PreSonus mixer-state methods; do not recover dependencies."""
from metering_inspect import main

NAMES = {
"Presonus::MixerClientComponentBase::isStereoChannelType(Presonus::ChannelType) const",
"Presonus::MixerClientComponentBase::getNumGeqs() const",
"Presonus::MixerClientComponentBase::getNumMixGeqs() const",
"Presonus::MixerClientComponentBase::getCascadeState() const",
"Presonus::MixerClientComponentBase::getSlaveMixer() const",
"Presonus::MixerClientComponentBase::getMasterMixer() const",
"Presonus::MixerClientComponent::isAggregateMeteringChannelType(Presonus::ChannelType) const",
}

if __name__ == "__main__":
    main(NAMES, "mixer-state")
