#include "core/portable/corecomponent.h"
#include "presonus/surface/FatChannelClipboard.hpp"

namespace Presonus::Surface {
namespace {
constexpr int kPasteSelectionTag = 15001;
}

void FatChannelClipboard::copy(Core::Portable::Component *source) {
  source_ = source;
  const int groupCount = roster_.count();
  for (int groupIndex = 0; groupIndex < groupCount; ++groupIndex) {
    auto *group = roster_.at(groupIndex);
    for (int childIndex = 0; childIndex < group->countChildren();
         ++childIndex) {
      auto *child = group->getChild(childIndex);
      if (auto *selection =
              child ? child->getParameterByTag(kPasteSelectionTag) : nullptr)
        selection->resetValue(false);
    }
  }
}

void FatChannelClipboard::collectPasteChannels(
    Core::Vector<Core::Portable::Component *> &channels) {
  const int groupCount = roster_.count();
  for (int groupIndex = 0; groupIndex < groupCount; ++groupIndex) {
    auto *group = roster_.at(groupIndex);
    for (int childIndex = 0; childIndex < group->countChildren();
         ++childIndex) {
      auto *child = group->getChild(childIndex);
      if (auto *selection =
              child ? child->getParameterByTag(kPasteSelectionTag) : nullptr;
          selection && selection->getValue() > 0.f)
        channels.add(child);
    }
  }
}
} // namespace Presonus::Surface
