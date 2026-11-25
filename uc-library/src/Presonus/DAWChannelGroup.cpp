#include "presonus/DAWChannelGroup.hpp"

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

void DAWChannelGroup::operator delete(void *receiver) noexcept {
  ::operator delete(receiver);
}

} // namespace Presonus
