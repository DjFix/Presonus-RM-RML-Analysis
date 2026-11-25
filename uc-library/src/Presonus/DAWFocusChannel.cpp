#include "presonus/DAWFocusChannel.hpp"

namespace Presonus {

DAWFocusChannel::DAWFocusChannel()
    : ClientComponent(""), focusParameter_(nullptr) {}

DAWFocusChannel::~DAWFocusChannel() = default;

void *DAWFocusChannel::castTo(int typeId) {
  constexpr int focusChannelType = 0x44774643;
  if (typeId == focusChannelType)
    return this;
  return ClientComponent::castTo(typeId);
}

void DAWFocusChannel::init() {
  focusParameter_ = getParameterByTag(0);
  if (focusParameter_)
    focusParameter_->setFeedbackNeeded(true);
}

} // namespace Presonus
