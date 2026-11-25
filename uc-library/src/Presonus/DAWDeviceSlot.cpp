#include "presonus/DAWDeviceSlot.hpp"

#include "presonus/DAWDeviceFolder.hpp"

namespace Presonus {

DAWDeviceSlot::DAWDeviceSlot() : ClientComponent("") {}
DAWDeviceSlot::~DAWDeviceSlot() = default;

void *DAWDeviceSlot::castTo(int typeId) {
  return typeId == kTypeID ? this : ClientComponent::castTo(typeId);
}

void DAWDeviceSlot::init() {
  editParameter = paramList.find("edit");
  if (editParameter)
    editParameter->setFeedbackNeeded(true);
}

DAWDeviceFolder *DAWDeviceSlot::getFolder() const {
  auto *parent = getParent();
  return parent ? static_cast<DAWDeviceFolder *>(
                      parent->castTo(DAWDeviceFolder::kTypeID))
                : nullptr;
}

} // namespace Presonus
