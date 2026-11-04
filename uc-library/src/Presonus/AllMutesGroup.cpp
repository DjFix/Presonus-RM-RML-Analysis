#include "presonus/AllMutesGroup.hpp"
#include <stdexcept>

namespace Presonus {
AllMutesGroup::AllMutesGroup(Mixer::MixerComponentBase &mixer)
    : MuteGroupBase(mixer) {}
AllMutesGroup::~AllMutesGroup() = default;
void AllMutesGroup::activate() {
  if (!mixerData)
    throw std::logic_error("mute mixer data is not bound");
  for (int i = 0; i < mixerData->allMutes.count(); ++i) {
    auto *parameter = mixerData->allMutes[i];
    parameter->setValue(1.f, true);
    state.members.add(parameter);
  }
}
} // namespace Presonus
