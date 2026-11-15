#include "presonus/mixer/GroupChangeObserver.hpp"
#include "presonus/mixer/AutoFilterGroupManager.hpp"
#include "presonus/mixer/ChannelComponent.hpp"
#include <stdexcept>

namespace Presonus::Mixer {
GroupChangeObserver::GroupChangeObserver(ChannelComponent *channel,
                                         AutoFilterGroupManager &manager)
    : Component(""), channel_(channel), manager_(manager) {
  // Native has no null guards. Reject invalid portable bindings explicitly
  // instead of reproducing native undefined accesses into missing providers.
  if (!channel_)
    throw std::invalid_argument("GroupChangeObserver requires channel");
  observed_ = channel_->getParameterByTag(25);
  if (!observed_)
    throw std::invalid_argument(
        "GroupChangeObserver requires parameter tag 25");
  observed_->addObserver(this);
}
GroupChangeObserver::~GroupChangeObserver() { detachSourcePortObserver(); }
void GroupChangeObserver::detachSourcePortObserver() {
  if (observed_) {
    observed_->removeObserver(this);
    observed_ = nullptr;
  }
}
void GroupChangeObserver::paramChanged(Core::Portable::Parameter *parameter,
                                       int message) {
  if (message == Core::Portable::Parameter::kDestroyed) {
    parameter->removeObserver(this);
    if (parameter == observed_)
      observed_ = nullptr;
  } else
    manager_.addUpdateChannel(channel_);
}
} // namespace Presonus::Mixer
