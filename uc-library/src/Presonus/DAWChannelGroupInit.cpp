#include "presonus/DAWChannel.hpp"
#include "presonus/DAWChannelGroup.hpp"

namespace Presonus {

void DAWChannelGroup::init(bool removeControls) {
  cachedParameter_ = paramList.byTag(0);
  cachedParameter_->setFeedbackNeeded(true);
  for (int index = 0; index < countChildren(); ++index) {
    auto *child = getChild(index);
    if (auto *channel = static_cast<DAWChannel *>(child->castTo(0x44617743)))
      channel->init(removeControls);
  }
}

void DAWChannelGroup::onIdle() {
  const int used = getUsedCount();
  if (used <= 0)
    return;
  const int available = countChildren();
  if (available <= 0)
    return;
  for (int index = 0; index < used && index < available; ++index)
    getChild(index)->onIdle();
}

} // namespace Presonus
