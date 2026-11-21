#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/mixer/MixerComponentBaseDelegate.hpp"
#include <iostream>
#include <string>

using Presonus::Mixer::ChannelComponent;
using Presonus::Mixer::MixerComponentBase;

namespace {
class Observer : public MixerComponentBase::Delegate {
public:
  explicit Observer(char name) : name(name) {}
  void clientsChanged() override {}
  void notifyStoring(bool) override {}
  void faderLocateDirty(ChannelComponent *channel) override {
    if (name == 'c')
      return;
    std::cout << name << ':' << (channel ? 'a' : 'z') << '\n';
  }

private:
  char name;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  MixerComponentBase mixer;
  ChannelComponent channel(ChannelComponent::SourcePortConstruction{});
  Observer first('a'), second('b'), noEffect('c');
  const std::string sequence(argv[1]);
  for (const char name : sequence)
    mixer.addDelegate(
        name == 'a'   ? static_cast<MixerComponentBase::Delegate &>(first)
        : name == 'b' ? static_cast<MixerComponentBase::Delegate &>(second)
                      : static_cast<MixerComponentBase::Delegate &>(noEffect));
  mixer.faderLocateDirty(argv[2][0] == 'a' ? &channel : nullptr);
  return mixer.delegates.count() == static_cast<int>(sequence.size()) ? 0 : 1;
}
