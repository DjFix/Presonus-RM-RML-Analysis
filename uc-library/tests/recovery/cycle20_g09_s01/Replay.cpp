#include "presonus/mixer/RackMixerComponent.hpp"
#include <cstdint>
#include <iostream>
#include <vector>

using Presonus::Mixer::MixerComponentBase;
using Presonus::Mixer::RackMixerComponent;

int main() {
  MixerComponentBase base;
  Core::Vector<Presonus::Mixer::ChannelComponent *> channels;
  std::uint32_t cascadeState = 0;
  RackMixerComponent rack(base, cascadeState);
  const RackMixerComponent &capability = rack;

  for (const std::uint32_t pattern :
       {0u, 0xaaaaaaaau, 0xffffffffu, 0x12345678u}) {
    cascadeState = pattern;
    base.selectedChannel = pattern;
    base.cascadeStatePending = pattern != 0;
    base.sceneChannels = pattern ? &channels : nullptr;
    rack.auxiliaryRouteCount = static_cast<int>(pattern & 0xffu);
    rack.talkbackRoutes =
        pattern ? std::vector<RackMixerComponent::TalkbackRouteState>{{nullptr,
                                                                       pattern,
                                                                       pattern ^
                                                                           1u}}
                : std::vector<RackMixerComponent::TalkbackRouteState>{};
    rack.danteSourceChannels = base.sceneChannels;
    const auto *routes = rack.talkbackRoutes.data();
    const bool result = capability.supportSubgroupMode();
    const bool unchanged =
        cascadeState == pattern && base.selectedChannel == pattern &&
        base.cascadeStatePending == (pattern != 0) &&
        base.sceneChannels == (pattern ? &channels : nullptr) &&
        channels.count() == 0 &&
        rack.auxiliaryRouteCount == static_cast<int>(pattern & 0xffu) &&
        rack.danteSourceChannels == base.sceneChannels &&
        rack.talkbackRoutes.data() == routes &&
        rack.talkbackRoutes.size() == (pattern ? 1u : 0u) &&
        (!pattern || (routes->identity == nullptr && routes->route == pattern &&
                      routes->mode == (pattern ^ 1u)));
    std::cout << pattern << ' ' << result << ' ' << unchanged << '\n';
  }
}
