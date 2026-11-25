#include "presonus/DAWDeviceFolder.hpp"

#include "presonus/DAWDeviceSlot.hpp"

#include <algorithm>

namespace Presonus {

DAWDeviceFolder::DAWDeviceFolder() : ClientComponent("") {}
DAWDeviceFolder::~DAWDeviceFolder() = default;

void *DAWDeviceFolder::castTo(int typeId) {
  return typeId == kTypeID ? this : ClientComponent::castTo(typeId);
}

void DAWDeviceFolder::init() {
  countParameter = getParameterByTag(0);
  countParameter->setFeedbackNeeded(true);

  const int count = countChildren();
  for (int index = 0; index < count; ++index) {
    if (auto *child = getChild(index)) {
      if (auto *slot = static_cast<DAWDeviceSlot *>(
              child->castTo(DAWDeviceSlot::kTypeID)))
        slot->init();
    }
  }
}

int DAWDeviceFolder::getUsedCount() const {
  return countParameter ? std::min(static_cast<int>(countParameter->getValue()),
                                   countChildren())
                        : 0;
}

} // namespace Presonus
