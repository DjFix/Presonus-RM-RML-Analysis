#include "presonus/mixer/RackMixerComponent.hpp"
#include "presonus/mixer/TalkbackInputComponent.hpp"
#include <iostream>
int main() {
  int selection, initial, count, kind;
  unsigned long long source, mode;
  while (std::cin >> selection >> initial >> count >> kind >> source >> mode) {
    Presonus::Mixer::MixerComponentBase base;
    std::uint32_t cascade = 0;
    Presonus::Mixer::RackMixerComponent rack(base, cascade);
    Presonus::Mixer::ChannelComponent ordinary{
        Presonus::Mixer::ChannelComponent::SourcePortConstruction{}};
    Presonus::Mixer::TalkbackInputComponent talkback{
        Presonus::Mixer::ChannelComponent::SourcePortConstruction{}};
    if (count > 0)
      base.inputChannels.add(kind == 2   ? &talkback
                             : kind == 1 ? &ordinary
                                         : nullptr);
    rack.talkbackRoutes.push_back({&talkback,
                                   static_cast<std::uint32_t>(source),
                                   static_cast<std::uint32_t>(mode)});
    unsigned char left = static_cast<unsigned char>(initial), right = 77;
    unsigned int resultMode = 123;
    rack.getTDMRoutes(selection, left, right, resultMode);
    std::cout << static_cast<unsigned>(left) << ' '
              << static_cast<unsigned>(right) << ' ' << resultMode << '\n';
  }
}
