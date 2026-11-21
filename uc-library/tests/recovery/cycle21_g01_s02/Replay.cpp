#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/mixer/TapeInputComponent.hpp"
#include <iostream>
#include <memory>
#include <string>
#include <vector>

using Presonus::Mixer::ChannelComponent;
using Presonus::Mixer::MixerComponentBase;
using Presonus::Mixer::TapeInputComponent;
namespace {
class ChannelServices : public presonus::mixer::ChannelApplicationServices {
public:
  bool isLinked(const ChannelComponent &) const override { return false; }
  void removeLink(ChannelComponent &) override {}
  ChannelComponent *linkablePair(ChannelComponent &) override {
    return nullptr;
  }
  void faderLocateDirty(ChannelComponent &) override {}
  void coefficientsChanged(ChannelComponent &, bool) override {}
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  presonus::mixer::ChannelState state;
  ChannelServices services;
  std::vector<std::unique_ptr<ChannelComponent>> storage;
  Core::Vector<ChannelComponent *> channels;
  for (const char name : std::string(argv[1])) {
    if (name == 't')
      storage.push_back(std::make_unique<TapeInputComponent>(
          TapeInputComponent::SourcePortConstruction{}, state, services));
    else if (name != 'n')
      storage.push_back(std::make_unique<ChannelComponent>(state, services));
    channels.add(name == 'n' ? nullptr : storage.back().get());
  }
  MixerComponentBase mixer;
  mixer.tapeInputChannels = &channels;
  const auto *selected = mixer.getTapeIn();
  int position = -1;
  if (selected) {
    position = channels.index(const_cast<ChannelComponent *>(selected));
    if (position < 0)
      return 1;
  }
  std::cout << position << '\n';
  return 0;
}
