#include "presonus/MixerClientComponentBase.hpp"
#include "presonus/SLChannel.hpp"

#include <cstring>

namespace Presonus {
Core::Portable::Component *
MixerClientComponentBase::getChannelGroup(ChannelType type) const {
  const char *name;
  switch (static_cast<int>(type)) {
  case 0:
    name = "line";
    break;
  case 1:
    name = "return";
    break;
  case 2:
    name = "fxreturn";
    break;
  case 3:
    name = "talkback";
    break;
  case 4:
    name = "aux";
    break;
  case 5:
    name = "fxbus";
    break;
  case 6:
    name = "sub";
    break;
  case 7:
    name = "main";
    break;
  case 8:
    name = "mono";
    break;
  case 10:
    name = "signalgen";
    break;
  default:
    return nullptr;
  }
  return channelGroups_->findChild(name);
}

ChannelType MixerClientComponentBase::getChannelGroupType(
    const Core::Portable::Component &group) const {
  const char *names[] = {"line", "return",   "fxreturn", "talkback",
                         "aux",  "fxbus",    "sub",      "main",
                         "mono", "signalgen"};
  for (int i = 0; i < 10; ++i)
    if (std::strcmp(group.getName(), names[i]) == 0)
      return static_cast<ChannelType>(i == 9 ? 10 : i);
  return static_cast<ChannelType>(-1);
}

SLChannelBase *MixerClientComponentBase::getSelectedChannel() const {
  if (selectedChannel_)
    return selectedChannel_;
  for (int type = 0; type < 9; ++type) {
    auto *group = getChannelGroup(static_cast<ChannelType>(type));
    if (!group)
      continue;
    for (int index = 0; index < group->countChildren(); ++index) {
      auto *channel =
          Core::Portable::core_cast<SLChannelBase>(group->getChild(index));
      if (!channel)
        continue;
      auto *selection = channel->getSelectionParameter();
      if (selection && selection->getValue() > 0.f) {
        selectedChannel_ = channel;
        break;
      }
    }
  }
  return selectedChannel_;
}
} // namespace Presonus
