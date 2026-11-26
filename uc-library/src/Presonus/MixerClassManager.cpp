#include "presonus/MixerClassManager.hpp"

#include <cstring>

namespace Presonus {

MixerClassManager::MixerClassManager() : classes_(0, 5) {}

MixerClassManager::~MixerClassManager() {
  for (int index = 0; index < classes_.count(); ++index)
    delete classes_.at(index);
}

const MixerClassManager::MixerClass *
MixerClassManager::getMixerClass(const char *name) const {
  const char *query = name ? name : "";
  for (int index = 0; index < classes_.count(); ++index) {
    const auto *entry = classes_.at(index);
    if (std::strcmp(query, entry->name ? entry->name : "") == 0)
      return entry;
  }
  return nullptr;
}

bool MixerClassManager::isMixerClass(const char *name) const {
  return getMixerClass(name) != nullptr;
}

} // namespace Presonus
