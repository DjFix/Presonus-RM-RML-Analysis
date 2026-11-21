#include "presonus/surface/SoloPageComponent.hpp"

#include "presonus/MixerClientComponentBase.hpp"

namespace Presonus::Surface {

SoloPageComponent::~SoloPageComponent() = default;

void SoloPageComponent::clearSolos() {
  if (!mixer_)
    return;
  for (const int type : {0, 4}) {
    auto *group = mixer_->getChannelGroup(static_cast<ChannelType>(type));
    if (!group)
      continue;
    for (int index = 0; index < group->countChildren(); ++index) {
      if (auto *child = group->getChild(index))
        if (auto *solo = child->getParameterByTag(14))
          solo->resetValue(true);
    }
  }
}

void SoloPageComponent::paramChanged(Core::Portable::Parameter *parameter,
                                     int message) {
  if ((message != 1 && message != 2) || !parameter ||
      parameter->getTag() != 100)
    return;
  if (message == 1)
    parameter->resetValue(false);
  else if (parameter->getValue() > 0.f)
    clearSolos();
}

bool SoloPageComponent::addAliasReference(Core::Portable::AliasParam &alias) {
  return aliases_.add(&alias);
}

} // namespace Presonus::Surface
