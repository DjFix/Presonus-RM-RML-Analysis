#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/mixer/MixerComponentBaseDelegate.hpp"
#include <iostream>

using namespace Presonus::Mixer;

struct DefaultObserver : MixerComponentBase::Delegate {
  unsigned marker = 0x12345678;
  void clientsChanged() override {}
};

struct RecordingObserver : DefaultObserver {
  unsigned count = 0;
  const ChannelComponent *last = nullptr;
  void faderLocateDirty(ChannelComponent *channel) override {
    ++count;
    last = channel;
  }
};

int main() {
  ChannelComponent first(ChannelComponent::SourcePortConstruction{});
  ChannelComponent second(ChannelComponent::SourcePortConstruction{});
  ChannelComponent *const channels[] = {nullptr, &first, &second};
  unsigned selector = 0;
  while (std::cin >> selector) {
    if (selector >= std::size(channels))
      return 1;
    DefaultObserver fallback;
    RecordingObserver concrete;
    MixerComponentBase mixer;
    mixer.addDelegate(fallback);
    mixer.addDelegate(concrete);
    mixer.faderLocateDirty(channels[selector]);
    std::cout << fallback.marker << ' ' << concrete.count << ' '
              << (concrete.last == channels[selector]) << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
