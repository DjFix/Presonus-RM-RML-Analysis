#include "presonus/DAWChannelGroup.hpp"

#include <algorithm>

namespace Presonus {

DAWChannelGroup::DAWChannelGroup()
    : UC::ClientComponent(""), cachedParameter_(nullptr) {}

DAWChannelGroup::~DAWChannelGroup() = default;

void *DAWChannelGroup::castTo(int typeId) {
  constexpr int groupType = 0x44774347;
  if (typeId == groupType)
    return this;
  return UC::ClientComponent::castTo(typeId);
}

int DAWChannelGroup::getUsedCount() const {
  return std::min(static_cast<int>(cachedParameter_->getValue()),
                  countChildren());
}

void DAWChannelGroup::resetUsedCount() {
  cachedParameter_->setValue(0.0f, false);
}

void DAWChannelGroup::operator delete(void *receiver) noexcept {
  ::operator delete(receiver);
}

} // namespace Presonus
