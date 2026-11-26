#include "presonus/DAWChannel.hpp"

#include "presonus/DAWDeviceFolder.hpp"

#include <new>

namespace Presonus {
namespace {

DAWDeviceFolder *findFolder(const Core::Portable::Component &component,
                            const char *name) {
  auto *child = component.findChild(name);
  return child ? static_cast<DAWDeviceFolder *>(
                     child->castTo(DAWDeviceFolder::kTypeID))
               : nullptr;
}

} // namespace

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

DAWDeviceFolder *DAWChannel::getInserts() const {
  return findFolder(*this, "inserts");
}

DAWDeviceFolder *DAWChannel::getCueMixes() const {
  return findFolder(*this, "cuemix");
}

DAWDeviceFolder *DAWChannel::getPosts() const {
  return findFolder(*this, "posts");
}

DAWDeviceFolder *DAWChannel::getSends() const {
  return findFolder(*this, "sends");
}

bool DAWChannel::isSelected() const {
  const auto *parameter = cachedParameters_[selectedCache];
  return parameter && parameter->getValue() > 0;
}

const char *DAWChannel::getID() const {
  const auto *parameter = cachedParameters_[idCache];
  if (!parameter)
    return nullptr;

  static char buffer[64]{};
  parameter->toString(buffer, sizeof(buffer));
  return buffer;
}

const char *DAWChannel::getType() const {
  const auto *parameter = cachedParameters_[channelStateCache];
  if (!parameter)
    return nullptr;
  static char buffer[32]{};
  parameter->toString(buffer, sizeof(buffer));
  return buffer;
}

} // namespace Presonus
