#include "presonus/mixer/AutoFilterGroupManager.hpp"
#include <new>
namespace Presonus::Mixer {
AutoFilterGroupManager::~AutoFilterGroupManager() {
  const int count = ownedComponents_.count();
  for (int i = 0; i < count; ++i)
    if (auto *component = ownedComponents_[i])
      delete component;
  ownedComponents_.resize(0);
}

void AutoFilterGroupManager::addUpdateChannel(ChannelComponent *channel) {
  try {
    if (updateChannels_.count() >= updateChannels_.getCapacity() &&
        !updateChannels_.resize(updateChannels_.count() + 1))
      return;
    updateChannels_.add(channel);
  } catch (const std::bad_alloc &) {
    // Pinned CCL uses throwing new; adapt to original failed-resize no-op.
  }
}
} // namespace Presonus::Mixer
