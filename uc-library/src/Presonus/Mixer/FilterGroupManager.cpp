#include "presonus/mixer/FilterGroupManager.hpp"
#include "core/public/corestringbuffer.h"
#include "presonus/uc/message_attributes.hpp"
#include <cstring>
namespace Presonus::Mixer {
FilterGroupManager::FilterGroupManager(const char *name)
    : Core::Portable::Component(name) {}
FilterGroupManager::~FilterGroupManager() = default;
void FilterGroupManager::resetChannelNames() {
  Core::Vector<Core::Portable::Component *> changed;
  changed.resize(0);
  for (int i = 0; i < countChildren(); ++i) {
    auto *child = getChild(i);
    const char *name = child->getName();
    if (std::strstr(name, "ch") != name)
      continue;
    Core::CString32 expected;
    expected.appendFormat("ch%d", i + 1);
    if (std::strcmp(expected, name) != 0) {
      child->setName(expected);
      changed.add(child);
    }
  }
  // Native observers run only after every selected name has been replaced.
  // Re-read each live parameter count, matching native synchronous traversal.
  for (int i = 0; i < changed.count(); ++i) {
    auto *child = changed.at(i);
    for (int j = 0; j < child->countParameters(); ++j)
      child->getParameterAt(j)->changed();
  }
}
void FilterGroupManager::notify(const UC::MessageAttributes &message) {
  const char *id = message.getID();
  // The native base notification has no observed effects.
  if (!id || std::strcmp(id, "ReorderChannels") != 0)
    return;

  const auto oldIndex = message.getInt("ReorderOldIndex");
  const auto newIndex = message.getInt("ReorderNewIndex");
  const int childCount = countChildren();
  // The native old-index sentinel can supply a null child. CCL mutation
  // requires a live child. Bound the destination before detaching it.
  if (oldIndex < 0 || oldIndex >= childCount || newIndex < 0 ||
      newIndex >= childCount)
    return;

  auto *child = getChild(static_cast<int>(oldIndex));
  removeChild(child);
  insertChildAt(static_cast<int>(newIndex), child);
  resetChannelNames();
}
} // namespace Presonus::Mixer
