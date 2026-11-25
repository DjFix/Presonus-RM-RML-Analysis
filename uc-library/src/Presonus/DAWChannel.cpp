#include "presonus/DAWChannel.hpp"

#include <new>

namespace Presonus {

DAWChannel::DAWChannel() : ClientComponent("") {}

DAWChannel::~DAWChannel() = default;

void *DAWChannel::castTo(int typeId) {
  constexpr int channelType = 0x44617743;
  if (typeId == channelType)
    return this;
  return ClientComponent::castTo(typeId);
}

void DAWChannel::operator delete(void *allocation) noexcept {
  ::operator delete(allocation);
}

} // namespace Presonus
